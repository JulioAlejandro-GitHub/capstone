#!/usr/bin/env python3
"""Validate a fresh install inside one disposable schema of the Capstone DB.

The script never targets ``public`` and always removes its explicitly generated
``capstone_test_*`` schema. It applies the immutable SQL ledger followed by the
full Alembic chain, checks seed idempotence, compares structural fingerprints,
and exercises the FastAPI auth/readiness surface against the fresh schema.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend_api"
ML_PROJECT = ROOT / "malaria_dl_local_project"
for import_root in (BACKEND, ML_PROJECT):
    sys.path.insert(0, str(import_root))

from app.config import Settings, reset_settings_cache  # noqa: E402
from app.database_safety import (  # noqa: E402
    assert_capstone_database,
    assert_safe_temporary_schema,
)
from app.db import get_engine, normalize_sqlalchemy_url  # noqa: E402
from app.security import hash_password  # noqa: E402
from scripts.init_db import (  # type: ignore[import-not-found]  # noqa: E402
    SQL_DIR,
    SQL_FILES,
    ensure_migration_ledger,
    execute_pending_sql_file,
    execute_sql_file,
)


CATALOG_QUERIES = {
    "relations": """
        SELECT c.relkind,c.relname,COALESCE(obj_description(c.oid,'pg_class'),'')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=:schema AND c.relkind IN ('r','p','v','m','S')
          AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.classid='pg_class'::regclass AND d.objid=c.oid AND d.deptype='e'
          )
        ORDER BY c.relkind,c.relname
    """,
    "columns": """
        SELECT c.relname,a.attnum,a.attname,
          format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
          COALESCE(pg_get_expr(d.adbin,d.adrelid),''),
          COALESCE(col_description(c.oid,a.attnum),'')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_attribute a ON a.attrelid=c.oid
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE n.nspname=:schema AND c.relkind IN ('r','p','v','m')
          AND a.attnum>0 AND NOT a.attisdropped
        ORDER BY c.relname,a.attnum
    """,
    "constraints": """
        SELECT c.relname,con.conname,con.contype,con.convalidated,
          pg_get_constraintdef(con.oid,true)
        FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=:schema
        ORDER BY c.relname,con.conname
    """,
    "indexes": """
        SELECT table_rel.relname,index_rel.relname,idx.indisunique,idx.indisprimary,
          idx.indisvalid,pg_get_indexdef(index_rel.oid)
        FROM pg_index idx JOIN pg_class index_rel ON index_rel.oid=idx.indexrelid
        JOIN pg_class table_rel ON table_rel.oid=idx.indrelid
        JOIN pg_namespace n ON n.oid=table_rel.relnamespace
        WHERE n.nspname=:schema
        ORDER BY table_rel.relname,index_rel.relname
    """,
    "views": """
        SELECT c.relname,c.relkind,pg_get_viewdef(c.oid,true)
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=:schema AND c.relkind IN ('v','m')
        ORDER BY c.relname
    """,
    "sequences": """
        SELECT c.relname,s.seqstart,s.seqincrement,s.seqmax,s.seqmin,s.seqcache,s.seqcycle
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_sequence s ON s.seqrelid=c.oid
        WHERE n.nspname=:schema
        ORDER BY c.relname
    """,
    "functions": """
        SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind,
          p.provolatile,p.prosecdef,COALESCE(obj_description(p.oid,'pg_proc'),''),
          pg_get_functiondef(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname=:schema
          AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e'
          )
        ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)
    """,
    "triggers": """
        SELECT c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid,true)
        FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=:schema AND NOT t.tgisinternal
        ORDER BY c.relname,t.tgname
    """,
    "types": """
        SELECT t.typname,t.typtype,COALESCE(format_type(t.typbasetype,t.typtypmod),''),
          COALESCE(obj_description(t.oid,'pg_type'),'')
        FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
        WHERE n.nspname=:schema AND t.typtype IN ('d','e','r','m')
          AND NOT EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.classid='pg_type'::regclass AND d.objid=t.oid AND d.deptype='e'
          )
        ORDER BY t.typname
    """,
    "policies": """
        SELECT tablename,policyname,permissive,roles,cmd,qual,with_check
        FROM pg_policies WHERE schemaname=:schema
        ORDER BY tablename,policyname
    """,
}


def _normalize(value: Any, schema: str) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize(item, schema) for item in value]
    rendered = str(value)
    rendered = rendered.replace(f'"{schema}".', "<schema>.")
    rendered = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(schema)}\.", "<schema>.", rendered)
    return " ".join(rendered.split())


def catalog_snapshot(connection, schema: str) -> dict[str, list[list[Any]]]:
    quoted = connection.dialect.identifier_preparer.quote(schema)
    connection.exec_driver_sql(f"SET LOCAL search_path TO {quoted}, pg_catalog")
    snapshot: dict[str, list[list[Any]]] = {}
    for category, query in CATALOG_QUERIES.items():
        rows = connection.execute(text(query), {"schema": schema}).all()
        snapshot[category] = [_normalize(list(row), schema) for row in rows]
    return snapshot


def fingerprint(snapshot: dict[str, list[list[Any]]]) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def projected_public_snapshot(admin_engine) -> tuple[str | None, str, dict[str, list[list[Any]]]]:
    """Project pending Alembic DDL in one outer transaction, then roll it back."""

    alembic_config = Config(str(ROOT / "alembic.ini"))
    with admin_engine.connect() as connection:
        before = connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one_or_none()
        connection.rollback()
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET LOCAL search_path TO public, pg_catalog")
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")
            projected_head = connection.execute(
                text("SELECT version_num FROM public.alembic_version")
            ).scalar_one()
            projected = catalog_snapshot(connection, "public")
        finally:
            transaction.rollback()
    with admin_engine.connect() as connection:
        after = connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalar_one_or_none()
    if after != before:
        raise RuntimeError("El preflight transaccional alteró alembic_version persistente")
    return before, projected_head, projected


def seed_snapshot(connection) -> dict[str, Any]:
    return {
        "experiments": connection.execute(text("""
          SELECT name FROM experiments WHERE metadata @> '{"seeded":true}'::jsonb ORDER BY name
        """)).scalars().all(),
        "datasets": connection.execute(text("""
          SELECT name FROM datasets WHERE metadata @> '{"seeded":true}'::jsonb ORDER BY name
        """)).scalars().all(),
        "splits": [list(row) for row in connection.execute(text("""
          SELECT d.name,s.split_name,s.num_samples FROM dataset_splits s
          JOIN datasets d ON d.id=s.dataset_id
          WHERE s.metadata @> '{"seeded":true}'::jsonb ORDER BY d.name,s.split_name
        """)).all()],
        "models": connection.execute(text("""
          SELECT name FROM models WHERE metadata @> '{"seeded":true}'::jsonb ORDER BY name
        """)).scalars().all(),
    }


def exercise_fastapi(schema: str, isolated_engine) -> dict[str, int]:
    username = f"fresh_{uuid4().hex[:12]}"
    password = f"Fresh-{uuid4().hex}-9!"
    with isolated_engine.begin() as connection:
        user_id = uuid4()
        connection.execute(
            text("""
              INSERT INTO users(id,username,password_hash)
              VALUES(:id,:username,:password_hash)
            """),
            {"id": user_id, "username": username, "password_hash": hash_password(password)},
        )
        connection.execute(
            text("""
              INSERT INTO user_roles(user_id,role_id)
              SELECT :id,id FROM roles WHERE name='administrator'
            """),
            {"id": user_id},
        )

    previous_pgoptions = os.environ.get("PGOPTIONS")
    os.environ["PGOPTIONS"] = f"-c search_path={schema},public"
    reset_settings_cache()
    get_engine.cache_clear()
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            statuses = {
                "health": client.get("/health").status_code,
                "ready": client.get("/ready").status_code,
                "openapi": client.get("/openapi.json").status_code,
            }
            login = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
            )
            statuses["login"] = login.status_code
            token = login.json().get("access_token") if login.status_code == 200 else None
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            statuses["session"] = client.get("/api/v1/auth/me", headers=headers).status_code
            statuses["history"] = client.get(
                "/api/v1/scientific/workflows", headers=headers
            ).status_code
            statuses["stage2"] = client.get(
                "/api/stage2/productive-model-availability", headers=headers
            ).status_code
    finally:
        get_engine.cache_clear()
        reset_settings_cache()
        if previous_pgoptions is None:
            os.environ.pop("PGOPTIONS", None)
        else:
            os.environ["PGOPTIONS"] = previous_pgoptions
    return statuses


def run_backend_integration(schema: str) -> int:
    environment = os.environ.copy()
    environment.update(
        {
            "PGOPTIONS": f"-c search_path={schema},public",
            "PYTHONPATH": str(BACKEND),
            "TEST_EXECUTION": "true",
            "TEST_ISOLATION_MODE": "transaction",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "backend_api/tests",
            "-m",
            "requires_local_postgres",
            "-k",
            "not test_no_temporary_schema_residue",
            "-q",
            "-rs",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-backend-integration",
        action="store_true",
        help="Run PostgreSQL-marked backend tests against the disposable schema.",
    )
    args = parser.parse_args()
    settings = Settings.from_env()
    schema = assert_safe_temporary_schema(
        settings, f"capstone_test_fresh_{uuid4().hex[:12]}"
    )
    url = normalize_sqlalchemy_url(settings.database_url)
    admin_engine = create_engine(url, future=True)
    isolated_engine = create_engine(
        url,
        connect_args={
            "connect_timeout": settings.database_connect_timeout,
            "options": f"-csearch_path={schema},public",
        },
        future=True,
    )
    quoted = admin_engine.dialect.identifier_preparer.quote(schema)
    created = False
    try:
        with admin_engine.begin() as connection:
            actual = connection.execute(text("SELECT current_database()")).scalar_one()
            assert_capstone_database(settings, actual)
            exists = connection.execute(
                text("SELECT 1 FROM pg_namespace WHERE nspname=:schema"),
                {"schema": schema},
            ).first()
            if exists:
                raise RuntimeError("El schema temporal generado ya existe")
            connection.exec_driver_sql(f"CREATE SCHEMA {quoted}")
            created = True

        with isolated_engine.begin() as connection:
            if connection.execute(text("SELECT current_schema()")).scalar_one() != schema:
                raise RuntimeError("search_path temporal no quedó aislado")
            ensure_migration_ledger(connection)
            for sql_path in SQL_FILES:
                execute_pending_sql_file(connection, sql_path)

        alembic_config = Config(str(ROOT / "alembic.ini"))
        with isolated_engine.connect() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")
            connection.commit()

        with isolated_engine.begin() as connection:
            head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            seeds_before = seed_snapshot(connection)
            execute_sql_file(connection, SQL_DIR / "004_seed.sql")
            seeds_after = seed_snapshot(connection)
            if seeds_before != seeds_after:
                raise RuntimeError("Los seeds obligatorios no son idempotentes")
            fresh_snapshot = catalog_snapshot(connection, schema)

        with admin_engine.begin() as connection:
            current_public_snapshot = catalog_snapshot(connection, "public")
            extensions = connection.execute(text("""
              SELECT extname,extversion FROM pg_extension ORDER BY extname
            """)).all()

        public_revision, projected_head, public_snapshot = projected_public_snapshot(
            admin_engine
        )
        if projected_head != head:
            raise RuntimeError("Fresh install y proyección de public resolvieron heads distintos")
        fresh_hash = fingerprint(fresh_snapshot)
        public_hash = fingerprint(public_snapshot)
        differences = {
            category: {
                "public": len(public_snapshot[category]),
                "fresh": len(fresh_snapshot[category]),
            }
            for category in CATALOG_QUERIES
            if public_snapshot[category] != fresh_snapshot[category]
        }
        statuses = exercise_fastapi(schema, isolated_engine)
        integration_exit = (
            run_backend_integration(schema)
            if args.with_backend_integration
            else None
        )
        result = {
            "schema": schema,
            "alembic_head": head,
            "persistent_public_revision": public_revision,
            "pending_public_migration": public_revision != head,
            "current_public_fingerprint": fingerprint(current_public_snapshot),
            "projected_public_fingerprint": public_hash,
            "fresh_fingerprint": fresh_hash,
            "schema_match": not differences,
            "differences": differences,
            "seed_counts": {key: len(value) for key, value in seeds_after.items()},
            "extensions": [list(row) for row in extensions],
            "fastapi_statuses": statuses,
            "backend_integration_exit": integration_exit,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if (
            differences
            or any(status != 200 for status in statuses.values())
            or integration_exit not in {None, 0}
        ):
            return 2
        return 0
    finally:
        isolated_engine.dispose()
        if created:
            with admin_engine.begin() as connection:
                assert_capstone_database(
                    settings,
                    connection.execute(text("SELECT current_database()")).scalar_one(),
                )
                assert_safe_temporary_schema(settings, schema)
                connection.exec_driver_sql(f"DROP SCHEMA {quoted} CASCADE")
        admin_engine.dispose()
        print(f"temporary_schema_removed={schema}")


if __name__ == "__main__":
    raise SystemExit(main())
