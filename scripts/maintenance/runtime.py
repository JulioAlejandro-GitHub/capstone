"""Docker-side RPC. The host never imports a database driver or connects to SQL."""
import json
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from app.db import get_primary_engine
from scripts.maintenance.database import (LOCK_KEY, validate_identity, check_idle, snapshot, rebuild, verify_clean)
from scripts.maintenance.verification import MaintenanceError, require, write_json
from scripts.maintenance.protected_resources import HISTORY_TABLES

REPORT = Path('/maintenance_report')


def owners(connection):
    """Persist only path identities, never full historical payloads or user rows."""
    paths = set()
    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and (value.startswith(('/app/', 'outputs/', 'releases/', 'var/')) or '/malaria_dl_local_project/' in value):
            paths.add(value)
    # Artifact-bearing tables; metrics/prediction payloads are not path owners.
    for table in ('artifacts', 'train_execution_sessions', 'train_execution_records', 'model_versions',
                  'stage2_model_publications', 'deployed_model_versions', 'assessment_artifacts',
                  'explainability_results', 'cell_explanation_artifacts'):
        if table not in HISTORY_TABLES:
            continue
        for value in connection.execute(text('SELECT to_jsonb(t) FROM "' + table + '" t')).scalars():
            walk(value)
    return sorted(paths)


def handle(action, payload):
    engine = get_primary_engine()
    expected = json.loads((REPORT / 'identity.json').read_text())
    if action == 'lease':
        with engine.connect().execution_options(postgresql_readonly=True) as c:
            validate_identity(c, expected)
        engine.dispose()
        admin = create_engine(engine.url.set(database='postgres'))
        with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
            require(c.execute(text('SELECT pg_try_advisory_lock(:a,:b)'), dict(zip(('a','b'), LOCK_KEY))).scalar_one(), 'MAINTENANCE_ALREADY_RUNNING')
            print(json.dumps({'status': 'LEASE_READY'}), flush=True)
            sys.stdin.buffer.read()  # EOF on host exit releases the session lock
        return None
    if action == 'inspect':
        with engine.connect().execution_options(postgresql_readonly=True, isolation_level='REPEATABLE READ') as c:
            actual = validate_identity(c, expected)
            check_idle(c, artifact_only=payload.get('artifact_only', False))
            return {'identity': actual, 'snapshot': snapshot(c), 'owned_paths': owners(c),
                    'models': list(c.execute(text('SELECT name FROM models')).scalars())}
    if action in ('create_restore', 'rebuild'):
        for key in ('restore', 'candidate', 'recovery'):
            require(bool(re.fullmatch(r'capstone_m3_[a-f0-9]{12}_' + {'restore':'restore','candidate':'new','recovery':'old'}[key], payload[key])), 'INVALID_MAINTENANCE_DATABASE_NAME')
    if action == 'create_restore':
        with engine.connect().execution_options(postgresql_readonly=True) as c:
            validate_identity(c, expected)
        from scripts.reset.reset1b.common import qi
        admin = create_engine(engine.url.set(database='postgres'))
        with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
            c.exec_driver_sql('CREATE DATABASE ' + qi(payload['restore']) + ' OWNER ' + qi(expected['user']))
        return {'status': 'CREATED'}
    if action == 'rebuild':
        original = json.loads((REPORT / 'source.json').read_text())['snapshot']
        return rebuild(engine, expected, original, payload['restore'], payload['candidate'], payload['recovery'], REPORT / 'db_cleanup.json')
    if action == 'verify':
        original = json.loads((REPORT / 'source.json').read_text())['snapshot']
        with engine.connect().execution_options(postgresql_readonly=True) as c:
            validate_identity(c, expected)
            check_idle(c)
            return verify_clean(c, original)
    if action in ('fence_files', 'unfence_files'):
        from scripts.reset.reset1b.common import qi
        engine.dispose()
        admin = create_engine(engine.url.set(database='postgres'))
        with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
            cluster = c.execute(text('SELECT system_identifier::text FROM pg_control_system()')).scalar_one()
            require(cluster == expected['cluster'], 'POSTGRES_IDENTITY_MISMATCH')
            oid = c.execute(text('SELECT oid FROM pg_database WHERE datname=:db'), {'db': expected['database']}).scalar_one()
            if action == 'fence_files':
                write_json(REPORT / 'file_fence.json', {'oid':oid, 'database':expected['database']})
                c.exec_driver_sql('ALTER DATABASE ' + qi(expected['database']) + ' ALLOW_CONNECTIONS false')
                count = c.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=:db AND backend_type='client backend'"), {'db':expected['database']}).scalar_one()
                require(count == 0, 'EXTERNAL_DATABASE_CONNECTIONS')
            else:
                saved = json.loads((REPORT / 'file_fence.json').read_text())
                require(saved['oid'] == oid, 'FILE_FENCE_IDENTITY_CHANGED')
                c.exec_driver_sql('ALTER DATABASE ' + qi(expected['database']) + ' ALLOW_CONNECTIONS true')
        return {'status':'FENCED' if action == 'fence_files' else 'UNFENCED'}
    if action == 'frontend_ready':
        import urllib.request
        with urllib.request.urlopen('http://frontend:80',timeout=3) as response:
            require(response.status == 200,'FRONTEND_HEALTH_FAILED')
        return {'status':'READY'}
    if action == 'protected_files':
        from scripts.maintenance.verification import filesystem_fingerprint, protected_link_targets
        roots = sorted(set(payload['roots']) | set(protected_link_targets(payload['roots'])))
        return {p: filesystem_fingerprint(p) for p in roots}
    if action == 'files':
        from scripts.maintenance.clean_experiment_artifacts import scan_roots, delete_manifest
        if payload['operation'] == 'scan':
            from scripts.maintenance.verification import protected_link_targets
            protected = payload['protected'] + protected_link_targets(payload['protected'])
            return scan_roots(payload['roots'], protected, payload['owned_paths'], payload['models'])
        if payload['operation'] == 'delete':
            return delete_manifest(payload['manifest'], REPORT / 'volume_journal.jsonl')
    raise MaintenanceError('UNKNOWN_RUNTIME_OPERATION')


def main():
    try:
        action = sys.argv[1]
        payload = {} if action == 'lease' else json.load(sys.stdin)
        result = handle(action, payload)
        if result is not None:
            print(json.dumps(result, default=str))
        return 0
    except BaseException as exc:
        # Driver messages can include URLs/bound values. Only our fixed error codes
        # and exception class names may cross the Docker boundary or enter logs.
        code = str(exc) if isinstance(exc, MaintenanceError) else type(exc).__name__
        print(json.dumps({'status': 'ERROR', 'error': code}), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
