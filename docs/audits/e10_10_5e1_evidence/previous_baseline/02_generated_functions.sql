-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.
CREATE OR REPLACE FUNCTION public.assessment_canonical(v jsonb)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE STRICT
 SET search_path TO 'public', 'pg_catalog'
AS $function$
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
END $function$;

CREATE OR REPLACE FUNCTION public.assessment_structural_hash(v jsonb)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE STRICT
 SET search_path TO 'public', 'pg_catalog'
AS $function$
 SELECT encode(sha256(convert_to(assessment_canonical(v),'UTF8')),'hex')
$function$;

