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

    def preflight_detail(self, connection, attempt_id: UUID) -> dict[str, Any] | None:
        """Exact attempt, without materializing samples or filesystem locators."""
        row = connection.execute(text("""
            SELECT a.id AS attempt_id,a.identity_id,a.state,a.ordinal,a.verification,
                   i.training_run_id,i.identity_hash,i.kind,i.identity - 'samples' AS identity
            FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
            WHERE a.id=:id
        """), {'id': attempt_id}).mappings().one_or_none()
        return dict(row) if row else None

    def preflight_candidates(self, connection, run_id: UUID) -> dict[str, Any]:
        return dict(connection.execute(text("""
            SELECT
              (SELECT count(*) FROM assessment_identities i JOIN assessment_attempts a
               ON a.identity_id=i.id WHERE i.training_run_id=:run AND i.kind='evaluate') AS attempts,
              (SELECT count(*) FROM evaluations e WHERE e.training_run_id=:run) AS evaluations
        """), {'run': run_id}).mappings().one())

    def preflight_population(self, connection, attempt_ids: list[UUID]) -> list[dict[str, Any]]:
        """Full SQL aggregates over exact attempts, never a page or diagnostic recalculation.

        Declared and observed IDs are compared in both directions. Membership is
        proved against governed assignments, not by assuming UUID namespaces match.
        """
        return [dict(row) for row in connection.execute(text("""
            WITH selected AS MATERIALIZED (
                -- Scalars are read once: referencing identity per governed row re-parses the
                -- whole JSONB (all samples, ~1 MB) for each assignment (~7.5 s per attempt).
                SELECT a.id,a.state,a.verification,i.identity,
                       CAST(i.identity#>>'{dataset,dataset_version_id}' AS uuid) AS dataset_version_id,
                       i.identity->>'split' AS split
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                WHERE a.id=ANY(CAST(:ids AS uuid[]))
            ), declared AS (
                SELECT s.id,x->>'sample_id' AS sample_id,min(x->>'label') AS label,
                       count(*) AS rows, count(DISTINCT x->>'label') AS labels
                FROM selected s CROSS JOIN LATERAL jsonb_array_elements(s.identity->'samples') x
                GROUP BY s.id,x->>'sample_id'
            ), observed AS (
                SELECT r.attempt_id AS id,r.sample_id::text AS sample_id,
                       r.payload->>'label' AS label
                FROM assessment_results r JOIN selected s ON s.id=r.attempt_id
            ), common AS (
                SELECT sample_id,count(DISTINCT id) AS participants,
                       count(DISTINCT label) AS labels
                FROM observed GROUP BY sample_id
            ), aligned AS (
                SELECT coalesce(d.id,o.id) AS id,
                       coalesce(d.sample_id,o.sample_id) AS sample_id,
                       d.rows AS declared_rows,d.label AS declared_label,d.labels AS declared_labels,
                       o.label AS observed_label,d.sample_id IS NOT NULL AS declared,
                       o.sample_id IS NOT NULL AS observed
                FROM declared d FULL JOIN observed o USING(id,sample_id)
            ), governed AS (
                SELECT DISTINCT s.id,a.source_record_id::text AS sample_id,a.class_index::text AS label
                FROM selected s JOIN dataset_split_assignments a
                  ON a.dataset_version_id=s.dataset_version_id
                 AND a.split_name=s.split
                JOIN dataset_source_records r ON r.id=a.source_record_id
            )
            SELECT s.id AS attempt_id,
                coalesce(sum(t.declared_rows),0)::bigint AS expected_rows,
                count(*) FILTER (WHERE t.declared) AS expected_unique,
                count(*) FILTER (WHERE t.observed) AS retrieved_rows,
                count(DISTINCT t.sample_id) FILTER (WHERE t.observed) AS retrieved_unique,
                (SELECT count(*) FROM common WHERE participants=:participants) AS intersection_unique,
                count(*) FILTER (WHERE t.observed AND c.labels>1) AS label_conflicts,
                count(*) FILTER (WHERE t.observed AND t.observed_label IS NULL) AS missing_labels,
                count(*) FILTER (WHERE t.declared AND NOT t.observed) AS missing_count,
                count(*) FILTER (WHERE t.observed AND NOT t.declared) AS unexpected_count,
                count(*) FILTER (WHERE t.declared AND t.observed AND
                    (t.observed_label IS DISTINCT FROM t.declared_label OR t.declared_labels>1)) AS declared_label_conflicts,
                count(*) FILTER (WHERE t.observed AND g.sample_id IS NULL) AS ungoverned_count,
                s.state,s.verification->>'count' AS verified_count
            FROM selected s LEFT JOIN aligned t ON t.id=s.id
            LEFT JOIN common c ON c.sample_id=t.sample_id
            LEFT JOIN governed g ON g.id=t.id AND g.sample_id=t.sample_id AND g.label=t.observed_label
            GROUP BY s.id,s.state,s.verification ORDER BY s.id
        """), {'ids': [str(i) for i in attempt_ids], 'participants': len(attempt_ids)}).mappings()]

    def comparison_results(self, connection, attempt_id):
        """Full exact-attempt population for server-side analysis, never sent as a browser array."""
        return [dict(row) for row in connection.execute(text(
            'SELECT sample_id,payload FROM assessment_results WHERE attempt_id=:id ORDER BY sample_id'
        ), {'id': attempt_id}).mappings()]

    def eligibility_training(self, connection, run_id):
        row = connection.execute(text("""
            SELECT r.status,r.run_type,s.state AS session_state,s.verification,
                   s.configuration#>'{resolved,input_contract}' AS input_contract
            FROM runs r LEFT JOIN train_execution_sessions s ON s.run_id=r.id
            WHERE r.id=:run
        """), {'run': run_id}).mappings().one_or_none()
        return dict(row) if row else None

    def eligibility_attempts(self, connection, run_id):
        """Counts belong to one attempt; identities without attempts remain visible."""
        return [dict(row) for row in connection.execute(text("""
            SELECT i.id AS identity_id,i.kind,i.identity - 'samples' AS identity,
                   jsonb_array_length(i.identity->'samples') AS expected_count,
                   a.id AS attempt_id,a.state,a.finished_at,a.verification,
                   (SELECT count(*) FROM assessment_results r WHERE r.attempt_id=a.id) AS result_count,
                   (SELECT count(*) FROM assessment_artifacts f WHERE f.attempt_id=a.id) AS artifact_count
            FROM assessment_identities i LEFT JOIN assessment_attempts a ON a.identity_id=i.id
            WHERE i.training_run_id=:run
            ORDER BY i.created_at DESC,i.id,a.ordinal DESC
        """), {'run': run_id}).mappings()]
