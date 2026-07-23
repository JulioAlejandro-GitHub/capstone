"""Opt-in real PostgreSQL verification of the four-step production flow."""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "malaria_dl_local_project"))

from src.model_contract_service import ModelContractService  # noqa: E402
from src.model_deployment_service import ModelDeploymentService  # noqa: E402
from src.model_release_lifecycle_service import ModelReleaseLifecycleService  # noqa: E402
from src.traceable_inference import TraceableInferenceService  # noqa: E402


def main():
    if os.getenv("RUN_PRODUCTION_E2E") != "1":
        raise SystemExit("Defina RUN_PRODUCTION_E2E=1 para ejecutar escrituras reales.")
    database_url = os.getenv(
        "MALARIA_DATABASE_URL", "postgresql+psycopg://julio@localhost:5432/malaria_experiments"
    ).replace("postgresql://", "postgresql+psycopg://", 1)
    model_version_id = os.environ["MODEL_VERSION_ID"]
    source_image_id = os.environ["SOURCE_IMAGE_ID"]
    actor = os.getenv("E2E_ACTOR", "operador-web-e2e")
    reason = os.getenv("E2E_REASON", "Verificación gobernada del flujo de cuatro pasos")
    engine = create_engine(database_url, pool_pre_ping=True)

    @contextmanager
    def connection_factory():
        with engine.begin() as connection:
            yield connection

    contract = ModelContractService(connection_factory)
    deployment_service = ModelDeploymentService(connection_factory)
    lifecycle = ModelReleaseLifecycleService(connection_factory)
    preview = contract.candidates(model_version_id)
    selections = {
        field["key"]: field["proposed_source_id"]
        for field in preview["fields"]
        if field.get("proposed_source_id")
    }
    completed = contract.complete(model_version_id, selections, actor, reason)
    threshold_id = completed["threshold_profile_id"]
    lifecycle.validate(model_version_id, threshold_id, actor, reason)
    lifecycle.approve(model_version_id, actor, reason)
    publication = deployment_service.publish_to_production(
        model_version_id=model_version_id,
        deployment_name="malaria-classifier",
        alias="champion",
        actor=actor,
        reason=reason,
        confirm_production=True,
        source_image_id=source_image_id,
        inference_service=TraceableInferenceService(connection_factory=connection_factory),
    )
    deployment_id = publication["deployment_id"]
    with connection_factory() as connection:
        available = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM deployed_model_versions d
                JOIN model_versions mv ON mv.id=d.model_version_id
                WHERE d.id=CAST(:id AS uuid) AND d.environment='production'
                  AND d.alias='champion' AND d.status='active'
                  AND mv.status IN ('approved','deployed')
                """
            ),
            {"id": deployment_id},
        ).scalar_one()
    result = {
        "model_version_id": model_version_id,
        "deployment_id": deployment_id,
        "smoke_status": publication["smoke_status"],
        "environment": "production",
        "status": "active",
        "alias": "champion",
        "available_for_inference": available == 1 and publication["available_for_inference"],
        "inference": publication["verification_inference"],
        "rollback_available": publication["rollback_available"],
    }
    print(json.dumps(result, ensure_ascii=False, default=str, sort_keys=True))


if __name__ == "__main__":
    main()
