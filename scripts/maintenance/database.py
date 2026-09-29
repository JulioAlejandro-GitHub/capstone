"""RESET.3's verified rebuild/COPY/name-swap, generalized to the canonical DB.

Imported only in Docker. No historical guard is disabled; no existing table is
truncated/deleted. Backups and the previous logical database are always retained.
"""
import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config
from scripts.reset.reset1b.common import fingerprint, catalog, qi
from scripts.maintenance.protected_resources import PROTECTED_TABLES, HISTORY_TABLES, EXPECTED_TABLES
from scripts.maintenance.verification import require, normalized_catalog, write_json
from src.malaria_dl.execution.schema import require_e10_schema

LOCK_KEY = (901973, 3)  # maintenance only; deliberately unrelated to GlobalGate


def identity(connection):
    row = connection.execute(text("SELECT current_database(), session_user, current_schema(), (SELECT system_identifier::text FROM pg_control_system()), current_setting('server_version_num')::int")).one()
    return dict(zip(('database', 'user', 'schema', 'cluster', 'server_version'), row))


def validate_identity(connection, expected):
    actual = identity(connection)
    require(all(actual[k] == expected[k] for k in ('database', 'user', 'cluster')), 'POSTGRES_IDENTITY_MISMATCH')
    require(actual['schema'] == 'public' and 170000 <= actual['server_version'] < 180000, 'POSTGRES17_PUBLIC_REQUIRED')
    require(actual['database'] not in ('postgres', 'template0', 'template1'), 'SYSTEM_DATABASE_FORBIDDEN')
    return actual


def check_idle(connection, *, artifact_only=False):
    checks = {
        'runs': "status IN ('pending','running')",
        'experimental_campaigns': "state='active'",
        'campaign_attempts': "state IN ('active','completed')",
        'train_execution_sessions': "state IN ('active','completed')",
        'local_execution_jobs': "state IN ('held','calculation_reported')",
    }
    for table, where in checks.items():
        require(connection.execute(text(f'SELECT count(*) FROM {qi(table)} WHERE {where}')).scalar_one() == 0, 'ACTIVE_EXECUTION:' + table)
    gate = connection.execute(text("SELECT owner IS NULL AND db_pid IS NULL AND blocked_reason IS NULL AND process_evidence='{}'::jsonb FROM experiment_execution_gate")).scalar_one()
    require(gate, 'GLOBAL_GATE_NOT_FREE')
    if artifact_only:
        for table in ('stage2_model_publications', 'deployed_model_versions'):
            require(connection.execute(text(f"SELECT count(*) FROM {qi(table)} WHERE status='active'")).scalar_one() == 0, 'ACTIVE_PUBLICATION')


def snapshot(connection):
    tables = set(connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars())
    require(tables == EXPECTED_TABLES, 'UNREVIEWED_TABLE_POLICY')
    require(list(connection.execute(text('SELECT version_num FROM alembic_version')).scalars()) == ['20260922_01'], 'UNREVIEWED_ALEMBIC_REVISION')
    require_e10_schema(connection)
    schemas = list(connection.execute(text("SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema' ORDER BY nspname")).scalars())
    return {
        'schemas': {s: fingerprint(connection, s) for s in schemas},
        'catalogs': {s: normalized_catalog(catalog(connection, s)) for s in schemas},
        'indexes': [list(r) for r in connection.execute(text("SELECT schemaname,indexname,indexdef FROM pg_indexes WHERE schemaname !~ '^pg_' ORDER BY schemaname,indexname"))],
    }


def history_count(snap):
    return sum(snap['schemas']['public'][t]['count'] for t in HISTORY_TABLES)


