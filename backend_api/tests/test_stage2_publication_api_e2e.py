"""Opt-in PostgreSQL lifecycle proof for Stage 2 candidate publications."""
from __future__ import annotations

import os
import unittest

from sqlalchemy import text

from app.db import get_engine
from app.routes.governance import stage2_publication_service


@unittest.skipUnless(
    os.getenv("RUN_STAGE2_PUBLICATION_E2E") == "1"
    and os.getenv("STAGE2_E2E_MODEL_VERSION_ID"),
    "opt-in Stage 2 publication E2E",
)
class Stage2PublicationApiE2E(unittest.TestCase):
    datasource = "malaria"
    model_version_id = os.getenv("STAGE2_E2E_MODEL_VERSION_ID")

    def test_publish_deactivate_reactivate_and_active_selector(self):
        service = stage2_publication_service(self.datasource)
        first = service.publish(
            self.model_version_id, "stage2-e2e", "publish", "stage2-e2e-publish"
        )
        self.assertTrue(first["eligible"])
        self.assertTrue(first["is_stage2_available"])
        publication_id = first["publication"]["id"]

        repeated = service.publish(
            self.model_version_id, "stage2-e2e", "publish-repeat",
            "stage2-e2e-publish-repeat",
        )
        self.assertEqual(repeated["publication"]["id"], publication_id)
        self.assertTrue(repeated["idempotent"])

        inactive = service.deactivate(
            publication_id, "stage2-e2e", "deactivate", "stage2-e2e-deactivate"
        )
        self.assertFalse(inactive["is_stage2_available"])
        repeated_inactive = service.deactivate(
            publication_id, "stage2-e2e", "deactivate-repeat",
            "stage2-e2e-deactivate-repeat",
        )
        self.assertTrue(repeated_inactive["idempotent"])

        active = service.publish(
            self.model_version_id, "stage2-e2e", "reactivate",
            "stage2-e2e-reactivate",
        )
        self.assertEqual(active["publication"]["id"], publication_id)
        candidates = service.models()
        self.assertIn(publication_id, {item["id"] for item in candidates})

        with get_engine(self.datasource).connect() as connection:
            event_types = connection.execute(text("""
              SELECT event_type FROM stage2_model_publication_events
              WHERE publication_id=CAST(:id AS uuid) ORDER BY event_at
            """), {"id": publication_id}).scalars().all()
        self.assertIn("MODEL_STAGE2_PUBLISHED", event_types)
        self.assertIn("MODEL_STAGE2_DEACTIVATED", event_types)
        self.assertIn("MODEL_STAGE2_REACTIVATED", event_types)


if __name__ == "__main__":
    unittest.main()
