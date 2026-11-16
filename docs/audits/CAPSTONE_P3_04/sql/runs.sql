BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT r.*,to_jsonb(m) model FROM runs r LEFT JOIN models m ON m.id=r.model_id ORDER BY r.created_at)t;
COMMIT;
