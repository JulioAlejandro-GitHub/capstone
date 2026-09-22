"""E10.7 actual TRAIN with deterministic scientific doubles and failure boundaries."""
from copy import deepcopy
from pathlib import Path
import shutil
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from src.malaria_dl.campaigns.contracts import CampaignError, digest
from src.malaria_dl.execution import train as train_module
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.worker import run_scientific_train
from test_campaign_executor_e5 import evidence
from docker_train_fixture import install_science, MemoryRepository


class Recorder:
    def __init__(self, trace, error_type=None):
        self.trace, self.events, self.error_type = trace, [], error_type
    def report(self, event):
        if event.event_type == self.error_type:
            raise RuntimeError('E10_REPORT_FAILED')
        self.events.append(event)
        self.trace.append(('event', event.event_type.value))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    session, _ = evidence(tmp_path)
    session.update(owner=str(uuid4()), attempt_id=str(uuid4()), state='active', artifact_root=str(tmp_path/'run'))
    session['configuration']['resolved']['execution'].update(seed=11, max_epochs=2, fine_tune_epochs=2, calibrate_threshold=False)
    descriptor, trace = install_science(monkeypatch)
    repo = MemoryRepository(session, trace)
    reporter = Recorder(trace)
    emitter = RunEventEmitter(reporter, run_id=UUID(session['run_id']), attempt_id=UUID(session['attempt_id']))
    return session, descriptor, trace, repo, reporter, emitter


def expected_types(phases=2, calibrated=False):
    epoch = [E.EPOCH_COMPLETED, E.ARTIFACT_PREPARED, E.ARTIFACT_CREATED, E.SELECTION_COMPLETED, E.PREDICTIONS_COMPLETED]
    return ([E.PHASE_STARTED, *epoch, *epoch, E.PHASE_COMPLETED] * phases
            + ([E.CALIBRATION_COMPLETED] if calibrated else []) + [E.EVALUATION_COMPLETED, E.TRAINING_COMPLETED])


@pytest.mark.parametrize('calibrated', [False, True])
def test_success_mapping_order_and_verification(setup, calibrated):
    s, desc, trace, repo, reporter, emitter = setup
    s['configuration']['resolved']['execution']['calibrate_threshold'] = calibrated
    run_scientific_train(repo, s, desc, emitter)
    events = reporter.events
    assert [e.event_type for e in events] == expected_types(calibrated=calibrated)
    assert [e.sequence for e in events] == list(range(1, len(events)+1))
    assert all(e.run_id == UUID(s['run_id']) and e.attempt_id == UUID(s['attempt_id']) for e in events)
    for index, entry in enumerate(trace):
        if entry[0] == 'event' and entry[1] not in ('training_completed', 'evaluation_completed'):
            assert trace[index-1][0] == 'legacy'
    rows = {(r['kind'], r['phase'], r['record_key']): r['payload'] for r in repo.rows}
    for ev in events[:-2]:
        wire = ev.to_dict()['payload']
        ref = wire['legacy_record']
        payload = rows[(ref['kind'], ref['phase'], ref['record_key'])]
        if ref['kind'] in ('epoch', 'artifact_prepared', 'artifact', 'selection', 'phase'):
            assert wire['result'] == payload
        elif ref['kind'] == 'predictions':
            assert wire['result'] == {k: payload[k] for k in ('epoch', 'role')}
            assert 'samples' not in wire['result']
        elif ref['kind'] == 'calibration':
            assert wire['result']['result'] == payload['result']
        else:
            assert wire['result']['callbacks'] == payload['callbacks']
    assert trace[-3:] == [('hash_read',), ('event', 'training_completed'), ('finish', 'completed')]
    assert emitter.closed and emitter.pending is None
    assert events[-1].to_dict()['payload'] == s['completion']
    assert verify_session(repo, s, lambda *a: None)['records_hash'] == s['completion']['records_hash']
    assert not list(Path(s['artifact_root']).glob('*.partial.keras'))
    assert events[-2].event_type is E.EVALUATION_COMPLETED


@pytest.mark.parametrize('mode', ['legacy', 'e10'])
def test_exact_pre_e10_7_baseline_equivalence(setup, monkeypatch, mode):
    s, desc, trace, repo, reporter, emitter = setup
    # Capture the committed implementation, not a second reimplementation of TRAIN.
    source = (Path(__file__).parent / 'fixtures/e10_6_train.py').read_text()
    baseline = ModuleType('src.malaria_dl.execution.baseline_train')
    baseline.__package__ = 'src.malaria_dl.execution'
    exec(compile(source, '<committed pre-E10.7 train>', 'exec'), baseline.__dict__)
    fixed_uuid = UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    baseline.uuid4 = lambda: fixed_uuid
    monkeypatch.setattr(train_module, 'uuid4', lambda: fixed_uuid)
    original = deepcopy(s)
    baseline.train(repo, s, desc)
    before_records, before_completion = repo.records(s['run_id']), deepcopy(s['completion'])
    before_artifacts = {p.name: p.read_bytes() for p in Path(s['artifact_root']).iterdir()}
    shutil.rmtree(s['artifact_root'])  # This test's own temporary files only.
    s.clear(); s.update(original); repo.rows.clear(); trace.clear()
    train_module.train(repo, s, desc, **({'event_emitter': emitter} if mode == 'e10' else {}))
    assert repo.records(s['run_id']) == before_records
    assert s['completion'] == before_completion
    assert digest(repo.records(s['run_id'])) == before_completion['records_hash']
    assert {p.name: p.read_bytes() for p in Path(s['artifact_root']).iterdir()} == before_artifacts
    assert bool(reporter.events) == (mode == 'e10')


