"""Own one ephemeral C2.12 database on the existing instance, including cleanup."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from sqlalchemy import URL
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from alembic_v2.safety import inspect_isolation  # noqa: E402
from alembic_v2.disposable import verify_created_database  # noqa: E402

EVIDENCE = ROOT / 'docs/audits/clinical_calibration_c2_12'


def command(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                          timeout=300, **kwargs)


def snapshot(connection: psycopg.Connection) -> dict:
    """Server-side fingerprints of B1 VAL provenance, never TEST or sample data."""
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        result = {}
        for table, predicate in {
            'runs': "campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'",
            'experimental_campaigns': "id='b54ea684-1b0c-421d-a4b2-9f12667bd619'",
            'campaign_configurations': "campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619'",
            'run_configurations': "run_id IN (SELECT id FROM runs WHERE campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619')",
            'evaluations': "split='val' AND training_run_id IN (SELECT id FROM runs WHERE campaign_id='b54ea684-1b0c-421d-a4b2-9f12667bd619')",
        }.items():
            result[table] = connection.execute(sql.SQL(
                "SELECT count(*) AS count,md5(string_agg(body,'' ORDER BY body)) AS fingerprint "
                "FROM (SELECT md5(to_jsonb(t)::text) body FROM {} t WHERE " + predicate + ") s"
            ).format(sql.Identifier(table))).fetchone()
        result['table_mutations'] = connection.execute("""SELECT relname,n_tup_ins,n_tup_upd,n_tup_del
            FROM pg_stat_user_tables ORDER BY relname""").fetchall()
        result['guards'] = connection.execute("""SELECT md5(string_agg(pg_get_functiondef(p.oid),'' ORDER BY p.oid)) AS functions
            FROM pg_proc p WHERE p.pronamespace='public'::regnamespace AND p.prokind='f'""").fetchone()
        return result


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    settings = dotenv_values(ROOT / '.env')
    assert settings['POSTGRES_DB'] == 'malaria_experiments', 'Protected database must be explicit'
    nonce = uuid4()
    name = 'capstone_c212_' + nonce.hex
    report: dict = dict(status='BLOCKED', started_at=datetime.now(timezone.utc).isoformat(),
                        protected_database=settings['POSTGRES_DB'], database=name, created=False)
    def save() -> None:
        (EVIDENCE / 'lifecycle.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    admin = psycopg.connect(host='127.0.0.1', port=5432, dbname='postgres',
        user=settings['POSTGRES_USER'], password=settings['POSTGRES_PASSWORD'],
        autocommit=True, row_factory=dict_row, application_name='C212_provision', connect_timeout=5)
    operational = psycopg.connect(host='127.0.0.1', port=5432, dbname=settings['POSTGRES_DB'],
        user=settings['POSTGRES_USER'], password=settings['POSTGRES_PASSWORD'],
        autocommit=True, row_factory=dict_row, application_name='C212_readonly',
        options='-c default_transaction_read_only=on', connect_timeout=5)
    target = None
    try:
        identity = admin.execute("SELECT system_identifier::text AS id FROM pg_control_system()").fetchone()
        assert identity['id'] == '7691366089693499436'
        assert admin.execute("SHOW server_version_num").fetchone()['server_version_num'] == '170009'
        protected = admin.execute('SELECT oid,pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname=%s',
                                 (settings['POSTGRES_DB'],)).fetchone()
        assert protected['owner'] == 'capstone_v2_migrator'
        assert not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (name,)).fetchone()
        cid = command(['docker', 'compose', 'ps', '-q', 'db'])
        assert cid.returncode == 0
        inspected = command(['docker', 'inspect', cid.stdout.strip()])
        assert inspected.returncode == 0
        container = json.loads(inspected.stdout)[0]
        target = dict(authorized_stage='C2.12.2', isolation_id=str(nonce), created_by_run=str(nonce),
            database=name, database_oid=1, database_owner='capstone_v2_migrator', provision_admin=settings['POSTGRES_USER'],
            protected_database=settings['POSTGRES_DB'], protected_database_oid=protected['oid'],
            postgres_system_identifier=identity['id'], container_id=container['Id'],
            volume=container['Mounts'][0]['Name'], host_port=5432, runner_pid=os.getpid())
        inspect_isolation(target)
        report['before'] = snapshot(operational)
        report['target'] = target.copy()
        save()
        admin.execute(sql.SQL('CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0').format(sql.Identifier(name)))
        report['created'] = True
        target['database_oid'] = admin.execute('SELECT oid FROM pg_database WHERE datname=%s', (name,)).fetchone()['oid']
        report['target'] = target.copy()
        save()
        admin.execute(sql.SQL('COMMENT ON DATABASE {} IS {}').format(sql.Identifier(name), sql.Literal('C2.12.2:' + str(nonce))))
        verify_created_database(target)
        url = URL.create('postgresql+psycopg', username=settings['POSTGRES_USER'],
            password=settings['POSTGRES_PASSWORD'], host='127.0.0.1', port=5432, database=name)
        with tempfile.TemporaryDirectory(prefix='c212_migration_') as directory:
            path = Path(directory) / 'target.json'
            path.write_text(json.dumps(target))
            migration = command([sys.executable, '-m', 'alembic', '-c', 'alembic_v2.ini', 'upgrade', 'head'],
                env={**os.environ, 'PGV2_TARGET': str(path), 'PGV2_DATABASE_URL': url.render_as_string(hide_password=False),
                     'PYTHONDONTWRITEBYTECODE': '1'})
            # Redact credentials even if an unexpected driver error includes a URL.
            output = migration.stdout + migration.stderr
            for secret in (url.render_as_string(hide_password=False), settings['POSTGRES_PASSWORD']):
                output = output.replace(secret, '[REDACTED]')
            (EVIDENCE / 'migration.txt').write_text(output)
            report['migration_exit'] = migration.returncode
            save()
            assert migration.returncode == 0, 'Official v2 migration failed'
        result = command(['docker', 'compose', 'exec', '-T',
            '-e', 'C212_DATABASE=' + name, '-e', 'C212_DATABASE_OID=' + str(target['database_oid']),
            '-e', 'C212_RUN_ID=' + str(nonce), '-e', 'PYTHONDONTWRITEBYTECODE=1',
            '-e', 'PYTHONPATH=/app:/app/malaria_dl_local_project:/app/malaria_dl_local_project/tests',
            'backend', 'python', '/scripts/calibration_postgres_e2e.py'])
        (EVIDENCE / 'e2e.txt').write_text(result.stdout + result.stderr)
        report['e2e_exit'] = result.returncode
        report['status'] = 'PASSED' if result.returncode == 0 else 'NOT_APPROVED'
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        report['status'] = 'BLOCKED'
    finally:
        if report['created'] and target is not None:
            try:
                inspect_isolation(target)
                verify_created_database(target)
                assert not admin.execute('SELECT pid FROM pg_stat_activity WHERE datid=%s',
                                         (target['database_oid'],)).fetchall(), 'Connections remain'
                # Close the race with new clients before the final activity check.
                admin.execute(sql.SQL('ALTER DATABASE {} ALLOW_CONNECTIONS false').format(sql.Identifier(name)))
                verify_created_database(target)
                assert not admin.execute('SELECT pid FROM pg_stat_activity WHERE datid=%s',
                                         (target['database_oid'],)).fetchall(), 'Connections appeared'
                admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
                report['cleanup'] = 'verified_identity_zero_connections_dropped'
                report['residue'] = admin.execute('SELECT datname FROM pg_database WHERE datname=%s OR oid=%s',
                                                  (name, target['database_oid'])).fetchall()
                assert not report['residue']
            except Exception as exc:
                report['cleanup'] = 'STOPPED_REQUIRES_EXPLICIT_RESOLUTION'
                report['cleanup_error_type'] = type(exc).__name__
                report['residue'] = name
                report['status'] = 'BLOCKED'
        report['after'] = snapshot(operational)
        report['operational_unchanged'] = report.get('before') == report['after']
        if not report['operational_unchanged']:
            report['status'] = 'BLOCKED'
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save()
        operational.close()
        admin.close()
    print(json.dumps({k: report.get(k) for k in ('status','database','migration_exit','e2e_exit','cleanup','residue','operational_unchanged')}))
    return 0 if report['status'] == 'PASSED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
