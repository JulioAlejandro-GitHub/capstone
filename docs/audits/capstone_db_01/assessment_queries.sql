\set ON_ERROR_STOP on
BEGIN READ ONLY;
SELECT jsonb_build_object('assessment_counts',jsonb_agg(to_jsonb(x))) FROM (SELECT i.kind,a.state,count(DISTINCT i.id) identities,count(DISTINCT i.training_run_id) training_runs,count(DISTINCT a.id) attempts,(SELECT count(*) FROM assessment_results r JOIN assessment_attempts aa ON aa.id=r.attempt_id JOIN assessment_identities ii ON ii.id=aa.identity_id WHERE ii.kind=i.kind AND aa.state=a.state) results,(SELECT count(*) FROM assessment_artifacts r JOIN assessment_attempts aa ON aa.id=r.attempt_id JOIN assessment_identities ii ON ii.id=aa.identity_id WHERE ii.kind=i.kind AND aa.state=a.state) artifacts FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id GROUP BY i.kind,a.state ORDER BY 1,2) x;
SELECT jsonb_build_object('assessment_integrity',jsonb_build_object('explain_missing_training',(SELECT count(*) FROM assessment_identities i LEFT JOIN runs r ON r.id=i.training_run_id WHERE i.kind='explain' AND (r.id IS NULL OR r.run_type<>'training')),'explain_campaign_links',(SELECT count(*) FROM assessment_campaign_consumers c JOIN assessment_identities i ON i.id=c.identity_id WHERE i.kind='explain'),'explain_matching_evaluate_training',(SELECT count(*) FROM assessment_identities i WHERE i.kind='explain' AND EXISTS(SELECT 1 FROM assessment_identities e WHERE e.kind='evaluate' AND e.training_run_id=i.training_run_id))));
SELECT jsonb_build_object('dataset_verification_status',jsonb_agg(to_jsonb(x))) FROM (SELECT after_state->>'consumer' consumer,success,error_code,after_state->>'integrity_status' integrity_status,after_state->>'global_integrity_status' global_integrity_status,after_state->>'physical_integrity_status' physical_integrity_status,count(*) FROM audit_events WHERE event_type='ml.dataset_verification' GROUP BY 1,2,3,4,5,6) x;
SELECT jsonb_build_object('campaign_evidence_consistency',jsonb_build_object('campaigns',count(*),'missing_evidence',count(*) FILTER (WHERE e.id IS NULL),'wrong_status',count(*) FILTER (WHERE (e.after_state->>'integrity_status') IS DISTINCT FROM 'verified'),'different_snapshot',count(*) FILTER (WHERE (e.after_state->'snapshot') IS DISTINCT FROM c.dataset_snapshot),'different_version',count(*) FILTER (WHERE (e.after_state->>'dataset_version_id') IS DISTINCT FROM c.dataset_version_id::text))) FROM experimental_campaigns c LEFT JOIN audit_events e ON e.id=c.dataset_evidence_id;
COMMIT;
BEGIN READ ONLY;
WITH selected_trainings AS (SELECT id FROM runs WHERE run_type='training'),
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
 SELECT jsonb_build_object('report_source_counts',jsonb_build_object('visible_evaluate_assessments',(SELECT count(*) FROM visible_assessments),'visible_explain_runs',(SELECT count(*) FROM eligible_run_lineage l JOIN runs r ON r.id=l.child_run_id WHERE r.run_type='explainability')));
COMMIT;
