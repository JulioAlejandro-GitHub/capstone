"""Bounded follow-up migration for an already-installed v2 application database.

Unlike baseline provisioning this path cannot initialize or replace a database.
It accepts only pg_v2_baseline -> cell_activation_v1 -> cell_checkpoint_reuse_v2, in one transaction.
"""
import os
from sqlalchemy import create_engine, pool
from alembic import context
from alembic.script import ScriptDirectory
from alembic_v2.safety import require


def migrate_activation(config, options):
    url = os.environ.get('PGV2_DATABASE_URL', '')
    expected_database = options.get('activation_database')
    require(bool(url) and bool(expected_database), 'CELL_MIGRATION_EXPLICIT_TARGET_REQUIRED')
    command = getattr(getattr(config, 'cmd_opts', None), 'cmd', None)
    require(command and command[0].__name__ == 'upgrade', 'CELL_MIGRATION_UPGRADE_ONLY')
    require(ScriptDirectory.from_config(config).get_current_head() == 'cell_checkpoint_reuse_v2', 'CELL_MIGRATION_UNEXPECTED_HEAD')
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    try:
        with engine.connect() as connection, connection.begin():
            require(connection.exec_driver_sql('SELECT current_database()').scalar_one() == expected_database,
                    'CELL_MIGRATION_DATABASE_MISMATCH')
            require(170000 <= int(connection.exec_driver_sql('SHOW server_version_num').scalar_one()) < 180000,
                    'CELL_MIGRATION_POSTGRES17_REQUIRED')
            require(connection.exec_driver_sql('SELECT pg_try_advisory_xact_lock(101005,2)').scalar_one(),
                    'CELL_MIGRATION_BUSY')
            if os.environ.get('PGV2_SET_ROLE') == 'capstone_v2_migrator':
                connection.exec_driver_sql('SET LOCAL ROLE capstone_v2_migrator')
            versions = connection.exec_driver_sql('SELECT version_num FROM public.alembic_version').scalars().all()
            require(versions in (['pg_v2_baseline'], ['cell_activation_v1'], ['cell_checkpoint_reuse_v2']), 'CELL_MIGRATION_UNKNOWN_REVISION')
            context.configure(connection=connection, transactional_ddl=True, version_table_schema='public')
            require(context.get_context().opts.get('destination_rev') == 'head', 'CELL_MIGRATION_HEAD_ONLY')
            connection.exec_driver_sql('SET LOCAL search_path=public,pg_catalog')
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
