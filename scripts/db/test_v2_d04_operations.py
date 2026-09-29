"""Real rollback, repetition and restore tests; exclusively attested isolated copies."""

import hashlib
import json
import os
import subprocess
import sys

import psycopg
from certify_v2_d04_adoption import (
    BACKUP,
    PASSWORD,
    E,
    T,
    apply_traced,
    connect,
    directory,
    guard,
    save,
)
from psycopg import sql
from psycopg.rows import dict_row

from adoption_v2.core import decode, digest, require, table_digest
from adoption_v2.execute import catalog_snapshot, reconcile

D = ["docker", "--host", "unix:///Users/julio/.docker/run/docker.sock"]


def admin(db="postgres"):
    return psycopg.connect(
        host="127.0.0.1",
        port=T["host_port"],
        dbname=db,
        user="postgres",
        password=PASSWORD,
        row_factory=dict_row,
        autocommit=True,
    )


def run(args, input=None, output=None):
    r = subprocess.run(
        args,
        input=input,
        stdout=output or subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    with (E / "operation_commands.jsonl").open("a") as f:
        f.write(
            json.dumps(
                {
                    "argv": args,
                    "exit_code": r.returncode,
                    "stdin_sha256": hashlib.sha256(input).hexdigest()
                    if input
                    else None,
                }
            )
            + "\n"
        )
    require(r.returncode == 0, "ISOLATED_COMMAND_FAILED")
    return r.stdout


def new_database(suffix):
    guard()
    child = dict(T, database=T["database"] + suffix)
    with admin() as c:
        require(
            c.execute(
                "SELECT system_identifier::text id FROM pg_control_system()"
            ).fetchone()["id"]
            == T["postgres_system_identifier"],
            "CLUSTER_CHANGED",
        )
        c.execute(
            sql.SQL(
                "CREATE DATABASE {} OWNER capstone_v2_migrator TEMPLATE template0"
            ).format(sql.Identifier(child["database"]))
        )
    with admin(child["database"]) as c:
        child["database_oid"] = c.execute(
            "SELECT oid FROM pg_database WHERE datname=current_database()"
        ).fetchone()["oid"]
        require(
            c.execute(
                "SELECT count(*) n FROM pg_class WHERE relnamespace='public'::regnamespace"
            ).fetchone()["n"]
            == 0,
            "AUXILIARY_NOT_EMPTY",
        )
    save(suffix + "_target.json", child)
    guard(child)
    return child


def dump(t, name):
    path = directory() / name
    with path.open("xb") as out:
        os.chmod(path, 0o600)
        run(
            D
            + [
                "exec",
                t["container_id"],
                "pg_dump",
                "-U",
                "postgres",
                "-d",
                t["database"],
                "-Fc",
            ],
            output=out,
        )
    return path


def restore(t, path, legacy=False):
    args = D + [
        "exec",
        "-i",
        t["container_id"],
        "pg_restore",
        "-U",
        "postgres",
        "--role=capstone_v2_migrator",
        "-d",
        t["database"],
        "--single-transaction",
        "--exit-on-error",
    ]
    if legacy:
        args += ["--no-owner", "--no-acl"]
    run(args, input=path.read_bytes())


def data(c):
    native = catalog_snapshot(c)
    hashes = {
        r["name"]: {"count": len(rows), "sha256": table_digest(rows)}
        for r in native["relations"]
        if r["relkind"] == "r"
        for rows in [
            c.execute(
                sql.SQL("SELECT * FROM public.{}").format(sql.Identifier(r["name"]))
            ).fetchall()
        ]
    }
    seq = c.execute(
        "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
    ).fetchone()
    return {"catalog": native, "tables": hashes, "sequence": seq}


def rollback():
    child = new_database("_d4_rollback")
    restore(child, BACKUP, True)
    backup = dump(child, "rollback_backup.dump")
    child["backup_sha256"] = hashlib.sha256(backup.read_bytes()).hexdigest()
    save("rollback_target.json", child)
    with connect(child) as c, c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        before = data(c)
    try:
        apply_traced(child, "rollback", backup=backup, inject_after=50)
    except psycopg.Error as ex:
        require(ex.sqlstate == "22012", "UNEXPECTED_ROLLBACK_FAILURE")
    else:
        raise AssertionError("Expected real failure was not raised")
    with connect(child) as c, c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        after = data(c)
        head = c.execute("SELECT version_num FROM alembic_version").fetchall()
    require(
        before == after and head == [{"version_num": "20260922_01"}],
        "ROLLBACK_NOT_EXACT",
    )
    save(
        "rollback_result.json",
        {
            "passed": True,
            "injected_after_ddl": 50,
            "catalog_before": digest(before["catalog"]),
            "catalog_after": digest(after["catalog"]),
            "tables_compared": len(before["tables"]),
            "data_before": digest(before["tables"]),
            "data_after": digest(after["tables"]),
            "sequence": after["sequence"],
            "head": head,
        },
    )


def completed():
    return decode(json.loads((directory() / "apply/plan.json").read_text()))


def repeat():
    plan = completed()
    t = dict(T, completed_plan_sha256=plan["plan_sha256"])
    with connect() as c, c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        before = data(c)
        physical_before = {
            r["name"]: c.execute(
                sql.SQL(
                    "SELECT xmin::text,ctid::text FROM public.{} ORDER BY ctid"
                ).format(sql.Identifier(r["name"]))
            ).fetchall()
            for r in before["catalog"]["relations"]
            if r["relkind"] == "r"
        }
    result = apply_traced(t, "repeat", completed=plan)
    with connect() as c, c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        after = data(c)
        physical_after = {
            r["name"]: c.execute(
                sql.SQL(
                    "SELECT xmin::text,ctid::text FROM public.{} ORDER BY ctid"
                ).format(sql.Identifier(r["name"]))
            ).fetchall()
            for r in after["catalog"]["relations"]
            if r["relkind"] == "r"
        }
    require(
        result["status"] == "already_adopted"
        and before == after
        and physical_before == physical_after,
        "REPETITION_CHANGED_STATE",
    )
    save(
        "repeat_result.json",
        {
            "passed": True,
            "status": result["status"],
            "catalog": digest(after["catalog"]),
            "data": digest(after["tables"]),
            "physical_rows_equal": True,
            "tables": len(after["tables"]),
            "sequence": after["sequence"],
        },
    )


def backup_restore():
    plan = completed()
    guard()
    backup = dump(T, "adopted.dump")
    child = new_database("_d4_restore")
    restore(child, backup)
    # Explicit pg_dump exclusions/canonical ACL restoration, identical to certified Ruta A procedure.
    with admin(child["database"]) as c:
        c.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(child["database"])
            )
        )
        c.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO capstone_v2_runtime").format(
                sql.Identifier(child["database"])
            )
        )
    with connect(child) as c:
        c.execute(
            "REVOKE ALL ON TABLE public.alembic_version FROM PUBLIC,capstone_v2_runtime"
        )
    with connect() as c, c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        before = data(c)
        reconcile(c, plan)
    with connect(child) as c, c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        after = data(c)
        report = reconcile(c, plan)
        require(
            c.execute("SELECT version_num FROM alembic_version").fetchall()
            == [{"version_num": "pg_v2_baseline"}],
            "RESTORED_HEAD_MISMATCH",
        )
    require(before == after, "RESTORE_NOT_EXACT")
    save("restored_catalog.json", after["catalog"])
    save("restored_inventory.json", report)
    save(
        "restore_result.json",
        {
            "passed": True,
            "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
            "private_backup": str(backup),
            "catalog": digest(after["catalog"]),
            "data": digest(after["tables"]),
            "tables": len(after["tables"]),
            "sequence": after["sequence"],
            "owners_acl_equal": True,
            "head": "pg_v2_baseline",
        },
    )


if __name__ == "__main__":
    {"rollback": rollback, "repeat": repeat, "backup_restore": backup_restore}[
        sys.argv[1]
    ]()
