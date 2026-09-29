"""D-06 comparison must preserve every semantic field outside proved rewrites."""

import copy
import json
import unittest
from unittest.mock import patch

from adoption_v2.check_catalog import canonical_tree, compare
from adoption_v2.core import ROOT


class CheckCatalogTests(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads(
            (
                ROOT / "docs/audits/e10_10_5d4_evidence/d06_native_and_tests.json"
            ).read_text()
        )

    def test_all_four_native_trees_canonicalize_identically(self):
        for name, row in self.evidence["legacy"].items():
            self.assertEqual(
                canonical_tree(row["tree"]),
                canonical_tree(self.evidence["route_a"][name]["tree"]),
            )

    def test_semantic_changes_are_not_erased(self):
        for name, row in self.evidence["legacy"].items():
            with self.subTest(name=name):
                raw = row["tree"]
                changed = (
                    raw.replace(":varattno 8 ", ":varattno 9 ", 1)
                    if name.endswith("reason_check")
                    else raw.replace(":boolop or ", ":boolop and ", 1)
                )
                self.assertNotEqual(canonical_tree(raw), canonical_tree(changed))

    def test_operator_change_not_erased(self):
        raw = self.evidence["legacy"]["campaign_controlled_requests_reason_check"][
            "tree"
        ]
        self.assertNotEqual(
            canonical_tree(raw), canonical_tree(raw.replace(":opno 521 ", ":opno 523 "))
        )

    def test_cast_and_collation_changes_not_erased(self):
        raw = self.evidence["legacy"]["ck_cell_prediction_label_index"]["tree"]
        for before, after in [
            (":resulttype 25 ", ":resulttype 1043 "),
            (":varcollid 100 ", ":varcollid 950 "),
        ]:
            self.assertNotEqual(
                canonical_tree(raw), canonical_tree(raw.replace(before, after, 1))
            )

    def test_no_global_constraint_exception(self):
        a = {
            "constraints": [
                {"relation": "unknown", "name": "x", "definition": "CHECK (false)"}
            ]
        }
        b = copy.deepcopy(a)
        b["constraints"][0]["definition"] = "CHECK (true)"
        self.assertTrue(compare(None, a, b)["unjustified"])

    def test_equal_tree_different_binding_or_dependency_rejected(self):
        name = "campaign_controlled_requests_reason_check"
        r = self.evidence["legacy"][name]
        s = self.evidence["route_a"][name]
        a = {
            "constraints": [
                {
                    "relation": "campaign_controlled_requests",
                    "name": name,
                    "definition": r["definition"],
                }
            ]
        }
        b = {"constraints": [dict(a["constraints"][0], definition=s["definition"])]}
        ref = dict(s, canonical=canonical_tree(s["tree"]), bindings=s["resolved"])
        obs = dict(r, canonical=canonical_tree(r["tree"]), bindings=r["resolved"])
        for field in ("bindings", "dependencies"):
            bad = copy.deepcopy(obs)
            bad[field] = []
            with (
                patch("adoption_v2.check_catalog.reference", return_value={name: ref}),
                patch("adoption_v2.check_catalog.capture", return_value=bad),
            ):
                self.assertTrue(compare(None, a, b)["unjustified"])
