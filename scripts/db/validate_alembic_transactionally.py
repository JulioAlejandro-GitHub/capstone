#!/usr/bin/env python3
"""Run pending Alembic upgrades on one shared PostgreSQL transaction and roll back."""

import os
import sys
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command


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


def main() -> None:
    import argparse

    argparse.ArgumentParser(description=__doc__).parse_args()
    from app.config import get_settings
    from app.database_safety import assert_capstone_database
    from app.db import normalize_sqlalchemy_url

    settings = get_settings()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    with engine.connect() as connection:
        actual = connection.execute(text("SELECT current_database()")).scalar_one()
        assert_capstone_database(settings, actual)
        before = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        transaction = (
            connection.begin_nested()
            if connection.in_transaction()
            else connection.begin()
        )
        try:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            head = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            print(
                f"Preflight transaccional válido: {before} -> {head}; se ejecutará rollback"
            )
        finally:
            transaction.rollback()
    with engine.connect() as connection:
        after = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
    if after != before:
        raise SystemExit("ERROR: la revisión persistente cambió durante el preflight")
    print(f"Rollback confirmado; revisión persistente: {after}")


if __name__ == "__main__":
    main()
