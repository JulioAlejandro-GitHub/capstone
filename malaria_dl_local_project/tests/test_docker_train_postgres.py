"""E10.7 real worker composition + TRAIN + committed PostgreSQL, synthetic science."""
from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from sqlalchemy import text
from src.malaria_dl.campaigns.contracts import CampaignError, digest
from src.malaria_dl.execution import worker, global_gate, campaign, controlled
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.composition import build_docker_run_reporter
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.results.errors import WriterNotAuthorized
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, apply, REVISION  # noqa: F401
from test_docker_reporter_postgres import legacy_repository
from docker_train_fixture import install_science
from test_docker_train_integration import expected_types

pytestmark = [pytest.mark.requires_docker_postgres, pytest.mark.skipif(
    os.getenv('RUN_E10_TRAIN_POSTGRES_TESTS') != '1', reason='Explicit disposable-schema opt-in required')]


@pytest.fixture
def docker(pg, monkeypatch, tmp_path):
    repo = legacy_repository(pg)
    # Keep the approved fixture's immutable legacy row; reserve a clean NEW run.
    repo.finish(pg.ctx.run_id, pg.ctx.owner, 'failed', cause='SYNTHETIC_FIXTURE_SETUP')
    session = repo.claim(pg.ctx.campaign_id, str(uuid4()), 'synthetic', 1, tmp_path/'train')
    descriptor, trace = install_science(monkeypatch)
    reporters, emitters, contexts, hashes = [], [], [], []
    monkeypatch.setattr(worker, 'ExecutionRepository', lambda: repo)
    # Process authorization is covered by GlobalGate regression; here no fake
    # scientific process is registered as an operational Linux child.
    monkeypatch.setattr(global_gate, 'attach_worker', lambda: None)
    monkeypatch.setattr(global_gate, 'token', lambda: str(pg.token))
    monkeypatch.setattr(worker, 'preflight', lambda *a: None)
    monkeypatch.setattr(worker.signal, 'signal', lambda *a: None)
    monkeypatch.setattr('src.malaria_dl.models.registry.resolve_descriptor', lambda *a: descriptor)
    def build(ctx, *, execution_token):
        contexts.append(ctx)
        real = build_docker_run_reporter(ctx, execution_token=execution_token, engine_factory=pg.factory)
        class Observed:
            def report(self, event):
                before = digest(repo.records(event.run_id))
                assert repo.session(event.run_id)['state'] == 'active'
                if event.event_type not in (E.TRAINING_COMPLETED, E.TRAINING_FAILED, E.EVALUATION_COMPLETED):
                    ref = event.payload['legacy_record']
                    assert any(all(r[k] == ref[k] for k in ('kind','phase','record_key')) for r in repo.records(event.run_id))
                real.report(event)
                real.report(event)  # Actual durable retry while still authorized.
                assert digest(repo.records(event.run_id)) == before
                hashes.append(before)
        reporters.append(real)
        return Observed()
    monkeypatch.setattr(worker, 'build_docker_run_reporter', build)
    real_emitter = RunEventEmitter
    def emitter(*args, **kwargs):
        result = real_emitter(*args, **kwargs); emitters.append(result); return result
    monkeypatch.setattr(worker, 'RunEventEmitter', emitter)
    def launch(s=session, ignored=None):
        monkeypatch.setattr(sys, 'argv', ['worker', '--run-id', str(s['run_id']), '--owner', str(s['owner'])])
        return worker.main()
    from types import SimpleNamespace
    return SimpleNamespace(pg=pg, repo=repo, session=session, launch=launch, contexts=contexts,
                           emitters=emitters, reporters=reporters, hashes=hashes, trace=trace)


def test_real_worker_train_completed_then_verified(docker):
    x = docker; s = x.session
    with x.pg.sql() as c:
        parameters = c.execute(text('SELECT parameters FROM runs WHERE id=:id'), {'id': s['run_id']}).scalar_one()
    assert x.launch() == 0
    current = x.repo.session(s['run_id'])
    events = x.repo.result_events(s['run_id'])
    phases = 2 if s['configuration']['resolved']['execution']['fine_tune_epochs'] else 1
    calibrated = s['configuration']['resolved']['execution']['calibrate_threshold']
    assert [e.event_type for e in events] == expected_types(phases, calibrated)
    assert [e.sequence for e in events] == list(range(1, len(events)+1))
    assert len(x.contexts) == len(x.reporters) == len(x.emitters) == 1
    ctx = x.contexts[0]
    assert ctx.owner == s['owner'] and ctx.owner != x.pg.token
    assert ctx.run_id == s['run_id'] and ctx.attempt_id == s['attempt_id']
    assert ctx.campaign_id == x.pg.ctx.campaign_id
    assert ctx.model_id == s['configuration']['model_id']
    assert ctx.adapter_version == s['configuration']['adapter_version']
    assert ctx.dataset_version_id == x.pg.ctx.dataset_version_id
    assert ctx.contract_hash == x.pg.ctx.contract_hash
    assert x.emitters[0].closed
    assert current['completion'] == events[-1].to_dict()['payload']
    assert current['completion']['records_hash'] == x.hashes[-1] == digest(x.repo.records(s['run_id']))
    proof = verify_session(x.repo, current, lambda *a: None)
    x.repo.finish(s['run_id'], s['owner'], 'verified', proof)
    assert x.repo.session(s['run_id'])['state'] == 'verified'
    with x.pg.sql() as c:
        assert c.execute(text('SELECT parameters FROM runs WHERE id=:id'), {'id': s['run_id']}).scalar_one() == parameters | {'training_results': {'schema_version': 'training_results_v1', 'validation': events[-2].to_dict()['payload']}}
    assert x.repo.result_events(s['run_id']) == events


