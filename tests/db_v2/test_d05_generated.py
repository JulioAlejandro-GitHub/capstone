"""Generated-column contract and dependency installation order."""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class GeneratedContractTests(unittest.TestCase):
    def test_dependency_order_and_exact_expression(self):
        early = (ROOT / "alembic_v2/baseline/02_generated_functions.sql").read_text()
        tables = (ROOT / "alembic_v2/baseline/03_tables.sql").read_text()
        late = (ROOT / "alembic_v2/baseline/04_functions.sql").read_text()
        self.assertLess(
            early.index("CREATE OR REPLACE FUNCTION public.assessment_canonical"),
            early.index("CREATE OR REPLACE FUNCTION public.assessment_structural_hash"),
        )
        self.assertNotIn(
            "CREATE OR REPLACE FUNCTION public.assessment_structural_hash", late
        )
        self.assertIn(
            "structural_hash text GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED",
            tables,
        )

    def test_manifest_contract(self):
        m = json.loads((ROOT / "alembic_v2/baseline/catalog_manifest.json").read_text())
        c = m["generated_column_contracts"][0]
        self.assertEqual(c["attgenerated"], "s")
        self.assertEqual(c["expression"], "assessment_structural_hash(identity)")
        self.assertTrue(c["nullable"])
        self.assertEqual(len(c["dependencies"]), 3)
