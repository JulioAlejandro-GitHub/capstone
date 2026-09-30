"""Offline comparison of the 16 authorized tables and explicit DBV2.4 SQL plan."""

import csv
import io
import json
import re

from dbv23_source import DATASET, OFFICIAL, USER, E, save


def main():
    source = json.loads((E / "source_catalog.json").read_text())
    dest = json.loads((E / "catalog_after_restart.json").read_text())
    tables = DATASET + USER
    rows = []
    differences = []
    dependencies = {t: set() for t in tables}
    edges = []
    for t in tables:
        sc = {x["name"]: x for x in source["columns"] if x["relation"] == t}
        dc = {x["name"]: x for x in dest["columns"] if x["relation"] == t}
        assert sc.keys() == dc.keys(), t
        for name, s in sc.items():
            d = dc[name]
            assert all(
                s[k] == d[k]
                for k in (
                    "type",
                    "attnotnull",
                    "attidentity",
                    "attgenerated",
                    "collation",
                )
            ), (t, name)
            assert not s["attidentity"] and not s["attgenerated"], (
                "unreviewed identity/generated",
                t,
                name,
            )
            if s["expression"] != d["expression"]:
                assert (
                    s["expression"] == "gen_random_uuid()"
                    and d["expression"] == "pg_catalog.gen_random_uuid()"
                )
                differences.append(
                    {
                        "table": t,
                        "column": name,
                        "kind": "UUID_DEFAULT_QUALIFICATION",
                        "impact": "NONE: explicit copied ID; default not evaluated",
                    }
                )
            technical = t == "dataset_versions" and name == "status"
            rows.append(
                {
                    "source_table": t,
                    "destination_table": t,
                    "source_column": name,
                    "destination_column": name,
                    "source_type": s["type"],
                    "destination_type": d["type"],
                    "nullable_compatible": True,
                    "source_nullable": not s["attnotnull"],
                    "destination_nullable": not d["attnotnull"],
                    "source_default": s["expression"],
                    "destination_default": d["expression"],
                    "identity_handling": "NOT_APPLICABLE_EXPLICIT_ID",
                    "generated_handling": "NOT_GENERATED_COPY_EXPLICITLY",
                    "direct_copy": not technical,
                    "transformation_required": "TECHNICAL_FROZEN_VALIDATED_FROZEN_SAME_TRANSACTION"
                    if technical
                    else "NONE",
                    "status": "TECHNICAL_HANDLING_REQUIRED"
                    if technical
                    else "DIRECT_INSERT_SELECT_COMPATIBLE",
                }
            )
        for category in ("constraints", "indexes", "triggers"):
            ss = {x["name"]: x for x in source[category] if x["relation"] == t}
            dd = {x["name"]: x for x in dest[category] if x["relation"] == t}
            assert ss.keys() == dd.keys(), (t, category, "identity difference")
            for name, s in ss.items():
                d = dd[name]
                for k in s.keys() - {"owner"}:
                    if s[k] == d[k]:
                        continue
                    assert (
                        category == "constraints"
                        and s["contype"] == "f"
                        and k == "definition"
                    )
                    assert (
                        re.sub(
                            r"ON DELETE (CASCADE|SET NULL)", "ON DELETE RESTRICT", s[k]
                        )
                        == d[k]
                    )
                    differences.append(
                        {
                            "table": t,
                            "constraint": name,
                            "kind": "DELETE_ACTION_RESTRICT",
                            "impact": "NONE for INSERT; parent rows preserved",
                        }
                    )
        for fk in [
            x for x in dest["constraints"] if x["relation"] == t and x["contype"] == "f"
        ]:
            parent = re.search(
                r"REFERENCES (?:public\.)?(\w+)\(", fk["definition"]
            ).group(1)
            assert parent in tables, (
                "REQUIRED_DEPENDENCY_DISCOVERED",
                t,
                parent,
                fk["name"],
            )
            dependencies[t].add(parent)
            edges.append(
                {
                    "child": t,
                    "parent": parent,
                    "fk": fk["name"],
                    "definition": fk["definition"],
                }
            )
    # Match every transfer-domain trigger's function body/attributes too.
    fnames = set()
    for tr in dest["triggers"]:
        if tr["relation"] in tables:
            fnames.add(
                re.search(
                    r"EXECUTE FUNCTION (?:public\.)?(\w+)\(", tr["definition"]
                ).group(1)
            )
    for name in fnames:
        s = next(x for x in source["functions"] if x["name"] == name)
        d = next(x for x in dest["functions"] if x["name"] == name)
        for k in (
            "definition",
            "prosecdef",
            "proleakproof",
            "provolatile",
            "proparallel",
            "proisstrict",
            "proconfig",
        ):
            assert s[k] == d[k], (name, k)
    order = []
    pending = set(tables)
    while pending:
        ready = sorted(t for t in pending if not dependencies[t] & pending)
        assert ready, "FK cycle"
        order += ready
        pending -= set(ready)
    save(
        "compatibility_details.json",
        {
            "status": "PASS",
            "differences": differences,
            "all_column_types_nullable_identity_generated_match": True,
            "all_PK_UNIQUE_CHECK_index_trigger_identities_match": True,
            "trigger_functions_preserved": sorted(fnames),
            "semantic_transformations_required": 0,
            "dataset": {"inspected": 13, "direct": 12, "technical": 1, "blocked": 0},
            "user": {"inspected": 3, "direct": 3, "technical": 0, "blocked": 0},
            "matrix_rows": len(rows),
            "unexpected_dependencies": [],
            "audit_events_transfer_required": False,
            "order": order,
            "edges": edges,
        },
    )
    buff = io.StringIO(newline="")
    w = csv.DictWriter(buff, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    (E / "dbv2_3_insert_select_matrix.csv").write_text(buff.getvalue())
    cols = {
        t: [x["name"] for x in dest["columns"] if x["relation"] == t] for t in tables
    }

    def quoted(names):
        return ", ".join('"' + n + '"' for n in names)

    def selection(t):
        result = "SELECT " + quoted(cols[t]) + ' FROM pg_temp."dbv24_src_' + t + '"'
        if t == "roles":
            result += " WHERE id IN (SELECT role_id FROM pg_temp.dbv24_src_user_roles)"
        return result

    counts = json.loads((E / "source_table_counts.json").read_text())
    counts["roles"] = json.loads((E / "data_preflight.json").read_text())[
        "referenced_role_count"
    ]
    plan = [
        "-- DBV2.4 TRANSFER PLAN",
        "-- GENERATED AND VALIDATED BY DBV2.3",
        "-- DO NOT EXECUTE DURING DBV2.3",
        "",
        "-- Requires explicit GATE DBV2.3 and DBV2.4 authorization before execution.",
        "-- Source and destination are distinct clusters. PostgreSQL has no native cross-database SELECT.",
        "-- DBV2.4 transport: export only the 16 authorized tables from one REPEATABLE READ READ ONLY",
        "-- source snapshot; load identical values into session-local pg_temp staging via COPY FROM STDIN.",
        "-- This is a reviewed SQL plan with a transport step, NOT an executable cross-database installer.",
        "-- Never load password_hash values into evidence/logs. No credential literals occur in this file.",
        "-- UUID columns are copied explicitly. None of these 16 tables has identity/generated columns.",
        "-- No FK/trigger disabling. No legacy data or scientific metadata is transformed.",
        "BEGIN;",
        "-- Destination must be the attested persistent BD-v2; verify cluster/host/database before BEGIN.",
        "-- The operator must populate the temporary tables at the transport boundary below before proceeding.",
    ]
    for t in tables:
        plan.append(
            f'CREATE TEMP TABLE "dbv24_src_{t}" (LIKE public."{t}") ON COMMIT DROP;'
        )
    plan += [
        "",
        "-- TRANSPORT BOUNDARY (DBV2.4 ONLY): populate all explicit columns with COPY FROM STDIN.",
        "-- Source export SELECT statements are comments, to run only on the READ ONLY source:",
    ]
    for t in tables:
        plan.append("-- SELECT " + quoted(cols[t]) + ' FROM public."' + t + '";')
    plan += [
        "",
        "-- No application writers may connect while transferring. Lock all authorized destination tables.",
        "LOCK TABLE "
        + ", ".join('public."' + t + '"' for t in order)
        + " IN ACCESS EXCLUSIVE MODE;",
        "DO $preflight$ BEGIN",
    ]
    for t in tables:
        plan += [
            f" IF EXISTS (SELECT 1 FROM public.\"{t}\") THEN RAISE EXCEPTION 'DESTINATION_NOT_EMPTY: {t}'; END IF;",
            f" IF (SELECT count(*) FROM ({selection(t)}) q) <> {counts[t]} THEN RAISE EXCEPTION 'SOURCE_COUNT_CHANGED_OR_STAGING_MISSING: {t}'; END IF;",
        ]
    plan += [
        " IF EXISTS (SELECT 1 FROM pg_temp.dbv24_src_dataset_versions WHERE status='FROZEN' AND frozen_at IS NULL) THEN RAISE EXCEPTION 'FROZEN_TIMESTAMP_CANNOT_BE_PRESERVED'; END IF;",
        "END $preflight$;",
        "",
    ]
    for t in order:
        plan.append(
            "-- "
            + t
            + ": explicit columns; "
            + (
                "approved DBV2.1 temporary lifecycle handling"
                if t == "dataset_versions"
                else "DIRECT_INSERT_SELECT_COMPATIBLE"
            )
        )
        selected = selection(t)
        if t == "dataset_versions":
            expr = [
                "CASE WHEN status='FROZEN' THEN 'VALIDATED' ELSE status END"
                if n == "status"
                else '"' + n + '"'
                for n in cols[t]
            ]
            selected = (
                "SELECT " + ", ".join(expr) + " FROM pg_temp.dbv24_src_dataset_versions"
            )
        plan += [
            'INSERT INTO public."' + t + '" (' + quoted(cols[t]) + ")",
            selected + ";",
            "",
        ]
    plan += [
        "-- Restore the ORIGINAL status before COMMIT; frozen_at is preserved (preflight forbids NULL).",
        "UPDATE public.dataset_versions AS d SET status=s.status FROM pg_temp.dbv24_src_dataset_versions AS s WHERE d.id=s.id AND s.status='FROZEN' AND d.status='VALIDATED';",
        "SET CONSTRAINTS ALL IMMEDIATE;",
        "",
        "-- Bidirectional exact row equality, including IDs, paths, hashes, NULLs and timestamps.",
        "-- Comparisons involving password_hash return no values; errors name only the table.",
        "DO $verify$ BEGIN",
    ]
    for t in tables:
        actual = "SELECT " + quoted(cols[t]) + ' FROM public."' + t + '"'
        expected = selection(t)
        plan.append(
            f" IF EXISTS (({actual}) EXCEPT ALL ({expected})) OR EXISTS (({expected}) EXCEPT ALL ({actual})) THEN RAISE EXCEPTION 'ROW_PRESERVATION_MISMATCH: {t}'; END IF;"
        )
    plan += [
        f" IF (SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id='{OFFICIAL}')<>27558 THEN RAISE EXCEPTION 'OFFICIAL_TOTAL_MISMATCH'; END IF;",
        f" IF (SELECT count(DISTINCT clinical_identity_id) FROM dataset_split_assignments WHERE dataset_version_id='{OFFICIAL}')<>201 THEN RAISE EXCEPTION 'OFFICIAL_PATIENTS_MISMATCH'; END IF;",
    ]
    for split, count in [("train", 22180), ("val", 2693), ("test", 2685)]:
        plan.append(
            f" IF (SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id='{OFFICIAL}' AND split_name='{split}')<>{count} THEN RAISE EXCEPTION 'OFFICIAL_SPLIT_MISMATCH: {split}'; END IF;"
        )
    plan += [
        " IF (SELECT count(*) FROM dataset_split_images)<>55116 THEN RAISE EXCEPTION 'PHYSICAL_INVENTORY_MISMATCH'; END IF;",
        " IF (SELECT count(*) FROM (SELECT dataset_dir FROM dataset_split_images GROUP BY dataset_dir HAVING count(*)=27558) q)<>2 THEN RAISE EXCEPTION 'PHYSICAL_ROOTS_MISMATCH'; END IF;",
        "END $verify$;",
        "COMMIT;",
        "-- All temporary staging disappears on COMMIT. Recompare persistent structural manifest.",
        "-- No audit_events, experiments, runs, campaigns, artifacts, XAI, publications or E10 transfer.",
    ]
    (E / "dbv2_4_transfer_plan.sql").write_text("\n".join(plan) + "\n")
    print(
        f"PASS {len(rows)} column mappings; dataset 12 direct + 1 technical; user 3 direct; no external dependency"
    )


if __name__ == "__main__":
    main()
