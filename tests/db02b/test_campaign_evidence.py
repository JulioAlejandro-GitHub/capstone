"""Regression of actual campaign guards; no datasets, executions or historical migrations."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from conftest import SQL_DIR
from src.malaria_dl.campaigns.contracts import CampaignError, canonical
from src.malaria_dl.campaigns.service import CampaignService
from src.malaria_dl.data.governed_dataset import GovernedDatasetSnapshot


@pytest.mark.parametrize('status', ['verified', 'verified_requested_splits'])
def test_accept_and_commit_full_campaign(case: SimpleNamespace, status: str) -> None:
    eid, cid = case.evidence(status), str(uuid4())
    contract = case.contract(eid)
    result = case.repo.create_frozen(cid, contract, 'db02b')
    assert result['state'] == 'frozen'
    assert result['contract'] == contract
    # Readback uses a new committed transaction, with real configuration/member guards.
    stored = case.repo.get(cid)
    assert len(stored['configurations']) == 1
    assert len(stored['members']) == 2
    assert str(stored['dataset_evidence_id']) == eid
    assert stored['dataset_snapshot'] == case.dataset
    assert case.repo.create_frozen(cid, contract, 'db02b')['id'] == result['id']


@pytest.mark.parametrize('changes', [
    {'missing': True}, {'success': False}, {'event_type': 'other'}, {'error_code': 'failure'},
    {'fields': {'dataset_version_id': str(uuid4())}}, {'fields': {'snapshot': {}}},
    {'status': 'unknown'}, {'status': None}, {'status': 'verified_metadata_only'},
    {'status': 'rejected'}, {'fields': {'required_splits': ['train']}},
    {'fields': {'physically_verified_splits': ['val']}},
    {'fields': {'physically_verified_splits': None}}, {'fields': {'required_splits': None}},
    {'fields': {'required_splits': 'train,val'}},
])
def test_reject_invalid_evidence(case: SimpleNamespace, changes: dict) -> None:
    eid = str(uuid4()) if changes.get('missing') else case.evidence(**changes)
    cid = str(uuid4())
    with pytest.raises(CampaignError, match='^CAMPAIGN_DATASET_EVIDENCE_CONFLICT$'):
        case.repo.create_frozen(cid, case.contract(eid), 'db02b')
    with case.scope(True) as c:
        for table in ('experimental_campaigns', 'campaign_configurations', 'campaign_members'):
            key = 'id' if table == 'experimental_campaigns' else 'campaign_id'
            assert c.execute(text(f'SELECT count(*) FROM {table} WHERE {key}=:id'), {'id': cid}).scalar_one() == 0


def test_missing_status_rejected(case: SimpleNamespace) -> None:
    # SQL NULL (absent key), distinct from JSON null.
    eid = case.evidence()
    with case.scope() as c:
        payload = c.execute(text('SELECT after_state FROM audit_events WHERE id=:id'), {'id':eid}).scalar_one()
    del payload['integrity_status']
    eid2 = str(uuid4())
    with case.scope() as c:
        c.execute(text("""INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,
            request_path,correlation_id,after_state,metadata,success)
            VALUES(CAST(:id AS uuid),'ml.dataset_verification','verify','dataset_version',:dataset,'TEST','db02b',CAST(:id AS text),
            CAST(:payload AS jsonb),'{}',true)"""),
            dict(id=eid2,dataset=case.dataset['dataset_version_id'],payload=canonical(payload)))
    with pytest.raises(CampaignError, match='CAMPAIGN_DATASET_EVIDENCE_CONFLICT'):
        case.draft(eid2)


def test_service_passes_fresh_evidence_and_exact_snapshot(case: SimpleNamespace) -> None:
    d = case.dataset
    snapshot = GovernedDatasetSnapshot(
        dataset_version_id=UUID(d['dataset_version_id']),
        dataset_materialization_id=UUID(d['dataset_materialization_id']), dataset_root=Path(d['dataset_root']),
        patient_assignment_fingerprint=d['patient_assignment_fingerprint'],
        record_assignment_fingerprint=d['record_assignment_fingerprint'],
        source_population_fingerprint=d['source_population_fingerprint'],
        clinical_identity_fingerprint=d['clinical_identity_fingerprint'], counts=d['counts'],
        evidence_id=case.evidence(), verified_splits=('train','val'))

    def verifier(version: str, *, consumer: str, required_splits: tuple[str, ...]) -> GovernedDatasetSnapshot:
        assert version == d['dataset_version_id']
        assert consumer == 'campaigns.configure' and required_splits == ('train','val')
        return snapshot

    service = CampaignService(case.repo, verifier, lambda: case.environment)
    result = service.configure(campaign_id=str(uuid4()), name='service', purpose='synthetic',
        dataset_version_id=d['dataset_version_id'],request=case.request,protocol=case.protocol,actor='db02b')
    with case.scope(True) as c:
        matched = c.execute(text("""SELECT e.after_state->'snapshot'=ec.dataset_snapshot,
            e.after_state->>'dataset_version_id'=ec.dataset_version_id::text
            FROM experimental_campaigns ec JOIN audit_events e ON e.id=ec.dataset_evidence_id
            WHERE ec.id=:id"""), {'id': result['id']}).one()
    assert tuple(matched) == (True, True)
    assert str(result['dataset_evidence_id']) == snapshot.evidence_id


@pytest.mark.parametrize('operation,message', [
    ('DELETE FROM experimental_campaigns WHERE id=:id','CAMPAIGN_DELETE_FORBIDDEN'),
    ("UPDATE experimental_campaigns SET actor='other' WHERE id=:id",'CAMPAIGN_IDENTITY_IMMUTABLE'),
    ("UPDATE experimental_campaigns SET id=gen_random_uuid() WHERE id=:id",'CAMPAIGN_IDENTITY_IMMUTABLE'),
    ("UPDATE experimental_campaigns SET created_at=now()+interval '1 day' WHERE id=:id",'CAMPAIGN_IDENTITY_IMMUTABLE'),
    ("UPDATE experimental_campaigns SET state='active' WHERE id=:id",'INVALID_CAMPAIGN_TRANSITION'),
    ("UPDATE experimental_campaigns SET state='frozen', canonical_contract='{}', contract='[]' WHERE id=:id",'CAMPAIGN_HASH_CONFLICT'),
    ("UPDATE experimental_campaigns SET dataset_snapshot='{}' WHERE id=:id",'CAMPAIGN_DATASET_EVIDENCE_CONFLICT'),
])
@pytest.mark.parametrize('definition', ['rollback.sql','apply.sql'])
def test_unchanged_draft_rules(case: SimpleNamespace, operation: str, message: str, definition: str) -> None:
    # Each definition is tested in a transaction that rolls back its DDL as well as data.
    row = case.draft(case.evidence('verified'))
    with case.engine.connect() as c:
        tx = c.begin()
        try:
            body = (SQL_DIR / definition).read_text().split('CREATE OR REPLACE',1)[1].rsplit('COMMIT;',1)[0]
            c.exec_driver_sql('CREATE OR REPLACE'+body)
            with pytest.raises(DBAPIError) as error:
                c.execute(text(operation), {'id':row['id']})
            assert error.value.orig.sqlstate == 'P0001'
            assert error.value.orig.diag.message_primary == message
        finally:
            tx.rollback()


@pytest.mark.parametrize('definition', ['rollback.sql','apply.sql'])
def test_frozen_immutability_and_terminal_rule(case: SimpleNamespace, definition: str) -> None:
    cid = str(uuid4())
    case.repo.create_frozen(cid,case.contract(case.evidence('verified')),'db02b')
    with case.engine.connect() as c:
        tx = c.begin()
        try:
            body = (SQL_DIR / definition).read_text().split('CREATE OR REPLACE',1)[1].rsplit('COMMIT;',1)[0]
            c.exec_driver_sql('CREATE OR REPLACE'+body)
            for statement, message in [
                ("UPDATE experimental_campaigns SET name='other' WHERE id=:id",'FROZEN_CAMPAIGN_IMMUTABLE'),
                ("DELETE FROM campaign_configurations WHERE campaign_id=:id",'FROZEN_CONFIGURATION_IMMUTABLE'),
            ]:
                with pytest.raises(DBAPIError) as error, c.begin_nested():
                    c.execute(text(statement),{'id':cid})
                assert error.value.orig.diag.message_primary == message
            c.execute(text("UPDATE experimental_campaigns SET state='active' WHERE id=:id"),{'id':cid})
            with pytest.raises(DBAPIError) as error, c.begin_nested():
                c.execute(text("UPDATE experimental_campaigns SET state='finalized' WHERE id=:id"),{'id':cid})
            assert error.value.orig.diag.message_primary == 'CAMPAIGN_NOT_TERMINAL'
        finally:
            tx.rollback()


def test_original_reproduces_rejection_and_rollback_restores(case: SimpleNamespace) -> None:
    eid = case.evidence()
    original = (SQL_DIR / 'rollback.sql').read_text()
    corrected = (SQL_DIR / 'apply.sql').read_text()
    with case.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        c.exec_driver_sql(original)
    try:
        with pytest.raises(CampaignError,match='CAMPAIGN_DATASET_EVIDENCE_CONFLICT'):
            case.draft(eid)
        with case.engine.connect() as c:
            restored = c.execute(text("SELECT pg_get_functiondef('public.campaign_guard()'::regprocedure)")).scalar_one()
            assert restored.strip()+';' in original
    finally:
        with case.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
            c.exec_driver_sql(corrected)
    assert case.draft(eid)['state'] == 'draft'


def test_failure_after_members_rolls_back_all_rows(case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    cid, contract = str(uuid4()), case.contract(case.evidence())
    from src.malaria_dl.campaigns import repository
    real_execute = repository.execute

    def fail_at_freeze(connection: object, statement: str, **params: object) -> object:
        if "SET state='frozen'" in statement:
            # Real DB rejection after draft, configuration and both member INSERTs.
            assert connection.execute(text('SELECT count(*) FROM campaign_members WHERE campaign_id=:id'), {'id':cid}).scalar_one() == 2
            params['hash'] = '0' * 64
        return real_execute(connection, statement, **params)

    monkeypatch.setattr(repository,'execute',fail_at_freeze)
    with pytest.raises(CampaignError,match='CAMPAIGN_HASH_CONFLICT'):
        case.repo.create_frozen(cid,contract,'db02b')
    with case.scope(True) as c:
        for table, key in [('experimental_campaigns','id'),('campaign_configurations','campaign_id'),('campaign_members','campaign_id')]:
            assert c.execute(text(f'SELECT count(*) FROM {table} WHERE {key}=:id'),{'id':cid}).scalar_one() == 0
        assert c.execute(text("SELECT count(*) FROM audit_events WHERE after_state->>'campaign_id'=:id OR after_state->>'id'=:id"),{'id':cid}).scalar_one() == 0


@pytest.mark.parametrize('definition', ['rollback.sql','apply.sql'])
@pytest.mark.parametrize('rule', ['matrix','grid','protocol','science','initial_members','starts_draft'])
def test_other_guard_branches(case: SimpleNamespace, definition: str, rule: str) -> None:
    eid = case.evidence('verified')
    row, contract = case.draft(eid), case.contract(eid)
    messages = dict(matrix='INCOMPLETE_FROZEN_MATRIX',grid='INCOMPLETE_CONFIGURATION_SEED_GRID',
        protocol='INVALID_FROZEN_PROTOCOL',science='INCOMPLETE_SCIENTIFIC_PROTOCOL',
        initial_members='INVALID_INITIAL_MEMBERS',starts_draft='CAMPAIGN_STARTS_DRAFT')
    if rule == 'matrix':
        contract['name'] = 'mismatch'
    elif rule == 'grid':
        contract['matrix']['seeds'] = [11,11]
    elif rule == 'protocol':
        contract['protocol']['test_access'] = 'always'
    elif rule == 'science':
        contract['protocol']['sensitivity_target'] = 2
    elif rule == 'initial_members':
        for member in contract['matrix']['members']:
            member['exclusion_reason'] = 'synthetic exclusion'
    with case.engine.connect() as c:
        tx = c.begin()
        try:
            body = (SQL_DIR / definition).read_text().split('CREATE OR REPLACE',1)[1].rsplit('COMMIT;',1)[0]
            c.exec_driver_sql('CREATE OR REPLACE'+body)
            c.execute(text('UPDATE experimental_campaigns SET protocol=CAST(:protocol AS jsonb) WHERE id=:id'),
                      {'protocol':canonical(contract['protocol']),'id':row['id']})
            with pytest.raises(DBAPIError) as error:
                if rule == 'starts_draft':
                    c.execute(text("""INSERT INTO experimental_campaigns
                        (id,name,purpose,state,dataset_version_id,dataset_snapshot,dataset_evidence_id,requested,protocol,environment,actor)
                        SELECT gen_random_uuid(),name,purpose,'frozen',dataset_version_id,dataset_snapshot,dataset_evidence_id,
                        requested,protocol,environment,actor FROM experimental_campaigns WHERE id=:id"""), {'id':row['id']})
                else:
                    case.repo._materialize(c,row['id'],contract)
            assert error.value.orig.sqlstate == 'P0001'
            assert error.value.orig.diag.message_primary == messages[rule]
        finally:
            tx.rollback()
