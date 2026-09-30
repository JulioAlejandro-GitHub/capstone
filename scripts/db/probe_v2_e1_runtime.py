"""E-01 real-login ACL and fail-closed revision checks in the attested E.1 cluster."""
import json
import os
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'docs/audits/e10_10_5e1_evidence/route_a'
os.environ['PGV2_EVIDENCE_DIR'] = str(E)
os.environ['PGPASSFILE'] = json.loads((E / 'private_paths.json').read_text())['pgpass']
sys.path[:0] = [str(ROOT), str(ROOT / 'malaria_dl_local_project')]
from verify_v2_route_a import guard, connect, RUNTIME
from sqlalchemy import create_engine, text
from src.malaria_dl.execution.schema import require_e10_schema, E10SchemaNotReady
import psycopg

def main():
    t = guard()
    results = {}
    with connect(t, role=RUNTIME) as c:
        identity = c.execute('SELECT session_user,current_user').fetchone()
        assert identity == dict(session_user=RUNTIME, current_user=RUNTIME)
        results['identity'] = identity
        assert c.execute('SELECT version_num FROM public.alembic_version').fetchone()['version_num'] == 'pg_v2_baseline'
        results['select'] = True
        for name, query in {
            'insert': "INSERT INTO public.alembic_version VALUES ('forbidden')",
            'update': "UPDATE public.alembic_version SET version_num='forbidden'",
            'delete': 'DELETE FROM public.alembic_version',
            'truncate': 'TRUNCATE public.alembic_version',
            'alter': 'ALTER TABLE public.alembic_version ADD COLUMN forbidden int',
            'drop': 'DROP TABLE public.alembic_version',
        }.items():
            try:
                with c.transaction():
                    c.execute(query)
                    raise AssertionError(name + ' unexpectedly permitted')
            except psycopg.errors.InsufficientPrivilege as exc:
                results[name] = {'rejected': True, 'sqlstate': exc.sqlstate}
        results['acl'] = c.execute("SELECT a.privilege_type, a.grantee::regrole::text AS grantee FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) a WHERE c.oid='public.alembic_version'::regclass ORDER BY 2,1").fetchall()
        assert not any(r['grantee'] == '-' for r in results['acl'])
        assert [r['privilege_type'] for r in results['acl'] if r['grantee'] == RUNTIME] == ['SELECT']
    url = f"postgresql+psycopg://{RUNTIME}@127.0.0.1:{t['host_port']}/{t['database']}"
    engine = create_engine(url)
    with engine.connect() as c:
        results['runtime_preflight'] = require_e10_schema(c)
    from uuid import uuid4
    from datetime import datetime, timezone
    from sqlalchemy import event as sa_event
    from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode, RunEvent, RunEventType
    from src.malaria_dl.persistence.result_repository import PostgresResultRepository
    from src.malaria_dl.results import ResultService
    ctx = ExecutionContext(run_id=uuid4(), owner=uuid4(), execution_mode=ExecutionMode.LOCAL_PYTHON,
                           dataset_version_id=uuid4(), model_id='synthetic', adapter_version='E1')
    event = RunEvent(event_id=uuid4(), run_id=ctx.run_id, attempt_id=None, sequence=1,
                     event_type=RunEventType.EPOCH_COMPLETED, occurred_at=datetime.now(timezone.utc), payload={'epoch': 0})
    for label, sql in [('unknown', "UPDATE alembic_version SET version_num='unknown'"), ('absent', 'DELETE FROM alembic_version'), ('multiple', "INSERT INTO alembic_version VALUES ('unknown')"), ('sql_error', 'REVOKE SELECT ON alembic_version FROM capstone_v2_runtime')]:
        try:
            with connect(t) as c:
                c.execute(sql)
            with engine.connect() as c:
                try:
                    require_e10_schema(c)
                    raise AssertionError(label + ' accepted')
                except E10SchemaNotReady as exc:
                    results[label] = str(exc)
                    assert ('schema_inspection_failed' if label == 'sql_error' else 'unsupported_alembic_revision') in str(exc)
            mutations = []
            def factory():
                e = create_engine(url)
                @sa_event.listens_for(e, 'before_cursor_execute')
                def capture(conn, cursor, statement, parameters, context, many):
                    if statement.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:
                        mutations.append(statement)
                return e
            service = ResultService(PostgresResultRepository(execution_token=uuid4(), engine_factory=factory))
            try:
                service.accept_event(ctx, event)
                raise AssertionError('Event accepted despite invalid schema')
            except E10SchemaNotReady:
                assert mutations == []
                results[label + '_event_rejected_before_mutation'] = True
        finally:
            with connect(t) as c:
                c.execute("DELETE FROM alembic_version; INSERT INTO alembic_version VALUES ('pg_v2_baseline'); GRANT SELECT ON alembic_version TO capstone_v2_runtime")
    # Exercise Alembic's real version-table writer on an authenticated runtime
    # connection as well as the guarded CLI rejection below. The denied DELETE
    # is transaction-scoped; no head is changed.
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.migration import MigrationContext
    from sqlalchemy.exc import DBAPIError
    script = ScriptDirectory.from_config(Config(str(ROOT / 'alembic_v2.ini')))
    try:
        with engine.begin() as c:
            assert c.execute(text('SELECT session_user')).scalar_one() == RUNTIME
            MigrationContext.configure(c).stamp(script, 'base')
            raise AssertionError('Alembic stamp permitted')
    except DBAPIError as exc:
        assert exc.orig.sqlstate == '42501'
        results['alembic_stamp_authenticated_writer'] = {'rejected': True, 'sqlstate': exc.orig.sqlstate}
    engine.dispose()
    for action in ['stamp', 'upgrade']:
        args = [sys.executable, '-m', 'alembic', '-c', 'alembic_v2.ini', '-x', 'target=' + str(E / 'target.json'), action, 'head']
        r = subprocess.run(args, cwd=ROOT, env=dict(os.environ, PGV2_DATABASE_URL=url), capture_output=True, text=True)
        assert r.returncode != 0 and 'V2_AUTHORIZATION_MISMATCH' in r.stderr
        results['alembic_' + action] = {'argv': args, 'exit_code': r.returncode, 'rejected_before_connection': True, 'reason': 'V2_AUTHORIZATION_MISMATCH'}
    results['passed'] = True
    (E / 'runtime_acl_revision.json').write_text(json.dumps(results, indent=2) + '\n')
    print('E.1 real runtime login ACL/revision checks passed')
if __name__ == '__main__':
    main()
