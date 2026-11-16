BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT * FROM dataset_split_validation_checks WHERE dataset_version_id='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2')t;
COMMIT;
