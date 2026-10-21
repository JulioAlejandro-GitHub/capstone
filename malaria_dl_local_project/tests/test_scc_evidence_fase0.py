"""SCC-EVIDENCE Fase 0: `src.train --campaign-id` runs through the campaign coordinator.

Mocked repository and SQL only; no operational database, no TRAIN.
"""
import json
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.malaria_dl.assessment.contracts import AssessmentError
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution import campaign, local_launch, operations, repository as module, train


@pytest.fixture
def calls(monkeypatch):
    log = []
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: log.append('bootstrap'))
    monkeypatch.setattr(train, 'standalone', lambda *a: pytest.fail('campaign mode never runs standalone TRAIN'))
    monkeypatch.setattr(operations, 'training_plan', lambda *a: pytest.fail('campaign mode never expands members itself'))
    return log


@pytest.mark.parametrize('mode,expected', [
    (None, []), ('--inspect', ['--plan']), ('--plan', ['--plan']), ('--dry-run', ['--dry-run'])])
def test_campaign_only_delegates_to_the_coordinator(mode, expected, calls, monkeypatch):
    campaign_id = str(uuid4())
    def coordinator(argv):
        calls.append(argv)
        return 7
    monkeypatch.setattr(campaign, 'main', coordinator)
    assert operations.main(['--campaign-id', campaign_id, *([mode] if mode else [])]) == 7
    assert calls == ['bootstrap', ['--campaign-id', campaign_id, *expected]]


def test_coordinator_campaign_error_stops_with_exit_2(calls, monkeypatch, capsys):
    def coordinator(argv):
        raise CampaignError('CAMPAIGN_NOT_EXECUTABLE')
    monkeypatch.setattr(campaign, 'main', coordinator)
    assert operations.main(['--campaign-id', str(uuid4())]) == 2
    assert capsys.readouterr().out.strip() == 'CAMPAIGN_NOT_EXECUTABLE'


def test_source_training_run_keeps_standalone_even_inside_a_campaign(monkeypatch, capsys):
    campaign_id, source = str(uuid4()), str(uuid4())
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: None)
    monkeypatch.setattr(campaign, 'main', lambda argv: pytest.fail('reference TRAIN is not a campaign member'))
    monkeypatch.setattr(operations, 'ExecutionRepository', object)
    config = {'model_id': 'custom_cnn'}
    plan = [dict(configuration=config, dataset_version_id=str(uuid4()), campaign_id=campaign_id,
                 source_training_run_id=source)]
    monkeypatch.setattr(operations, 'training_plan', lambda repo, c, t: plan if (c, t) == (campaign_id, source) else None)
    created = []
    def standalone(args):
        created.append(args)
        return {'run_id': 'new-run', 'state': 'verified'}
    monkeypatch.setattr(train, 'standalone', standalone)
    assert operations.main(['--campaign-id', campaign_id, '--source-training-run-id', source]) == 0
    assert json.loads(capsys.readouterr().out) == [
        {'source_training_run_id': source, 'run_id': 'new-run', 'state': 'verified'}]
    assert created[0].campaign_id == campaign_id and created[0].output_dir == 'outputs/train_runs'


def test_training_plan_only_expands_a_source_training_run():
    with pytest.raises(AssessmentError, match='SOURCE_TRAINING_RUN_REQUIRED'):
        operations.training_plan(object(), str(uuid4()), None)


def test_bootstrap_precedes_both_engines():
    source = operations.__file__
    text = open(source, encoding='utf-8').read()
    assert text.index('bootstrap()') < text.index('from . import campaign')
    assert text.index('bootstrap()') < text.index('from .train import standalone')


@pytest.mark.parametrize('state', ['draft', 'paused', 'finalized'])
def test_claim_requires_an_executable_campaign(state, monkeypatch):
    repo = module.ExecutionRepository(lambda **kw: nullcontext(None))
    monkeypatch.setattr(repo, '_campaign', lambda c, cid, lock: {'state': state})
    with pytest.raises(CampaignError, match='CAMPAIGN_NOT_EXECUTABLE'):
        repo.claim(str(uuid4()), str(uuid4()), 'host', 1, '/tmp/root')


def test_claim_never_selects_verified_members_and_respects_budget(monkeypatch):
    """Rerunning a campaign only reserves pending/failed/interrupted members within budget."""
    repo = module.ExecutionRepository(lambda **kw: nullcontext(None))
    monkeypatch.setattr(repo, '_campaign', lambda c, cid, lock: {
        'state': 'active', 'protocol': {'budget': {'max_attempts_per_member': 3}}})
    statements = []
    def execute(connection, sql, **params):
        statements.append((sql, params))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(one_or_none=lambda: None))
    monkeypatch.setattr(module, 'execute', execute)
    assert repo.claim(str(uuid4()), str(uuid4()), 'host', 1, '/tmp/root') is None
    sql, params = statements[0]
    assert "state IN ('pending','failed','interrupted')" in sql
    assert '<:budget' in sql and params['budget'] == 3
    assert 'verified' not in sql
    assert not any('INSERT' in s for s, _ in statements)


def test_coordinator_entry_runs_the_frozen_campaign_with_resume(monkeypatch, capsys):
    """`src.train --campaign-id` reaches execute_campaign under the global gate, not standalone."""
    campaign_id = str(uuid4())
    row = {'id': campaign_id, 'dataset_version_id': str(uuid4()), 'state': 'frozen', 'members': [],
           'environment': {}}
    class Repo:
        def get(self, cid, dataset=None):
            assert cid == campaign_id
            return row
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: None)
    monkeypatch.setattr(train, 'standalone', lambda *a: pytest.fail('no standalone TRAIN'))
    monkeypatch.setattr(campaign, 'ExecutionRepository', Repo)
    monkeypatch.setattr(campaign, 'runtime_environment', lambda: {
        'execution_mode': 'local_python', 'platform': 'Darwin', 'machine': 'arm64'})
    gates = []
    class Gate:
        def __init__(self, name):
            gates.append(name)
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False
    from src.malaria_dl.execution import global_gate
    monkeypatch.setattr(global_gate, 'GlobalGate', Gate)
    received = {}
    def execute_campaign(repo, cid, root, **kwargs):
        received.update(cid=cid, root=root, **kwargs)
        return 0, {'state': 'finalized', 'expected': 0,
                   'members': {'verified': 0, 'failed': 0, 'interrupted': 0, 'pending': 0}}
    monkeypatch.setattr(campaign, 'execute_campaign', execute_campaign)
    assert operations.main(['--campaign-id', campaign_id]) == 0
    assert gates == ['campaign']
    assert received['cid'] == campaign_id and received['resume'] is True
    assert received['dataset'] == row['dataset_version_id']
    assert received['root'].parts[-2:] == ('outputs', 'campaign_runs')
