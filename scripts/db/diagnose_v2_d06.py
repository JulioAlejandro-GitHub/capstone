"""Read native CHECK trees and probe semantics only in isolated temporary fixtures."""

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from alembic_v2.safety import inspect_isolation

E = ROOT / "docs/audits/e10_10_5d4_evidence"
PAIRS = [
    ("campaign_controlled_requests", "campaign_controlled_requests_reason_check"),
    ("cell_predictions", "ck_cell_prediction_label_index"),
    ("smear_analysis_summaries", "ck_smear_summary_fraction"),
    ("smear_analysis_summaries", "ck_smear_summary_probabilities"),
]
QUERY = """SELECT c.conname,c.conrelid::regclass::text relation,pg_get_constraintdef(c.oid,false) definition,pg_get_expr(c.conbin,c.conrelid,false) expression,c.conbin::text tree,c.convalidated,c.connoinherit,c.condeferrable,c.condeferred,
(SELECT json_agg(json_build_object('deptype',d.deptype,'catalog',d.refclassid::regclass::text,'object',pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid)) ORDER BY d.deptype,d.refclassid::regclass::text,pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid)) FROM pg_depend d WHERE d.classid='pg_constraint'::regclass AND d.objid=c.oid) dependencies
FROM pg_constraint c WHERE c.conrelid=%s::regclass AND c.conname=%s"""


def values(name):
    if name.endswith("reason_check"):
        return ["reason"], [
            (v,)
            for v in [None, "", " ", "  ", "\t", "\n", "\t \n", " x ", "x", "\u00a0"]
        ]
    if name == "ck_cell_prediction_label_index":
        return [
            "prediction_status",
            "predicted_class_index",
            "predicted_label",
            "probability_parasitized",
            "threshold_used",
        ], list(
            itertools.product(
                [None, "completed", "pending"],
                [None, -1, 0, 1, 2],
                [None, "parasitized", "uninfected", "other"],
                [None, -0.01, 0.0, 0.49, 0.5, 0.51, 1.0, 1.01],
                [None, 0.0, 0.5, 1.0],
            )
        )
    if name == "ck_smear_summary_fraction":
        return [
            "classified_cell_count",
            "parasitized_candidate_count",
            "parasitized_candidate_fraction",
        ], list(
            itertools.product(
                [None, -1, 0, 1, 2],
                [None, -1, 0, 1, 2],
                [None, -1.0, 0.0, 0.5, 1.0, 2.0, 0.5 + 1e-9, 0.5 + 1.1e-9],
            )
        )
    return [
        "classified_cell_count",
        "maximum_probability_parasitized",
        "mean_probability_parasitized",
        "median_probability_parasitized",
    ], list(
        itertools.product(
            [None, -1, 0, 1, 2],
            [None, -0.01, 0.0, 0.5, 1.0, 1.01],
            [None, -0.01, 0.0, 0.5, 1.0, 1.01],
            [None, -0.01, 0.0, 0.5, 1.0, 1.01],
        )
    )


