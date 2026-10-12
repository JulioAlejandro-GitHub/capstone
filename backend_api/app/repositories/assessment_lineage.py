"""Shared read projection for TRAIN children; never materializes scientific records.

The caller supplies selected_trainings(id). One E6 evaluation per identity is
visible: a verified attempt wins, otherwise the latest ordinal is shown. Failed,
interrupted and active attempts remain observable, without verified metrics.
Explicit evaluations.source_assessment_attempt_id links deduplicate legacy runs;
E6 is authoritative even when that link points at an older attempt.
"""

LINEAGE_SOURCES_CTES = """
ranked_assessments AS (
    SELECT i.id AS identity_id, i.training_run_id, i.identity,
           a.id AS attempt_id, a.state, a.ordinal, a.verification,
           a.started_at, a.finished_at, i.created_at,
           row_number() OVER (
               PARTITION BY i.id
               ORDER BY (a.state = 'verified') DESC, a.ordinal DESC, a.id
           ) AS attempt_rank
    FROM assessment_identities i
    JOIN selected_trainings selected ON selected.id = i.training_run_id
    JOIN assessment_attempts a ON a.identity_id = i.id
    WHERE i.kind = 'evaluate'
      AND a.state IN ('verified', 'active', 'failed', 'interrupted')
), visible_assessments AS MATERIALIZED (
    SELECT * FROM ranked_assessments WHERE attempt_rank = 1
), eligible_run_lineage AS MATERIALIZED (
    SELECT lineage.*
    FROM run_lineage lineage
    JOIN selected_trainings selected ON selected.id = lineage.parent_run_id
    JOIN runs child ON child.id = lineage.child_run_id
    WHERE (
        (lineage.relationship_type = 'evaluates_checkpoint_from'
         AND child.run_type = 'evaluation')
        OR (lineage.relationship_type = 'explains_checkpoint_from'
            AND child.run_type = 'explainability')
    ) AND NOT (
        child.run_type = 'evaluation' AND EXISTS (
            SELECT 1 FROM evaluations e
            JOIN assessment_attempts a ON a.id = e.source_assessment_attempt_id
            JOIN visible_assessments v ON v.identity_id = a.identity_id
            WHERE e.run_id = child.id AND e.source_kind = 'assessment'
              AND v.training_run_id = lineage.parent_run_id
              AND e.training_run_id = lineage.parent_run_id
        )
    )
)
"""
