"""Local composition and transport recovery; never resumes scientific calculation."""
from copy import deepcopy
from pathlib import Path
from uuid import UUID

from ..execution.contracts import RunEventType
from ..execution.emitter import RunEventEmitter
from ..execution.journal import JournalError
from .event_client import build_http_run_reporter
from .event_journal import SQLiteEventJournal, StreamIdentity
from .event_transport import RemoteExecutionIdentity
from .storage import resolve


def stream_identity(job):
    session = job['session']
    if job['run_id'] != session['run_id']:
        raise JournalError('LOCAL_EVENT_RUN_CONFLICT')
    return StreamIdentity(UUID(job['job_id']), UUID(job['agent_id']), UUID(session['run_id']),
                          UUID(session['attempt_id']) if session.get('attempt_id') else None)


def journal_path(state_path, job):
    identity = stream_identity(job)
    return Path(state_path).absolute().parent / 'e10_journals' / (str(identity.job_id)+'_'+str(identity.run_id)+'.sqlite3')


def check_remote(api, identity, state=None):
    remote = api.call('event-state', {'job_id':str(identity.job_id),'agent_id':str(identity.agent_id)})
    fields = {'run_id','attempt_id','last_sequence','last_event_id','terminal_type','legacy_exists'}
    if (type(remote) is not dict or remote.keys() != fields
            or remote['run_id'] != str(identity.run_id)
            or remote['attempt_id'] != (str(identity.attempt_id) if identity.attempt_id else None)
            or type(remote['last_sequence']) is not int or remote['last_sequence'] < 0
            or type(remote['legacy_exists']) is not bool):
        raise JournalError('LOCAL_EVENT_STATE_INVALID')
    last = remote['last_sequence']
    if state is None:
        if last or remote['legacy_exists'] or remote['terminal_type'] or remote['last_event_id']:
            raise JournalError('LOCAL_E10_JOURNAL_REQUIRED_FOR_RECOVERY')
        return
    accepted_pending = (state.pending is not None and last == state.next_sequence
                        and remote['last_event_id'] == str(state.pending.event_id))
    if not accepted_pending and last != state.next_sequence-1:
        raise JournalError('LOCAL_EVENT_JOURNAL_DIVERGED')
    terminal = state.terminal_type.value if state.terminal_type else None
    if accepted_pending and state.pending.event_type in (RunEventType.TRAINING_COMPLETED, RunEventType.TRAINING_FAILED):
        terminal = state.pending.event_type.value
    if remote['terminal_type'] != terminal:
        raise JournalError('LOCAL_EVENT_JOURNAL_DIVERGED')


def prepare_payload(job, artifact_root):
    def prepare(payload):
        value = deepcopy(payload)
        result = value.get('result')
        if isinstance(result, dict) and 'path' in result:
            path = Path(result['path'])
            relative = path.relative_to(Path(artifact_root).resolve()).as_posix()
            if resolve(artifact_root, relative) != path.resolve():
                raise JournalError('LOCAL_EVENT_ARTIFACT_ROOT_CONFLICT')
            result['path'] = {'root_id':job['artifact_root_id'], 'relative_path':relative}
        return value
    return prepare


def compose(api, job, path, artifact_root):
    identity = stream_identity(job)
    # Check remote history before creating ANY new journal. Existing empty/corrupt
    # files are opened, never deleted/reinitialized. The exclusive lock prevents
    # concurrent worker/recovery users of an existing path.
    if not Path(path).exists():
        check_remote(api, identity)
    journal = SQLiteEventJournal(path, identity, create=True)
    try:
        state = journal.load(identity.run_id, identity.attempt_id)
        if not state.closed:
            check_remote(api, identity, state)
        reporter = build_http_run_reporter(api.url.removesuffix('/execution/local'), api.bearer,
            RemoteExecutionIdentity(job_id=identity.job_id, agent_id=identity.agent_id), timeout=api.timeout)
        emitter = RunEventEmitter(reporter, run_id=identity.run_id, attempt_id=identity.attempt_id,
                                  journal=journal, prepare_payload=prepare_payload(job, artifact_root))
        return journal, emitter
    except BaseException:
        journal.close()
        raise


def recover_pending(api, job, path, artifact_root):
    """Explicit transport recovery before exit reconciliation; no TRAIN call."""
    if not Path(path).exists():
        check_remote(api, stream_identity(job))
        raise JournalError('LOCAL_E10_JOURNAL_REQUIRED_FOR_RECOVERY')
    journal, emitter = compose(api, job, path, artifact_root)
    with journal:
        if emitter.pending is not None:
            emitter.retry_pending()


def has_pending(path, job):
    if not Path(path).exists():
        return False
    identity = stream_identity(job)
    with SQLiteEventJournal(path, identity) as journal:
        return journal.load(identity.run_id, identity.attempt_id).pending is not None
