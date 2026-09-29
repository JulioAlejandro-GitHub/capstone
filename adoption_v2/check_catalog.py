"""D-06 bounded canonical comparison of four native PostgreSQL CHECK trees.

Never rewrites constraints. Every raw definition remains in the comparison report.
"""

import hashlib
import json
import re
from copy import deepcopy

from .core import ROOT, require

REFERENCE_HASH = "80d721bafdb1af9fc229cad5abc8a35c9a5558df663fa8a69202440ce9dfe0d1"
PAIRS = {
    ("campaign_controlled_requests", "campaign_controlled_requests_reason_check"),
    ("cell_predictions", "ck_cell_prediction_label_index"),
    ("smear_analysis_summaries", "ck_smear_summary_fraction"),
    ("smear_analysis_summaries", "ck_smear_summary_probabilities"),
}
QUERY = """SELECT pg_get_constraintdef(c.oid,false) definition,c.conbin::text tree,
(SELECT json_agg(json_build_object('deptype',d.deptype,'catalog',d.refclassid::regclass::text,'object',pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid)) ORDER BY d.deptype,d.refclassid::regclass::text,pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid)) FROM pg_depend d WHERE d.classid='pg_constraint'::regclass AND d.objid=c.oid) dependencies
FROM pg_constraint c WHERE c.conrelid=%s::regclass AND c.conname=%s AND c.contype='c'"""


def parse_tree(raw):
    tokens = re.findall(r"\{|\}|\(|\)|\[|\]|[^\s{}()\[\]]+", raw)
    i = 0

    def value():
        nonlocal i
        token = tokens[i]
        i += 1
        if token == "{":
            node = {"@": tokens[i]}
            i += 1
            while tokens[i] != "}":
                key = tokens[i]
                i += 1
                require(key.startswith(":"), "CHECK_TREE_INVALID")
                items = []
                while tokens[i] != "}" and not tokens[i].startswith(":"):
                    items.append(value())
                require(bool(items) and key not in node, "CHECK_TREE_INVALID")
                node[key] = items[0] if len(items) == 1 else {"values": items}
            i += 1
            return node
        if token in ("(", "["):
            close = ")" if token == "(" else "]"
            items = []
            while tokens[i] != close:
                items.append(value())
            i += 1
            return items if token == "(" else {"bytes": items}
        return token

    result = value()
    require(i == len(tokens), "CHECK_TREE_INVALID")
    return result


def canonical_tree(raw):
    def normalize(v):
        if isinstance(v, list):
            return [normalize(x) for x in v]
        if not isinstance(v, dict):
            return v
        d = {k: normalize(x) for k, x in v.items() if k != ":location"}
        if (
            d.get("@") == "FUNCEXPR"
            and d.get(":funcid") == "885"
            and d.get(":funcformat") in ("0", "3")
        ):
            # pg_catalog.btrim(text), identity/definition reverified by capture().
            d[":funcformat"] = "0"
        if d.get("@") == "BOOLEXPR" and d.get(":boolop") in ("and", "or"):
            d[":args"] = [
                x
                for arg in d[":args"]
                for x in (
                    arg[":args"]
                    if isinstance(arg, dict)
                    and arg.get("@") == "BOOLEXPR"
                    and arg.get(":boolop") == d[":boolop"]
                    else [arg]
                )
            ]
        return d

    return normalize(parse_tree(raw))


def bindings(c, tree):
    result = {}
    for field, catalog, expr in [
        ("funcid", "pg_proc", "oid::regprocedure::text"),
        ("opno", "pg_operator", "oid::regoperator::text"),
        ("opfuncid", "pg_proc", "oid::regprocedure::text"),
        ("consttype", "pg_type", "oid::regtype::text"),
        ("vartype", "pg_type", "oid::regtype::text"),
        ("resulttype", "pg_type", "oid::regtype::text"),
        ("funcresulttype", "pg_type", "oid::regtype::text"),
        ("opresulttype", "pg_type", "oid::regtype::text"),
    ]:
        ids = sorted({int(x) for x in re.findall(":" + field + r" (\d+)", tree)})
        result[field] = []
        for oid in ids:
            if not oid:
                continue
            row = c.execute(
                "SELECT " + expr + " AS object FROM " + catalog + " WHERE oid=%s",
                (oid,),
            ).fetchone()
            require(row is not None, "CHECK_BINDING_MISSING")
            record = {"oid": oid, **row}
            if catalog == "pg_proc":
                record.update(
                    c.execute(
                        "SELECT pg_get_functiondef(oid) AS definition,provolatile,proisstrict,prosecdef,proleakproof,proparallel,proacl::text FROM pg_proc WHERE oid=%s",
                        (oid,),
                    ).fetchone()
                )
                require(record["provolatile"] == "i", "CHECK_VOLATILE_BINDING")
            result[field].append(record)
    return result


def capture(c, pair):
    rows = c.execute(QUERY, ("public." + pair[0], pair[1])).fetchall()
    require(len(rows) == 1, "CHECK_REFERENCE_MISSING", pair[1])
    r = rows[0]
    r["canonical"] = canonical_tree(r["tree"])
    r["bindings"] = bindings(c, r["tree"])
    return r


def reference():
    path = ROOT / "docs/audits/e10_10_5d4_evidence/route_a/check_reference.json"
    raw = path.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == REFERENCE_HASH, "CHECK_REFERENCE_CHANGED"
    )
    return json.loads(raw)["constraints"]


def compare(c, actual, expected):
    require(set(actual) == set(expected), "CATALOG_CATEGORY_MISMATCH")
    adjusted = deepcopy(actual)
    justified = []
    expected_rows = {(r["relation"], r["name"]): r for r in expected["constraints"]}
    refs = None
    for row in adjusted["constraints"]:
        pair = (row["relation"], row["name"])
        wanted = expected_rows.get(pair)
        if wanted is None or row == wanted or pair not in PAIRS:
            continue
        if {k: v for k, v in row.items() if k != "definition"} != {
            k: v for k, v in wanted.items() if k != "definition"
        }:
            continue
        if refs is None:
            refs = reference()
        ref = refs[pair[1]]
        observed = capture(c, pair)
        require(
            ref["definition"] == wanted["definition"]
            and observed["definition"] == row["definition"],
            "CHECK_SNAPSHOT_MISMATCH",
        )
        if all(
            observed[k] == ref[k] for k in ("canonical", "bindings", "dependencies")
        ):
            justified.append(
                {
                    "relation": pair[0],
                    "name": pair[1],
                    "actual_definition": row["definition"],
                    "expected_definition": wanted["definition"],
                    "canonical_sha256": hashlib.sha256(
                        json.dumps(ref["canonical"], sort_keys=True).encode()
                    ).hexdigest(),
                    "rule": "D-06: locations; identical btrim(text) formatting; ordered AND/OR associativity; exact bindings and dependencies",
                }
            )
            row["definition"] = wanted["definition"]
    differences = {
        k: {"actual": actual[k], "expected": expected[k]}
        for k in expected
        if adjusted[k] != expected[k]
    }
    return {
        "unjustified": differences,
        "justified": justified,
        "raw_catalog_equal": actual == expected,
    }
