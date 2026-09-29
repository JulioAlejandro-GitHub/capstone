"""Transaction-boundary simulation only: drivers, connections and Docker are mocked."""

import hashlib
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fixtures import rich

from adoption_v2.core import Blocked, digest
from adoption_v2.execute import apply
from adoption_v2.planner import build_plan
from adoption_v2.preflight import schema_signature


class TransactionTests(unittest.TestCase):
    def simulate(self, failure=None, completed=False):
        source, bindings = rich()
        plan = build_plan(source, bindings)
        approval = {
            "mapping_sha256": digest(bindings),
            "legacy_schema_sha256": digest(schema_signature(source["catalog"])),
            "source_inventory_sha256": plan["source_inventory_sha256"],
            "completed_plan_sha256": plan["plan_sha256"],
        }
        statements = []
        status = []

        class Connection:
            adapters = SimpleNamespace(register_loader=Mock())

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            @contextmanager
            def transaction(self):
                try:
                    yield
                except Exception:
                    status.append("rollback")
                    raise
                else:
                    status.append("commit")

            def execute(self, sql, *args):
                statements.append(sql)
                if failure == "ddl" and sql == "SYNTHETIC DDL":
                    raise RuntimeError("synthetic injected failure")
                if "pg_try_advisory" in sql:
                    value = {"locked": True}
                elif "count(*)" in sql:
                    value = {"n": 0}
                else:
                    value = {}
                rows = (
                    [{"version_num": "pg_v2_baseline" if completed else "20260922_01"}]
                    if sql.startswith("SELECT version_num")
                    else []
                )
                return SimpleNamespace(
                    fetchone=lambda: value, fetchall=lambda: rows, rowcount=1
                )

        connection = Connection()
        drivers = {
            "psycopg": SimpleNamespace(connect=Mock(return_value=connection)),
            "psycopg.rows": SimpleNamespace(dict_row=object()),
            "psycopg.types.string": SimpleNamespace(TextLoader=object()),
            "sqlalchemy.engine": SimpleNamespace(
                make_url=lambda _: SimpleNamespace(
                    host="synthetic.invalid",
                    port=55599,
                    username="synthetic",
                    password=None,
                    database="synthetic",
                )
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            backup = Path(directory) / "backup"
            backup.write_bytes(b"SYNTHETIC BACKUP")
            approval["backup_sha256"] = hashlib.sha256(backup.read_bytes()).hexdigest()
            with (
                patch.dict(sys.modules, drivers),
                patch("adoption_v2.execute.authorization", return_value=approval),
                patch("alembic_v2.safety.inspect_isolation") as inspect,
                patch("alembic_v2.safety.validate_server_snapshot"),
                patch("adoption_v2.execute.private_write"),
                patch("adoption_v2.execute.capture", return_value=source),
                patch(
                    "adoption_v2.execute.delta",
                    return_value={
                        "prepare": ["SYNTHETIC DDL"],
                        "finalize": [],
                        "validate": [],
                        "triggers": [],
                        "acl": [],
                    },
                ),
                patch("adoption_v2.execute.mutate_rows") as mutate,
                patch(
                    "adoption_v2.execute.reconcile",
                    side_effect=Blocked("FINAL_CATALOG_MISMATCH")
                    if failure == "catalog"
                    else None,
                    return_value={"synthetic": True},
                ),
            ):
                try:
                    result = apply(
                        approval,
                        "synthetic",
                        bindings,
                        directory,
                        backup_path=backup,
                        completed_plan=plan if completed else None,
                    )
                except (RuntimeError, Blocked):
                    result = None
                inspect.assert_called_once()
                if completed:
                    mutate.assert_not_called()
        return result, statements, status

    def test_intermediate_failure_rolls_back_without_head_promotion(self):
        result, sql, status = self.simulate("ddl")
        self.assertIsNone(result)
        self.assertEqual(status, ["rollback"])
        self.assertFalse(
            any(s.startswith("UPDATE public.alembic_version") for s in sql)
        )

    def test_failed_catalog_reconciliation_cannot_promote_head(self):
        result, sql, status = self.simulate("catalog")
        self.assertIsNone(result)
        self.assertEqual(status, ["rollback"])
        self.assertFalse(
            any(s.startswith("UPDATE public.alembic_version") for s in sql)
        )

    def test_success_promotes_only_after_constraints(self):
        result, sql, status = self.simulate()
        self.assertEqual(result["status"], "committed")
        self.assertEqual(status, ["commit"])
        head = next(
            i
            for i, s in enumerate(sql)
            if s.startswith("UPDATE public.alembic_version")
        )
        self.assertGreater(head, sql.index("SET CONSTRAINTS ALL IMMEDIATE"))

    def test_completed_plan_replay_is_noop(self):
        result, sql, status = self.simulate(completed=True)
        self.assertEqual(result["status"], "already_adopted")
        self.assertEqual(status, ["commit"])
        self.assertNotIn("SYNTHETIC DDL", sql)
        self.assertFalse(
            any(s.startswith("UPDATE public.alembic_version") for s in sql)
        )
