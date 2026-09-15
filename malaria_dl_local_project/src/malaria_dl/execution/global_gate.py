"""Global experimental execution fence, Linux process barrier and resource circuit.

An advisory lock serializes coordinators; durable process identity prevents a
released DB connection from authorizing work while an orphan is still alive.
No timeout/lease expiry is treated as proof that a process died.
"""
from contextvars import ContextVar
from pathlib import Path
import ctypes
import json
import os
import socket
import time
from uuid import uuid4

from sqlalchemy import text
from ..campaigns.contracts import CampaignError
from ..persistence.database import get_engine

LOCK_NAMESPACE = 120994
LOCK_ID = 1
POLICY = {'version': 'e93_sequential_v1', 'minimum_available_bytes': 1024**3,
          'pause_after_consecutive_failures': 2, 'pause_on_new_oom_kill': True}
CURRENT = ContextVar('capstone_global_execution', default=None)


def token():
    gate = CURRENT.get()
    return gate.owner if gate else os.getenv('CAPSTONE_EXECUTION_TOKEN')


def process_table():
    result = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            result[int(path.name)] = {
                'pid': int(path.name), 'ppid': int(fields[1]),
                'session': int(fields[3]), 'start_ticks': fields[19],
                'state': fields[0],
            }
        except FileNotFoundError:
            continue
        except OSError:
            raise CampaignError('PROCESS_VISIBILITY_REQUIRED') from None
    return result


