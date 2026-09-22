"""Private host SQLite journal; exclusive writer, FULL commits, no credentials."""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID

from ..execution.contracts import RunEvent, RunEventType
from ..execution.journal import EventJournal, EventState, JournalError


@dataclass(frozen=True, slots=True)
class StreamIdentity:
    job_id: UUID
    agent_id: UUID
    run_id: UUID
    attempt_id: UUID | None

    def __post_init__(self):
        if any(not isinstance(x, UUID) for x in (self.job_id, self.agent_id, self.run_id)) or (
                self.attempt_id is not None and not isinstance(self.attempt_id, UUID)):
            raise TypeError('STREAM_UUID_REQUIRED')

    def wire(self):
        return {k: str(v) if v is not None else None for k, v in (
            ('job_id', self.job_id), ('agent_id', self.agent_id),
            ('run_id', self.run_id), ('attempt_id', self.attempt_id))}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def state_wire(state):
    return dict(next_sequence=state.next_sequence, pending=state.pending.to_dict() if state.pending else None,
                closed=state.closed, terminal_type=state.terminal_type.value if state.terminal_type else None)


class SQLiteEventJournal(EventJournal):
    VERSION = 1

    def __init__(self, path, identity: StreamIdentity, *, create=False):
        self.path, self.identity = Path(path), identity
        self.connection = None
        self._lock = None
        self.created = False
        try:
            if not self.path.parent.exists():
                if not create: raise JournalError('LOCAL_E10_JOURNAL_REQUIRED_FOR_RECOVERY')
                self.path.parent.mkdir(parents=True, mode=0o700)
            if self.path.is_symlink() or self.path.parent.is_symlink():
                raise JournalError('EVENT_JOURNAL_SYMLINK_FORBIDDEN')
            self._lock = os.open(str(self.path)+'.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise JournalError('EVENT_JOURNAL_ALREADY_OPEN') from None
            if not self.path.exists():
                if not create: raise JournalError('LOCAL_E10_JOURNAL_REQUIRED_FOR_RECOVERY')
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                self.created = True
            os.chmod(self.path, 0o600)
            self.connection = sqlite3.connect(str(self.path), isolation_level=None, timeout=0)
            self.connection.execute('PRAGMA synchronous=FULL')
            self.connection.execute('PRAGMA fullfsync=ON')
            if self.created:
                self.connection.execute('PRAGMA journal_mode=DELETE')
                with self._transaction():
                    self.connection.execute('CREATE TABLE stream (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL, sha256 TEXT NOT NULL)')
                    self.connection.execute('PRAGMA user_version=1')
                    body = self._body(EventState())
                    self.connection.execute('INSERT INTO stream VALUES(1,?,?)', (body, self._hash(body)))
                fd = os.open(self.path.parent, os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
            self.load(identity.run_id, identity.attempt_id)
        except BaseException as exc:
            self.close()
            if isinstance(exc, (sqlite3.Error, OSError)):
                raise JournalError('EVENT_JOURNAL_UNAVAILABLE_OR_CORRUPT') from None
            raise

    @staticmethod
    def _hash(body):
        return hashlib.sha256(body.encode('ascii')).hexdigest()

    def _body(self, state):
        state.validate(self.identity.run_id, self.identity.attempt_id)
        return encoded(dict(version=self.VERSION, identity=self.identity.wire(), state=state_wire(state)))

    @contextmanager
    def _transaction(self):
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.connection.execute('COMMIT')
        except BaseException:
            if self.connection.in_transaction:
                self.connection.execute('ROLLBACK')
            raise

    def load(self, run_id, attempt_id):
        if (run_id, attempt_id) != (self.identity.run_id, self.identity.attempt_id):
            raise JournalError('EVENT_JOURNAL_IDENTITY_MISMATCH')
        try:
            if self.connection is None: raise JournalError('EVENT_JOURNAL_CLOSED')
            if self.connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError()
            if self.connection.execute('PRAGMA user_version').fetchone()[0] != self.VERSION:
                raise ValueError()
            objects = self.connection.execute("SELECT type,name FROM sqlite_master ORDER BY type,name").fetchall()
            if objects != [('table','stream')]: raise ValueError()
            if [r[1:3] for r in self.connection.execute('PRAGMA table_info(stream)')] != [('id','INTEGER'),('body','TEXT'),('sha256','TEXT')]:
                raise ValueError()
            rows = self.connection.execute('SELECT id,body,sha256 FROM stream').fetchall()
            if len(rows) != 1 or rows[0][0] != 1: raise ValueError()
            _, body, checksum = rows[0]
            if self._hash(body) != checksum: raise ValueError()
            value = json.loads(body)
            if value.keys() != {'version','identity','state'} or type(value['version']) is not int or value['version'] != self.VERSION:
                raise ValueError()
            if value['identity'] != self.identity.wire():
                raise JournalError('EVENT_JOURNAL_IDENTITY_MISMATCH')
            s = value['state']
            if s.keys() != {'next_sequence','pending','closed','terminal_type'}: raise ValueError()
            state = EventState(s['next_sequence'], RunEvent.from_dict(s['pending']) if s['pending'] is not None else None,
                               s['closed'], RunEventType(s['terminal_type']) if s['terminal_type'] else None)
            state.validate(run_id, attempt_id)
            if self._body(state) != body: raise ValueError()
            return state
        except (sqlite3.Error, ValueError, TypeError, KeyError, AttributeError, UnicodeError):
            raise JournalError('EVENT_JOURNAL_CORRUPT') from None

    def transition(self, expected, updated):
        old, new = self._body(expected), self._body(updated)
        try:
            with self._transaction():
                # Validate stored data before comparison; no blind overwrite on corruption.
                self.load(self.identity.run_id, self.identity.attempt_id)
                changed = self.connection.execute('UPDATE stream SET body=?,sha256=? WHERE id=1 AND body=? AND sha256=?',
                    (new, self._hash(new), old, self._hash(old))).rowcount
                if changed != 1: raise JournalError('EVENT_JOURNAL_STATE_CONFLICT')
        except sqlite3.Error:
            raise JournalError('EVENT_JOURNAL_COMMIT_UNCONFIRMED') from None

    def close(self):
        try:
            if self.connection is not None: self.connection.close()
        finally:
            self.connection = None
            if self._lock is not None: os.close(self._lock)
            self._lock = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