def verify_clean(connection, original):
    current = snapshot(connection)
    require(history_count(current) == 0, 'HISTORY_REMAINS')
    for table in PROTECTED_TABLES:
        require(current['schemas']['public'][table] == original['schemas']['public'][table], 'PROTECTED_TABLE_CHANGED:' + table)
    require(connection.execute(text("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated")).scalar_one() == 0, 'UNVALIDATED_CONSTRAINT')
    require(connection.execute(text("SELECT count(*) FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid WHERE r.relnamespace='public'::regnamespace AND t.tgenabled<>'O'")).scalar_one() == 0, 'DISABLED_TRIGGER')
    fks = connection.execute(text("""SELECT k.conname, k.conrelid::regclass::text AS child,
        k.confrelid::regclass::text AS parent,
        ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY x(n,i) JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=x.n ORDER BY x.i) AS child_columns,
        ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY x(n,i) JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=x.n ORDER BY x.i) AS parent_columns
        FROM pg_constraint k WHERE k.contype='f' AND k.connamespace='public'::regnamespace""")).mappings()
    count = 0
    for fk in fks:
        # All approved public FKs resolve into the approved public table policy.
        require(fk['child'] in EXPECTED_TABLES and fk['parent'] in EXPECTED_TABLES, 'EXTERNAL_PROTECTED_DEPENDENCY')
        nonnull = ' AND '.join('c.' + qi(a) + ' IS NOT NULL' for a in fk['child_columns'])
        join = ' AND '.join('c.' + qi(a) + '=p.' + qi(b) for a, b in zip(fk['child_columns'], fk['parent_columns']))
        require(connection.execute(text(f"SELECT count(*) FROM {qi(fk['child'])} c WHERE {nonnull} AND NOT EXISTS (SELECT 1 FROM {qi(fk['parent'])} p WHERE {join})")).scalar_one() == 0, 'ORPHAN:' + fk['conname'])
        count += 1
    return {'snapshot': current, 'foreign_keys_checked': count, 'protected_tables_equal': list(PROTECTED_TABLES)}


