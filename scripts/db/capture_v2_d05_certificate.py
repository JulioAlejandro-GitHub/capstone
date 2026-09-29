"""Verify the new isolated certificate, generated legacy contract and D-04 continuity."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
E = ROOT / "docs/audits/e10_10_5d4_evidence/route_a"
os.environ["PGV2_EVIDENCE_DIR"] = str(E)
os.environ["PGPASSFILE"] = json.loads((E / "private_paths.json").read_text())["pgpass"]
from verify_v2_route_a import connect, guard

from adoption_v2.check_catalog import PAIRS, canonical_tree, capture, reference
from adoption_v2.core import CATALOG_HASH, MANIFEST_HASH
from adoption_v2.execute import catalog_snapshot, certified_catalog
from adoption_v2.function_guard import DEPENDENCY_SQL

t = guard()
legacy = json.loads(
    (
        ROOT / "docs/audits/e10_10_5d4_evidence/route_b/preflight_catalog.json"
    ).read_text()
)
olddeps = json.loads(
    (
        ROOT / "docs/audits/e10_10_5d3_evidence/route_a_function_dependencies.json"
    ).read_text()
)["dependencies"]
with connect(t) as c:
    actual = catalog_snapshot(c)
    assert actual == certified_catalog()
    assert c.execute(DEPENDENCY_SQL).fetchall() == olddeps
    refs = {name: capture(c, (table, name)) for table, name in sorted(PAIRS)}
    assert refs == reference()
    diagnosed = json.loads((E.parent / "d06_native_and_tests.json").read_text())[
        "route_a"
    ]
    for name, ref in refs.items():
        old = diagnosed[name]
        assert ref["definition"] == old["definition"]
        assert ref["canonical"] == canonical_tree(old["tree"])
        assert ref["dependencies"] == old["dependencies"]
        for field, objects in old["resolved"].items():
            assert [
                {"oid": r["oid"], "object": r["object"]} for r in ref["bindings"][field]
            ] == objects
    generated_evidence = {}
    for kind in ["columns", "default_functions", "default_dependencies"]:

        def select(cat, kind=kind):
            return [
                r
                for r in cat[kind]
                if r.get("relation") == "assessment_identities"
                and r.get("name", r.get("column_name")) == "structural_hash"
            ]

        rows, original = select(actual), select(legacy)
        assert rows and rows == original
        generated_evidence[kind] = rows
result = {
    "passed": True,
    "manifest_sha256": MANIFEST_HASH,
    "catalog_sha256": CATALOG_HASH,
    "d04_function_dependencies_unchanged": True,
    "generated_columns_exact_legacy": True,
    "four_check_references_reproduced": True,
    "d06_diagnosed_contract_identical_in_new_route_a": True,
    "generated_native_entries": generated_evidence,
}
(E / "contract_continuity.json").write_text(json.dumps(result, indent=2) + "\n")
print("contract continuity passed")
