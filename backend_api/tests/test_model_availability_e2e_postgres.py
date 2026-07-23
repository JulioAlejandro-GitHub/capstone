"""Opt-in end-to-end proof against an isolated PostgreSQL database clone."""
from __future__ import annotations

import os
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import get_engine
from app.main import app


@unittest.skipUnless(os.getenv("RUN_MODEL_AVAILABILITY_E2E") == "1", "opt-in PostgreSQL E2E")
class ModelAvailabilityE2E(unittest.TestCase):
    datasource = "malaria"
    model_version_id = "cca40382-d9f5-4f48-8d07-c2311005df1b"
    invalid_deployment_id = "8c76f936-d60b-48d3-9e40-6848c892cb34"

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        engine = get_engine(cls.datasource)
        with engine.connect() as connection:
            cls.threshold_id = str(connection.execute(text(
                "SELECT run_threshold_calibration_id FROM run_threshold_calibration "
                "WHERE model_version_id=:id AND calibration_status IN ('recorded','validated') "
                "ORDER BY created_at DESC LIMIT 1"
            ), {"id": cls.model_version_id}).scalar_one())
            cls.image_id = str(connection.execute(text(
                "SELECT image_id FROM dataset_split_images ORDER BY image_id LIMIT 1"
            )).scalar_one())

    def post(self, path, payload):
        response = self.client.post(f"{path}?datasource={self.datasource}", json=payload)
        self.assertLess(response.status_code, 400, response.text)
        return response.json()

    def test_complete_availability_lineage_and_rollback(self):
        suffix = uuid4().hex[:8]
        base = {"model_version_id": self.model_version_id,
                "deployment_name": f"availability-e2e-{suffix}",
                "environment": "experimental", "alias": "champion",
                "threshold_profile_id": self.threshold_id, "deployed_by": "e2e",
                "activate": False}
        first = self.post("/api/deployments", base)
        smoke = self.post(f"/api/deployments/{first['id']}/smoke-test",
                          {"source_image_id": self.image_id, "actor": "e2e"})
        self.assertEqual(smoke["smoke_test"]["status"], "PASS")
        active = self.post(f"/api/deployments/{first['id']}/activate",
                           {"actor": "e2e", "confirm_production": False})
        self.assertEqual(active["status"], "active")
        available = self.client.get("/api/models/available?datasource=malaria").json()["items"]
        self.assertIn(first["id"], {item["id"] for item in available})
        inference = self.post("/api/image-analysis-jobs",
                              {"deployed_model_version_id": first["id"],
                               "source_image_id": self.image_id})
        self.assertEqual(inference["deployed_model_version_id"], first["id"])
        self.assertIn(inference["predicted_class"], (0, 1))
        self.assertIn(inference["predicted_label"], ("uninfected", "parasitized"))
        with get_engine(self.datasource).connect() as connection:
            lineage = connection.execute(text("""SELECT r.id inference_run_id,j.id job_id,p.id prediction_id,
              p.deployed_model_version_id,p.model_version_id,mv.training_run_id
              FROM runs r JOIN image_analysis_jobs j ON j.inference_run_id=r.id
              JOIN predictions p ON p.image_analysis_job_id=j.id
              JOIN model_versions mv ON mv.id=p.model_version_id WHERE j.id=:id"""),
              {"id": inference["image_analysis_job_id"]}).mappings().one()
        self.assertEqual(str(lineage["training_run_id"]), "084604a0-cb23-43c0-be0f-eab5b0ba1a31")

        second = self.post("/api/deployments", base)
        self.post(f"/api/deployments/{second['id']}/smoke-test",
                  {"source_image_id": self.image_id, "actor": "e2e"})
        self.post(f"/api/deployments/{second['id']}/activate",
                  {"actor": "e2e", "confirm_production": False})
        rollback = self.post(f"/api/deployments/{second['id']}/rollback",
                             {"target_deployment_id": first["id"], "actor": "e2e",
                              "reason": "E2E rollback"})
        self.assertEqual(rollback["status"], "pending")
        self.assertEqual(rollback["rollback_of_deployment_id"], second["id"])

    def test_invalid_legacy_snapshot_fails_smoke(self):
        response = self.client.post(
            f"/api/deployments/{self.invalid_deployment_id}/smoke-test?datasource=malaria",
            json={"source_image_id": self.image_id, "actor": "e2e"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["smoke_test"]["status"], "FAIL")

    def test_production_requires_explicit_confirmation(self):
        deployment = self.post("/api/deployments", {
            "model_version_id": self.model_version_id,
            "deployment_name": f"availability-prod-e2e-{uuid4().hex[:8]}",
            "environment": "production", "alias": "champion",
            "threshold_profile_id": self.threshold_id, "deployed_by": "e2e",
            "activate": False,
        })
        self.post(f"/api/deployments/{deployment['id']}/smoke-test",
                  {"source_image_id": self.image_id, "actor": "e2e"})
        response = self.client.post(
            f"/api/deployments/{deployment['id']}/activate?datasource=malaria",
            json={"actor": "e2e", "confirm_production": False},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("confirmación explícita", response.text)
        active = self.post(f"/api/deployments/{deployment['id']}/activate",
                           {"actor": "e2e", "confirm_production": True})
        self.assertEqual(active["status"], "active")
