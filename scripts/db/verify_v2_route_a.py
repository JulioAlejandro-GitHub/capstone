"""Server-backed Route A checks, exclusively against the attested isolated cluster.

The reference database renders the manifest SQL on PostgreSQL 17 for canonical
catalog comparison. It is not an independent scientific oracle. Negative tests
exercise the installed baseline separately. No historical SQL is executed.
"""

import hashlib
import json
import os
import sys

import psycopg
from certify_v2_route_a import DOCKER, EVIDENCE, ROOT, TARGET, run
from psycopg import sql
from psycopg.rows import dict_row
from v2_catalog_probe import snapshot

sys.path.insert(0, str(ROOT))
from alembic_v2.resources import load_baseline
from alembic_v2.safety import inspect_isolation, validate_server_snapshot

MIGRATOR = "capstone_v2_migrator"
RUNTIME = "capstone_v2_runtime"


def save(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, indent=2, default=str) + "\n")


def connect(t, database=None, role=MIGRATOR):
    return psycopg.connect(
        host="127.0.0.1",
        port=t["host_port"],
        user=role,
        dbname=database or t["database"],
        autocommit=True,
        row_factory=dict_row,
    )


def guard():
    from alembic_v2.safety import IDENTITY_SQL, ROLES_SQL

    t = json.loads(TARGET.read_text())
    inspect_isolation(t)
    with connect(t) as c:
        identity = c.execute(IDENTITY_SQL).fetchone()
        roles = c.execute(ROLES_SQL).fetchall()
        validate_server_snapshot(t, identity, roles)
    save("latest_preflight.json", {"identity": identity, "roles": roles})
    return t


def new_database(t, suffix):
    name = t["database"] + suffix
    with connect(t, "postgres", "postgres") as c:
        ident = c.execute(
            "SELECT system_identifier::text AS id FROM pg_control_system()"
        ).fetchone()
        assert ident["id"] == t["postgres_system_identifier"]
        c.execute(
            sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                sql.Identifier(name), sql.Identifier(MIGRATOR)
            )
        )
    with connect(t, name, "postgres") as c:
        # Authorize identity reads only, as in the approved provisioning contract.
        c.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION pg_control_system() TO {}").format(
                sql.Identifier(MIGRATOR)
            )
        )
    child = dict(t, database=name)
    with connect(child) as c:
        from alembic_v2.safety import IDENTITY_SQL, ROLES_SQL

        identity = c.execute(IDENTITY_SQL).fetchone()
        child["database_oid"] = identity["database_oid"]
        validate_server_snapshot(child, identity, c.execute(ROLES_SQL).fetchall())
        assert (
            c.execute(
                "SELECT count(*) AS n FROM pg_class WHERE relnamespace='public'::regnamespace"
            ).fetchone()["n"]
            == 0
        )
    save(suffix[1:] + "_target.json", child)
    save(suffix[1:] + "_preflight.json", identity)
    return child


