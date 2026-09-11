#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text


def resolve_capstone_root(environ=None, script_file=None):
    environ = os.environ if environ is None else environ
    if "CAPSTONE_ROOT" in environ:
        raw = environ["CAPSTONE_ROOT"]
        if not raw or not Path(raw).is_absolute():
            raise SystemExit("CAPSTONE_ROOT_INVALID")
        root = Path(raw)
    else:
        location = script_file if script_file is not None else globals().get("__file__")
        if (
            not location
            or str(location).startswith("<")
            or not Path(location).is_file()
        ):
            raise SystemExit("CAPSTONE_ROOT_REQUIRED_FOR_STDIN")
        path = Path(location).resolve()
        if len(path.parents) < 3:
            raise SystemExit("CAPSTONE_SCRIPT_LOCATION_INVALID")
        root = path.parents[2]
    if (
        not root.is_dir()
        or not (root / "alembic.ini").is_file()
        or not (root / "alembic").is_dir()
    ):
        raise SystemExit("CAPSTONE_ROOT_INVALID")
    return root.resolve()


ROOT = resolve_capstone_root()
sys.path.insert(0, str(ROOT / "backend_api"))


def _scripts():
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def _linear_head() -> str:
    scripts = _scripts()
    heads = scripts.get_heads()
    revisions = list(scripts.walk_revisions())
    if len(heads) != 1 or any(
        revision.is_branch_point or revision.is_merge_point for revision in revisions
    ):
        raise SystemExit("Historial Alembic incompatible: se requiere una línea única")
    return heads[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-stamp", action="store_true")
    args = parser.parse_args()
    from app.config import get_settings
    from app.database_safety import assert_capstone_database
    from app.db import normalize_sqlalchemy_url

    settings = get_settings()
    url = settings.database_url
    assert_capstone_database(settings)
    required = {
        "runs",
        "model_versions",
        "stage2_model_publications",
        "schema_migrations",
    }
    with create_engine(normalize_sqlalchemy_url(url)).connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        actual_database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()
        assert_capstone_database(settings, actual_database)
        tables = set(
            connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            ).scalars()
        )
        missing = required - tables
        final = connection.execute(
            text(
                "SELECT checksum FROM schema_migrations WHERE migration_id='029_stage2_model_publications.sql'"
            )
        ).first()
        has_alembic = "alembic_version" in tables
        version = (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            if has_alembic
            else None
        )
    if missing or not final:
        raise SystemExit(
            f"Esquema incompatible; faltan tablas/migración final: {sorted(missing)}"
        )
    if args.pre_stamp and version is not None:
        raise SystemExit(
            "La base ya posee alembic_version; adopción pre-stamp rechazada"
        )
    _linear_head()
    scripts = _scripts()
    compatible_versions = {revision.revision for revision in scripts.walk_revisions()}
    if not args.pre_stamp and version not in compatible_versions:
        raise SystemExit("alembic_version incompatible")
    print(f"Adopción Alembic válida en {actual_database}: {version or 'pre-stamp'}")


if __name__ == "__main__":
    main()