@pytest.mark.parametrize('kind', ['runtime', 'epoch', 'artifact_prepared', 'artifact', 'selection', 'predictions', 'phase', 'calibration'])
def test_legacy_failure_does_not_emit_corresponding_success(setup, kind):
    s, desc, trace, repo, reporter, emitter = setup
    repo.fail_kind = kind
    with pytest.raises(RuntimeError, match='LEGACY_WRITE_FAILED'):
        run_scientific_train(repo, s, desc, emitter)
    assert not any(e.payload.get('legacy_record', {}).get('kind') == kind for e in reporter.events)
    assert reporter.events[-1].event_type is E.TRAINING_FAILED
    assert emitter.closed and s['state'] == 'active'
    assert not any(t[0] == 'finish' for t in trace)


@pytest.mark.parametrize('kind', [E.PHASE_STARTED, E.EPOCH_COMPLETED, E.ARTIFACT_PREPARED,
    E.ARTIFACT_CREATED, E.SELECTION_COMPLETED, E.PREDICTIONS_COMPLETED, E.PHASE_COMPLETED,
    E.CALIBRATION_COMPLETED, E.EVALUATION_COMPLETED, E.TRAINING_COMPLETED])
def test_report_failure_stops_and_keeps_pending(setup, kind):
    s, desc, trace, repo, reporter, emitter = setup
    s['configuration']['resolved']['execution']['calibrate_threshold'] = True
    reporter.error_type = kind
    with pytest.raises(RuntimeError, match='E10_REPORT_FAILED'):
        run_scientific_train(repo, s, desc, emitter)
    assert emitter.pending.event_type is kind and not emitter.closed
    assert not any(t[0] == 'finish' for t in trace)
    assert not any(e.event_type is E.TRAINING_FAILED for e in reporter.events)
    assert emitter.next_sequence == len(reporter.events)+1


@pytest.mark.parametrize('failure_delivery', [False, True])
def test_runtime_failure_preserves_original_even_failed_delivery(setup, monkeypatch, failure_delivery):
    s, _, trace, repo, reporter, emitter = setup
    original = ValueError('sensitive runtime message must not enter event')
    desc, _ = install_science(monkeypatch, fit_error=original)
    if failure_delivery:
        reporter.error_type = E.TRAINING_FAILED
    with pytest.raises(ValueError) as caught:
        run_scientific_train(repo, s, desc, emitter)
    assert caught.value is original
    event = emitter.pending if failure_delivery else reporter.events[-1]
    assert event.event_type is E.TRAINING_FAILED
    assert event.to_dict()['payload'] == {'cause': 'TRAIN_RUNTIME_FAILED'}
    assert emitter.closed is not failure_delivery


def test_finish_failure_keeps_completed_terminal_and_original(setup):
    s, desc, trace, repo, reporter, emitter = setup
    original = OSError('finish failed')
    repo.finish_error = original
    with pytest.raises(OSError) as caught:
        run_scientific_train(repo, s, desc, emitter)
    assert caught.value is original and emitter.closed
    assert reporter.events[-1].event_type is E.TRAINING_COMPLETED
    assert s['state'] == 'active' and 'verification' not in s


def test_verify_failure_does_not_reopen_stream(setup):
    s, desc, trace, repo, reporter, emitter = setup
    run_scientific_train(repo, s, desc, emitter)
    def loader(*args):
        raise ValueError('cannot load')
    with pytest.raises(CampaignError, match='CHECKPOINT_NOT_LOADABLE'):
        verify_session(repo, s, loader)
    assert s['state'] == 'completed' and emitter.closed
    assert reporter.events[-1].event_type is E.TRAINING_COMPLETED


def context_inputs(session):
    campaign, member = uuid4(), uuid4()
    session['state'] = 'active'
    row = dict(id=campaign, state='active', dataset_version_id=UUID(session['dataset']['dataset_version_id']), contract_hash='a'*64)
    attempt = dict(id=UUID(session['attempt_id']), state='active', training_run_id=UUID(session['run_id']), member_id=member)
    member_row = dict(id=member, campaign_id=campaign, state='active', configuration_hash='b'*64)
    return row, attempt, member_row


def test_context_fields_come_from_reserved_session_and_lineage(setup):
    from src.malaria_dl.execution.worker import docker_context
    from src.malaria_dl.execution.contracts import ExecutionMode
    s, *_ = setup
    row, a, m = context_inputs(s)
    c = docker_context(s, row, a, m)
    assert c.run_id == UUID(s['run_id']) and c.owner == UUID(s['owner'])
    assert c.attempt_id == a['id'] and c.member_id == m['id'] and c.campaign_id == row['id']
    assert c.configuration_hash == m['configuration_hash'] and c.contract_hash == row['contract_hash']
    assert c.model_id == s['configuration']['model_id'] and c.adapter_version == s['configuration']['adapter_version']
    assert c.execution_mode is ExecutionMode.DOCKER and str(c.dataset_version_id) == s['dataset']['dataset_version_id']


@pytest.mark.parametrize('target,key,value', [
    ('session','state','completed'), ('attempt','id',uuid4()), ('attempt','state','failed'),
    ('attempt','training_run_id',uuid4()), ('attempt','member_id',uuid4()),
    ('member','campaign_id',uuid4()), ('member','state','verified'),
    ('row','dataset_version_id',uuid4()), ('row','state','finalized'),
])
def test_context_rejects_incoherent_lineage(setup, target, key, value):
    from src.malaria_dl.execution.worker import docker_context
    s, *_ = setup
    row, a, m = context_inputs(s)
    {'session':s, 'attempt':a, 'member':m, 'row':row}[target][key] = value
    with pytest.raises(CampaignError, match='CHILD_FROZEN_IDENTITY_CONFLICT'):
        docker_context(s, row, a, m)
