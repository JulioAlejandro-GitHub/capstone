"""Alembic control-flow tests using no engine, server or PostgreSQL substitute."""

import ast
import os
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
except ImportError:
    Config = None

from alembic_v2.safety import UnsafeTarget

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(
    Config is None,
    "Use alembic_v2/requirements.txt interpreter for Alembic envelope tests",
)
class AlembicEnvelopeTests(unittest.TestCase):
    def test_independent_root_and_only_head(self):
        script = ScriptDirectory.from_config(Config(str(ROOT / "alembic_v2.ini")))
        self.assertEqual(script.get_heads(), ["pg_v2_baseline"])
        revisions = list(script.walk_revisions())
        self.assertEqual(len(revisions), 1)
        self.assertIsNone(revisions[0].down_revision)
        self.assertIsNone(revisions[0].dependencies)

    def test_missing_authorization_stops_before_engine_or_docker(self):
        config = Config(str(ROOT / "alembic_v2.ini"))
        with (
            patch("alembic.context.config", config, create=True),
            patch("alembic.context.is_offline_mode", return_value=False),
            patch("alembic.context.get_x_argument", return_value={}),
            patch("sqlalchemy.create_engine") as engine,
            patch("alembic_v2.safety.inspect_isolation") as docker,
            patch.dict(os.environ, {}, clear=True),
        ):
            with self.assertRaisesRegex(UnsafeTarget, "EXPLICIT_TARGET_REQUIRED"):
                runpy.run_path(str(ROOT / "alembic_v2/env.py"))
            engine.assert_not_called()
            docker.assert_not_called()

    def test_offline_upgrade_cannot_export_an_unguarded_installer(self):
        with (
            patch(
                "alembic.context.config",
                Config(str(ROOT / "alembic_v2.ini")),
                create=True,
            ),
            patch("alembic.context.is_offline_mode", return_value=True),
            patch("sqlalchemy.create_engine") as engine,
        ):
            with self.assertRaisesRegex(UnsafeTarget, "OFFLINE_EXECUTION_DISABLED"):
                runpy.run_path(str(ROOT / "alembic_v2/env.py"))
            engine.assert_not_called()

    def test_revision_refuses_unverified_connection_and_downgrade(self):
        script = ScriptDirectory.from_config(Config(str(ROOT / "alembic_v2.ini")))
        module = script.get_revision("head").module
        with (
            patch.object(module.op, "get_bind", return_value=SimpleNamespace(info={})),
            self.assertRaisesRegex(UnsafeTarget, "UNVERIFIED_CONNECTION"),
        ):
            module.upgrade()
        with self.assertRaisesRegex(RuntimeError, "DESTRUCTIVE_DOWNGRADE_DISABLED"):
            module.downgrade()

    def test_no_legacy_settings_import_or_bootstrap(self):
        for p in (ROOT / "alembic_v2").rglob("*.py"):
            source = p.read_text()
            tree = ast.parse(source)
            imports = [
                n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
            ]
            self.assertFalse(
                any(n.startswith(("app.", "malaria_dl.", "dotenv")) for n in imports), p
            )
            self.assertNotIn("create_all(", source)
            self.assertNotIn("init_db", source)
            self.assertNotIn("autocommit_block", source)


if __name__ == "__main__":
    unittest.main()
