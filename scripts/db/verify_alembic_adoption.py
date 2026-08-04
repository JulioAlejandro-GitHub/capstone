#!/usr/bin/env python3
import argparse
import hashlib
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend_api"))
from app.config import get_settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-stamp", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    url = settings.database_url
    assert_capstone_database(settings)
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise SystemExit(f"Cadena Alembic incompatible; heads detectados: {heads}")
    revisions = list(scripts.walk_revisions())
    if any(
        revision.is_branch_point or revision.is_merge_point
        for revision in revisions
    ):
        raise SystemExit("Cadena Alembic incompatible; se esperaba historia lineal")
    known_revisions = {revision.revision for revision in revisions}
    sql_paths = sorted(
        (ROOT / "malaria_dl_local_project" / "db" / "init").glob(
            "[0-9][0-9][0-9]_*.sql"
        )
    )
    expected_checksums = {
        sql_path.name: hashlib.sha256(sql_path.read_bytes()).hexdigest()
        for sql_path in sql_paths
    }
    required = {
        "runs",
        "model_versions",
        "stage2_model_publications",
        "schema_migrations",
    }
    with create_engine(normalize_sqlalchemy_url(url)).connect() as connection:
        actual_database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()
        assert_capstone_database(settings, actual_database)
        tables = set(connection.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        )).scalars())
        missing = required - tables
        recorded_checksums = (
            dict(connection.execute(text(
                "SELECT migration_id, checksum FROM schema_migrations"
            )).all())
            if "schema_migrations" in tables
            else {}
        )
        has_alembic = "alembic_version" in tables
        version = (
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            if has_alembic
            else None
        )
    missing_migrations = sorted(
        expected_checksums.keys() - recorded_checksums.keys()
    )
    checksum_mismatches = sorted(
        migration_id
        for migration_id, checksum in expected_checksums.items()
        if recorded_checksums.get(migration_id) not in {None, checksum}
    )
    if missing or missing_migrations or checksum_mismatches:
        raise SystemExit(
            "Esquema SQL incompatible; "
            f"tablas faltantes={sorted(missing)}, "
            f"migraciones faltantes={missing_migrations}, "
            f"checksums distintos={checksum_mismatches}"
        )
    if args.pre_stamp and version is not None:
        raise SystemExit("La base ya posee alembic_version; adopción pre-stamp rechazada")
    if not args.pre_stamp and version not in known_revisions:
        raise SystemExit(
            f"alembic_version incompatible: {version!r}; "
            f"se esperaba una revisión ancestro del head {heads[0]}"
        )
    print(f"Adopción Alembic válida en {actual_database}: {version or 'pre-stamp'}")


if __name__ == "__main__":
    main()
