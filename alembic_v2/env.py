"""Guarded v2-only Alembic environment. No legacy bootstrap or .env loading."""

import os

from sqlalchemy import create_engine, pool

from alembic import context
from alembic_v2.resources import REVISION, load_baseline
from alembic_v2.safety import (
    inspect_isolation,
    read_authorization,
    require,
    verify_connection,
)

config = context.config


def migrate():
    require(
        not context.is_offline_mode(),
        "V2_OFFLINE_EXECUTION_DISABLED_USE_STATIC_VALIDATOR",
    )
    opts = context.get_x_argument(as_dictionary=True)
    url = os.environ.get("PGV2_DATABASE_URL", "")
    target = read_authorization(opts.get("target") or os.environ.get("PGV2_TARGET"), url)
    # All resources and host/volume identity are validated BEFORE connecting.
    manifest, _ = load_baseline()
    inspect_isolation(target)
    require(
        config.attributes.get("connection") is None, "V2_EXTERNAL_CONNECTION_FORBIDDEN"
    )
    engine = create_engine(
        url,
        poolclass=pool.NullPool,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
        isolation_level="READ COMMITTED",
    )
    try:
        with engine.connect() as connection, connection.begin():
            if target.get('authorized_stage') == 'C2.12.2':
                from alembic_v2.disposable import assume_migration_identity
                assume_migration_identity(connection, target)
            verify_connection(connection, target)
            # Transaction-owned serialization. Nothing has been written, including the ledger.
            locked = connection.exec_driver_sql(
                "SELECT pg_try_advisory_xact_lock(101005, 2)"
            ).scalar_one()
            require(locked is True, "V2_MIGRATION_BUSY")
            other_schemas = connection.exec_driver_sql(
                """
                SELECT count(*) FROM pg_namespace
                WHERE nspname NOT IN ('public','pg_catalog','information_schema')
                  AND nspname NOT LIKE 'pg_toast%' AND nspname NOT LIKE 'pg_temp_%'
            """,
                execution_options={"no_parameters": True},
            ).scalar_one()
            require(other_schemas == 0, "V2_UNEXPECTED_APPLICATION_SCHEMA")
            relations = set(
                connection.exec_driver_sql("""
                SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')
            """).scalars()
            )
            expected = {
                e["name"]
                for e in manifest["statements"]
                if e["kind"] in ("table", "view", "sequence")
            }
            expected.update(
                s["sequence"] for s in manifest.get("identity_sequences", [])
            )
            if relations:
                require(
                    relations == expected | {"alembic_version"},
                    "V2_NONEMPTY_OR_PARTIAL_TARGET",
                )
                versions = list(
                    connection.exec_driver_sql(
                        "SELECT version_num FROM public.alembic_version"
                    ).scalars()
                )
                require(versions == [REVISION], "V2_UNKNOWN_OR_LEGACY_REVISION")
                extensions = set(
                    connection.exec_driver_sql(
                        "SELECT extname FROM pg_extension"
                    ).scalars()
                )
                require(
                    extensions == {"plpgsql", "pgcrypto"}, "V2_UNEXPECTED_EXTENSIONS"
                )
            else:
                # An "empty" schema with functions/types/extensions is not an empty installation.
                objects = connection.exec_driver_sql("""
                    SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')
                    OR EXISTS(SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public')
                    OR EXISTS(SELECT 1 FROM pg_extension WHERE extname<>'plpgsql')
                """).scalar_one()
                require(not objects, "V2_NONEMPTY_TARGET_OBJECTS")

            # Check CLI commands before context can create/update alembic_version.
            command = getattr(config.cmd_opts, "cmd", None) if config.cmd_opts else None
            if command:
                require(
                    command[0].__name__ in ("upgrade", "current"), "V2_STAMP_DOWNGRADE_FORBIDDEN"
                )
            context.configure(
                connection=connection,
                target_metadata=None,
                transactional_ddl=True,
                transaction_per_migration=False,
                version_table_schema="public",
            )
            migration_context = context.get_context()
            require(
                migration_context.opts.get("destination_rev") == "head"
                or (command and command[0].__name__ == "current"),
                "V2_ONLY_UPGRADE_HEAD_ALLOWED",
            )
            connection.exec_driver_sql("SET LOCAL search_path = public, pg_catalog")
            connection.info["pg_v2_verified_target"] = target["isolation_id"]
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


migrate()