def test_worker_restart_rejected_before_science_or_new_emitter(docker):
    x = docker
    row = x.repo.get(x.pg.ctx.campaign_id)
    a = next(a for a in row['attempts'] if a['id'] == x.session['attempt_id'])
    m = next(m for m in row['members'] if m['id'] == a['member_id'])
    ctx = worker.docker_context(x.session, row, a, m)
    reporter = build_docker_run_reporter(ctx, execution_token=x.pg.token, engine_factory=x.pg.factory)
    RunEventEmitter(reporter, run_id=ctx.run_id, attempt_id=ctx.attempt_id).emit(E.PHASE_STARTED, {})
    with pytest.raises(CampaignError, match='E10_ACTIVE_STREAM_RECOVERY_UNSUPPORTED'):
        x.repo.preflight_result_events(ctx.run_id)
    assert x.launch() == 3
    assert not x.trace and not x.emitters
    assert len(x.repo.result_events(ctx.run_id)) == 1
    assert x.repo.session(ctx.run_id)['child_pid'] is None


def test_missing_migration_fails_before_science(docker):
    x = docker
    with x.pg.sql() as c:
        apply(c, REVISION, 'downgrade')  # Only the disposable schema; no E10 rows.
    with pytest.raises(CampaignError, match='E10_RESULT_EVENTS_MIGRATION_REQUIRED_20260922_01'):
        x.repo.preflight_result_events(x.session['run_id'])
    assert x.launch() == 3
    assert not x.trace and not x.emitters


@pytest.mark.parametrize('case', ['owner', 'legacy', 'report', 'runtime', 'finish', 'verify'])
def test_failures_never_falsely_verified(docker, monkeypatch, case):
    x = docker; s = x.session
    if case == 'owner':
        def bad(ctx, *, execution_token):
            return build_docker_run_reporter(replace(ctx, owner=uuid4()), execution_token=execution_token, engine_factory=x.pg.factory)
        monkeypatch.setattr(worker, 'build_docker_run_reporter', bad)
    elif case == 'legacy':
        put = x.repo.put
        def fail(*args):
            if args[2] == 'epoch': raise CampaignError('SYNTHETIC_LEGACY_FAILURE')
            return put(*args)
        monkeypatch.setattr(x.repo, 'put', fail)
    elif case == 'report':
        build = worker.build_docker_run_reporter
        def broken(*args, **kwargs):
            reporter = build(*args, **kwargs)
            class Fail:
                def report(self, event):
                    if event.event_type is E.EPOCH_COMPLETED:
                        reporter.report(event)  # durable commit, then lost ACK
                        raise OSError('ACK_LOST')
                    reporter.report(event)
            return Fail()
        monkeypatch.setattr(worker, 'build_docker_run_reporter', broken)
    elif case == 'runtime':
        desc, _ = install_science(monkeypatch, fit_error=ValueError('scientific failure'))
        monkeypatch.setattr('src.malaria_dl.models.registry.resolve_descriptor', lambda *a: desc)
    elif case == 'finish':
        finish = x.repo.finish
        def failed_finish(run, owner, state, *args, **kwargs):
            if state == 'completed': raise OSError('finish rejected')
            return finish(run, owner, state, *args, **kwargs)
        monkeypatch.setattr(x.repo, 'finish', failed_finish)
    code = x.launch()
    current = x.repo.session(s['run_id']); events = x.repo.result_events(s['run_id'])
    if case == 'verify':
        assert code == 0 and current['state'] == 'completed'
        def loader(*args): raise ValueError('load rejected')
        with pytest.raises(CampaignError, match='CHECKPOINT_NOT_LOADABLE'):
            verify_session(x.repo, current, loader)
        assert events[-1].event_type is E.TRAINING_COMPLETED and x.emitters[0].closed
    else:
        assert code != 0 and current['state'] == 'active'
        if case == 'finish':
            assert events[-1].event_type is E.TRAINING_COMPLETED and x.emitters[0].closed
        elif case in ('legacy', 'runtime'):
            assert events[-1].event_type is E.TRAINING_FAILED
        else:
            assert x.emitters[0].pending is not None and not x.emitters[0].closed
            assert not any(e.event_type in (E.TRAINING_COMPLETED, E.TRAINING_FAILED, E.EVALUATION_COMPLETED) for e in events)
        # Existing coordinator failure path can close the active legacy session.
        x.repo.finish(s['run_id'], s['owner'], 'failed', cause='SYNTHETIC_CHILD_EXIT')
        assert x.repo.session(s['run_id'])['state'] == 'failed'
    assert x.repo.session(s['run_id'])['state'] != 'verified'
    assert x.repo.result_events(s['run_id']) == events


