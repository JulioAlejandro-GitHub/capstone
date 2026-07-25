"""Simple, persistent Stage 2 candidate publication lifecycle."""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text

from src.model_governance.errors import GovernanceNotFoundError, GovernanceStateError


class Stage2PublicationService:
    """Publishes immutable model-version references; never mutates model bytes."""

    def __init__(self, connection_factory, datasource="malaria"):
        self.connection_factory = connection_factory
        self.datasource = datasource

    @staticmethod
    def _id(value):
        return str(UUID(str(value)))

    def _context(self, connection, model_version_id):
        row = connection.execute(text("""
          SELECT mv.id::text model_version_id,mv.training_run_id::text,
            mv.checkpoint_artifact_id::text,mv.model_name,mv.version_number,
            artifact.name checkpoint_name,training.status train_status
          FROM model_versions mv
          JOIN runs training ON training.id=mv.training_run_id
          JOIN artifacts artifact ON artifact.id=mv.checkpoint_artifact_id
          WHERE mv.id=CAST(:id AS uuid)
          FOR SHARE OF mv,training,artifact
        """), {"id": model_version_id}).mappings().one_or_none()
        if not row:
            raise GovernanceNotFoundError("model version inexistente")
        evaluation = connection.execute(text("""
          SELECT child.id::text evaluation_run_id,child.status evaluation_status
          FROM run_lineage lineage
          JOIN runs child ON child.id=lineage.child_run_id
          WHERE lineage.parent_run_id=CAST(:training AS uuid)
            AND lineage.relationship_type='evaluates_checkpoint_from'
            AND child.run_type='evaluation'
          ORDER BY
            CASE WHEN child.status='completed' THEN 0 ELSE 1 END,
            child.finished_at DESC NULLS LAST,child.created_at DESC,child.id
          LIMIT 1
        """), {
            "training": row["training_run_id"],
        }).mappings().one_or_none()
        result = dict(row)
        result.update(dict(evaluation) if evaluation else {
            "evaluation_run_id": None, "evaluation_status": None,
        })
        return result

    @staticmethod
    def _eligibility(context):
        train_completed = context["train_status"] == "completed"
        evaluate_completed = context["evaluation_status"] == "completed"
        missing = []
        if not train_completed:
            missing.append("TRAIN no completado")
        if context["evaluation_run_id"] is None:
            missing.append("EVALUATE no encontrado")
        elif not evaluate_completed:
            missing.append("EVALUATE no completado")
        return train_completed and evaluate_completed, {
            "train_completed": train_completed,
            "evaluate_completed": evaluate_completed,
            "missing_conditions": missing,
        }

    def status(self, model_version_id):
        model_version_id = self._id(model_version_id)
        with self.connection_factory() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": f"stage2-publication:{model_version_id}"},
            )
            context = self._context(connection, model_version_id)
            publication = connection.execute(text("""
              SELECT * FROM stage2_model_publications
              WHERE model_version_id=CAST(:id AS uuid) AND scope='stage2'
              ORDER BY is_active DESC,updated_at DESC LIMIT 1
            """), {"id": model_version_id}).mappings().one_or_none()
        return self._response(context, dict(publication) if publication else None)

    def status_for_training(self, training_run_id):
        training_run_id = self._id(training_run_id)
        with self.connection_factory() as connection:
            model_version_id = connection.execute(text("""
              SELECT id::text FROM model_versions
              WHERE training_run_id=CAST(:id AS uuid)
              ORDER BY created_at DESC,id LIMIT 1
            """), {"id": training_run_id}).scalar_one_or_none()
        if not model_version_id:
            raise GovernanceNotFoundError("model version inexistente")
        return self.status(model_version_id)

    def publish(self, model_version_id, actor=None, reason=None, correlation_id=None):
        model_version_id = self._id(model_version_id)
        with self.connection_factory() as connection:
            context = self._context(connection, model_version_id)
            eligible, eligibility = self._eligibility(context)
            if not eligible:
                raise GovernanceStateError(
                    "No elegible: " + ", ".join(eligibility["missing_conditions"])
                )
            publication = connection.execute(text("""
              SELECT * FROM stage2_model_publications
              WHERE model_version_id=CAST(:id AS uuid) AND scope='stage2'
              ORDER BY created_at DESC LIMIT 1 FOR UPDATE
            """), {"id": model_version_id}).mappings().one_or_none()
            if publication and publication["is_active"]:
                return self._response(context, dict(publication), idempotent=True)
            if publication:
                publication = connection.execute(text("""
                  UPDATE stage2_model_publications SET
                    status='active',is_active=TRUE,published_at=NOW(),published_by=:actor,
                    deactivated_at=NULL,deactivated_by=NULL,updated_at=NOW(),
                    metadata=metadata||CAST(:metadata AS jsonb)
                  WHERE id=:id RETURNING *
                """), {
                    "id": publication["id"], "actor": actor,
                    "metadata": json.dumps({"last_reason": reason}),
                }).mappings().one()
                event_type = "MODEL_STAGE2_REACTIVATED"
                previous = "inactive"
            else:
                publication = connection.execute(text("""
                  INSERT INTO stage2_model_publications(
                    datasource,model_version_id,training_run_id,evaluation_run_id,
                    checkpoint_artifact_id,published_by,metadata)
                  VALUES(:datasource,:model_version,:training,:evaluation,:checkpoint,:actor,
                    CAST(:metadata AS jsonb)) RETURNING *
                """), {
                    "datasource": self.datasource, "model_version": model_version_id,
                    "training": context["training_run_id"],
                    "evaluation": context["evaluation_run_id"],
                    "checkpoint": context["checkpoint_artifact_id"], "actor": actor,
                    "metadata": json.dumps({"immutable_reference": True, "last_reason": reason}),
                }).mappings().one()
                event_type = "MODEL_STAGE2_PUBLISHED"
                previous = None
            self._event(connection, publication, event_type, previous, "active",
                        actor, reason, correlation_id)
            return self._response(context, dict(publication))

    def deactivate(self, publication_id, actor=None, reason=None, correlation_id=None):
        publication_id = self._id(publication_id)
        with self.connection_factory() as connection:
            publication = connection.execute(text("""
              SELECT * FROM stage2_model_publications
              WHERE id=CAST(:id AS uuid) FOR UPDATE
            """), {"id": publication_id}).mappings().one_or_none()
            if not publication:
                raise GovernanceNotFoundError("publicación inexistente")
            context = self._context(connection, str(publication["model_version_id"]))
            if not publication["is_active"]:
                return self._response(context, dict(publication), idempotent=True)
            publication = connection.execute(text("""
              UPDATE stage2_model_publications SET
                status='inactive',is_active=FALSE,deactivated_at=NOW(),
                deactivated_by=:actor,updated_at=NOW(),
                metadata=metadata||CAST(:metadata AS jsonb)
              WHERE id=:id RETURNING *
            """), {
                "id": publication_id, "actor": actor,
                "metadata": json.dumps({"deactivation_reason": reason}),
            }).mappings().one()
            self._event(connection, publication, "MODEL_STAGE2_DEACTIVATED",
                        "active", "inactive", actor, reason, correlation_id)
            return self._response(context, dict(publication))

    def models(self):
        with self.connection_factory() as connection:
            rows = connection.execute(text("""
              SELECT publication.*,mv.model_name,mv.version_number,
                artifact.name checkpoint_name
              FROM stage2_model_publications publication
              JOIN model_versions mv ON mv.id=publication.model_version_id
              JOIN artifacts artifact ON artifact.id=publication.checkpoint_artifact_id
              WHERE publication.datasource=:datasource
                AND publication.scope='stage2' AND publication.is_active
              ORDER BY publication.published_at DESC
            """), {"datasource": self.datasource}).mappings().all()
        return [self._serialize(dict(row)) for row in rows]

    def _event(self, connection, publication, event_type, previous, new,
               actor, reason, correlation_id):
        connection.execute(text("""
          INSERT INTO stage2_model_publication_events(
            publication_id,event_type,actor,model_version_id,training_run_id,
            evaluation_run_id,datasource,previous_status,new_status,reason,correlation_id)
          VALUES(:publication,:event,:actor,:model_version,:training,:evaluation,
            :datasource,:previous,:new,:reason,:correlation)
        """), {
            "publication": publication["id"], "event": event_type, "actor": actor,
            "model_version": publication["model_version_id"],
            "training": publication["training_run_id"],
            "evaluation": publication["evaluation_run_id"],
            "datasource": publication["datasource"], "previous": previous,
            "new": new, "reason": reason, "correlation": correlation_id,
        })

    def _response(self, context, publication, idempotent=False):
        eligible, eligibility = self._eligibility(context)
        active = bool(publication and publication["is_active"])
        return {
            "model_version_id": context["model_version_id"],
            "training_run_id": context["training_run_id"],
            "evaluation_run_id": context["evaluation_run_id"],
            "checkpoint_artifact_id": context["checkpoint_artifact_id"],
            "checkpoint": context["checkpoint_name"],
            "model_name": context["model_name"],
            "version_number": context["version_number"],
            "train_status": context["train_status"],
            "evaluation_status": context["evaluation_status"],
            "eligible": eligible,
            "eligible_for_stage2_production": eligible,
            "eligibility": eligibility,
            "stage2_status": "production" if active else (
                "available" if eligible else "not_available"
            ),
            "is_stage2_available": active,
            "is_stage2_production": active,
            "publication": self._serialize(publication) if publication else None,
            "idempotent": idempotent,
            "blockers": [
                {"code": "STAGE2_CONDITION_MISSING", "message": item}
                for item in eligibility["missing_conditions"]
            ],
            "warnings": [],
            "warning": (
                "Esta publicación es técnica y experimental. No constituye "
                "aprobación clínica ni diagnóstico automatizado."
            ),
        }

    @staticmethod
    def _serialize(row):
        if not row:
            return None
        return {
            key: (value.isoformat() if hasattr(value, "isoformat") else str(value)
                  if isinstance(value, UUID) else value)
            for key, value in row.items()
        }
