"""Real PostgreSQL 17 integration. Only the disposable test cluster is accepted."""
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from app.db import get_primary_engine
from scripts.maintenance.database import identity, snapshot, history_count, rebuild, check_idle, verify_clean, LOCK_KEY
from scripts.maintenance.verification import MaintenanceError, write_json, filesystem_fingerprint
from scripts.maintenance.orchestrator import execute
from scripts.maintenance.clean_experiment_artifacts import scan_roots, delete_manifest


def isolated_engine():
    engine=get_primary_engine()
    with engine.connect() as c:
        actual=identity(c)
        assert actual['database']=='maintenance_fixture'
        assert actual['cluster']!='7668020338728398886'
        assert os.environ['MAINTENANCE_ISOLATED']=='1'
    return engine


def test_real_rebuild_protected_hashes_and_idempotence(tmp_path, monkeypatch):
    engine=isolated_engine()
    with engine.connect() as c:
        before=snapshot(c); expected=identity(c)
        check_idle(c)
    engine.dispose()
    assert history_count(before)>0
    # Real SQL + real files through the same orchestration state machine. The
    # disposable test network replaces discovery/service lifecycle, not SQL.
    import scripts.maintenance.runtime as runtime
    class IsolatedTransport:
        rebuilds=0
        def __init__(self, report):
            self.report=report
            self.root=tmp_path/'artifacts'
            self.root.mkdir(exist_ok=True)
            self.protected=tmp_path/'dataset'
            self.protected.mkdir(exist_ok=True)
            (self.protected/'source.npy').write_bytes(b'protected original')
            self.roots=[dict(path=str(self.root),category='ml_outputs',physical_root='isolated')]
        def discover(self):
            monkeypatch.setattr(runtime,'REPORT',self.report)
            write_json(self.report/'identity.json',expected)
        def inspect(self,**kw):
            with engine.connect() as c:
                check_idle(c)
                return {'identity':identity(c),'snapshot':snapshot(c),'owned_paths':[],'models':['custom_cnn']}
        def stop_writers(self):
            engine.dispose()
        def filesystem_state(self):
            return filesystem_fingerprint(self.protected)
        def scan(self,source):
            return {'host':scan_roots(self.roots,[str(self.protected)],[],['custom_cnn']),
                    'volume':{'files':[],'issues':[],'excluded':[]}}
        def cleanup_db(self,source):
            self.rebuilds+=1
            engine.dispose()
            return rebuild(engine,expected,source['snapshot'],'capstone_m3_aaaaaaaaaaaa_restore','capstone_m3_aaaaaaaaaaaa_new','capstone_m3_aaaaaaaaaaaa_old',self.report/'db_cleanup.json')
        def rpc(self,action):
            return runtime.handle(action,{})
        def delete_files(self,manifest):
            value=delete_manifest(manifest['host'],self.report/'journal.jsonl')
            return dict(status='COMPLETED' if value['deleted_files'] else 'NO_ARTIFACTS_FOUND',**value)
        def restart(self): pass  # No application writers exist in this fixture.
        def close(self): engine.dispose()
    report=tmp_path/'first';report.mkdir()
    transport=IsolatedTransport(report)
    (transport.root/'custom_cnn').mkdir()
    artifact=transport.root/'custom_cnn'/'best_model.keras'
    artifact.write_bytes(b'non-ML test fixture')
    assert execute('all',transport,report)==0, (report/'summary.json').read_text()
    assert not artifact.exists()
    result=json.loads((report/'db_cleanup.json').read_text())
    second=tmp_path/'second';second.mkdir()
    transport.report=second
    assert execute('all',transport,second)==0, (second/'summary.json').read_text()
    assert json.loads((second/'summary.json').read_text())['status']=='ALREADY_CLEAN'
    assert transport.rebuilds==1
    assert result['status']=='COMPLETED' and result['commit_reconciled']
    with engine.connect() as c:
        after=snapshot(c)
        assert history_count(after)==0
        check_idle(c)
        assert verify_clean(c,before)['protected_tables_equal']
        # Idempotence inspection itself must not add rows/change protected state.
        assert snapshot(c)==after
    evidence={'postgres':'real isolated PostgreSQL 17','source_history_rows':history_count(before),
        'final_history_rows':history_count(after),'protected_tables':result['integrity']['protected_tables_equal'],
        'foreign_keys_checked':result['integrity']['foreign_keys_checked'],
        'commit_reconciled':True,'combined_real_sql_and_files':True,'second_execution':'ALREADY_CLEAN','source_public_counts':{k:v['count'] for k,v in before['schemas']['public'].items()},
        'authentication_equal':all(before['schemas']['public'][k]==after['schemas']['public'][k] for k in ('users','roles','user_roles'))}
    Path('/maintenance_report/postgres_evidence.json').write_text(json.dumps(evidence,indent=2))


def test_real_advisory_lock_excludes_second_connection():
    engine=isolated_engine()
    admin=create_engine(engine.url.set(database='postgres'))
    with admin.connect() as one,admin.connect() as two:
        assert one.execute(text('SELECT pg_try_advisory_lock(:a,:b)'),dict(zip(('a','b'),LOCK_KEY))).scalar_one()
        assert not two.execute(text('SELECT pg_try_advisory_lock(:a,:b)'),dict(zip(('a','b'),LOCK_KEY))).scalar_one()
        one.execute(text('SELECT pg_advisory_unlock(:a,:b)'),dict(zip(('a','b'),LOCK_KEY)))
    admin.dispose()


def test_real_active_train_rejected_without_running_train():
    engine=isolated_engine()
    # Retained old logical DB is part of this disposable cluster only.
    admin=create_engine(engine.url.set(database='postgres'))
    with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        c.exec_driver_sql('ALTER DATABASE capstone_m3_aaaaaaaaaaaa_old ALLOW_CONNECTIONS true')
    historical=create_engine(engine.url.set(database='capstone_m3_aaaaaaaaaaaa_old'))
    with historical.connect() as c:
        tx=c.begin()
        c.exec_driver_sql("UPDATE runs SET status='running' WHERE id=(SELECT id FROM runs LIMIT 1)")
        with pytest.raises(MaintenanceError,match='ACTIVE_EXECUTION:runs'):
            check_idle(c)
        tx.rollback()
    historical.dispose();admin.dispose()


def test_real_sql_failure_keeps_source_and_files(tmp_path, monkeypatch):
    import scripts.maintenance.database as module
    engine=isolated_engine()
    old=create_engine(engine.url.set(database='capstone_m3_aaaaaaaaaaaa_old'))
    with old.connect() as c:
        original=snapshot(c);expected=identity(c)
    old.dispose()
    marker=tmp_path/'historical.keras';marker.write_bytes(b'must survive SQL failure')
    def fail_bootstrap(c):
        c.exec_driver_sql('SELECT 1/0')
    monkeypatch.setattr(module,'bootstrap',fail_bootstrap)
    with pytest.raises(Exception):
        rebuild(old,expected,original,'capstone_m3_aaaaaaaaaaaa_restore','capstone_m3_bbbbbbbbbbbb_new','capstone_m3_bbbbbbbbbbbb_old',tmp_path/'failure.json')
    with old.connect() as c:
        assert snapshot(c)==original
    assert marker.read_bytes()==b'must survive SQL failure'
    old.dispose()
