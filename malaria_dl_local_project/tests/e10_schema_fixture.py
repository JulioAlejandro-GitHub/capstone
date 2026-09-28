"""Existing E10 migration + Alembic metadata, disposable schemas exclusively."""
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from test_campaigns_postgres import migration


def install_e10(c):
    schema = c.execute(text('SELECT current_schema()')).scalar_one()
    assert schema.startswith('capstone_test_e4_'), schema
    mod = migration('20260922_01_result_events')
    mod.op = Operations(MigrationContext.configure(c))
    mod.upgrade()
    # Operations.upgrade fixtures do not execute Alembic's version bookkeeping.
    c.execute(text('CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY)'))
    c.execute(text("INSERT INTO alembic_version VALUES ('20260922_01')"))
