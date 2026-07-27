#!/usr/bin/env python3
"""Run pending Alembic upgrades on one shared PostgreSQL transaction and roll back."""
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend_api"))

from app.config import get_settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url


def main() -> None:
    settings = get_settings()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    config = Config(str(ROOT / "alembic.ini"))
    with engine.connect() as connection:
        actual = connection.execute(text("SELECT current_database()")).scalar_one()
        assert_capstone_database(settings, actual)
        before = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        transaction = connection.begin_nested() if connection.in_transaction() else connection.begin()
        try:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            print(f"Preflight transaccional válido: {before} -> {head}; se ejecutará rollback")
        finally:
            transaction.rollback()
    with engine.connect() as connection:
        after = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    if after != before:
        raise SystemExit("ERROR: la revisión persistente cambió durante el preflight")
    print(f"Rollback confirmado; revisión persistente: {after}")


if __name__ == "__main__":
    main()
