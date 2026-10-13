"""Apply the authorized EXEC.1 change through the active Alembic environment."""
import os
from alembic import context
from sqlalchemy import create_engine, pool


def migrate_exec1() -> None:
    engine = create_engine(os.environ['PGV2_DATABASE_URL'],poolclass=pool.NullPool,hide_parameters=True)
    try:
        with engine.begin() as connection:
            if os.environ.get('PGV2_SET_ROLE') == 'capstone_v2_migrator':
                connection.exec_driver_sql('SET LOCAL ROLE capstone_v2_migrator')
            connection.exec_driver_sql('SELECT pg_advisory_xact_lock(101005,2)')
            context.configure(connection=connection,transactional_ddl=True,version_table_schema='public')
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