def digest(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


def catalog():
    t = guard()
    manifest, statements = load_baseline()
    with connect(t) as c:
        actual = snapshot(c)
    save("installed_catalog.json", actual)
    # Fresh reference names permit deliberate reruns without reusing a partial descriptor.
    from uuid import uuid4

    ref = new_database(t, "_ref_" + uuid4().hex[:6])
    metadata_differences = []
    with connect(ref) as c, c.transaction():
        # Alembic's version table is declared by the manifest; no version is stamped.
        c.execute(
            "CREATE TABLE public.alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY(version_num))"
        )
        for entry, statement in zip(manifest["statements"], statements, strict=True):
            if entry["kind"] != "seed":
                c.execute(statement)
        expected = snapshot(c)
        # Independently render final column metadata recorded in the manifest,
        # rather than treating statement SQL alone as the expected column contract.
        for i, entry in enumerate(
            e for e in manifest["statements"] if e["kind"] == "table"
        ):
            temp = "manifest_columns_" + str(i)
            declarations = ",".join(v["declaration"] for v in entry["columns"].values())
            c.execute(
                sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(
                    sql.Identifier(temp), sql.SQL(declarations)
                )
            )
            cols = c.execute(
                """SELECT a.attname AS name,format_type(a.atttypid,a.atttypmod) AS type,
                a.attgenerated,a.attidentity,pg_get_expr(d.adbin,d.adrelid) AS expression,
                CASE WHEN a.attcollation=0 THEN NULL ELSE a.attcollation::regcollation::text END AS collation
                FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                WHERE a.attrelid=%s::regclass AND a.attnum>0 ORDER BY a.attnum""",
                (temp,),
            ).fetchall()
            for col in cols:
                observed = next(
                    a
                    for a in actual["columns"]
                    if a["relation"] == entry["name"] and a["name"] == col["name"]
                )
                if any(observed[k] != v for k, v in col.items()):
                    metadata_differences.append(
                        {"table": entry["name"], "expected": col, "actual": observed}
                    )
        # Reference state is transaction-local; never an install with a manufactured head.
        c.execute("ROLLBACK")
    save("manifest_rendered_catalog.json", expected)
    differences = {
        k: {"expected": expected[k], "actual": actual[k]}
        for k in expected
        if expected[k] != actual[k]
    }
    # Names and final columns are additionally checked directly against manifest metadata.
    direct = metadata_differences
    for entry in manifest["statements"]:
        kind, name = entry["kind"], entry["name"]
        if kind == "table":
            cols = [a for a in actual["columns"] if a["relation"] == name]
            if list(entry["columns"]) != [a["name"] for a in cols]:
                direct.append({"table": name, "error": "column order/names mismatch"})
            for a in cols:
                e = entry["columns"][a["name"]]
                if a["attidentity"] != e.get("identity", ""):
                    direct.append(
                        {
                            "table": name,
                            "column": a["name"],
                            "error": "identity mismatch",
                        }
                    )
                if a["attnotnull"] == e["nullable"]:
                    direct.append(
                        {
                            "table": name,
                            "column": a["name"],
                            "error": "nullability mismatch",
                        }
                    )
        elif kind == "function":
            matches = [
                a
                for a in actual["functions"]
                if "public." + a["name"] == name and a["extension"] is None
            ]
            if len(matches) != 1:
                direct.append({"function": name, "error": "missing or ambiguous"})
    for contract in manifest.get("identity_sequences", []):
        sequences = [
            r for r in actual["sequences"] if r["name"] == contract["sequence"]
        ]
        expected_sequence = {
            "name": contract["sequence"],
            "type": "bigint",
            "seqstart": contract["start"],
            "seqincrement": contract["increment"],
            "seqmin": contract["min"],
            "seqmax": contract["max"],
            "seqcache": contract["cache"],
            "seqcycle": contract["cycle"],
            "owned_table": contract["table"],
            "owned_column": contract["column"],
            "deptype": "i",
        }
        if sequences != [expected_sequence]:
            direct.append(
                {
                    "identity_sequence": contract["sequence"],
                    "expected": expected_sequence,
                    "actual": sequences,
                }
            )
    for generated in manifest.get("generated_column_contracts", []):
        cols = [
            r
            for r in actual["columns"]
            if r["relation"] == generated["table"] and r["name"] == generated["column"]
        ]
        if (
            len(cols) != 1
            or any(
                cols[0][k] != generated[v]
                for k, v in [
                    ("type", "type"),
                    ("attgenerated", "attgenerated"),
                    ("expression", "expression"),
                ]
            )
            or cols[0]["attnotnull"] == generated["nullable"]
        ):
            direct.append(
                {
                    "generated_column": generated["table"] + "." + generated["column"],
                    "actual": cols,
                }
            )
        deps = [
            {k: r[k] for k in ("deptype", "referenced_catalog", "referenced_object")}
            for r in actual["default_dependencies"]
            if r["relation"] == generated["table"]
            and r["column_name"] == generated["column"]
        ]
        if deps != generated["dependencies"]:
            direct.append(
                {"generated_dependencies": generated["table"], "actual": deps}
            )
    result = {
        "stage": t.get("recertification_stage", "E10.10.5B"),
        "comparison_executed": True,
        "method": "PostgreSQL 17 canonical rendering of verified manifest statements in a separate empty isolated database, plus direct manifest metadata checks",
        "manifest_sha256": hashlib.sha256(
            (ROOT / "alembic_v2/baseline/catalog_manifest.json").read_bytes()
        ).hexdigest(),
        "installed_sha256": digest(actual),
        "expected_sha256": digest(expected),
        "counts": {k: len(v) for k, v in actual.items()},
        "differences": differences,
        "direct_manifest_differences": direct,
        "status": "passed" if not differences and not direct else "failed",
    }
    (ROOT / "docs/audits/e10_10_5_catalog_diff.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n"
    )
    assert not differences and not direct, "catalog comparison failed"


def rollback():
    from uuid import uuid4

    t = guard()
    child = new_database(t, "_rollback_" + uuid4().hex[:6])
    target_path = EVIDENCE / "rollback_target.json"
    save("rollback_target.json", child)
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT),
        PGV2_DATABASE_URL=f"postgresql+psycopg://{MIGRATOR}@127.0.0.1:{child['host_port']}/{child['database']}",
    )
    harness = ROOT / "scripts/db/v2_inject_failure.py"
    result = run([sys.executable, str(harness), str(target_path)], env=env, check=False)
    with connect(child) as c:
        observed = snapshot(c)
        head = c.execute(
            "SELECT to_regclass('public.alembic_version') AS head"
        ).fetchone()["head"]
    passed = (
        result.returncode != 0
        and "V2_INJECTED_FAILURE_AFTER_500" in result.stderr
        and not observed["relations"]
        and not observed["functions"]
        and head is None
        and len(observed["extensions"]) == 1
    )
    save(
        "rollback_result.json",
        {
            "passed": passed,
            "returncode": result.returncode,
            "head": head,
            "after": observed,
        },
    )
    assert passed, "rollback/false head check failed"


