"""Read immutable assessment attempts and their individual evidence."""
from __future__ import annotations

from typing import Any
from uuid import UUID
from sqlalchemy import text
from app.db import read_only_transaction


class AssessmentReadRepository:
    def list(self, training_run_id: UUID | None, campaign_id: UUID | None,
             limit: int | None, offset: int) -> list[dict[str, Any]]:
        with read_only_transaction("malaria") as c:
            rows = c.execute(text("""
                SELECT i.id,i.id AS identity_id,r.model_id,i.identity_hash,i.training_run_id,i.kind,a.id AS attempt_id,a.state,a.ordinal,
                       i.identity->>'split' AS split,i.identity->>'purpose' AS purpose,
                       a.started_at,a.finished_at,a.verification,i.identity#>>'{dataset,dataset_version_id}' AS dataset_version_id,
                       i.identity#>>'{model,checkpoint_artifact_id}' AS checkpoint_artifact_id,
                       (i.identity#>>'{decision,effective}')::float8 AS threshold
                FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id
                JOIN runs r ON r.id=i.training_run_id
                WHERE (CAST(:train AS uuid) IS NULL OR i.training_run_id=CAST(:train AS uuid))
                  AND (CAST(:campaign AS uuid) IS NULL OR r.campaign_id=CAST(:campaign AS uuid)
                       OR i.identity->>'campaign_id'=CAST(:campaign AS text)
                       OR EXISTS(SELECT 1 FROM assessment_campaign_consumers cc
                            WHERE cc.identity_id=i.id AND cc.campaign_id=CAST(:campaign AS uuid)))
                ORDER BY a.started_at DESC,a.id LIMIT :limit OFFSET :offset
            """), dict(train=str(training_run_id) if training_run_id else None,
                       campaign=str(campaign_id) if campaign_id else None,limit=limit,offset=offset)).mappings().all()
        return [dict(r) for r in rows]

    def detail(self, attempt_id: UUID) -> dict[str, Any] | None:
        with read_only_transaction("malaria") as c:
            row = c.execute(text("""SELECT a.*,a.id AS attempt_id,r.model_id,i.identity,i.identity_hash,i.training_run_id,i.kind
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                JOIN runs r ON r.id=i.training_run_id
                WHERE a.id=CAST(:id AS uuid)"""), dict(id=str(attempt_id))).mappings().one_or_none()
        if row is None:
            return None
        return {k:v for k,v in row.items() if k not in ('owner','host','pid')}

    def payloads(self, attempt_id: UUID, kind: str, limit: int, offset: int) -> list[dict[str, Any]]:
        table, order = {'results': ('assessment_results','sample_id'),
                        'artifacts': ('assessment_artifacts','sample_id,role')}[kind]
        with read_only_transaction("malaria") as c:
            return list(c.execute(text(f"SELECT payload FROM {table} WHERE attempt_id=CAST(:id AS uuid) "
                                       f"ORDER BY {order} LIMIT :limit OFFSET :offset"),
                                  dict(id=str(attempt_id),limit=limit,offset=offset)).scalars())
