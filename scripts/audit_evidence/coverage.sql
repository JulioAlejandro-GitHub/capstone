-- CAPSTONE-EVIDENCE-COVERAGE-01 — cobertura de evidencia por RUN.
-- Solo lectura: transacción READ ONLY y ROLLBACK. Emite un único documento JSON.
\set ON_ERROR_STOP on
\pset tuples_only on
\pset format unaligned
BEGIN TRANSACTION READ ONLY;

WITH trains AS (
  SELECT r.id, r.run_name, r.status, r.started_at, r.finished_at, r.dataset_version_id,
         r.execution_type, r.random_seed,
         r.execution_parameters ->> 'source_training_run_id' AS source_training_run_id,
         m.name AS model_name, m.architecture, m.framework, m.num_parameters
  FROM runs r LEFT JOIN models m ON m.id = r.model_id
  WHERE r.run_type = 'training'
),
sessions AS (
  SELECT s.run_id, s.state, s.artifact_root,
         s.completion ->> 'epochs' AS completion_epochs,
         s.completion -> 'selection' ->> 'selected_epoch' AS selected_epoch,
         s.completion ->> 'records_hash' IS NOT NULL AS sealed,
         s.configuration -> 'resolved' -> 'execution' ->> 'max_epochs' AS max_epochs,
         s.configuration -> 'resolved' -> 'execution' ->> 'fine_tune_epochs' AS fine_tune_epochs,
         s.configuration -> 'resolved' -> 'execution' ->> 'batch_size' AS batch_size,
         s.configuration -> 'resolved' ? 'optimizer' AS has_optimizer_config,
         s.configuration -> 'resolved' ? 'recipe' AS has_recipe,
         s.environment <> '{}'::jsonb AS has_environment,
         s.dataset <> '{}'::jsonb AS has_dataset_snapshot
  FROM train_execution_sessions s
),
kinds AS (
  SELECT run_id, jsonb_object_agg(kind, n) AS record_kinds
  FROM (SELECT run_id, kind, count(*) AS n FROM train_execution_records GROUP BY run_id, kind) k
  GROUP BY run_id
),
phases AS (
  SELECT run_id, array_agg(DISTINCT phase ORDER BY phase) AS epoch_phases
  FROM train_execution_records WHERE kind = 'epoch' GROUP BY run_id
),
epoch_keys AS (
  SELECT run_id, array_agg(DISTINCT key ORDER BY key) AS epoch_metric_keys
  FROM train_execution_records, jsonb_object_keys(payload) AS key
  WHERE kind = 'epoch' GROUP BY run_id
),
val_predictions AS (
  SELECT run_id, count(*) AS epochs_with_val_predictions,
         max(jsonb_array_length(payload -> 'samples')) AS val_samples_per_epoch
  FROM train_execution_records WHERE kind = 'predictions' GROUP BY run_id
),
assessments AS (
  SELECT i.training_run_id AS run_id,
         i.kind,
         i.identity ->> 'split' AS split,
         i.identity -> 'explanation' ->> 'method' AS method,
         md5(COALESCE((SELECT string_agg(x ->> 'sample_id', ',' ORDER BY x ->> 'sample_id')
                       FROM jsonb_array_elements(i.identity -> 'samples') x), '')) AS population,
         jsonb_array_length(COALESCE(i.identity -> 'samples', '[]'::jsonb)) AS population_size,
         a.id AS attempt_id, a.state,
         (SELECT count(*) FROM assessment_results ar WHERE ar.attempt_id = a.id) AS results,
         (SELECT jsonb_object_agg(role, n) FROM (SELECT role, count(*) n FROM assessment_artifacts aa
                                                 WHERE aa.attempt_id = a.id GROUP BY role) q) AS artifact_roles
  FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id = i.id
),
assessment_summary AS (
  SELECT run_id, jsonb_agg(jsonb_build_object(
           'kind', kind, 'split', split, 'method', method, 'state', state,
           'attempt_id', attempt_id, 'population', population, 'population_size', population_size,
           'results', results, 'artifact_roles', artifact_roles) ORDER BY kind, split, method) AS attempts
  FROM assessments GROUP BY run_id
),
represent_populations AS (
  -- CKA es derivable entre dos TRAIN con REPRESENT verificado sobre la misma población.
  SELECT population, count(DISTINCT run_id) AS trains
  FROM assessments WHERE kind = 'represent' AND state = 'verified' GROUP BY population
)
SELECT jsonb_pretty(jsonb_build_object(
  'audit', 'CAPSTONE-EVIDENCE-COVERAGE-01',
  'generated_at', clock_timestamp(),
  'database', current_database(),
  'trains', (SELECT jsonb_agg(jsonb_build_object(
      'run_id', t.id, 'run_name', t.run_name, 'status', t.status,
      'model_name', t.model_name, 'architecture', t.architecture, 'framework', t.framework,
      'num_parameters', t.num_parameters, 'dataset_version_id', t.dataset_version_id,
      'execution_type', t.execution_type, 'seed', t.random_seed,
      'source_training_run_id', t.source_training_run_id,
      'started_at', t.started_at, 'finished_at', t.finished_at,
      'session', to_jsonb(s) - 'run_id',
      'record_kinds', k.record_kinds,
      'epoch_phases', p.epoch_phases,
      'epoch_metric_keys', e.epoch_metric_keys,
      'val_predictions', to_jsonb(v) - 'run_id',
      'assessments', a.attempts) ORDER BY t.started_at)
    FROM trains t
    LEFT JOIN sessions s ON s.run_id = t.id
    LEFT JOIN kinds k ON k.run_id = t.id
    LEFT JOIN phases p ON p.run_id = t.id
    LEFT JOIN epoch_keys e ON e.run_id = t.id
    LEFT JOIN val_predictions v ON v.run_id = t.id
    LEFT JOIN assessment_summary a ON a.run_id = t.id),
  'represent_populations', (SELECT jsonb_agg(to_jsonb(rp)) FROM represent_populations rp),
  'record_kinds_global', (SELECT jsonb_object_agg(kind, n) FROM
      (SELECT kind, count(*) n FROM train_execution_records GROUP BY kind) g)
));

ROLLBACK;
