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


class SqlFileExecutionError(RuntimeError):
    pass


def statement_preview(statement, max_length=500):
    compact = " ".join(statement.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def split_sql_statements(sql):
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
            for sql_path in SQL_FILES:
                execute_sql_file(connection, sql_path)
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
