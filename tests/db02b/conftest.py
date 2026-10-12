"""Current DDL only, synthetic data, dedicated Compose network and tmpfs database."""
from __future__ import annotations

import gzip
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from src.malaria_dl.campaigns.contracts import canonical, expand_matrix
from src.malaria_dl.campaigns.repository import CampaignRepository
from src.malaria_dl.campaigns.service import frozen_contract
from test_campaigns_e4 import dataset, protocol, request

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / 'scripts/db/capstone_db_02b'


@pytest.fixture(scope='session')
def engine() -> Iterator[Engine]:
    # Fixed isolated service; no operational URL or .env is accepted.
    with psycopg.connect('host=db02b-db dbname=db02b_test user=postgres', autocommit=True) as c:
        dump = gzip.decompress((Path(__file__).parent / 'fixtures/operational_schema.sql.gz').read_bytes()).decode()
        ddl = '\n'.join(line for line in dump.splitlines() if not line.startswith('\\'))
        c.execute(ddl)
        original = c.execute("SELECT pg_get_functiondef('public.campaign_guard()'::regprocedure)").fetchone()[0]
        assert original.strip() + ';' in (SQL_DIR / 'rollback.sql').read_text()
        c.execute((SQL_DIR / 'apply.sql').read_text())
        c.execute("INSERT INTO public.models(id,name,architecture,model_type,framework) VALUES(gen_random_uuid(),'custom_cnn','custom_cnn','cnn','tensorflow')")
    instance = create_engine('postgresql+psycopg://postgres@db02b-db/db02b_test')
    yield instance
    instance.dispose()


@pytest.fixture
def case(engine: Engine) -> SimpleNamespace:
    d, p, req = dataset(), protocol(), request([11, 12])
    req.update(models=['custom_cnn'], optimizers=['adam'])
    environment = dict(source_sha256='e' * 64, tensorflow='synthetic', python='synthetic',
                       packages={'synthetic': '1'}, determinism_environment={})
    with engine.begin() as c:
        c.execute(text("""INSERT INTO dataset_versions(id,name,semantic_version,grouping_strategy,grouping_field,
            stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
            target_train_ratio,target_val_ratio,target_test_ratio,positive_class)
            VALUES(:id,:name,'0.0.0','synthetic','patient','synthetic','synthetic','1',11,.5,.5,0,'parasitized')"""),
            {'id': d['dataset_version_id'], 'name': 'DB02B '+d['dataset_version_id']})

    @contextmanager
    def scope(readonly: bool = False) -> Iterator[Connection]:
        with engine.begin() as c:
            if readonly:
                c.execute(text('SET TRANSACTION READ ONLY'))
            yield c

    def evidence(status: str | None = 'verified_requested_splits', *, fields: dict | None = None,
                 success: bool = True, event_type: str = 'ml.dataset_verification',
                 error_code: str | None = None) -> str:
        eid = str(uuid4())
        splits = ['train', 'val', 'test'] if status == 'verified' else ['train', 'val']
        payload = dict(dataset_version_id=d['dataset_version_id'], snapshot=d,
                       integrity_status=status, required_splits=splits,
                       physically_verified_splits=splits, physical_integrity_status='verified',
                       global_integrity_status='verified_frozen_metadata')
        payload.update(fields or {})
        with scope() as c:
            c.execute(text("""INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,
                request_method,request_path,correlation_id,after_state,metadata,success,error_code)
                VALUES(CAST(:id AS uuid),:event,'verify','dataset_version',:dataset,'TEST','db02b',CAST(:id AS text),
                       CAST(:payload AS jsonb),'{}',:success,:error)"""),
                dict(id=eid,event=event_type,dataset=d['dataset_version_id'],payload=canonical(payload),
                     success=success,error=error_code))
        return eid

    def contract(eid: str) -> dict:
        return frozen_contract(name='DB02B synthetic',purpose='trigger regression',experiment_id=None,
            dataset=d,evidence_id=eid,requested=req,protocol=p,environment=environment,
            matrix=expand_matrix(req,p,frozen=True,dataset=d))

    repo = CampaignRepository(scope)

    def draft(eid: str) -> dict:
        return repo.create(name='DB02B synthetic',purpose='trigger regression',dataset=d,
            evidence_id=eid,requested=req,protocol=p,environment=environment,actor='db02b')

    return SimpleNamespace(engine=engine, scope=scope, repo=repo, dataset=d, protocol=p,
                           request=req, environment=environment, evidence=evidence, contract=contract, draft=draft)
