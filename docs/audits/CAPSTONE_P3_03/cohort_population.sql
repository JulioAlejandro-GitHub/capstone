BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
WITH selected AS MATERIALIZED (
 SELECT a.id,i.identity->>'split' split,r.dataset_version_id
 FROM runs r JOIN assessment_identities i ON i.training_run_id=r.id
 JOIN assessment_attempts a ON a.identity_id=i.id
 WHERE r.campaign_id='eb7ae3da-c954-4f2f-8d19-0398824089c5'
   AND r.status='completed' AND i.kind='evaluate' AND a.state='verified'
), per_sample AS (
 SELECT s.split,r.sample_id,count(DISTINCT s.id) participants,
 count(DISTINCT r.payload->>'label') labels,
 count(DISTINCT r.payload->>'patient_id') patient_labels,
 bool_and(EXISTS (SELECT 1 FROM dataset_split_assignments d WHERE d.dataset_version_id=s.dataset_version_id AND d.split_name=s.split AND d.source_record_id=r.sample_id AND d.class_index::text=r.payload->>'label')) governed
 FROM selected s JOIN assessment_results r ON r.attempt_id=s.id GROUP BY s.split,r.sample_id
)
SELECT json_agg(t) FROM (
 SELECT split,(SELECT count(*) FROM selected s WHERE s.split=p.split) attempts,
 count(*) unique_samples,min(participants) min_participants,max(participants) max_participants,
 count(*) FILTER(WHERE labels<>1) label_conflicts,
 count(*) FILTER(WHERE patient_labels<>1) patient_conflicts,
 count(*) FILTER(WHERE NOT governed) ungoverned_samples
 FROM per_sample p GROUP BY split ORDER BY split)t;
COMMIT;