def main():
    result = {}
    for kind, path in [
        ("legacy", "docs/audits/e10_10_5d2_evidence/route_b"),
        ("route_a", "docs/audits/e10_10_5d2_evidence/route_a"),
    ]:
        folder = ROOT / path
        t = json.loads((folder / "target.json").read_text())
        inspect_isolation(t)
        if kind == "route_a":
            kwargs = {
                "passfile": json.loads((folder / "private_paths.json").read_text())[
                    "pgpass"
                ]
            }
        else:
            private = Path(
                json.loads(
                    (
                        ROOT / "docs/audits/e10_10_5d_evidence/private_location.json"
                    ).read_text()
                )["directory"]
            )
            kwargs = {
                "password": (private / "container.env")
                .read_text()
                .splitlines()[0]
                .split("=", 1)[1]
            }
        with psycopg.connect(
            host="127.0.0.1",
            port=t["host_port"],
            dbname=t["database"],
            user="capstone_v2_migrator",
            row_factory=dict_row,
            autocommit=True,
            **kwargs,
        ) as c:
            assert (
                c.execute(
                    "SELECT system_identifier::text id FROM pg_control_system()"
                ).fetchone()["id"]
                == t["postgres_system_identifier"]
            )
            assert (
                c.execute("SHOW server_version_num").fetchone()["server_version_num"]
                == "170009"
            )
            with c.transaction():
                c.execute("SET LOCAL search_path=public,pg_catalog")
                result[kind] = {}
                for table, name in PAIRS:
                    observation = c.execute(QUERY, ("public." + table, name)).fetchone()
                    columns, fixtures = values(name)
                    types = {
                        r["attname"]: r["type"]
                        for r in c.execute(
                            "SELECT attname,format_type(atttypid,atttypmod) type FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped",
                            ("public." + table,),
                        ).fetchall()
                    }
                    declarations = sql.SQL(",").join(
                        sql.SQL("{} {}").format(
                            sql.Identifier(col), sql.SQL(types[col])
                        )
                        for col in columns
                    )
                    c.execute(
                        sql.SQL("CREATE TEMP TABLE fixture ({}) ON COMMIT DROP").format(
                            declarations
                        )
                    )
                    c.execute(
                        sql.SQL(
                            "CREATE TEMP TABLE checked (LIKE fixture, CHECK ({})) ON COMMIT DROP"
                        ).format(sql.SQL(observation["expression"]))
                    )
                    output = []
                    for row in fixtures:
                        verdict = None
                        error = None
                        try:
                            with c.transaction():
                                query = sql.SQL(
                                    "SELECT ({}) AS verdict FROM (VALUES ({})) AS x({})"
                                ).format(
                                    sql.SQL(observation["expression"]),
                                    sql.SQL(",").join(
                                        sql.SQL("%s::" + types[col]) for col in columns
                                    ),
                                    sql.SQL(",").join(map(sql.Identifier, columns)),
                                )
                                verdict = c.execute(query, row).fetchone()["verdict"]
                        except psycopg.Error as exc:
                            error = exc.sqlstate
                        try:
                            with c.transaction():
                                c.execute(
                                    sql.SQL("INSERT INTO checked VALUES ({})").format(
                                        sql.SQL(",").join(
                                            sql.Placeholder() for _ in columns
                                        )
                                    ),
                                    row,
                                )
                                effective = "accepted"
                        except psycopg.Error as exc:
                            effective = exc.sqlstate
                        assert effective == (
                            "accepted"
                            if verdict is not False and error is None
                            else error or "23514"
                        )
                        output.append(
                            {
                                "values": row,
                                "truth": verdict,
                                "evaluation_error": error,
                                "check_result": effective,
                            }
                        )
                    c.execute("DROP TABLE checked,fixture")
                    # Resolve all referenced function/operator/cast/type identities from the stored tree.
                    import re

                    resolved = {}
                    for field, catalog, expr in [
                        ("funcid", "pg_proc", "oid::regprocedure::text"),
                        ("opno", "pg_operator", "oid::regoperator::text"),
                        ("opfuncid", "pg_proc", "oid::regprocedure::text"),
                        ("consttype", "pg_type", "oid::regtype::text"),
                        ("vartype", "pg_type", "oid::regtype::text"),
                        ("resulttype", "pg_type", "oid::regtype::text"),
                        ("funcresulttype", "pg_type", "oid::regtype::text"),
                    ]:
                        ids = sorted(
                            {
                                int(x)
                                for x in re.findall(
                                    ":" + field + r" (\d+)", observation["tree"]
                                )
                            }
                        )
                        resolved[field] = [
                            {
                                "oid": oid,
                                "object": c.execute(
                                    "SELECT "
                                    + expr
                                    + " value FROM "
                                    + catalog
                                    + " WHERE oid=%s",
                                    (oid,),
                                ).fetchone()["value"],
                            }
                            for oid in ids
                            if oid
                        ]
                    observation["resolved"] = resolved
                    observation["column_types"] = {k: types[k] for k in columns}
                    observation["fixture_count"] = len(fixtures)
                    observation["tests"] = output
                    result[kind][name] = observation
                c.execute("ROLLBACK")
        (E / "d06_native_and_tests.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
    for _, name in PAIRS:
        a, b = result["legacy"][name], result["route_a"][name]
        assert a["tests"] == b["tests"], name + " BEHAVIOR_DIFFERENCE"
    print({name: result["legacy"][name]["fixture_count"] for _, name in PAIRS})


if __name__ == "__main__":
    main()
