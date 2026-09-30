"""Catalog identity, repeatability, injected failure and restore for DBV2.2."""

import argparse
import hashlib
import json
import os
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from certify_dbv22 import (
    DOCKER,
    IDENTITY_SQL,
    PYTHON,
    ROLES_SQL,
    ROOT,
    TARGET,
    E,
    connect,
    guard,
    run,
    save,
    snapshot,
    upgrade,
    validate_server_snapshot,
)
from psycopg import sql

from alembic_v2.resources import load_baseline


def child(t, suffix):
    guard(t)
    name = t["database"] + "_" + suffix + "_" + uuid4().hex[:5]
    with connect(t, role="postgres", database="postgres") as c:
        i = c.execute(
            "SELECT current_database() AS database,current_setting('server_version_num')::int AS version,system_identifier::text AS id FROM pg_control_system()"
        ).fetchone()
        assert i == {
            "database": "postgres",
            "version": 170009,
            "id": t["postgres_system_identifier"],
        }
        c.execute(
            sql.SQL(
                "CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0"
            ).format(sql.Identifier(name))
        )
    ct = dict(t, database=name)
    with connect(ct, role="postgres") as c:
        assert c.execute(
            "SELECT current_database() AS db,current_setting('server_version_num')::int AS version,system_identifier::text AS id FROM pg_control_system()"
        ).fetchone() == {
            "db": name,
            "version": 170009,
            "id": t["postgres_system_identifier"],
        }
        c.execute(
            "GRANT EXECUTE ON FUNCTION pg_control_system() TO capstone_v2_migrator"
        )
        ct["database_oid"] = c.execute(
            "SELECT oid::int AS oid FROM pg_database WHERE datname=current_database()"
        ).fetchone()["oid"]
    guard(ct)
    save(suffix + "_target.json", ct)
    return ct


def physical(c):
    return c.execute(
        "SELECT oid,relname,relkind,relfilenode FROM pg_class WHERE relnamespace='public'::regnamespace ORDER BY oid"
    ).fetchall()


def compare():
    t = guard()
    manifest, statements = load_baseline()
    with connect(t) as c:
        actual = snapshot(c)
    ref = child(t, "reference")
    with connect(ref) as c:
        c.execute("BEGIN")
        try:
            c.execute(
                "CREATE TABLE public.alembic_version (version_num VARCHAR(32) NOT NULL,CONSTRAINT alembic_version_pkc PRIMARY KEY(version_num))"
            )
            # Server normalization of resources independently AST-checked against DBV2.1.
            # Does NOT execute the design file or claim a second install method.
            for entry, statement in zip(
                manifest["statements"], statements, strict=True
            ):
                if entry["kind"] != "seed":
                    c.execute(statement)
            expected = snapshot(c)
        finally:
            c.execute("ROLLBACK")
    save("expected_catalog.json", expected)
    differences = {
        k: {"EXPECTED": expected[k], "ACTUAL": actual[k], "status": "DIFFERENCE"}
        for k in expected
        if expected[k] != actual[k]
    }
    save(
        "catalog_comparison.json",
        {
            "status": "MATCH" if not differences else "DIFFERENCE",
            "categories": {
                k: {
                    "expected_count": len(expected[k]),
                    "actual_count": len(actual[k]),
                    "status": "DIFFERENCE" if k in differences else "MATCH",
                }
                for k in expected
            },
            "differences": differences,
        },
    )
    assert not differences, str(list(differences))
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic_v2.ini")))
    assert (
        script.get_heads() == ["pg_v2_baseline"]
        and script.get_bases() == ["pg_v2_baseline"]
        and len(list(script.walk_revisions())) == 1
    )
    env = dict(
        os.environ,
        PGV2_DATABASE_URL=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}",
        PGV2_TARGET=str(TARGET),
        PYTHONPATH=str(ROOT),
    )
    save(
        "alembic_history.json",
        {
            "roots": script.get_bases(),
            "heads": script.get_heads(),
            "down_revision": script.get_revision("pg_v2_baseline").down_revision,
            "current": run(
                [PYTHON, "-m", "alembic", "-c", "alembic_v2.ini", "current"], env=env
            ).stdout,
            "heads_output": run(
                [PYTHON, "-m", "alembic", "-c", "alembic_v2.ini", "heads"], env=env
            ).stdout,
        },
    )
    with connect(t) as c:
        counts = {
            r["name"]: c.execute(
                sql.SQL("SELECT count(*) AS n FROM {}").format(
                    sql.Identifier(r["name"])
                )
            ).fetchone()["n"]
            for r in actual["relations"]
            if r["relkind"] == "r"
        }
    assert {n: v for n, v in counts.items() if v} == {
        "alembic_version": 1,
        "experiment_execution_gate": 1,
    }
    save("empty_application_tables.json", counts)
    print(
        "PASS exact normalized catalog equality, 18 categories, single root/head, empty scientific tables"
    )