def host_identity():
    return {'host': socket.gethostname(),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def process_identity(pid):
    row = process_table().get(pid)
    return {**host_identity(), 'pid': pid,
            'start_ticks': row['start_ticks'] if row else None}


def managed_execution(args):
    words = [arg.decode(errors='replace') if isinstance(arg, bytes) else arg for arg in args]
    names = {Path(word).name for word in words if word}
    if 'run_train_all_models.py' in names:
        return not any(flag in words for flag in ('--inspect', '--result', '--dry-run'))
    if 'src.malaria_dl.execution.controlled' in words:
        return any(operation in words for operation in ('execute', 'recover'))
    return bool(names & {'run_evaluate_all_trainings.py', 'run_explain_all_trainings.py', 'train.py'}
                or set(words) & {'src.malaria_dl.execution.worker', 'src.train',
                                 'src.malaria_dl.training.cli', 'src.evaluate', 'src.explain'})


def process_absent(identity, table=None):
    if any(identity.get(k) != v for k, v in host_identity().items()):
        raise CampaignError('REMOTE_PROCESS_ABSENCE_UNPROVEN')
    table = process_table() if table is None else table
    actual = table.get(identity['pid'])
    return actual is None or (identity.get('start_ticks') is not None
                              and actual['start_ticks'] != identity['start_ticks'])


def descendants(table, parent):
    found = set()
    pending = {parent}
    while pending:
        children = {pid for pid, row in table.items() if row['ppid'] in pending} - found
        found.update(children)
        pending = children
    return found


def resources():
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemAvailable:', 'MemTotal:'))}
    events = dict(line.split() for line in Path('/sys/fs/cgroup/memory.events').read_text().splitlines())
    current = int(Path('/sys/fs/cgroup/memory.current').read_text())
    maximum = Path('/sys/fs/cgroup/memory.max').read_text().strip()
    available = memory['MemAvailable']
    if maximum != 'max':
        available = min(available, max(0, int(maximum) - current))
    return {'available_bytes': available, 'cgroup_current_bytes': current,
            'cgroup_max': maximum, 'oom_kill': int(events['oom_kill'])}


def assert_available(value):
    if value['available_bytes'] < POLICY['minimum_available_bytes']:
        raise CampaignError('INSUFFICIENT_MEMORY_HEADROOM')


def verify_retained_processes(evidence):
    if not evidence:
        return
    table = process_table()
    for identity in evidence.get('identities', []):
        if not process_absent(identity, table):
            raise CampaignError('PREVIOUS_EXPERIMENT_PROCESS_STILL_ALIVE')
    for sid in evidence.get('sessions', []):
        if any(p['session'] == sid for p in table.values()):
            raise CampaignError('PREVIOUS_EXPERIMENT_DESCENDANTS_STILL_ALIVE')
    if evidence.get('release_confirmed') is False:
        raise CampaignError('PROCESS_TREE_RELEASE_UNPROVEN')


class GlobalGate:
    def __init__(self, kind, acknowledge=False, engine_factory=get_engine):
        self.kind = kind
        self.acknowledge = acknowledge
        self.engine_factory = engine_factory
        self.owner = str(uuid4())
        self.engine = self.connection = None
        self.reset = None
        self.children = []
        self.sessions = []
        self.active_run = None
        self.failures = 0
        self.baseline = None
        self.blocked = None
        self.locked = self.owned = False

    def sql(self, statement, **params):
        value = self.connection.execute(text(statement), params)
        self.connection.commit()
        return value

    def event(self, event, **payload):
        self.sql('INSERT INTO experiment_execution_events(owner,event,payload) '
                 'VALUES(CAST(:owner AS uuid),:event,CAST(:payload AS jsonb))',
                 owner=self.owner, event=event,
                 payload=json.dumps({'policy': POLICY, **payload}))

    def __enter__(self):
        if CURRENT.get() is not None:
            raise CampaignError('NESTED_COORDINATOR_FORBIDDEN')
        self.engine = self.engine_factory()
        self.connection = self.engine.connect()
        try:
            if not self.sql("SELECT to_regclass('experiment_execution_gate') IS NOT NULL").scalar_one():
                raise CampaignError('GLOBAL_EXECUTION_MIGRATION_REQUIRED')
            if not self.sql('SELECT pg_try_advisory_lock(:namespace,:key)', namespace=LOCK_NAMESPACE, key=LOCK_ID).scalar_one():
                raise CampaignError('GLOBAL_EXPERIMENT_BUSY')
            self.locked = True
            row = self.sql('SELECT * FROM experiment_execution_gate WHERE singleton').mappings().one()
            verify_retained_processes(row['process_evidence'])
            # Reject legacy managed processes even when no durable gate was recorded.
            for pid in process_table():
                if pid == os.getpid():
                    continue
                try:
                    args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                    if managed_execution(args):
                        raise CampaignError('UNREGISTERED_COORDINATOR_OR_WORKER_ALIVE')
                except FileNotFoundError:
                    pass
            assert_available(resources())
            if row['blocked_reason'] and not self.acknowledge:
                raise CampaignError('GLOBAL_RESOURCE_CIRCUIT_REQUIRES_ACK')
            # Adopt orphaned descendants, including children that create a new SID.
            if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
                raise CampaignError('PROCESS_SUBREAPER_REQUIRED')
            parent = process_identity(os.getpid())
            self.sql("UPDATE experiment_execution_gate SET owner=CAST(:owner AS uuid),"
                     "db_pid=pg_backend_pid(),process_evidence=CAST(:process AS jsonb),"
                     "blocked_reason=NULL,updated_at=clock_timestamp() WHERE singleton",
                     owner=self.owner, process=json.dumps({'identities': [parent], 'sessions': [], 'release_confirmed': True}))
            self.owned = True
            self.sql("SELECT set_config('capstone.execution_token',:token,false)", token=self.owner)
            self.reset = CURRENT.set(self)
            self.baseline = resources()
            self.event('acquired', kind=self.kind, process=parent,
                       acknowledgement=self.acknowledge, resources=self.baseline)
            return self
        except BaseException as original:
            try:
                self.close()
            except Exception:
                original.add_note('GLOBAL_GATE_CLEANUP_UNCONFIRMED')
            raise

    def require_healthy(self):
        if self.blocked:
            raise CampaignError(self.blocked)
        # Querying the owning connection also detects a lost global DB lock.
        if self.sql('SELECT owner::text FROM experiment_execution_gate WHERE singleton').scalar_one() != self.owner:
            raise CampaignError('GLOBAL_EXECUTION_OWNER_LOST')
        self.sql('SELECT experiment_require_owner()')
        now = resources()
        if self.baseline and now['oom_kill'] > self.baseline['oom_kill']:
            self.blocked = 'NEW_CONTAINER_OOM_PAUSE'
            self.sql('UPDATE experiment_execution_gate SET blocked_reason=:reason WHERE singleton', reason=self.blocked)
            raise CampaignError(self.blocked)
        assert_available(now)

    def child_started(self, pid):
        identity = process_identity(pid)
        self.children.append(identity)
        self.sessions.append(pid)  # Every owned subprocess uses start_new_session.
        self.sql('UPDATE experiment_execution_gate SET process_evidence=CAST(:e AS jsonb),'
                 'updated_at=clock_timestamp() WHERE singleton AND owner=CAST(:owner AS uuid)',
                 owner=self.owner, e=json.dumps({'identities': [process_identity(os.getpid()), *self.children],
                                                'sessions': self.sessions, 'release_confirmed': False}))
        self.event('process_started', run_id=self.active_run, process=identity)

    def after_wait(self, pid, code, phase):
        # The primary child was already wait()ed. Reap adopted exited descendants.
        while True:
            try:
                child, _ = os.waitpid(-1, os.WNOHANG)
                if not child:
                    break
            except ChildProcessError:
                break
        table = process_table()
        remaining = sorted(descendants(table, os.getpid()) |
                           {p for p, row in table.items() if row['session'] in self.sessions})
        now = resources()
        delta = now['oom_kill'] - self.baseline['oom_kill']
        if remaining:
            self.blocked = 'EXPERIMENT_DESCENDANTS_NOT_RELEASED'
        elif delta > 0:
            self.blocked = 'NEW_CONTAINER_OOM_PAUSE'
        elif now['available_bytes'] < POLICY['minimum_available_bytes']:
            self.blocked = 'INSUFFICIENT_MEMORY_HEADROOM'
        self.event('process_exit', pid=pid, exit_code=code, phase=phase,
                   run_id=self.active_run,
                   remaining_pids=remaining, resources=now, oom_kill_delta=delta,
                   individual_oom_attribution='not established')
        self.sql('UPDATE experiment_execution_gate SET process_evidence=CAST(:e AS jsonb) WHERE singleton AND owner=CAST(:owner AS uuid)',
                 owner=self.owner, e=json.dumps({'identities': [process_identity(os.getpid()), *self.children],
                                                'sessions': self.sessions, 'release_confirmed': not remaining}))
        if self.blocked:
            self.sql('UPDATE experiment_execution_gate SET blocked_reason=:reason WHERE singleton', reason=self.blocked)
        self.baseline = now
        return not remaining

    def outcome(self, success):
        self.failures = 0 if success else self.failures + 1
        if self.failures >= POLICY['pause_after_consecutive_failures']:
            self.blocked = self.blocked or 'CONSECUTIVE_EXPERIMENT_FAILURES'
            self.sql('UPDATE experiment_execution_gate SET blocked_reason=:reason WHERE singleton', reason=self.blocked)
        self.event('experiment_outcome', run_id=self.active_run, success=success, consecutive_failures=self.failures)
        self.require_healthy()

    def close(self):
        if self.reset is not None:
            CURRENT.reset(self.reset)
            self.reset = None
        if self.connection is not None:
            try:
                if self.owned:
                    table = process_table()
                    alive = descendants(table, os.getpid()) | {
                        pid for pid, row in table.items() if row['session'] in self.sessions
                    }
                    # Persist escaped descendants before this subreaper exits.
                    evidence = {'identities': [process_identity(os.getpid()),
                                               *[process_identity(pid) for pid in sorted(alive)]],
                                'sessions': self.sessions, 'release_confirmed': not alive}
                    self.sql('UPDATE experiment_execution_gate SET process_evidence=CAST(:e AS jsonb) WHERE singleton AND owner=CAST(:owner AS uuid)',
                             owner=self.owner, e=json.dumps(evidence))
                    self.sql('UPDATE experiment_execution_gate SET owner=NULL,db_pid=NULL WHERE singleton AND owner=CAST(:owner AS uuid)', owner=self.owner)
                if self.locked:
                    self.sql('SELECT pg_advisory_unlock(:namespace,:key)', namespace=LOCK_NAMESPACE, key=LOCK_ID)
            finally:
                self.connection.close()
                self.engine.dispose()
                self.connection = None

    def __exit__(self, *exc):
        try:
            self.close()
        except Exception:
            if exc[1] is None:
                raise
            exc[1].add_note('GLOBAL_GATE_CLEANUP_UNCONFIRMED')


def attach_worker():
    """The worker shares the coordinator's token but never acquires another lock."""
    start_fd = os.getenv('CAPSTONE_START_FD')
    if start_fd is not None:
        fd = int(start_fd)
        if os.read(fd, 1) != b'1':
            raise CampaignError('COORDINATOR_START_NOT_AUTHORIZED')
        os.close(fd)
    if not token():
        raise CampaignError('GLOBAL_EXECUTION_TOKEN_REQUIRED')
    engine = get_engine()
    try:
        with engine.begin() as c:
            c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), {'token': token()})
            c.execute(text('SELECT experiment_require_owner()'))
            evidence = c.execute(text('SELECT process_evidence FROM experiment_execution_gate WHERE singleton')).scalar_one()
            current = process_identity(os.getpid())
            if current not in evidence.get('identities', []):
                raise CampaignError('WORKER_PROCESS_NOT_REGISTERED')
    finally:
        engine.dispose()


