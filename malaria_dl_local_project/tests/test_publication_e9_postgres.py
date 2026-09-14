"""Manual publication service, synthetic schema only; no deployment activation."""
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
import os

import pytest
from sqlalchemy import text
from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
from test_campaigns_postgres import isolated, safe_test  # noqa: F401

pytestmark = pytest.mark.skipif(os.getenv('RUN_STAGE9_POSTGRES_TESTS') != '1', reason='Compose E9 opt-in required')


@pytest.fixture
def publication(isolated):  # noqa: F811
    s = isolated
    s.c.exec_driver_sql('''
        ALTER TABLE runs ADD COLUMN created_at timestamptz DEFAULT now();
        CREATE TABLE artifacts(id uuid PRIMARY KEY,name text);
        CREATE TABLE model_versions(id uuid PRIMARY KEY,training_run_id uuid REFERENCES runs(id),
            checkpoint_artifact_id uuid REFERENCES artifacts(id),model_name text,version_number int,
            created_at timestamptz DEFAULT now(), UNIQUE(id,checkpoint_artifact_id));
        CREATE TABLE run_lineage(parent_run_id uuid REFERENCES runs(id),child_run_id uuid REFERENCES runs(id),relationship_type text);
    ''')
    ddl = Path(__file__).resolve().parents[1] / 'db/init/029_stage2_model_publications.sql'
    s.c.exec_driver_sql(ddl.read_text())
    ids = {k: str(uuid4()) for k in ('train','evaluation','artifact','version')}
    for key,kind in [('train','training'),('evaluation','evaluation')]:
        s.c.execute(text("INSERT INTO runs(id,run_type,status) VALUES(CAST(:id AS uuid),:kind,'completed')"), {'id':ids[key],'kind':kind})
    s.c.execute(text("INSERT INTO artifacts VALUES(CAST(:id AS uuid),'synthetic.keras')"),{'id':ids['artifact']})
    s.c.execute(text("INSERT INTO model_versions(id,training_run_id,checkpoint_artifact_id,model_name,version_number) VALUES(CAST(:version AS uuid),CAST(:train AS uuid),CAST(:artifact AS uuid),'synthetic',1)"),ids)
    s.c.execute(text("INSERT INTO run_lineage VALUES(CAST(:train AS uuid),CAST(:evaluation AS uuid),'evaluates_checkpoint_from')"),ids)
    return s,ids


@safe_test
def test_publication_service_rollback_and_idempotence(publication):
    s,ids=publication
    s.make_visible()
    outer=s.c.begin()
    s.c.execute(text(f'SET LOCAL search_path TO {s.schema},pg_catalog'))
    @contextmanager
    def scope():
        with s.c.begin_nested():
            yield s.c
    service=Stage2PublicationService(scope,'synthetic-e9')
    try:
        first=service.publish(ids['version'],'synthetic-e9','isolated proof')
        second=service.publish(ids['version'],'synthetic-e9','repeat')
        assert first['publication']['id']==second['publication']['id']
        assert second['idempotent'] is True
        assert first['checkpoint_artifact_id']==ids['artifact']
        assert s.c.execute(text('SELECT count(*) FROM stage2_model_publication_events')).scalar_one()==1
        service.deactivate(first['publication']['id'],'synthetic-e9','isolated deactivation')
        assert service.status(ids['version'])['is_stage2_available'] is False
    finally:
        outer.rollback()
        with s.c.engine.connect() as c,c.begin():
            c.execute(text('SET TRANSACTION READ ONLY'))
            assert c.execute(text(f'SELECT count(*) FROM {s.schema}.stage2_model_publications')).scalar_one()==0
            assert c.execute(text(f'SELECT count(*) FROM {s.schema}.stage2_model_publication_events')).scalar_one()==0
    print('E9 synthetic publication: explicit version/checkpoint, idempotence, manual deactivate, rollback zero; no operational deployment touched')
