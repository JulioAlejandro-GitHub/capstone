import hashlib
import json
import re
import sys
from pathlib import Path

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection, test_connection


SQL_DIR = PROJECT_ROOT / "db" / "init"
REQUIRED_SQL_FILES = [
    SQL_DIR / "001_schema.sql",
    SQL_DIR / "002_indexes.sql",
    SQL_DIR / "003_views.sql",
    SQL_DIR / "004_seed.sql",
]
SQL_FILES = sorted(SQL_DIR.glob("[0-9][0-9][0-9]_*.sql"))
LEGACY_BASELINE_FILES = [
    sql_path
    for sql_path in SQL_FILES
    if int(sql_path.name.split("_", 1)[0]) <= 22
]


class SqlFileExecutionError(RuntimeError):
    pass


class MigrationChecksumMismatchError(RuntimeError):
    pass


def statement_preview(statement, max_length=500):
    compact = " ".join(statement.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def split_sql_statements(sql):
    """Divide SQL PostgreSQL sin cortar strings, comentarios ni bloques dollar-quoted."""
    statements = []
    current = []
    in_single_quote = False
    in_escape_string = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag = None
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if dollar_tag is not None:
            if sql.startswith(dollar_tag, index):
                current.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
            else:
                current.append(char)
                index += 1
            continue

        if in_single_quote:
            current.append(char)
            if in_escape_string and char == "\\" and next_char:
                current.append(next_char)
                index += 2
                continue
            if char == "'":
                if next_char == "'":
                    current.append(next_char)
                    index += 2
                    continue
                in_single_quote = False
                in_escape_string = False
            index += 1
            continue

        if in_double_quote:
            current.append(char)
            if char == '"':
                if next_char == '"':
                    current.append(next_char)
                    index += 2
                    continue
                in_double_quote = False
            index += 1
            continue

        if char == "-" and next_char == "-":
            current.extend((char, next_char))
            in_line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            current.extend((char, next_char))
            in_block_comment = True
            index += 2
            continue
        if char == "'":
            current.append(char)
            in_single_quote = True
            previous_char = sql[index - 1] if index > 0 else ""
            prefix_char = sql[index - 2] if index > 1 else ""
            in_escape_string = previous_char in {"e", "E"} and not (
                prefix_char.isalnum() or prefix_char == "_"
            )
            index += 1
            continue
        if char == '"':
            current.append(char)
            in_double_quote = True
            index += 1
            continue
        if char == "$":
            match = re.match(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$", sql[index:])
            if match:
                dollar_tag = match.group(0)
                current.append(dollar_tag)
                index += len(dollar_tag)
                continue

        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def migration_checksum(sql_path):
    return hashlib.sha256(sql_path.read_bytes()).hexdigest()


def ensure_migration_ledger(connection):
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                execution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                CONSTRAINT chk_schema_migrations_checksum_sha256
                    CHECK (checksum ~ '^[0-9a-f]{64}$')
            )
            """
        )
    )


def recorded_migration_checksum(connection, migration_id):
    row = connection.execute(
        text(
            """
            SELECT checksum
            FROM schema_migrations
            WHERE migration_id = :migration_id
            """
        ),
        {"migration_id": migration_id},
    ).first()
    return str(row[0]) if row else None


def record_migration(
    connection,
    sql_path,
    checksum,
    statement_count,
    *,
    baseline=False,
):
    metadata = {
        "path": str(sql_path.relative_to(PROJECT_ROOT)),
        "runner": "scripts/init_db.py",
        "statement_count": statement_count,
        "baseline": bool(baseline),
    }
    connection.execute(
        text(
            """
            INSERT INTO schema_migrations (
                migration_id, checksum, execution_metadata
            )
            VALUES (
                :migration_id, :checksum, CAST(:execution_metadata AS jsonb)
            )
            """
        ),
        {
            "migration_id": sql_path.name,
            "checksum": checksum,
            "execution_metadata": json.dumps(metadata, ensure_ascii=False),
        },
    )


def legacy_schema_is_complete(connection):
    """Reconoce el esquema previo a 023 sin asumir que una BD vacía está migrada."""
    row = connection.execute(
        text(
            """
            SELECT
                to_regclass('public.runs') IS NOT NULL
                AND to_regclass('public.model_versions') IS NOT NULL
                AND to_regclass('public.artifacts') IS NOT NULL
                AND to_regclass('public.predictions') IS NOT NULL
                AND to_regclass('public.run_io_records') IS NOT NULL
                AND to_regclass('public.run_threshold_calibration') IS NOT NULL
                AND to_regclass('public.run_lineage') IS NOT NULL
                AND to_regclass('public.vw_run_dashboard') IS NOT NULL
                AND to_regclass('public.vw_case_level_explainability') IS NOT NULL
                AND to_regclass('public.vw_uploaded_predictions') IS NOT NULL
                AND to_regclass('public.vw_dataset_browser_summary') IS NOT NULL
                AND to_regclass('public.vw_visual_explainability_audit') IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'runs'
                      AND column_name = 'execution_type'
                )
                AND EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'runs'
                      AND column_name = 'max_epochs'
                ) AS is_complete
            """
        )
    ).first()
    return bool(row and row[0])


def baseline_legacy_migrations(connection):
    """Registra 001-022 ya instaladas sin reejecutarlas sobre datos existentes."""
    row = connection.execute(text("SELECT COUNT(*) FROM schema_migrations")).first()
    if row and int(row[0]) > 0:
        return False
    if not legacy_schema_is_complete(connection):
        return False

    for sql_path in LEGACY_BASELINE_FILES:
        sql = sql_path.read_text(encoding="utf-8")
        record_migration(
            connection,
            sql_path,
            migration_checksum(sql_path),
            len(split_sql_statements(sql)),
            baseline=True,
        )
    print(
        "Baseline registrado para migraciones legacy 001-022; "
        "no se reejecutaron sobre el esquema existente."
    )
    return True


def execute_sql_file(connection, sql_path):
    print(f"Ejecutando {sql_path.relative_to(PROJECT_ROOT)}")
    sql = sql_path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)

    for index, statement in enumerate(statements, start=1):
        try:
            connection.execute(text(statement))
        except Exception as exc:
            relative_path = sql_path.relative_to(PROJECT_ROOT)
            raise SqlFileExecutionError(
                f"Error en {relative_path}, sentencia {index}/{len(statements)}: "
                f"{statement_preview(statement)}"
            ) from exc

    print(f"OK: {sql_path.name} ({len(statements)} sentencias)")
    return len(statements)


def execute_pending_sql_file(connection, sql_path):
    checksum = migration_checksum(sql_path)
    recorded_checksum = recorded_migration_checksum(connection, sql_path.name)
    if recorded_checksum is not None:
        if recorded_checksum != checksum:
            raise MigrationChecksumMismatchError(
                "La migración aplicada cambió de contenido: "
                f"{sql_path.name}. Registrado={recorded_checksum}, actual={checksum}. "
                "Crea una migración nueva en vez de editar una ya aplicada."
            )
        print(f"Omitiendo {sql_path.name}: ya aplicada con el mismo checksum.")
        return False

    statement_count = execute_sql_file(connection, sql_path)
    record_migration(connection, sql_path, checksum, statement_count)
    return True


def main():
    for sql_path in REQUIRED_SQL_FILES:
        if not sql_path.exists():
            raise FileNotFoundError(f"No existe el archivo SQL requerido: {sql_path}")

    try:
        info = test_connection()
    except Exception as exc:
        print("Error conectando a PostgreSQL local.")
        print(str(exc))
        print(
            "Si la base no existe, créala con: "
            "createdb -h localhost -p 5432 -U postgres malaria_experiments"
        )
        raise SystemExit(1) from exc

    print("Conexión OK:")
    print(f"  database: {info['database_name']}")
    print(f"  user: {info['user_name']}")
    print(f"  version: {info['postgres_version'].splitlines()[0]}")

    try:
        with get_connection() as connection:
            ensure_migration_ledger(connection)
            baseline_legacy_migrations(connection)
            for sql_path in SQL_FILES:
                execute_pending_sql_file(connection, sql_path)
    except MigrationChecksumMismatchError as exc:
        print("Error de integridad del historial de migraciones.")
        print(str(exc))
        raise SystemExit(1) from exc
    except SqlFileExecutionError as exc:
        print("Error ejecutando migraciones SQL.")
        print(str(exc))
        if exc.__cause__ is not None:
            print(f"Causa original: {exc.__cause__}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print("Error inicializando PostgreSQL local.")
        print(str(exc))
        raise SystemExit(1) from exc

    print("Inicialización de base de datos completada.")


if __name__ == "__main__":
    main()
