"""Read-only Stage 2 evidence, using the same E6 identities as the lineage UI."""

from uuid import UUID
from sqlalchemy import text
from sqlalchemy.engine import Connection
from app.repositories.assessment_lineage import LINEAGE_SOURCES_CTES

TRAIN_SQL = """
SELECT r.id AS training_run_id, r.run_type, r.status AS train_status,
       r.started_at AS train_started_at, r.finished_at AS train_finished_at,
       m.name AS model_name, m.architecture,
       r.execution_parameters, r.parameters, r.metadata,
       s.state AS session_state, s.verification AS session_verification,
       s.configuration AS session_configuration
FROM runs r LEFT JOIN models m ON m.id=r.model_id
LEFT JOIN train_execution_sessions s ON s.run_id=r.id
WHERE r.id=CAST(:id AS uuid)
"""

EVALUATIONS_SQL = """
WITH selected_trainings AS (SELECT CAST(:id AS uuid) AS id),
""" + LINEAGE_SOURCES_CTES + """
SELECT 'assessment_e6' AS evaluation_source_kind, NULL::uuid AS evaluation_run_id,
       v.attempt_id AS evaluation_attempt_id, v.identity_id AS evaluation_identity_id,
       v.state AS evaluation_status, v.finished_at AS evaluation_finished_at,
       v.started_at AS evaluation_started_at, v.identity->>'split' AS evaluation_split,
       v.identity->>'purpose' AS evaluation_purpose,
       (v.identity#>>'{model,training_run_id}'=v.training_run_id::text
        AND v.identity->>'kind'='evaluate') AS evaluation_link_valid,
       (v.verification IS NOT NULL) AS evaluation_verified_evidence,
       v.identity->'model' AS model_binding,
       v.identity#>>'{model,model_version_id}' AS model_version_id,
       v.identity#>>'{model,checkpoint_artifact_id}' AS checkpoint_artifact_id
FROM visible_assessments v
UNION ALL
SELECT DISTINCT 'run', child.id, NULL::uuid, NULL::uuid, child.status,
       child.finished_at, child.started_at, NULL::text, NULL::text,
       NOT EXISTS (
           SELECT 1 FROM run_lineage other
           WHERE other.child_run_id=child.id
             AND other.relationship_type='evaluates_checkpoint_from'
             AND other.parent_run_id<>lineage.parent_run_id
       ), false, NULL::jsonb, lineage.model_version_id::text,
       lineage.checkpoint_artifact_id::text
FROM eligible_run_lineage lineage JOIN runs child ON child.id=lineage.child_run_id
WHERE child.run_type='evaluation'
ORDER BY evaluation_finished_at DESC NULLS LAST, evaluation_started_at DESC NULLS LAST,
         evaluation_source_kind, evaluation_run_id, evaluation_attempt_id,
         model_version_id, checkpoint_artifact_id
"""


def read_training(connection: Connection, training_run_id: UUID) -> dict | None:
    row = connection.execute(text(TRAIN_SQL), {"id": training_run_id}).mappings().one_or_none()
    return dict(row) if row else None


def read_evaluations(connection: Connection, training_run_id: UUID) -> list[dict]:
    return [dict(row) for row in connection.execute(text(EVALUATIONS_SQL), {"id": training_run_id}).mappings()]


def read_explanations(connection: Connection, training_run_id: UUID) -> list[dict]:
    return [dict(row) for row in connection.execute(text("""
        SELECT DISTINCT child.id AS run_id, child.status, child.finished_at
        FROM run_lineage l JOIN runs child ON child.id=l.child_run_id
        WHERE l.parent_run_id=CAST(:id AS uuid)
          AND l.relationship_type='explains_checkpoint_from' AND child.run_type='explainability'
        ORDER BY child.finished_at DESC NULLS LAST, child.id
    """), {"id": training_run_id}).mappings()]


def read_version(connection: Connection, training_run_id: UUID, version_id: str | None) -> dict | None:
    row = connection.execute(text("""
        SELECT mv.*, a.name AS artifact_name, a.path AS artifact_path,
               a.checksum AS artifact_checksum
        FROM model_versions mv LEFT JOIN artifacts a ON a.id=mv.checkpoint_artifact_id
        WHERE mv.training_run_id=CAST(:train AS uuid)
          AND (CAST(:version AS uuid) IS NULL OR mv.id=CAST(:version AS uuid))
        ORDER BY mv.created_at DESC, mv.id LIMIT 1
    """), {"train": training_run_id, "version": version_id}).mappings().one_or_none()
    return dict(row) if row else None


def read_publication(connection: Connection, training_run_id: UUID, version_id: str | None) -> dict | None:
    row = connection.execute(text("""
        SELECT * FROM stage2_model_publications
        WHERE training_run_id=CAST(:train AS uuid) AND model_version_id=CAST(:version AS uuid)
          AND scope='stage2' AND datasource='malaria'
        ORDER BY is_active DESC, updated_at DESC, id LIMIT 1
    """), {"train": training_run_id, "version": version_id}).mappings().one_or_none()
    return dict(row) if row else None


def read_deployment(connection: Connection, version_id: str | None, artifact_id: str | None) -> dict | None:
    row = connection.execute(text("""
        SELECT id AS deployment_id, status AS deployment_status, environment, alias,
               deployed_at, artifact_sha256, threshold_value AS threshold,
               threshold_profile_snapshot->>'source' AS threshold_source,
               COALESCE(metadata->'technical_smoke_test'->>'status',
                        metadata->'stage2_smoke_test'->>'status') AS smoke_status
        FROM deployed_model_versions
        WHERE model_version_id=CAST(:version AS uuid)
          AND checkpoint_artifact_id=CAST(:artifact AS uuid)
          AND environment='stage2' AND alias='default'
        ORDER BY (status='active') DESC, deployed_at DESC NULLS LAST, id LIMIT 1
    """), {"version": version_id, "artifact": artifact_id}).mappings().one_or_none()
    return dict(row) if row else None
