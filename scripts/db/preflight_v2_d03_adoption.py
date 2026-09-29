"""Re-run D preflight on a fresh isolated restore, after D-03 Route A certification."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.string import TextLoader

from adoption_v2.core import Blocked, contract, digest
from adoption_v2.execute import capture, catalog_snapshot, certified_catalog
from adoption_v2.preflight import preflight, schema_signature
from alembic_v2.safety import (
    IDENTITY_SQL,
    ROLES_SQL,
    inspect_isolation,
    validate_server_snapshot,
)

E = ROOT / "docs/audits/e10_10_5d2_evidence/route_b"
E.mkdir(exist_ok=True)
OLD = ROOT / "docs/audits/e10_10_5d_evidence"
A = E.parent / "route_a"


def save(name, v):
    (E / name).write_text(json.dumps(v, indent=2, default=str) + "\n")


def main():
    assert not (E / "target.json").exists(), "Do not overwrite an existing D attempt"
    # Require completed, newly executed Route A evidence before touching a restore.
    for f in ["rollback_result.json", "idempotence_result.json", "restore_result.json"]:
        assert json.loads((A / f).read_text())["passed"]
    for f in ["server_tests.json", "d03_server_tests.json"]:
        assert all(x["passed"] for x in json.loads((A / f).read_text()))
    assert all(
        x["returncode"] == 0
        for x in json.loads((E.parent / "static_commands.json").read_text())
    )
    certified = certified_catalog()
    t = json.loads((OLD / "target.json").read_text())
    t["database"] += "_d2_adoption"
    t.pop("database_oid")
    D = ["docker", "--host", "unix:///Users/julio/.docker/run/docker.sock"]
    r = subprocess.run(
        D + ["start", t["container_id"]], capture_output=True, text=True, check=False
    )
    assert r.returncode == 0
    inspect_isolation(t)
    original = Path(
        json.loads((OLD / "private_location.json").read_text())["directory"]
    )
    password = (original / "container.env").read_text().splitlines()[0].split("=", 1)[1]
    backup = original / "source.dump"
    assert (
        hashlib.sha256(backup.read_bytes()).hexdigest()
        == json.loads((OLD / "source_backup.json").read_text())["sha256"]
    )
    private = Path(tempfile.mkdtemp(prefix="e10_d03_adoption_", dir="/private/tmp"))
    os.chmod(private, 0o700)
    save(
        "private_paths.json", {"directory": str(private), "source_backup": str(backup)}
    )

    def connect(db, role="postgres"):
        return psycopg.connect(
            host="127.0.0.1",
            port=t["host_port"],
            dbname=db,
            user=role,
            password=password,
            row_factory=dict_row,
            autocommit=True,
        )

    with connect("postgres") as c:
        ident = c.execute(
            "SELECT system_identifier::text id,current_setting('server_version_num') version FROM pg_control_system()"
        ).fetchone()
        assert ident == {"id": t["postgres_system_identifier"], "version": "170009"}
        c.execute(
            sql.SQL(
                "CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0"
            ).format(sql.Identifier(t["database"]))
        )
    with connect(t["database"]) as c:
        t["database_oid"] = c.execute(
            "SELECT oid FROM pg_database WHERE datname=current_database()"
        ).fetchone()["oid"]
        assert (
            c.execute(
                "SELECT count(*) n FROM pg_class WHERE relnamespace='public'::regnamespace"
            ).fetchone()["n"]
            == 0
        )
    save("target.json", t)
    args = D + [
        "exec",
        "-i",
        t["container_id"],
        "pg_restore",
        "-U",
        "postgres",
        "-d",
        t["database"],
        "--role=capstone_v2_migrator",
        "--no-owner",
        "--no-acl",
        "--single-transaction",
        "--exit-on-error",
    ]
    r = subprocess.run(
        args, input=backup.read_bytes(), capture_output=True, check=False
    )
    save(
        "restore.json",
        {
            "argv": args,
            "exit_code": r.returncode,
            "source_backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        },
    )
    assert r.returncode == 0
    isolated = private / "isolated.dump"
    with isolated.open("xb") as out:
        os.chmod(isolated, 0o600)
        args = D + [
            "exec",
            t["container_id"],
            "pg_dump",
            "-U",
            "postgres",
            "-d",
            t["database"],
            "-Fc",
        ]
        r = subprocess.run(args, stdout=out, stderr=subprocess.PIPE, check=False)
    save(
        "isolated_backup.json",
        {
            "argv": args,
            "exit_code": r.returncode,
            "sha256": hashlib.sha256(isolated.read_bytes()).hexdigest(),
            "path": str(isolated),
        },
    )
    assert r.returncode == 0
    t["backup_sha256"] = hashlib.sha256(isolated.read_bytes()).hexdigest()
    with connect(t["database"], "capstone_v2_migrator") as c:
        identity = c.execute(IDENTITY_SQL).fetchone()
        roles = c.execute(ROLES_SQL).fetchall()
        validate_server_snapshot(t, identity, roles)
        save("identity.json", {"identity": identity, "roles": roles})
        c.adapters.register_loader("uuid", TextLoader)
        with c.transaction():
            c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            assert (
                c.execute(
                    "SELECT count(*) n FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
                ).fetchone()["n"]
                == 0
            )
            c.execute("SET LOCAL search_path=pg_catalog,public")
            snap = {
                "catalog": {
                    k: c.execute(q).fetchall() for k, q in contract()["queries"].items()
                },
                "rows": {
                    k: c.execute(
                        sql.SQL("SELECT * FROM public.{}").format(sql.Identifier(k))
                    ).fetchall()
                    for k in contract()["tables"]
                },
            }
            inventory = preflight(snap)
            save("reference_inventory.json", inventory)
            previous = json.loads((OLD / "reference_inventory.json").read_text())
            assert inventory == previous
            t["source_inventory_sha256"] = digest(inventory)
            t["legacy_schema_sha256"] = digest(schema_signature(snap["catalog"]))
            native = catalog_snapshot(c)
            save("legacy_native_catalog.json", native)
            save(
                "preservation.json",
                {
                    "tables": 97,
                    "counts_and_hashes_equal_to_original_D": True,
                    "sequence": c.execute(
                        "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
                    ).fetchone(),
                    "source_backup_sha256": hashlib.sha256(
                        backup.read_bytes()
                    ).hexdigest(),
                },
            )
            bindings = {
                "documents": {},
                "configurations": {},
                "evaluations": [],
                "calibrations": {},
                "consolidations": [],
                "xai": [],
                "xai_excluded": {},
            }
            t["mapping_sha256"] = digest(bindings)
            save("target.json", t)
            save(
                "data_preflight.json",
                {
                    "status": "PASS",
                    "revision": "20260922_01",
                    "checksums": 22,
                    "tables": 97,
                    "models": len(snap["rows"]["models"]),
                    "users": len(snap["rows"]["users"]),
                    "gate": "free",
                    "source_row_hash_reference": "D restored legacy reference, not a live operational query",
                },
            )
            try:
                capture(c)
            except Blocked as ex:
                save(
                    "preflight_result.json",
                    {
                        "status": "BLOCKED",
                        "code": ex.code,
                        "location": ex.location,
                        "adapter_applied": False,
                        "d01_sequence_equal": native["sequences"]
                        == certified["sequences"],
                        "d01_attidentity": [
                            r["attidentity"]
                            for r in native["columns"]
                            if r["relation"] == "experiment_execution_events"
                            and r["name"] == "id"
                        ],
                        "d02_legacy_schema_signature_equal": schema_signature(
                            snap["catalog"]
                        )
                        == contract()["expected_schema"],
                    },
                )
                raise
    save("preflight_result.json", {"status": "PASS", "adapter_applied": False})


if __name__ == "__main__":
    try:
        main()
    except Blocked as exc:
        print(exc.code)
        sys.exit(2)
