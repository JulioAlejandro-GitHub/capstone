-- DBV2.2 + approved R1. Install exclusively via guarded Alembic v2.
CREATE OR REPLACE FUNCTION public.assessment_canonical(v jsonb) RETURNS text LANGUAGE plpgsql IMMUTABLE RETURNS NULL ON NULL INPUT SET search_path TO 'public', 'pg_catalog' AS $$
DECLARE result text;
BEGIN
 CASE jsonb_typeof(v)
 WHEN 'object' THEN
   SELECT '{'||coalesce(string_agg(to_jsonb(key)::text||':'||assessment_canonical(value),',' ORDER BY key COLLATE "C"),'')||'}' INTO result FROM jsonb_each(v);
 WHEN 'array' THEN
   SELECT '['||coalesce(string_agg(assessment_canonical(value),',' ORDER BY ord),'')||']' INTO result FROM jsonb_array_elements(v) WITH ORDINALITY a(value,ord);
 WHEN 'number' THEN result=trim_scale((v::text)::numeric)::text;
 ELSE result=v::text;
 END CASE;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION public.assessment_structural_hash(v jsonb) RETURNS text LANGUAGE sql IMMUTABLE RETURNS NULL ON NULL INPUT SET search_path TO 'public', 'pg_catalog' AS $$
 SELECT encode(sha256(convert_to(assessment_canonical(v),'UTF8')),'hex')
$$;

