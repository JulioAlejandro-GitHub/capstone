"""Future D transaction runner. No connections on import; C never invokes apply()."""

import json
import os
from pathlib import Path

from .core import (
    CATALOG_HASH,
    ROOT,
    canonical,
    contract,
    digest,
    require,
    row_key,
    table_digest,
    target,
)
from .ddl import delta, qi, qtable
from .planner import build_plan
from .preflight import authorization, schema_signature


def private_write(path, value):
    path = Path(path)
    require(path.parent.is_dir(), "PRIVATE_ARCHIVE_DIRECTORY_REQUIRED")
    info = path.parent.stat()
    require(
        info.st_uid == os.getuid() and info.st_mode & 0o077 == 0,
        "PRIVATE_DIRECTORY_MODE_REQUIRED",
    )
    require(
        not path.parent.resolve().is_relative_to(ROOT),
        "PRIVATE_ARCHIVE_OUTSIDE_REPOSITORY_REQUIRED",
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(canonical(value))
        f.flush()
        os.fsync(f.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def capture(c):
    spec = contract()
    catalog = {}
    for kind, query in spec["queries"].items():
        catalog[kind] = c.execute(query).fetchall()
    rows = {
        t: c.execute("SELECT * FROM " + qtable(t)).fetchall() for t in spec["tables"]
    }
    types = c.execute(
        "SELECT c.relname AS table_name,a.attname AS column_name,format_type(a.atttypid,a.atttypmod) AS type FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid WHERE c.relnamespace='public'::regnamespace AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped"
    ).fetchall()
    from .ddl import same_type

    actual = {(r["table_name"], r["column_name"]): r["type"] for r in types}
    for t, cols in spec["column_types"].items():
        for k, v in cols.items():
            require(
                (t, k) in actual and same_type(actual[t, k], v),
                "LEGACY_TYPEMOD_DRIFT",
                t + "." + k,
            )
    native = catalog_snapshot(c)
    certified = certified_catalog()
    require(native["extensions"] == certified["extensions"], "LEGACY_EXTENSION_DRIFT")
    require(native["sequences"] == certified["sequences"], "LEGACY_SEQUENCE_DRIFT")
    require(
        all(r["owner"] == "capstone_v2_migrator" for r in native["relations"]),
        "LEGACY_OWNER_MISMATCH",
    )
    require(
        all(r["owner"] == "capstone_v2_migrator" for r in native["functions"]),
        "LEGACY_FUNCTION_OWNER_MISMATCH",
    )
    namespaces = c.execute(
        "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('public','information_schema')"
    ).fetchall()
    require(not namespaces, "UNEXPECTED_USER_SCHEMA")
    sequences = {
        r["name"]: c.execute(
            "SELECT last_value,is_called FROM " + qtable(r["name"])
        ).fetchone()
        for r in native["sequences"]
    }
    return {
        "catalog": catalog,
        "rows": rows,
        "native_catalog": native,
        "sequence_values": sequences,
    }


def catalog_snapshot(c):
    from scripts.db.v2_catalog_probe import snapshot

    return snapshot(c)


def certified_catalog():
    path = ROOT / "docs/audits/e10_10_5b_evidence/run_b01/installed_catalog.json"
    value = json.loads(path.read_text())
    import hashlib

    actual = hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()
    require(actual == CATALOG_HASH, "ROUTE_A_CERTIFICATE_CHANGED")
    return value


def reconcile(c, plan):
    tables = {e["name"]: e for e in target()[0]["statements"] if e["kind"] == "table"}
    report = {}
    for t, expected in plan["rows"].items():
        if t == "alembic_version":
            continue
        actual = c.execute("SELECT * FROM " + qtable(t)).fetchall()
        if t in plan["preserved_tables"]:
            require(
                table_digest(actual) == table_digest(expected),
                "PROTECTED_RECONCILIATION_FAILED",
                t,
            )
        else:
            # Compare only explicitly projected columns; generated fields checked by server/catalog.
            require(len(actual) == len(expected), "ROW_COUNT_MISMATCH", t)
            keys = contract()["primary_keys"].get(t)
            if keys is None:
                entries = [
                    e
                    for e in target()[0]["statements"]
                    if e["kind"] == "constraint"
                    and e.get("table") == t
                    and e.get("constraint_type") == "CONSTR_PRIMARY"
                ]
                require(len(entries) == 1, "TARGET_PRIMARY_KEY_REQUIRED", t)
                keys = entries[0]["keys"]
            keyed = lambda r, keys=keys: tuple(str(r[k]) for k in keys)
            observed = {keyed(r): r for r in actual}
            for r in expected:
                require(keyed(r) in observed, "DESTINATION_IDENTIFIER_MISSING", t)
                a = observed[keyed(r)]
                for k, v in r.items():
                    if tables[t]["columns"][k]["generated"]:
                        continue
                    if isinstance(v, (dict, list)):
                        equal = digest(a[k]) == digest(v)
                    elif v is None:
                        equal = a[k] is None
                    elif t == "run_clinical_metrics" and k in (
                        "accuracy",
                        "precision_parasitized",
                        "recall_parasitized",
                        "sensitivity_parasitized",
                        "specificity",
                        "f1_parasitized",
                        "f2_parasitized",
                        "balanced_accuracy",
                    ):
                        from decimal import Decimal

                        equal = a[k] is not None and abs(
                            Decimal(str(a[k])) - Decimal(str(v))
                        ) <= Decimal("1e-12")
                    else:
                        equal = str(a[k]) == str(v)
                    require(equal, "PROJECTED_VALUE_MISMATCH", t + "." + k)
        report[t] = {"count": len(actual), "sha256": table_digest(actual)}
    for name, expected in plan["original_archive"].get("sequence_values", {}).items():
        require(
            c.execute("SELECT last_value,is_called FROM " + qtable(name)).fetchone()
            == expected,
            "SEQUENCE_VALUE_CHANGED",
            name,
        )
    require(catalog_snapshot(c) == certified_catalog(), "FINAL_CATALOG_MISMATCH")
    return report


def mutate_rows(c, plan):
    from psycopg.types.json import Jsonb

    spec = contract()
    manifest, _ = target()
    cols = {
        e["name"]: e["columns"] for e in manifest["statements"] if e["kind"] == "table"
    }
    # PostgreSQL arrays must remain native arrays, not JSONB parameters.
    adapt = lambda t, k, v: (
        Jsonb(v) if v is not None and cols[t][k]["type"] in ("json", "jsonb") else v
    )
    # New FK constraints/triggers are installed after data projection; existing legacy guards stay active.
    for t, rows in plan["rows"].items():
        if t == "alembic_version" or t in plan["preserved_tables"]:
            continue
        original = plan["original_archive"]["rows"].get(t, [])
        keycols = spec["primary_keys"].get(t)
        old = {row_key(t, r): r for r in original} if keycols else {}
        newkeys = set()
        for row in rows:
            key = row_key(t, row) if keycols else None
            if key is not None:
                newkeys.add(key)
            values = {k: v for k, v in row.items() if not cols[t][k]["generated"]}
            if key in old:
                changed = {
                    k: v
                    for k, v in values.items()
                    if k not in old[key] or digest(v) != digest(old[key][k])
                }
                if not changed:
                    continue
                statement = (
                    "UPDATE "
                    + qtable(t)
                    + " SET "
                    + ",".join(qi(k) + "=%s" for k in changed)
                    + " WHERE "
                    + " AND ".join(qi(k) + "=%s" for k in keycols)
                )
                count = c.execute(
                    statement,
                    [adapt(t, k, v) for k, v in changed.items()]
                    + [old[key][k] for k in keycols],
                ).rowcount
                require(count == 1, "UPDATE_CARDINALITY", t)
            else:
                statement = (
                    "INSERT INTO "
                    + qtable(t)
                    + " ("
                    + ",".join(qi(k) for k in values)
                    + ") VALUES ("
                    + ",".join("%s" for _ in values)
                    + ")"
                )
                c.execute(statement, [adapt(t, k, v) for k, v in values.items()])
        removed = set(old) - newkeys
        require(not removed or t == "run_metrics", "UNAPPROVED_ROW_REMOVAL", t)
        for key in sorted(removed):
            c.execute(
                "DELETE FROM "
                + qtable(t)
                + " WHERE "
                + " AND ".join(qi(k) + "=%s" for k in keycols),
                [old[key][k] for k in keycols],
            )


def apply(
    approval, url, bindings, archive_directory, *, completed_plan=None, backup_path=None
):
    """D-only. Archive writes are private; rollback occurs on every precommit error.

    No provision, roles mutation, image I/O, operational connections or stamp.
    """
    t = authorization(
        approval, url
    )  # MUST precede driver import and connection creation.
    require(digest(bindings) == t["mapping_sha256"], "MAPPING_NOT_AUTHORIZED")
    require(
        backup_path is not None and Path(backup_path).is_file(),
        "ISOLATED_BACKUP_REQUIRED",
    )
    import hashlib

    with Path(backup_path).open("rb") as backup:
        require(
            hashlib.file_digest(backup, "sha256").hexdigest() == t["backup_sha256"],
            "ISOLATED_BACKUP_HASH_MISMATCH",
        )
    from alembic_v2.safety import (
        IDENTITY_SQL,
        ROLES_SQL,
        inspect_isolation,
        validate_server_snapshot,
    )

    inspect_isolation(t)
    import psycopg
    from psycopg.rows import dict_row
    from sqlalchemy.engine import make_url

    u = make_url(url)
    with psycopg.connect(
        host=u.host,
        port=u.port,
        user=u.username,
        password=u.password,
        dbname=u.database,
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=5,
    ) as c:
        from psycopg.types.string import TextLoader

        c.adapters.register_loader("uuid", TextLoader)
        identity = c.execute(IDENTITY_SQL).fetchone()
        roles = c.execute(ROLES_SQL).fetchall()
        validate_server_snapshot(t, identity, roles)
        private_write(
            Path(archive_directory) / "preflight_identity.json",
            {"identity": identity, "roles": roles, "authorization": t},
        )
        with c.transaction():
            # Every source table is locked before capture. READ COMMITTED ensures
            # capture sees commits completed while acquiring those locks, rather
            # than retaining the earlier advisory-lock/identity query snapshot.
            c.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            c.execute("SET LOCAL search_path=public,pg_catalog")
            c.execute("SET LOCAL lock_timeout='5s'")
            locked = c.execute(
                "SELECT pg_try_advisory_xact_lock(101005,3) AS locked"
            ).fetchone()["locked"]
            require(locked, "ADOPTION_BUSY")
            versions = c.execute(
                "SELECT version_num FROM public.alembic_version"
            ).fetchall()
            if versions == [{"version_num": "pg_v2_baseline"}]:
                require(completed_plan is not None, "COMPLETED_PLAN_REQUIRED")
                saved = dict(completed_plan)
                h = saved.pop("plan_sha256")
                require(
                    digest(saved) == h and h == t.get("completed_plan_sha256"),
                    "COMPLETED_PLAN_NOT_AUTHORIZED",
                )
                require(
                    saved["bindings_sha256"] == t["mapping_sha256"]
                    and saved["source_inventory_sha256"]
                    == t["source_inventory_sha256"],
                    "COMPLETED_PLAN_SOURCE_MISMATCH",
                )
                c.execute(
                    "LOCK TABLE "
                    + ",".join(qtable(name) for name in sorted(saved["rows"]))
                    + " IN ACCESS EXCLUSIVE MODE"
                )
                require(
                    c.execute(
                        "SELECT count(*) AS n FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
                    ).fetchone()["n"]
                    == 0,
                    "OTHER_DATABASE_SESSIONS_PRESENT",
                )
                report = reconcile(c, completed_plan)
                return {
                    "status": "already_adopted",
                    "reconciliation": report,
                    "plan_sha256": h,
                }
            require(
                versions == [{"version_num": "20260922_01"}], "LEGACY_REVISION_MISMATCH"
            )
            c.execute(
                "LOCK TABLE "
                + ",".join(qtable(t) for t in sorted(contract()["tables"]))
                + " IN ACCESS EXCLUSIVE MODE"
            )
            sessions = c.execute(
                "SELECT count(*) AS n FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
            ).fetchone()["n"]
            require(sessions == 0, "OTHER_DATABASE_SESSIONS_PRESENT")
            source = capture(c)
            require(
                digest(schema_signature(source["catalog"]))
                == t["legacy_schema_sha256"],
                "SOURCE_SCHEMA_NOT_AUTHORIZED",
            )
            plan = build_plan(source, bindings)
            require(
                plan["source_inventory_sha256"] == t["source_inventory_sha256"],
                "SOURCE_INVENTORY_CHANGED",
            )
            archive = Path(archive_directory)
            private_write(archive / "source_snapshot.json", source)
            private_write(archive / "bindings.json", bindings)
            private_write(archive / "plan.json", plan)
            phases = delta()
            private_write(archive / "ddl.json", phases)
            for statement in phases["prepare"]:
                c.execute(statement)
            mutate_rows(c, plan)
            for group in ("finalize", "validate", "triggers", "acl"):
                for statement in phases[group]:
                    c.execute(statement)
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            report = reconcile(c, plan)
            # Explicit adoption ledger transition, only AFTER structure + data equivalence.
            changed = c.execute(
                "UPDATE public.alembic_version SET version_num='pg_v2_baseline' WHERE version_num='20260922_01'"
            ).rowcount
            require(changed == 1, "HEAD_TRANSITION_CARDINALITY")
            private_write(
                archive / "prepared_receipt.json",
                {
                    "plan_sha256": plan["plan_sha256"],
                    "source_revision": "20260922_01",
                    "target_revision": "pg_v2_baseline",
                    "reconciliation": report,
                },
            )
        private_write(
            archive / "committed_receipt.json",
            {"plan_sha256": plan["plan_sha256"], "status": "committed"},
        )
        return {"status": "committed", "plan_sha256": plan["plan_sha256"]}