def test_resume_reconciles_old_stream_and_new_run_starts_one(docker, monkeypatch, tmp_path):
    x = docker; s = x.session
    # Simulate a worker's uncertain delivery leaving an active, nonterminal stream.
    build = worker.build_docker_run_reporter
    def broken(*args, **kwargs):
        real = build(*args, **kwargs)
        class Lost:
            def report(self, event):
                real.report(event); raise OSError('lost ack')
        return Lost()
    monkeypatch.setattr(worker, 'build_docker_run_reporter', broken)
    assert x.launch() != 0
    previous_events = x.repo.result_events(s['run_id'])
    x.repo.pause(x.pg.ctx.campaign_id, 'SYNTHETIC_RESUME')
    monkeypatch.setattr(campaign, 'dead_local', lambda s: True)
    monkeypatch.setattr(worker, 'build_docker_run_reporter', build)
    launches = []
    def launch(new, repo):
        assert repo.session(s['run_id'])['state'] == 'interrupted'
        assert new['run_id'] != s['run_id'] and new['attempt_id'] != s['attempt_id']
        launches.append(new)
        code = x.launch(new)
        # Bound test: pause after one new attempt, preserving real resume/reconcile.
        repo.pause(x.pg.ctx.campaign_id, 'SYNTHETIC_ONE_RUN_LIMIT')
        return code
    assert campaign.parse_args(['--campaign-id', str(x.pg.ctx.campaign_id), '--resume']).resume
    code, _ = campaign.execute_campaign(x.repo, x.pg.ctx.campaign_id, tmp_path/'resumed', resume=True,
                                       check=lambda *a: None, launch=launch, loader=lambda *a: None)
    assert code == 0 and len(launches) == 1
    assert x.repo.result_events(launches[0]['run_id'])[0].sequence == 1
    assert x.repo.session(launches[0]['run_id'])['state'] == 'verified'
    assert x.repo.result_events(s['run_id']) == previous_events


def test_controlled_uses_same_worker_and_recover_does_not_restart(docker, monkeypatch, tmp_path):
    x = docker
    x.repo.finish(x.session['run_id'], x.session['owner'], 'failed', cause='SYNTHETIC_CONTROL_SETUP')
    repo = controlled.ControlledRepository(x.repo.scope)
    repo.pause(x.pg.ctx.campaign_id, 'SYNTHETIC_PAUSE')
    row = repo.get(x.pg.ctx.campaign_id)
    previous = next(a for a in row['attempts'] if a['id'] == x.session['attempt_id'])
    env = deepcopy(row['environment']); env['source_sha256'] = 'f'*64
    proposal = dict(original_environment=row['environment'], environment=env, contract_hash=row['contract_hash'],
                    reason='synthetic E10.7', files={'execution/worker.py':'a'*64}, tests=['synthetic'], authorization='fixture only')
    revision = str(uuid4()); repo.register_revision(row['id'], revision, proposal)
    monkeypatch.setattr(controlled, 'planning_environment', lambda: env)
    args = dict(campaign=str(row['id']), member=str(previous['member_id']), previous=str(previous['id']),
                dataset=str(row['dataset_version_id']), revision_id=revision, request_id=str(uuid4()),
                reason='fixture only', root=tmp_path/'controlled')
    result = controlled.execute_one(repo, **args, check=lambda *a: None, launch=x.launch, loader=lambda *a: None)
    assert result['state'] == 'verified' and result['launched']
    assert result['run_id'] != str(x.session['run_id'])
    events = repo.result_events(result['run_id'])
    assert events[0].sequence == 1 and events[-1].event_type is E.TRAINING_COMPLETED
    again = controlled.execute_one(repo, **args, launch=lambda *a: pytest.fail('relaunch'))
    assert not again['launched'] and again['run_id'] == result['run_id']
    recovered = repo.recover(row['id'], args['request_id'])
    assert not recovered['launched'] and recovered['state'] == 'verified'
    assert repo.result_events(result['run_id']) == events
    assert repo.get(row['id'])['state'] == 'paused'
