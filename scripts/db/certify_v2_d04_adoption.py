"""D-04 continuation, isolated-only runner. No application configuration or source connection."""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row
from psycopg.types.string import TextLoader

from adoption_v2.core import (
    contract,
    digest,
    require,
    table_digest,
)
from adoption_v2.execute import (
    apply,
    capture,
    catalog_snapshot,
    private_write,
)
from adoption_v2.planner import build_plan
from adoption_v2.preflight import preflight, schema_signature
from alembic_v2.safety import (
    IDENTITY_SQL,
    ROLES_SQL,
    inspect_isolation,
    validate_server_snapshot,
)

E = ROOT / "docs/audits/e10_10_5d3_evidence"
PREVIOUS = ROOT / "docs/audits/e10_10_5d2_evidence/route_b"
T = json.loads((PREVIOUS / "target.json").read_text())
OLD = ROOT / "docs/audits/e10_10_5d_evidence"
ORIGINAL_PRIVATE = Path(
    json.loads((OLD / "private_location.json").read_text())["directory"]
)
PASSWORD = (
    (ORIGINAL_PRIVATE / "container.env").read_text().splitlines()[0].split("=", 1)[1]
)
BACKUP = Path(json.loads((PREVIOUS / "isolated_backup.json").read_text())["path"])
BINDINGS = {
    "documents": {},
    "configurations": {},
    "evaluations": [],
    "calibrations": {},
    "consolidations": [],
    "xai": [],
    "xai_excluded": {},
}


def save(name, value):
    (E / name).write_text(json.dumps(value, indent=2, default=str) + "\n")


def directory():
    path = E / "private_paths.json"
    if not path.exists():
        private = Path(tempfile.mkdtemp(prefix="e10_d04_", dir="/private/tmp"))
        os.chmod(private, 0o700)
        save(path.name, {"directory": str(private)})
    return Path(json.loads(path.read_text())["directory"])


def connect(t=T):
    c = psycopg.connect(
        host="127.0.0.1",
        port=t["host_port"],
        dbname=t["database"],
        user=t["migration_role"],
        password=PASSWORD,
        row_factory=dict_row,
        autocommit=True,
    )
    c.adapters.register_loader("uuid", TextLoader)
    return c


def guard(t=T):
    inspect_isolation(t)
    require(
        hashlib.sha256(BACKUP.read_bytes()).hexdigest() == T["backup_sha256"],
        "BACKUP_CHANGED",
    )
    with connect(t) as c:
        identity = c.execute(IDENTITY_SQL).fetchone()
        roles = c.execute(ROLES_SQL).fetchall()
        validate_server_snapshot(t, identity, roles)
        require(
            identity["server_version_num"] == 170009, "EXACT_POSTGRES_VERSION_REQUIRED"
        )
    return identity


def do_preflight():
    ident = guard()
    with connect() as c, c.transaction():
        c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        require(
            c.execute(
                "SELECT count(*) n FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
            ).fetchone()["n"]
            == 0,
            "OTHER_DATABASE_SESSIONS_PRESENT",
        )
        source = capture(c)
        inventory = preflight(source)
        require(
            digest(inventory) == T["source_inventory_sha256"],
            "SOURCE_INVENTORY_CHANGED",
        )
        require(
            digest(schema_signature(source["catalog"])) == T["legacy_schema_sha256"],
            "SOURCE_SCHEMA_NOT_AUTHORIZED",
        )
        plan = build_plan(source, BINDINGS)
        private_write(directory() / "preflight_source.json", source)
        private_write(directory() / "preflight_plan.json", plan)
        save("preflight_inventory.json", inventory)
        save("preflight_catalog.json", source["native_catalog"])
        save(
            "preflight_result.json",
            {
                "status": "PASS",
                "identity": ident,
                "tables": 97,
                "source_inventory_sha256": digest(inventory),
                "plan_sha256": plan["plan_sha256"],
                "functions": 101,
                "pgcrypto_functions_exact": 36,
                "own_functions": 65,
                "source_revision": "20260922_01",
                "sequence_values": source["sequence_values"],
            },
        )


