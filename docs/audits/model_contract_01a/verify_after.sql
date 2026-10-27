SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='runs'
AND column_name IN ('tensorflow_version','keras_version');
SELECT count(*) AS runs, count(*) FILTER (
  WHERE execution_parameters #>> '{runtime_environment,tensorflow}'='2.17.1'
    AND execution_parameters #>> '{runtime_environment,packages,keras}'='3.15.1'
) AS matching_jsonb_environments FROM public.runs;
SELECT md5(string_agg(to_jsonb(r)::text,'' ORDER BY id)) AS runs_hash FROM public.runs r;
SELECT 'artifacts' AS object,count(*),md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM public.artifacts t
UNION ALL SELECT 'model_versions',count(*),md5(string_agg(to_jsonb(t)::text,'' ORDER BY id)) FROM public.model_versions t;
