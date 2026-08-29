from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "db" / "init"
SEED_SQL = SQL_DIR / "004_seed.sql"
SAFE_CONFIRMATION = "PURGE_DB"
SYSTEM_SCHEMAS = {"information_schema", "pg_catalog", "pg_toast"}

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection, get_database_url, test_connection  # noqa: E402


def quote_identifier(identifier: str) -> str:
    return '"' + str(identifier).replace('"', '""') + '"'


def validate_schema(schema: str) -> None:
    if not schema or schema in SYSTEM_SCHEMAS or schema.startswith("pg_"):
        raise ValueError(f"Schema no permitido para purga: {schema!r}")


def get_connection_config() -> dict:
    database_url = get_database_url()
    parsed_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(parsed_url)
    database = parsed.path.lstrip("/")
    user = unquote(parsed.username or "")
    if parsed.hostname != "db" or (parsed.port is not None and parsed.port != 5432):
        raise RuntimeError("La purga solo permite PostgreSQL Docker en db:5432")
    if not database or not user:
        raise RuntimeError("DATABASE_URL debe identificar usuario y base canónica")

    return {
        "host": parsed.hostname,
        "port": str(parsed.port or 5432),
        "database": database,
        "user": user,
    }


def get_user_tables(connection, schema: str = "public") -> list[str]:
    validate_schema(schema)
    rows = connection.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ),
        {"schema": schema},
    ).mappings().all()
    return [row["table_name"] for row in rows]


def build_truncate_sql(tables: list[str], schema: str = "public") -> str:
    validate_schema(schema)
    if not tables:
        raise ValueError("No hay tablas para truncar.")

    table_list = ", ".join(
        f"{quote_identifier(schema)}.{quote_identifier(table)}" for table in tables
    )
    return f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"


def create_db_backup(config: dict, backup_dir: Path) -> Path:
    del config, backup_dir
    verified_backup = os.getenv("CAPSTONE_VERIFIED_BACKUP", "").strip()
    if not verified_backup:
        raise RuntimeError(
            "--backup-before requiere el wrapper Docker scripts/db/purge.sh"
        )
    return Path(verified_backup)


def split_sql_statements(sql: str) -> list[str]:
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False
    previous = ""

    for char in sql:
        if char == "'" and not in_double_quote and previous != "\\":
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and previous != "\\":
            in_double_quote = not in_double_quote

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        previous = char

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def reseed_database(connection) -> int:
    if not SEED_SQL.exists():
        raise FileNotFoundError(f"No existe archivo seed requerido: {SEED_SQL}")

    statements = split_sql_statements(SEED_SQL.read_text(encoding="utf-8"))
    for statement in statements:
        connection.execute(text(statement))
    return len(statements)


def purge_database_data(
    execute: bool,
    confirm: str | None,
    schema: str,
    backup_before: bool,
    backup_dir: Path,
    reseed: bool,
    verbose: bool = False,
) -> dict:
    validate_schema(schema)
    if execute and confirm != SAFE_CONFIRMATION:
        raise ValueError(
            f"Confirmación inválida. Para ejecutar use --confirm {SAFE_CONFIRMATION}."
        )
    if execute and os.getenv("PURGE_DB_ALLOW_EXECUTION") != "1":
        raise ValueError("PURGE_DB_ALLOW_EXECUTION=1 es obligatorio para ejecutar")

    config = get_connection_config()
    connection_info = test_connection()
    if (
        connection_info.get("database_name") != config["database"]
        or connection_info.get("user_name") != config["user"]
    ):
        raise RuntimeError("La conexión no corresponde a la identidad Docker canónica")
    backup_path = None
    if execute and backup_before:
        backup_path = create_db_backup(config, backup_dir)

    with get_connection() as connection:
        tables = get_user_tables(connection, schema=schema)
        truncate_sql = build_truncate_sql(tables, schema) if tables else None

        if execute and tables:
            if verbose:
                print(f"SQL: {truncate_sql}")
            connection.execute(text(truncate_sql))

        seed_statements = 0
        if execute and reseed:
            seed_statements = reseed_database(connection)

    return {
        "mode": "EXECUTE" if execute else "DRY RUN",
        "database": connection_info.get("database_name"),
        "user": connection_info.get("user_name"),
        "schema": schema,
        "tables": tables,
        "tables_count": len(tables),
        "backup_path": None if backup_path is None else str(backup_path),
        "executed": bool(execute),
        "truncate_sql": truncate_sql,
        "restart_identity": bool(tables),
        "cascade": bool(tables),
        "reseed": bool(reseed),
        "seed_statements": seed_statements,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Purga datos de PostgreSQL sin eliminar esquema, tablas, índices ni vistas."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Modo seguro por defecto.")
    mode.add_argument("--execute", action="store_true", help="Ejecuta la purga real.")
    parser.add_argument("--confirm", default=None, help=f"Debe ser {SAFE_CONFIRMATION}.")
    parser.add_argument("--schema", default="public")
    parser.add_argument("--backup-before", action="store_true")
    parser.add_argument("--backup-dir", default="backups/db")
    parser.add_argument("--reseed", action="store_true", help="Ejecuta db/init/004_seed.sql tras purgar.")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def print_summary(result: dict) -> None:
    print(f"Modo: {result['mode']}")
    print(f"Base de datos detectada: {result['database']} (user={result['user']})")
    print(f"Schema objetivo: {result['schema']}")
    if result.get("backup_path"):
        print(f"Backup: creado en {result['backup_path']}")
    elif result["mode"] == "EXECUTE":
        print("Backup: no solicitado")
    else:
        print("Backup: no creado en dry-run")

    print("Tablas encontradas:")
    if result["tables"]:
        for table in result["tables"]:
            print(f"- {table}")
    else:
        print("- ninguna")

    if result["mode"] == "DRY RUN":
        print("No se eliminaron datos. Para ejecutar realmente, use:")
        print(
            "PURGE_DB_ALLOW_EXECUTION=1 scripts/db/purge.sh --execute "
            f"--confirm {SAFE_CONFIRMATION}"
        )
        return

    print("Tablas truncadas:")
    for table in result["tables"]:
        print(f"- {table}")
    print(f"Secuencias reiniciadas: {'sí' if result['restart_identity'] else 'no'}")
    print(f"Cascade: {'sí' if result['cascade'] else 'no'}")
    if result.get("reseed"):
        print(f"Seed ejecutado: sí ({result['seed_statements']} sentencias)")
    print("Estado: purga completada correctamente")


def main():
    args = parse_args()
    try:
        result = purge_database_data(
            execute=bool(args.execute),
            confirm=args.confirm,
            schema=args.schema,
            backup_before=bool(args.backup_before),
            backup_dir=Path(args.backup_dir),
            reseed=bool(args.reseed),
            verbose=bool(args.verbose),
        )
        print_summary(result)
    except Exception as exc:
        print("Error purgando datos de PostgreSQL.")
        print(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
