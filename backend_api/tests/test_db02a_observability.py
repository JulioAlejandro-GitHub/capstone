"""Safe diagnostics and rollback on the isolated schema; no operational writes."""
import json
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db import get_primary_engine
from app.observability import correlation_id_context
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.campaigns.repository import CampaignRepository


@pytest.mark.parametrize('statement,code,state', [
    ("SELECT nonexistent_db02a_column", 'CAMPAIGN_DATABASE_OPERATION_FAILED', '42703'),
    ("INSERT INTO experimental_campaigns (id,state,dataset_evidence_id) VALUES ('11111111-1111-4111-8111-111111111111','draft','22222222-2222-4222-8222-222222222222')", 'CAMPAIGN_DATASET_EVIDENCE_CONFLICT', 'P0001'),
    ("DO $$ BEGIN RAISE EXCEPTION 'private-clinical-value'; END $$", 'CAMPAIGN_DATABASE_OPERATION_FAILED', 'P0001'),
])
def test_safe_diagnostics_and_transaction_rollback(caplog, statement, code, state):
    engine = get_primary_engine()
    with engine.connect() as c:
        assert c.execute(text('SELECT current_database()')).scalar_one() == 'capstone_db02a_test_20261012'
    correlation = str(uuid4())
    @contextmanager
    def scope(readonly=False):
        with engine.begin() as c:
            yield c
    repository = CampaignRepository(scope=scope, correlation_id=correlation)
    with pytest.raises(CampaignError, match=code):
        with repository.transaction() as c:
            c.execute(text('CREATE TEMP TABLE db02a_rollback_probe (value text) ON COMMIT DROP'))
            c.execute(text('INSERT INTO db02a_rollback_probe VALUES (:value)'), {'value': 'private-clinical-value'})
            c.execute(text(statement))
    record = next(json.loads(r.message) for r in caplog.records if 'campaign.database_error' in r.message)
    assert record['sqlstate'] == state
    assert record['exception_class']
    assert record['correlation_id'] == correlation
    assert record['message'] == (code if state == 'P0001' and code.startswith('CAMPAIGN_DATASET') else None)
    assert 'private-clinical-value' not in caplog.text
    assert 'INSERT' not in caplog.text and 'SELECT' not in caplog.text
    with engine.connect() as c:
        assert c.execute(text("SELECT to_regclass('pg_temp.db02a_rollback_probe')")).scalar_one() is None
