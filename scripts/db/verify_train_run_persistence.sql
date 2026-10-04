-- Read only. psql: set run_id to the UUID of a NEW training run.
-- Example: psql ... -v run_id=UUID -f scripts/db/verify_train_run_persistence.sql
SELECT r.*,
       s.attempt_id,
       s.state AS session_state,
       s.completion->'selection' AS checkpoint_selection,
       s.verification->>'status' AS verification_status,
       a.id AS checkpoint_artifact_id,
       a.path AS checkpoint_path,
       a.checksum AS checkpoint_sha256,
       a.file_size_bytes AS checkpoint_bytes,
       a.metadata AS checkpoint_metadata,
       r.duration_seconds = EXTRACT(EPOCH FROM r.finished_at-r.started_at) AS duration_matches,
       (SELECT count(*) FROM train_execution_records er
        WHERE er.run_id=r.id AND er.kind='epoch' AND er.event_id IS NULL) AS recorded_epochs
FROM runs r
LEFT JOIN train_execution_sessions s ON s.run_id=r.id
LEFT JOIN artifacts a ON a.run_id=r.id AND a.id=
    (r.execution_parameters->'e10_v2_evaluation_context_v1'->>'checkpoint_artifact_id')::uuid
WHERE r.id=:'run_id'::uuid AND r.run_type='training';
