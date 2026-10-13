"""Read current evidence without preparing, publishing or executing a model."""

import hashlib
import json
from pathlib import Path
from uuid import UUID

from app.db import read_only_transaction
from app.repositories import stage2_status as repository
from app.schemas.stage2_status import Stage2Status
from src.malaria_dl.governance.eligibility import evaluation_completed, stage2_eligibility
from src.malaria_dl.governance.services.deployment_service import _project_path
from src.malaria_dl.governance.services.stage2_availability_service import Stage2ModelAvailabilityService


class Stage2TrainingNotFound(LookupError):
    pass


def checkpoint_readiness(path: str | None, sha256: str | None, size: int | None) -> tuple[bool, bool]:
    if not path:
        return False, False
    candidate = _project_path(path)
    try:
        if not candidate.is_file():
            return False, False
        if not sha256 or (size is not None and candidate.stat().st_size != size):
            return True, False
        with candidate.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        return True, actual == sha256
    except OSError:
        return False, False


class Stage2StatusService:
    def status(self, training_run_id: UUID, datasource: str | None) -> Stage2Status:
        with read_only_transaction(datasource) as connection:
            training = repository.read_training(connection, training_run_id)
            if training is None:
                raise Stage2TrainingNotFound(str(training_run_id))
            candidates = repository.read_evaluations(connection, training_run_id)
            evaluation = next((item for item in candidates if evaluation_completed(item)), candidates[0] if candidates else {})
            explanations = repository.read_explanations(connection, training_run_id)
            session = training.get("session_verification") or {}
            selected_artifact = session.get("artifact") or {}
            binding = evaluation.get("model_binding") or {}
            version_id = evaluation.get("model_version_id") or selected_artifact.get("version_id")
            version = repository.read_version(connection, training_run_id, version_id)
            version_id = version_id or (str(version["id"]) if version else None)
            artifact_id = (str(version["checkpoint_artifact_id"]) if version and version.get("checkpoint_artifact_id") else evaluation.get("checkpoint_artifact_id"))
            publication = repository.read_publication(connection, training_run_id, version_id)
            deployment = repository.read_deployment(connection, version_id, artifact_id) or {}

        eligible, eligibility = stage2_eligibility({**training, **evaluation})
        source = "assessment_e6" if binding else "model_versions" if version else "train_execution_sessions" if selected_artifact else None
        # An E6/E5 evidence UUID is descriptive; it does not imply a registered model_version.
        path = binding.get("path") or (version or {}).get("artifact_path") or selected_artifact.get("path")
        checksum = binding.get("sha256") or (version or {}).get("artifact_sha256") or selected_artifact.get("sha256")
        size = binding.get("bytes") or (version or {}).get("artifact_size_bytes") or selected_artifact.get("bytes")
        accessible, verified = checkpoint_readiness(path, checksum, size)
        technical = []
        package = None
        warnings = ["Elegibilidad técnica y experimental; no constituye aprobación clínica."]
        if not version:
            technical.append({"code": "MODEL_VERSION_NOT_REGISTERED", "message": "La identidad del modelo tiene evidencia, pero falta registrar la versión para despliegue."})
        if not accessible:
            technical.append({"code": "CHECKPOINT_UNAVAILABLE", "message": "El checkpoint no está accesible desde el backend de despliegue."})
        elif not verified:
            technical.append({"code": "CHECKPOINT_UNVERIFIED", "message": "No se pudo confirmar tamaño y SHA-256 del checkpoint."})
        if evaluation.get("evaluation_source_kind") != "assessment_e6" and version:
            # Preserve the existing operational package checks for traditional candidates.
            # Every DB access of this preview is forced read-only; enable() is never called.
            preview = Stage2ModelAvailabilityService(lambda: read_only_transaction(datasource)).preview(str(training_run_id))
            technical.extend(preview.get("technical_blockers", []))
            package = preview.get("package")
            warnings.extend(preview.get("warnings", []))
            if preview.get("model_version_id") != version_id:
                technical.append({"code": "MODEL_VERSION_SELECTION_CONFLICT", "message": "El paquete operativo no corresponde a la versión evaluada."})
        ready = not technical
        published = bool(publication and publication["is_active"])
        available = bool(published and deployment.get("deployment_status") == "active" and deployment.get("smoke_status") == "PASS")
        input_contract = binding.get("input_contract") or (training.get("session_configuration") or {}).get("resolved", {}).get("input_contract", {})
        public_evaluation = {key: value for key, value in evaluation.items() if key.startswith("evaluation_")}
        return Stage2Status.model_validate({
            **{key: value for key, value in training.items() if key.startswith("train_")},
            **public_evaluation, **deployment,
            "training_run_id": training_run_id,
            "eligible": eligible, "eligible_for_stage2_production": eligible, "eligibility": eligibility,
            "explainability_run_ids": [item["run_id"] for item in explanations],
            "explanations": json.loads(json.dumps(explanations, default=str)),
            "model_version_id": version_id, "model_version_registered": bool(version),
            "version_number": (version or {}).get("version_number"),
            "model_name": training.get("model_name") or (version or {}).get("model_name") or input_contract.get("architecture"),
            "architecture": training.get("architecture") or input_contract.get("architecture"),
            "checkpoint_artifact_id": artifact_id, "checkpoint": Path(path).name if path else None,
            "checkpoint_sha256": checksum, "checkpoint_bytes": size, "evidence_source": source,
            "publication": json.loads(json.dumps(publication, default=str)) if publication else None,
            "published": published, "available": available, "is_stage2_available": available,
            "is_stage2_production": available, "available_for_inference": available,
            "stage2_status": "production" if available else "not_available",
            "production_state": "active" if available else "eligible" if eligible else "not_eligible",
            "next_action": "view_stage2_model" if available else "enable_for_stage2" if eligible else "unavailable",
            "deployment_readiness": {"ready": ready, "status": "ready" if ready else "blocked", "checkpoint_accessible": accessible, "checkpoint_verified": verified},
            "blockers": [{"code": "STAGE2_CONDITION_MISSING", "message": message} for message in eligibility["missing_conditions"]],
            "technical_blockers": technical,
            "warnings": warnings,
            "package": package,
        })
