-- Etapa 2 is a technical, non-clinical availability lane. It reuses the
-- governed deployment revision and only relaxes candidate activation for the
-- explicit stage2/default slot after its dedicated smoke test passed.

CREATE OR REPLACE FUNCTION validate_deployed_model_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    version_status TEXT;
    version_sha256 TEXT;
    version_size BIGINT;
    artifact_checksum TEXT;
    artifact_size BIGINT;
    physical_status TEXT;
    calibrated_threshold NUMERIC;
    is_stage2 BOOLEAN;
    is_technical_production BOOLEAN;
BEGIN
    SELECT mv.status,mv.artifact_sha256,mv.artifact_size_bytes,LOWER(a.checksum),
           a.file_size_bytes,a.artifact_status
      INTO version_status,version_sha256,version_size,artifact_checksum,
           artifact_size,physical_status
      FROM model_versions mv
      JOIN artifacts a ON a.id=mv.checkpoint_artifact_id
                      AND a.run_id=mv.training_run_id
     WHERE mv.id=NEW.model_version_id
       AND mv.checkpoint_artifact_id=NEW.checkpoint_artifact_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Deployment sin par version/artifact gobernado: version %, artifact %',
            NEW.model_version_id,NEW.checkpoint_artifact_id USING ERRCODE='23503';
    END IF;

    IF NEW.artifact_size_bytes IS NULL THEN NEW.artifact_size_bytes:=version_size; END IF;
    IF LOWER(NEW.artifact_sha256) IS DISTINCT FROM version_sha256
       OR version_sha256 IS DISTINCT FROM artifact_checksum THEN
        RAISE EXCEPTION 'SHA-256 de deployment, model_version y artifact no coincide'
            USING ERRCODE='23514';
    END IF;
    IF NEW.artifact_size_bytes IS DISTINCT FROM version_size
       OR version_size IS DISTINCT FROM artifact_size THEN
        RAISE EXCEPTION 'Tamaño de deployment, model_version y artifact no coincide'
            USING ERRCODE='23514';
    END IF;

    IF NEW.threshold_calibration_id IS NOT NULL THEN
        SELECT threshold_selected INTO calibrated_threshold
          FROM run_threshold_calibration
         WHERE run_threshold_calibration_id=NEW.threshold_calibration_id
           AND model_version_id=NEW.model_version_id;
        IF calibrated_threshold IS DISTINCT FROM NEW.threshold_value THEN
            RAISE EXCEPTION 'threshold_value (%) no coincide con calibración % (%)',
                NEW.threshold_value,NEW.threshold_calibration_id,calibrated_threshold
                USING ERRCODE='23514';
        END IF;
    END IF;

    IF NEW.status='active' THEN
        is_stage2:=NEW.environment='stage2' AND NEW.alias='default';
        is_technical_production:=NEW.environment='production' AND NEW.alias='champion'
          AND COALESCE(NEW.metadata->>'production_scope','')='stage2_technical';
        IF is_stage2 OR is_technical_production THEN
            IF version_status NOT IN ('candidate','validated','approved','deployed') THEN
                RAISE EXCEPTION 'Model version % no apta para Etapa 2',version_status
                    USING ERRCODE='23514';
            END IF;
            IF COALESCE(NEW.metadata#>>'{stage2,eligible}','false')<>'true'
               OR COALESCE(NEW.metadata#>>'{technical_smoke_test,status}',
                           NEW.metadata#>>'{stage2_smoke_test,status}','')<>'PASS' THEN
                RAISE EXCEPTION 'Etapa 2 exige elegibilidad técnica y smoke PASS'
                    USING ERRCODE='23514';
            END IF;
        ELSIF version_status NOT IN ('approved','deployed') THEN
            RAISE EXCEPTION 'Solo una model_version approved/deployed puede activarse; estado actual %',
                version_status USING ERRCODE='23514';
        END IF;
        IF physical_status IS DISTINCT FROM 'available' THEN
            RAISE EXCEPTION 'El artifact debe estar available para activar; estado actual %',
                physical_status USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$;

COMMENT ON FUNCTION validate_deployed_model_version() IS
'Preserva producción formal y admite candidate solo en stage2/default con evidencia técnica PASS.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_deployed_model_versions_one_production_champion
ON deployed_model_versions(environment,alias)
WHERE status='active' AND environment='production' AND alias='champion';
