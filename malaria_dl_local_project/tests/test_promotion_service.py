"""Tests for PrepareModelReleaseService and Promotion Status rules."""

from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from src.model_governance.entities import ModelVersionStatus
from src.model_governance.errors import GovernanceStateError, GovernanceValidationError
from src.model_governance.promotion_service import PrepareModelReleaseService
from src.model_governance.repository import (
    create_deployed_model_version,
    create_model_version,
)


class PrepareModelReleaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = PrepareModelReleaseService()

    def test_run_inexistente(self):
        fake_id = str(uuid4())
        status = self.service.get_promotion_status(fake_id)
        self.assertEqual(status["next_action"], "unavailable")
        self.assertFalse(status["button_enabled"])
        self.assertTrue(any("TRAINING_RUN_NOT_FOUND" in r for r in status["blocking_reasons"]))

    def test_uuid_invalido(self):
        with self.assertRaises(GovernanceValidationError):
            self.service.prepare_release("invalid-uuid")

    def test_promotion_status_get_side_effect_free(self):
        fake_id = str(uuid4())
        res1 = self.service.get_promotion_status(fake_id)
        res2 = self.service.get_promotion_status(fake_id)
        self.assertEqual(res1, res2)
        self.assertEqual(res1["next_action"], "unavailable")


if __name__ == "__main__":
    unittest.main()
