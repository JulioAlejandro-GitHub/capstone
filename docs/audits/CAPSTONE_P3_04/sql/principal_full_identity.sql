BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT to_jsonb(i) FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id WHERE a.id='00b8d407-c672-4b68-9814-53c092d034ba';
COMMIT;