def bootstrap(connection):
    """Same official legacy DDL + Alembic path as RESET.3; no illustrative seed."""
    require(connection.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one() == 0, 'CANDIDATE_NOT_EMPTY')
    path = Path('/app/malaria_dl_local_project/scripts/init_db.py')
    spec = importlib.util.spec_from_file_location('maintenance_legacy', path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    legacy.ensure_migration_ledger(connection)
    for file in legacy.SQL_FILES:
        if file.name == '004_seed.sql':
            continue
        with connection.connection.driver_connection.cursor() as cursor:
            cursor.execute(file.read_text())
        legacy.record_migration(connection, file, legacy.migration_checksum(file), len(legacy.split_sql_statements(file.read_text())))
    config = Config('/app/alembic.ini')
    config.set_main_option('script_location', '/app/alembic')
    config.attributes['connection'] = connection
    command.upgrade(config, '20260922_01')


def import_protected(source, destination):
    """COPY every column/row; original statuses/hashes must be restored exactly."""
    for table in PROTECTED_TABLES:
        columns = list(source.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"), {'t': table}).scalars())
        if table == 'roles':
            # Only newly seeded candidate roles; no application users/associations yet.
            destination.execute(text('DELETE FROM roles'))
        require(destination.execute(text('SELECT count(*) FROM ' + qi(table))).scalar_one() == 0, 'CANDIDATE_TABLE_NOT_EMPTY')
        selection = ["'DRAFT'::text" if table == 'dataset_versions' and c == 'status' else qi(c) for c in columns]
        with source.connection.driver_connection.cursor() as reader, destination.connection.driver_connection.cursor() as writer:
            with reader.copy(f"COPY (SELECT {','.join(selection)} FROM {qi(table)}) TO STDOUT") as stream, writer.copy(f"COPY {qi(table)} ({','.join(map(qi, columns))}) FROM STDIN") as sink:
                for block in stream:
                    sink.write(block)
    transitions = {'DRAFT': (), 'GENERATED': ('GENERATED',), 'VALIDATED': ('GENERATED', 'VALIDATED'), 'FROZEN': ('GENERATED', 'VALIDATED', 'FROZEN'), 'ARCHIVED': ('ARCHIVED',)}
    for version, state in source.execute(text('SELECT id,status FROM dataset_versions')):
        require(state in transitions, 'UNKNOWN_DATASET_LIFECYCLE')
        for next_state in transitions[state]:
            destination.execute(text('UPDATE dataset_versions SET status=:s WHERE id=:id'), {'s': next_state, 'id': version})
    destination.exec_driver_sql('SET CONSTRAINTS ALL IMMEDIATE')


def rebuild(engine, expected, original, restored_name, candidate_name, recovery_name, report_path):
    """Fence new connections, reverify backup/source, rebuild, reconcile commit.

Backup was already physically restored. Any exception before a confirmed cutover
retains the original DB. A lost commit response never implies rollback.
"""
    admin_engine = create_engine(engine.url.set(database='postgres'))
    result = {'status': 'PREPARING', 'backup_restore_database': restored_name, 'candidate': candidate_name, 'recovery_database': recovery_name}
    swapped = False
    fenced = False
    source_oid = None
    candidate_oid = None
    try:
        with engine.connect().execution_options(postgresql_readonly=True) as source:
            validate_identity(source, expected)
            check_idle(source)
            with admin_engine.connect().execution_options(isolation_level='AUTOCOMMIT') as admin:
                source_oid = admin.execute(text('SELECT oid FROM pg_database WHERE datname=:db'), {'db': expected['database']}).scalar_one()
                result.update(source_oid=source_oid)
                write_json(report_path, result)
                admin.exec_driver_sql('ALTER DATABASE ' + qi(expected['database']) + ' ALLOW_CONNECTIONS false')
                fenced = True
                # This source session is the sole admitted reader; external clients block operation.
                peers = admin.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=:db AND pid<>:pid AND backend_type='client backend'"), {'db': expected['database'], 'pid': source.execute(text('SELECT pg_backend_pid()')).scalar_one()}).scalar_one()
                require(peers == 0, 'EXTERNAL_DATABASE_CONNECTIONS')
                source_oid = admin.execute(text('SELECT oid FROM pg_database WHERE datname=:db'), {'db': expected['database']}).scalar_one()
                source.rollback()
                source.execution_options(isolation_level='REPEATABLE READ', postgresql_readonly=True)
                require(snapshot(source) == original, 'SOURCE_CHANGED_AFTER_BACKUP')
                restored = create_engine(engine.url.set(database=restored_name))
                try:
                    with restored.connect().execution_options(postgresql_readonly=True) as c:
                        require(snapshot(c) == original, 'BACKUP_RESTORE_MISMATCH')
                finally:
                    restored.dispose()
                admin.exec_driver_sql('CREATE DATABASE ' + qi(candidate_name) + ' OWNER ' + qi(expected['user']))
                candidate_oid = admin.execute(text('SELECT oid FROM pg_database WHERE datname=:db'), {'db': candidate_name}).scalar_one()
            candidate = create_engine(engine.url.set(database=candidate_name))
            try:
                with candidate.begin() as destination:
                    bootstrap(destination)
                    import_protected(source, destination)
                    verified = verify_clean(destination, original)
            finally:
                candidate.dispose()
        engine.dispose()  # close source before its name is changed
        result.update(source_oid=source_oid, candidate_oid=candidate_oid, integrity=verified, status='COMMIT_UNCERTAIN')
        write_json(report_path, result)  # durable before COMMIT
        try:
            with admin_engine.begin() as admin:
                admin.exec_driver_sql("SET LOCAL lock_timeout='5s'")
                admin.exec_driver_sql('ALTER DATABASE ' + qi(candidate_name) + ' ALLOW_CONNECTIONS false')
                admin.exec_driver_sql('ALTER DATABASE ' + qi(expected['database']) + ' RENAME TO ' + qi(recovery_name))
                admin.exec_driver_sql('ALTER DATABASE ' + qi(candidate_name) + ' RENAME TO ' + qi(expected['database']))
                admin.exec_driver_sql('ALTER DATABASE ' + qi(expected['database']) + ' ALLOW_CONNECTIONS true')
            result['commit_response_received'] = True
        except Exception:
            result['commit_response_received'] = False
        # Fresh connection: use object identity, not a response or a guessed rollback.
        admin_engine.dispose()  # force a new physical connection after COMMIT
        with admin_engine.connect() as fresh:
            mapping = dict(fresh.execute(text('SELECT datname,oid FROM pg_database WHERE oid IN (:old,:new)'), {'old': source_oid, 'new': candidate_oid}).all())
        swapped = mapping == {expected['database']: candidate_oid, recovery_name: source_oid}
        require(swapped, 'COMMIT_NOT_CONFIRMED_STOP_WRITERS')
        with engine.connect().execution_options(postgresql_readonly=True) as c:
            verified = verify_clean(c, original)
        result.update(status='COMPLETED', integrity=verified, deleted_records=history_count(original), commit_reconciled=True)
        write_json(report_path, result)
        return result
    finally:
        # Only reopen the original if a fresh observation proves it still owns the
        # canonical name. Never infer rollback or swap back after ambiguous COMMIT.
        if fenced and not swapped:
            with admin_engine.connect().execution_options(isolation_level='AUTOCOMMIT') as admin:
                oid = admin.execute(text('SELECT oid FROM pg_database WHERE datname=:db'), {'db': expected['database']}).scalar_one_or_none()
                if oid == source_oid:
                    admin.exec_driver_sql('ALTER DATABASE ' + qi(expected['database']) + ' ALLOW_CONNECTIONS true')
        admin_engine.dispose()
