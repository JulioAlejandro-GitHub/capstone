BEGIN;
SET LOCAL lock_timeout = '10s';
LOCK TABLE public.runs IN ACCESS EXCLUSIVE MODE;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.runs
        WHERE (tensorflow_version IS NOT NULL AND tensorflow_version IS DISTINCT FROM execution_parameters #>> '{runtime_environment,tensorflow}')
           OR (keras_version IS NOT NULL AND keras_version IS DISTINCT FROM execution_parameters #>> '{runtime_environment,packages,keras}')
    ) THEN
        RAISE EXCEPTION 'Historical runtime evidence mismatch';
    END IF;
END $$;
ALTER TABLE public.runs
    DROP COLUMN tensorflow_version,
    DROP COLUMN keras_version;
COMMIT;
