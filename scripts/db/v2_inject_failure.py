"""Test-only SQLAlchemy hook. Does not change or bypass baseline/identity checks."""

import sys

from alembic.config import CommandLine
from sqlalchemy import event
from sqlalchemy.engine import Engine

count = 0


@event.listens_for(Engine, "after_cursor_execute")
def fail_after_real_ddl(connection, cursor, statement, parameters, context, many):
    global count
    if statement.lstrip().upper().startswith(("CREATE ", "ALTER ")):
        count += 1
        if count == 500:
            # A real database error aborts the PostgreSQL transaction after substantial DDL.
            print("V2_INJECTED_FAILURE_AFTER_500", file=sys.stderr, flush=True)
            cursor.execute("""SELECT json_build_object(
                'public_tables',(SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r'),
                'public_functions',(SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace),
                'head_rows',(SELECT count(*) FROM public.alembic_version))""")
            print(
                "STATE_BEFORE_FAILURE",
                cursor.fetchone()[0],
                file=sys.stderr,
                flush=True,
            )
            cursor.execute("SELECT 1/0")


CommandLine().main(
    argv=["-c", "alembic_v2.ini", "-x", "target=" + sys.argv[1], "upgrade", "head"]
)
