"""Fixed legacy bytes and verifier regression, without changing stored evidence."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from src.malaria_dl.campaigns.contracts import CampaignError, canonical, digest
from src.malaria_dl.execution.artifacts import verify_session
from test_campaign_executor_e5 import evidence


KINDS = ('artifact', 'artifact_prepared', 'calibration', 'epoch', 'phase',
         'predictions', 'runtime', 'selection')
# Frozen pre-E10.6 representation, including Unicode, bool and numeric normalization.
GOLDEN_BYTES = (
    '[{"kind":"artifact","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"artifact_prepared","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"calibration","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"epoch","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"phase","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"predictions","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"runtime","payload":{"legacy":true},"phase":"base","record_key":"configuration"},'
    '{"kind":"runtime","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"},'
    '{"kind":"selection","payload":{"text":"á","values":[1,true,0,null]},"phase":"golden","record_key":"1"}]'
).encode('utf-8')
GOLDEN_HASH = '5ac32b86fba927bfc9efdc66c6425d41f35dd4ef63395d3e11c06e0545d20c40'


def golden_rows():
    rows = json.loads(GOLDEN_BYTES)
    for row in rows:
        if row['phase'] == 'golden': row['payload']['values'] = [1.0, True, -0.0, None]
    return rows


def test_fixed_legacy_bytes_and_sha256():
    assert canonical(golden_rows()).encode('utf-8') == GOLDEN_BYTES
    assert digest(golden_rows()) == hashlib.sha256(GOLDEN_BYTES).hexdigest() == GOLDEN_HASH


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('mutation', ['change', 'remove'])
def test_each_legacy_kind_still_protected_by_hash_and_verification(tmp_path, kind, mutation):
    session, rows = evidence(tmp_path)
    repo = SimpleNamespace(records=lambda _: rows)
    assert verify_session(repo, session, lambda *_: None)['status'] == 'verified'
    altered = deepcopy(rows)
    if mutation == 'remove': altered = [r for r in altered if r['kind'] != kind]
    else: next(r for r in altered if r['kind'] == kind)['payload']['tampered'] = True
    assert digest(altered) != session['completion']['records_hash']
    repo.records = lambda _: altered
    with pytest.raises(CampaignError, match='TRAIN_RESULTS_INCOMPLETE'):
        verify_session(repo, session, lambda *_: None)
