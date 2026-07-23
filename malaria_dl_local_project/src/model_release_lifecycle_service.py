"""Explicit, audited model-version lifecycle transitions."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text

from src.model_deployment_service import ModelDeploymentService
from src.model_governance.errors import GovernanceNotFoundError, GovernanceStateError


class ModelReleaseLifecycleService:
    def __init__(self, connection_factory, model_loader=None):
        self.connection_factory = connection_factory
        self.deployment_validator = ModelDeploymentService(
            connection_factory=connection_factory, model_loader=model_loader
        )

    def validate(self, model_version_id, threshold_profile_id, actor=None, reason=None):
        model_version_id = str(UUID(str(model_version_id)))
        with self.connection_factory() as connection:
            row = connection.execute(
                text("SELECT status FROM model_versions WHERE id=:id"),
                {"id": model_version_id},
            ).mappings().one_or_none()
            if not row:
                raise GovernanceNotFoundError("model version inexistente")
            if row["status"] not in {"candidate", "discovered", "validated"}:
                raise GovernanceStateError("sólo candidate, discovered o validated puede validarse")
        self.deployment_validator.validate_activation(
            model_version_id, threshold_profile_id,
            allowed_statuses={"candidate", "discovered", "validated"},
        )
        audit = {
            "last_audit_event": "validated",
            "actor": actor,
            "reason": reason,
            "at": datetime.now(UTC).isoformat(),
            "threshold_profile_id": str(threshold_profile_id),
        }
        with self.connection_factory() as connection:
            return dict(connection.execute(text("""UPDATE model_versions
              SET status='validated',validated_at=COALESCE(validated_at,NOW()),
              metadata=metadata||CAST(:audit AS jsonb) WHERE id=:id RETURNING *"""),
              {"id": model_version_id, "audit": json.dumps(audit)}).mappings().one())

    def approve(self, model_version_id, actor, reason):
        if not actor or not reason:
            raise GovernanceStateError("aprobación exige actor y motivo")
        model_version_id = str(UUID(str(model_version_id)))
        audit = {"last_audit_event": "approved", "actor": actor, "reason": reason,
                 "at": datetime.now(UTC).isoformat()}
        with self.connection_factory() as connection:
            row = connection.execute(text("""UPDATE model_versions
              SET status='approved',approved_at=NOW(),metadata=metadata||CAST(:audit AS jsonb)
              WHERE id=:id AND status='validated' RETURNING *"""),
              {"id": model_version_id, "audit": json.dumps(audit)}).mappings().one_or_none()
        if not row:
            raise GovernanceStateError("aprobación exige model version validated")
        return dict(row)

    def reject(self, model_version_id, actor, reason):
        if not actor or not reason:
            raise GovernanceStateError("rechazo exige actor y motivo")
        model_version_id = str(UUID(str(model_version_id)))
        audit = {"last_audit_event": "rejected", "actor": actor, "reason": reason,
                 "at": datetime.now(UTC).isoformat()}
        with self.connection_factory() as connection:
            row = connection.execute(text("""UPDATE model_versions
              SET status='rejected',metadata=metadata||CAST(:audit AS jsonb)
              WHERE id=:id AND status IN ('candidate','discovered','validated') RETURNING *"""),
              {"id": model_version_id, "audit": json.dumps(audit)}).mappings().one_or_none()
        if not row:
            raise GovernanceStateError("model version no puede rechazarse desde su estado actual")
        return dict(row)
