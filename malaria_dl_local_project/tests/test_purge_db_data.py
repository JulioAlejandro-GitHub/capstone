import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import purge_db_data as purger


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeConnection:
    def __init__(self, tables):
        self.tables = tables
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)
        if "information_schema.tables" in sql:
            return FakeResult([{"table_name": table} for table in self.tables])
        return FakeResult([])


class PurgeDbDataTests(unittest.TestCase):
    def test_build_truncate_sql_incluye_restart_identity_y_cascade(self):
        sql = purger.build_truncate_sql(["runs", "predictions"], schema="public")

        self.assertEqual(
            sql,
            'TRUNCATE TABLE "public"."runs", "public"."predictions" '
            "RESTART IDENTITY CASCADE",
        )

    def test_get_user_tables_excluye_vistas_y_sistema_por_query(self):
        connection = FakeConnection(["artifacts", "runs"])

        tables = purger.get_user_tables(connection, schema="public")

        self.assertEqual(tables, ["artifacts", "runs"])
        query = connection.statements[0]
        self.assertIn("table_type = 'BASE TABLE'", query)
        self.assertIn("table_schema = :schema", query)

    def test_execute_sin_confirmacion_falla(self):
        with self.assertRaisesRegex(ValueError, "Confirmación inválida"):
            purger.purge_database_data(
                execute=True,
                confirm=None,
                schema="public",
                backup_before=False,
                backup_dir=Path("backups/db"),
                reseed=False,
            )

    def test_confirmacion_incorrecta_falla(self):
        with self.assertRaisesRegex(ValueError, "Confirmación inválida"):
            purger.purge_database_data(
                execute=True,
                confirm="WRONG",
                schema="public",
                backup_before=False,
                backup_dir=Path("backups/db"),
                reseed=False,
            )

    def test_execute_requiere_opt_in_de_entorno(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "PURGE_DB_ALLOW_EXECUTION"):
                purger.purge_database_data(
                    execute=True,
                    confirm=purger.SAFE_CONFIRMATION,
                    schema="public",
                    backup_before=False,
                    backup_dir=Path("backups/db"),
                    reseed=False,
                )

    def test_connection_config_usa_solo_database_url_canonica(self):
        with mock.patch.object(
            purger,
            "get_database_url",
            return_value="postgresql+psycopg://tester:fictional@db:5432/capstone",
        ), mock.patch.dict(
            "os.environ",
            {
                "DB_HOST": "ignored",
                "DB_NAME": "ignored",
                "DB_USER": "ignored",
            },
            clear=True,
        ):
            config = purger.get_connection_config()

        self.assertEqual(
            config,
            {
                "host": "db",
                "port": "5432",
                "database": "capstone",
                "user": "tester",
            },
        )

    def test_backup_requiere_wrapper_docker_y_acepta_su_evidencia(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "scripts/db/purge.sh"):
                purger.create_db_backup({}, Path("backups/db"))
        with mock.patch.dict(
            "os.environ",
            {"CAPSTONE_VERIFIED_BACKUP": "/controlled/capstone.dump"},
            clear=True,
        ):
            self.assertEqual(
                purger.create_db_backup({}, Path("backups/db")),
                Path("/controlled/capstone.dump"),
            )

    def test_dry_run_no_ejecuta_truncate(self):
        fake_connection = FakeConnection(["runs", "predictions"])

        @contextmanager
        def fake_get_connection():
            yield fake_connection

        with mock.patch.object(purger, "get_connection", fake_get_connection), \
            mock.patch.object(
                purger,
                "test_connection",
                return_value={
                    "database_name": "malaria_experiments",
                    "user_name": "tester",
                },
            ), \
            mock.patch.object(
                purger,
                "get_connection_config",
                return_value={
                    "database": "malaria_experiments",
                    "host": "db",
                    "port": "5432",
                    "user": "tester",
                },
            ):
            result = purger.purge_database_data(
                execute=False,
                confirm=None,
                schema="public",
                backup_before=False,
                backup_dir=Path("backups/db"),
                reseed=False,
            )

        self.assertEqual(result["mode"], "DRY RUN")
        self.assertEqual(result["tables"], ["runs", "predictions"])
        self.assertFalse(
            any(statement.startswith("TRUNCATE TABLE") for statement in fake_connection.statements)
        )

    def test_identidad_distinta_falla_antes_de_abrir_conexion(self):
        with mock.patch.object(
            purger,
            "get_connection_config",
            return_value={"database": "capstone", "user": "tester"},
        ), mock.patch.object(
            purger,
            "test_connection",
            return_value={"database_name": "other", "user_name": "tester"},
        ), mock.patch.object(purger, "get_connection") as get_connection:
            with self.assertRaisesRegex(RuntimeError, "identidad Docker canónica"):
                purger.purge_database_data(
                    execute=False,
                    confirm=None,
                    schema="public",
                    backup_before=False,
                    backup_dir=Path("backups/db"),
                    reseed=False,
                )

        get_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
