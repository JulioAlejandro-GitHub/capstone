"""D-04 negative fixtures from native sanitized catalogs, never scientific rows."""

import copy
import json
import unittest

from adoption_v2.core import ROOT, Blocked
from adoption_v2.execute import certified_catalog
from adoption_v2.function_guard import check_functions, dependency_reference


class FunctionGuardTests(unittest.TestCase):
    def setUp(self):
        path = (
            ROOT / "docs/audits/e10_10_5d2_evidence/route_b/legacy_native_catalog.json"
        )
        self.rows = json.loads(path.read_text())["functions"]
        self.certified = certified_catalog()["functions"]
        keys = {(r["name"], r["arguments"]) for r in self.rows}
        self.reference = dependency_reference()
        self.deps = [r for r in self.reference if (r["name"], r["arguments"]) in keys]
        self.own = next(i for i, r in enumerate(self.rows) if r["extension"] is None)
        self.ext = next(
            i for i, r in enumerate(self.rows) if r["extension"] == "pgcrypto"
        )

    def verify(self):
        check_functions(self.rows, self.certified, self.deps, self.reference)

    def rejects(self, index, field, value):
        self.rows[index][field] = value
        with self.assertRaises(Blocked):
            self.verify()

    def test_exact_legacy_and_certified_extension_pass(self):
        self.verify()
        self.assertEqual(sum(r["extension"] == "pgcrypto" for r in self.rows), 36)

    def test_wrong_own_owner_rejected_even_postgres(self):
        self.rejects(self.own, "owner", "postgres")

    def test_wrong_extension_owner_rejected(self):
        self.rejects(self.ext, "owner", "capstone_v2_migrator")

    def test_acl_difference_in_each_class_rejected(self):
        for index in (self.own, self.ext):
            with self.subTest(index=index):
                saved = copy.deepcopy(self.rows)
                self.rejects(index, "proacl", "{unexpected=X/postgres}")
                self.rows = saved

    def test_definition_change_in_each_class_rejected(self):
        for index in (self.own, self.ext):
            with self.subTest(index=index):
                saved = copy.deepcopy(self.rows)
                self.rejects(
                    index, "definition", self.rows[index]["definition"] + "\n-- altered"
                )
                self.rows = saved

    def test_signature_change_rejected(self):
        self.rejects(self.ext, "arguments", "unexpected integer")

    def test_wrong_extension_membership_rejected(self):
        self.rejects(self.ext, "extension", "unexpected_extension")

    def test_unexpected_function_rejected(self):
        r = copy.deepcopy(self.rows[self.ext])
        r["name"] = "unexpected"
        self.rows.append(r)
        with self.assertRaises(Blocked):
            self.verify()

    def test_required_function_absent_in_each_class_rejected(self):
        for index in (self.own, self.ext):
            with self.subTest(index=index):
                saved = copy.deepcopy(self.rows)
                self.rows.pop(index)
                with self.assertRaises(Blocked):
                    self.verify()
                self.rows = saved

    def test_reclassification_both_directions_rejected(self):
        for index, extension in [(self.own, "pgcrypto"), (self.ext, None)]:
            with self.subTest(index=index):
                saved = copy.deepcopy(self.rows)
                self.rejects(index, "extension", extension)
                self.rows = saved

    def test_native_dependency_tamper_rejected(self):
        self.deps = copy.deepcopy(self.deps)
        self.deps[0]["referenced_object"] = "unexpected object"
        with self.assertRaisesRegex(Blocked, "FUNCTION_DEPENDENCY_MISMATCH"):
            self.verify()

    def test_native_membership_dependency_absent_rejected(self):
        self.deps = [r for r in self.deps if r["deptype"] != "e"]
        with self.assertRaisesRegex(Blocked, "FUNCTION_DEPENDENCY_MISMATCH"):
            self.verify()

    def test_duplicate_signature_rejected(self):
        self.rows.append(copy.deepcopy(self.rows[self.ext]))
        with self.assertRaisesRegex(Blocked, "DUPLICATE_SOURCE_FUNCTION"):
            self.verify()

    def test_property_difference_rejected(self):
        self.rejects(self.ext, "prosecdef", not self.rows[self.ext]["prosecdef"])
