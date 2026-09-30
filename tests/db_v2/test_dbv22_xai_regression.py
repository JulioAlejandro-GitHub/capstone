"""No server: ensure the original regression and missing rejection are detected."""

import re
import unittest
from pathlib import Path

from scripts.db.dbv22_xai_regression import validate_xai_dispatch

SQL = Path(__file__).resolve().parents[2] / "docs/audits/db_v2/dbv2_1_target_schema.sql"


class XAIDispatchRegression(unittest.TestCase):
    def test_corrected_contract(self):
        validate_xai_dispatch(SQL.read_text())

    def test_original_case_is_rejected(self):
        source = re.sub(
            r"IF TG_TABLE_NAME = 'xai_quantitative_evaluations'.*?END IF;",
            "eid := CASE WHEN TG_TABLE_NAME='xai_quantitative_evaluations' THEN NEW.id ELSE NEW.evaluation_id END;",
            SQL.read_text(),
            count=1,
            flags=re.DOTALL,
        )
        with self.assertRaises(AssertionError):
            validate_xai_dispatch(source)

    def test_unknown_table_must_be_rejected(self):
        source = SQL.read_text().replace(
            "'dbv21_xai_evaluation_complete invoked from unsupported table: %'",
            "'unexpected'",
        )
        with self.assertRaises(AssertionError):
            validate_xai_dispatch(source)