def repeat():
    t = guard()
    with connect(t) as c:
        before = snapshot(c)
        p0 = physical(c)
    upgrade(t)
    with connect(t) as c:
        after = snapshot(c)
        p1 = physical(c)
        head = c.execute("SELECT version_num FROM alembic_version").fetchall()
    assert before == after and p0 == p1 and head == [{"version_num": "pg_v2_baseline"}]
    save(
        "repeatability.json",
        {
            "status": "PASS",
            "catalog_equal": True,
            "physical_oids_and_relfilenodes_equal": True,
            "head": head,
            "physical_before": p0,
            "physical_after": p1,
        },
    )
    print("PASS second upgrade catalog and physical object identities unchanged")


def failure():
    t = child(guard(), "failure")
    with connect(t) as c:
        before = snapshot(c)
    result = upgrade(t, fail=True)
    assert (
        result.returncode != 0
        and "V2_INJECTED_FAILURE_AFTER_500" in result.stderr
        and "division by zero" in result.stderr
    )
    with connect(t) as c:
        after = snapshot(c)
    assert before == after and not after["relations"] and not after["functions"]
    save(
        "failure_rollback.json",
        {
            "status": "PASS",
            "returncode": result.returncode,
            "stderr": result.stderr,
            "empty_catalog_restored": True,
            "no_false_ledger": True,
        },
    )
    upgrade(t)
    with connect(t) as c:
        recovered = snapshot(c)
    actual = json.loads((E / "dbv2_2_catalog_manifest.json").read_text())
    assert recovered == actual
    save("failure_recovery.json", {"status": "PASS", "full_catalog_equal": True})
    print(
        "PASS failure after 500 DDL, total rollback, subsequent fresh upgrade and catalog equality"
    )


def restore():
    t = guard()
    r = child(t, "restore")
    # Structural dump plus only Alembic's head and technical singleton: no scientific data.
    dump = run(
        DOCKER
        + [
            "exec",
            t["container_id"],
            "pg_dump",
            "-U",
            "capstone_v2_migrator",
            "-d",
            t["database"],
            "--schema-only",
        ]
    ).stdout
    (E / "structural_backup.sql").write_text(dump)
    ledger = run(
        DOCKER
        + [
            "exec",
            t["container_id"],
            "pg_dump",
            "-U",
            "capstone_v2_migrator",
            "-d",
            t["database"],
            "--data-only",
            "--table=public.alembic_version",
            "--table=public.experiment_execution_gate",
        ]
    ).stdout
    (E / "technical_state_backup.sql").write_text(ledger)
    guard(r)
    run(
        DOCKER
        + [
            "exec",
            "-i",
            t["container_id"],
            "psql",
            "-X",
            "-U",
            "capstone_v2_migrator",
            "-d",
            r["database"],
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=dump + "\n" + ledger,
    )
    # pg_dump without --create omits database ACL. Restore its approved ACL explicitly.
    with connect(r) as c:
        validate_server_snapshot(
            r, c.execute(IDENTITY_SQL).fetchone(), c.execute(ROLES_SQL).fetchall()
        )
        c.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC,capstone_v2_runtime").format(
                sql.Identifier(r["database"])
            )
        )
        c.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO capstone_v2_runtime").format(
                sql.Identifier(r["database"])
            )
        )
        restored = snapshot(c)
        head = c.execute("SELECT version_num FROM alembic_version").fetchall()
    actual = json.loads((E / "dbv2_2_catalog_manifest.json").read_text())
    differences = {
        k: {"expected": actual[k], "actual": restored[k]}
        for k in actual
        if actual[k] != restored[k]
    }
    save(
        "backup_restore.json",
        {
            "status": "PASS" if not differences else "DIFFERENCE",
            "differences": differences,
            "head": head,
            "structural_backup_sha256": hashlib.sha256(dump.encode()).hexdigest(),
            "technical_backup_sha256": hashlib.sha256(ledger.encode()).hexdigest(),
            "database_acl_restored_explicitly": True,
        },
    )
    assert not differences and head == [{"version_num": "pg_v2_baseline"}], list(
        differences
    )
    print("PASS schema restore, ownership, ACL, head and full catalog equality")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["compare", "repeat", "failure", "restore"])
    a = p.parse_args()
    globals()[a.action]()
