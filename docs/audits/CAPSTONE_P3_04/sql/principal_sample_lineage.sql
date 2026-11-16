BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (
SELECT p.attempt_id,p.sample_id,p.payload,to_jsonb(r) source_record,to_jsonb(c) clinical_identity,to_jsonb(s) assignment
FROM assessment_results p JOIN dataset_source_records r ON r.id=p.sample_id
JOIN clinical_identities c ON c.id=r.clinical_identity_id
JOIN dataset_split_assignments s ON s.source_record_id=r.id AND s.dataset_version_id='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
WHERE p.attempt_id='00b8d407-c672-4b68-9814-53c092d034ba' AND (p.sample_id IN ('01a133b1-74db-5f12-bf42-8db74b539b26','fb1c9a4b-cf64-5b03-a839-13a8bb677135','014d8b8e-3397-5ae8-88fd-8cef2a2d6c64') OR (p.payload->>'label'='1' AND p.payload->>'predicted'='0')) ORDER BY p.sample_id)t;
COMMIT;