def status(repository):
    """Read-only eligibility; an observation is not a reservation."""
    with repository.transaction(readonly=True) as c:
        installed = c.execute(text("SELECT to_regclass('experiment_execution_gate') IS NOT NULL")).scalar_one()
        if not installed:
            return {'installed': False, 'available': False, 'reason': 'GLOBAL_EXECUTION_MIGRATION_REQUIRED'}
        row = c.execute(text('SELECT * FROM experiment_execution_gate WHERE singleton')).mappings().one()
        active = c.execute(text("SELECT (SELECT count(*) FROM train_execution_sessions WHERE state IN ('active','completed')) + (SELECT count(*) FROM assessment_attempts WHERE state='active')")).scalar_one()
    try:
        mine = token() and str(row['owner']) == token()
        if not mine:
            verify_retained_processes(row['process_evidence'])
        assert_available(resources())
        reason = row['blocked_reason'] or ('GLOBAL_EXPERIMENT_BUSY' if row['owner'] and not mine else None)
        reason = reason or ('GLOBAL_EXPERIMENT_RECORD_ACTIVE' if active else None)
    except CampaignError as exc:
        reason = str(exc)
    return {'installed': True, 'available': reason is None, 'reason': reason,
            'active_records': active, 'policy': POLICY}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['ack-breaker'])
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    if not args.reason.strip():
        parser.error('reason required')
    with GlobalGate('resource-circuit-acknowledgement', acknowledge=True) as gate:
        gate.event('operator_acknowledgement', reason=args.reason)
    print(json.dumps({'acknowledged': True, 'experiment_launched': False}))

if __name__ == '__main__':
    main()
