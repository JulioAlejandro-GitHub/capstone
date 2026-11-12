BEGIN READ ONLY;
SELECT coalesce(json_agg(t),'[]') FROM (SELECT attempt_id,sample_id,payload FROM assessment_results WHERE attempt_id IN ('1ea90a63-65ea-41d9-97a0-1469fe671e47','7956a4c2-f65a-4e45-848a-499376b3e61f') ORDER BY attempt_id,sample_id)t;
COMMIT;
