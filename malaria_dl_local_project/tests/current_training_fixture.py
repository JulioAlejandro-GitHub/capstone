"""Synthetic TRAIN fixture from the live schema, in a disposable database only.

Parent identities are synthetic; this fixture tests execution persistence, not
parent dataset FKs. No migration history or production permission changes.
"""
import os
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from src.malaria_dl.campaigns.repository import CampaignRepository
from src.malaria_dl.campaigns.service import CampaignService
from src.malaria_dl.data.governed_dataset import GovernedDatasetSnapshot
from test_campaigns_e4 import dataset


@pytest.fixture
def isolated(monkeypatch):
    url = os.getenv('CONTRACT_TEST_DATABASE_URL')
    if not url:
        pytest.skip('CONTRACT_TEST_DATABASE_URL requires a disposable current-schema database')
    engine = create_engine(url)
    with engine.connect() as c, c.begin() as outer:
        assert c.execute(text('SELECT current_database()')).scalar_one() == 'contract01b_test'
        schema = 'capstone_test_current_' + uuid4().hex
        c.execute(text(f'CREATE SCHEMA {schema}'))
        tables = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars().all()
        for table in tables:
            if table == 'dataset_versions':
                c.execute(text(f"CREATE TABLE {schema}.{table}(id uuid PRIMARY KEY,status text DEFAULT 'DRAFT')"))
            elif table == 'experiments':
                c.execute(text(f'CREATE TABLE {schema}.{table}(id uuid PRIMARY KEY)'))
            else:
                c.execute(text(f'CREATE TABLE {schema}.{table}(LIKE public.{table} INCLUDING ALL)'))
        c.execute(text(f'SET LOCAL search_path TO {schema},pg_catalog'))
        functions = c.execute(text("""SELECT pg_get_functiondef(p.oid) FROM pg_proc p
            JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind='f'""")).scalars().all()
        for definition in functions:
            c.execute(text(definition.replace('public.',schema+'.').replace('SET search_path TO \'public\'', f'SET search_path TO {schema}')))
        triggers = c.execute(text("""SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t
            JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal""")).scalars().all()
        for definition in triggers:
            c.execute(text(definition.replace('public.',schema+'.')))
        c.execute(text(f'SET LOCAL search_path TO {schema},pg_catalog'))
        c.execute(text('INSERT INTO experiment_execution_gate(singleton) VALUES(true)'))
        models = {}
        for name in ('custom_cnn','vgg16','densenet121'):
            models[name] = str(uuid4())
            c.execute(text("INSERT INTO models(id,name,model_type,framework,metadata) VALUES(:id,:name,'binary_classification','tensorflow/keras','{}')"), {'id':models[name],'name':name})
        d = dataset()
        c.execute(text('INSERT INTO dataset_versions VALUES(:id)'), {'id':d['dataset_version_id']})
        evidence = uuid4()
        c.execute(text("""INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,
            request_path,correlation_id,metadata,after_state,success) VALUES(:id,'ml.dataset_verification','verify',
            'dataset_version',:dataset,'TEST','synthetic',:correlation,'{}',CAST(:payload AS jsonb),true)"""),
            {'id':evidence,'dataset':d['dataset_version_id'],'correlation':str(evidence), 'payload':json.dumps({'dataset_version_id':d['dataset_version_id'],'snapshot':d,'integrity_status':'verified'})})
        @contextmanager
        def scope(readonly=False):
            with c.begin_nested():
                yield c
        from src.malaria_dl.models import registry
        monkeypatch.setattr(registry, 'model_catalog', lambda: tuple(dict(row) for row in c.execute(
            text('SELECT name,architecture,model_type,framework FROM models ORDER BY name')).mappings()))
        repo = CampaignRepository(scope)
        snapshot = GovernedDatasetSnapshot(UUID(d['dataset_version_id']), UUID(d['dataset_materialization_id']),
            Path(d['dataset_root']), d['patient_assignment_fingerprint'], d['record_assignment_fingerprint'],
            d['source_population_fingerprint'], d['clinical_identity_fingerprint'], d['counts'],str(evidence))
        environment = {'source_sha256':'e'*64,'tensorflow':'synthetic','determinism_environment':{},'python':'synthetic','packages':{'synthetic':'1'}}
        service = CampaignService(repo,lambda *a,**k:snapshot,lambda:environment)
        yield SimpleNamespace(c=c,repo=repo,service=service,dataset=d,models=models,schema=schema)
        outer.rollback()
    engine.dispose()