def idempotence():
    t = guard()

    def data(c, catalog):
        rows = {}
        for table in (r["name"] for r in catalog["relations"] if r["relkind"] == "r"):
            query = sql.SQL(
                "SELECT row_to_json(t)::text AS row,xmin::text,ctid::text FROM {} t ORDER BY row_to_json(t)::text"
            ).format(sql.Identifier(table))
            rows[table] = c.execute(query).fetchall()
        rows["sequence_state"] = c.execute(
            "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
        ).fetchall()
        return rows

    with connect(t) as c:
        before = snapshot(c)
        all_data_before = data(c, before)
        data_before = c.execute(
            "SELECT xmin::text,ctid::text,version_num FROM alembic_version"
        ).fetchall()
        gate_before = c.execute(
            "SELECT row_to_json(g)::text AS row,xmin::text,ctid::text FROM experiment_execution_gate g"
        ).fetchall()
    from certify_v2_route_a import upgrade

    upgrade()
    with connect(t) as c:
        after = snapshot(c)
        all_data_after = data(c, after)
        data_after = c.execute(
            "SELECT xmin::text,ctid::text,version_num FROM alembic_version"
        ).fetchall()
        gate_after = c.execute(
            "SELECT row_to_json(g)::text AS row,xmin::text,ctid::text FROM experiment_execution_gate g"
        ).fetchall()
    passed = (
        before == after
        and data_before == data_after
        and gate_before == gate_after
        and all_data_before == all_data_after
    )
    save(
        "idempotence_result.json",
        {
            "passed": passed,
            "before": digest(before),
            "after": digest(after),
            "all_data_before": digest(all_data_before),
            "all_data_after": digest(all_data_after),
            "tables_checked": len(all_data_before) - 1,
            "head_before": data_before,
            "head_after": data_after,
            "gate_before": gate_before,
            "gate_after": gate_after,
        },
    )
    assert passed


def backup_restore(reuse_backup=False):
    t = guard()
    from test_v2_route_a_server import evaluation, fixture, pair

    # Commit synthetic rows so restoration checks cover linked scientific-shaped
    # data, generated columns and metrics, not just empty table definitions.
    if not reuse_backup:
        with connect(t, role=RUNTIME) as c, c.transaction():
            ids = fixture(c)
            pair(c, evaluation(ids))
        save("backup_synthetic_fixture.json", {k: str(v) for k, v in ids.items()})
    restored = new_database(t, "_restore_retry" if reuse_backup else "_restore")
    dump_path = "/tmp/v2_route_a.dump"
    local = EVIDENCE / "isolated_backup.dump"
    if not reuse_backup:
        run(
            DOCKER
            + [
                "exec",
                t["container_id"],
                "pg_dump",
                "-U",
                "postgres",
                "-d",
                t["database"],
                "-Fc",
                "-f",
                dump_path,
            ]
        )
        run(DOCKER + ["cp", t["container_id"] + ":" + dump_path, str(local)])
    run(
        DOCKER
        + [
            "exec",
            t["container_id"],
            "pg_restore",
            "-U",
            "postgres",
            "--role",
            MIGRATOR,
            "-d",
            restored["database"],
            "--exit-on-error",
            "--single-transaction",
            dump_path,
        ]
    )
    # pg_dump without --create does not restore database ACLs; explicitly replay the source database ACL.
    with connect(restored, role="postgres") as c:
        name = sql.Identifier(restored["database"])
        c.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(name))
        c.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO capstone_v2_runtime").format(name)
        )
    with connect(restored) as c:
        # Replay the exact E-01 version-table contract, including runtime SELECT.
        # Retain catalog representation as well as effective privileges.
        c.execute(
            "REVOKE ALL ON TABLE public.alembic_version FROM PUBLIC, capstone_v2_runtime"
        )
        c.execute("GRANT SELECT ON TABLE public.alembic_version TO capstone_v2_runtime")
    with connect(t) as c, connect(restored) as r:
        before, after = snapshot(c), snapshot(r)
        tables = [a["name"] for a in before["relations"] if a["relkind"] == "r"]
        source_data, restored_data = {}, {}
        for table in tables:
            query = sql.SQL(
                "SELECT row_to_json(t)::text AS row FROM {} t ORDER BY row_to_json(t)::text"
            ).format(sql.Identifier(table))
            source_data[table] = c.execute(query).fetchall()
            restored_data[table] = r.execute(query).fetchall()
        source_seq = c.execute(
            "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
        ).fetchone()
        restored_seq = r.execute(
            "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
        ).fetchone()
    save("restored_catalog.json", after)
    passed = (
        before == after and source_data == restored_data and source_seq == restored_seq
    )
    save(
        "restore_result.json",
        {
            "passed": passed,
            "backup_sha256": hashlib.sha256(local.read_bytes()).hexdigest(),
            "source_catalog": digest(before),
            "restored_catalog": digest(after),
            "source_data": digest(source_data),
            "restored_data": digest(restored_data),
            "tables_compared": len(tables),
            "source_sequence": source_seq,
            "restored_sequence": restored_seq,
        },
    )
    assert passed, "restore comparison failed"


if __name__ == "__main__":
    {
        "catalog": catalog,
        "rollback": rollback,
        "idempotence": idempotence,
        "backup_restore": backup_restore,
        "restore_retry": lambda: backup_restore(True),
    }[sys.argv[1]]()