class TracedConnection:
    def __init__(self, connection, label, inject_after=None):
        self.connection = connection
        self.label = label
        self.index = 0
        self.ddl = 0
        self.inject_after = inject_after

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *args):
        return self.connection.__exit__(*args)

    def execute(self, statement, *args, **kwargs):
        self.index += 1
        text = str(statement)
        entry = {
            "index": self.index,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "statement": text,
            "parameters_logged": False,
        }
        try:
            result = self.connection.execute(statement, *args, **kwargs)
            entry["status"] = "ok"
            entry["rowcount"] = result.rowcount
        except Exception as exc:
            entry["status"] = "error"
            entry["sqlstate"] = getattr(exc, "sqlstate", None)
            raise
        finally:
            with (E / (self.label + "_statements.jsonl")).open("a") as f:
                f.write(json.dumps(entry) + "\n")
        if text.lstrip().upper().startswith(("CREATE ", "ALTER ", "DROP ")):
            self.ddl += 1
            if self.inject_after == self.ddl:
                save(
                    self.label + "_injection.json",
                    {
                        "ddl_completed": self.ddl,
                        "sqlstate_expected": "22012",
                        "head": self.connection.execute(
                            "SELECT version_num FROM alembic_version"
                        ).fetchall(),
                    },
                )
                self.connection.execute("SELECT 1/0")
        return result


def apply_traced(t, label, backup=BACKUP, completed=None, inject_after=None):
    archive = directory() / label
    archive.mkdir(mode=0o700)
    url = f"postgresql+psycopg://{t['migration_role']}:{PASSWORD}@127.0.0.1:{t['host_port']}/{t['database']}"
    original = psycopg.connect
    with patch(
        "psycopg.connect",
        side_effect=lambda *a, **kw: TracedConnection(
            original(*a, **kw), label, inject_after
        ),
    ):
        return apply(
            t, url, BINDINGS, archive, completed_plan=completed, backup_path=backup
        )


def do_apply():
    require(
        json.loads((E / "preflight_result.json").read_text())["status"] == "PASS",
        "PREFLIGHT_REQUIRED",
    )
    guard()
    result = apply_traced(T, "apply")
    save("apply_result.json", result)


def diagnose_after_failure():
    guard()
    with connect() as c, c.transaction():
        c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        snapshot = catalog_snapshot(c)
        original = json.loads((E / "preflight_catalog.json").read_text())
        inv = {
            k: {"count": len(rows), "sha256": table_digest(rows)}
            for k in contract()["tables"]
            for rows in [c.execute('SELECT * FROM public."' + k + '"').fetchall()]
        }
        same = inv == json.loads((E / "preflight_inventory.json").read_text())
        save(
            "after_failure.json",
            {
                "catalog_unchanged": snapshot == original,
                "all_97_tables_unchanged": same,
                "head": c.execute("SELECT version_num FROM alembic_version").fetchall(),
                "sequence": c.execute(
                    "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
                ).fetchone(),
            },
        )


def main():
    {"preflight": do_preflight, "apply": do_apply, "diagnose": diagnose_after_failure}[
        sys.argv[1]
    ]()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- keep private values out of public errors
        # No row values or credentials in public exceptions.
        save(
            "last_failure.json",
            {
                "action": sys.argv[1],
                "type": type(exc).__name__,
                "code": getattr(exc, "code", None),
                "location": getattr(exc, "location", None),
                "sqlstate": getattr(exc, "sqlstate", None),
                "adapter_result": "not certified",
            },
        )
        path = directory() / ("failure_" + sys.argv[1] + ".txt")
        path.write_text(str(exc))
        os.chmod(path, 0o600)
        print(
            "FAILED "
            + type(exc).__name__
            + " "
            + str(getattr(exc, "code", getattr(exc, "sqlstate", None)))
        )
        sys.exit(2)
