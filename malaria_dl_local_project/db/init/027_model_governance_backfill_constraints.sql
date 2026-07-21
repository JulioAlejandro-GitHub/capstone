-- Backfill conservador: solo se atribuye por el mismo training_run_id, el
-- checkpoint_path exacto y un SHA-256 válido cuando existe un único candidato.
-- No se selecciona la versión más reciente, no se compara por basename y no se
-- reemplaza ningún checksum histórico.

DO $backfill$
DECLARE
    governance_batch_id UUID := gen_random_uuid();
BEGIN
    WITH artifact_candidates AS (
        SELECT
            mv.id AS model_version_id,
            a.id AS checkpoint_artifact_id,
            a.path AS matched_path,
            LOWER(a.checksum) AS artifact_sha256,
            a.file_size_bytes AS artifact_size_bytes,
            m.name AS catalog_model_name,
            m.framework AS catalog_framework,
            CASE
                WHEN LOWER(COALESCE(m.framework, '')) LIKE '%keras%'
                    THEN COALESCE(r.keras_version, r.tensorflow_version)
                ELSE COALESCE(r.tensorflow_version, r.keras_version)
            END AS observed_framework_version,
            COUNT(*) OVER (PARTITION BY mv.id) AS candidate_count
        FROM model_versions mv
        JOIN artifacts a
          ON a.run_id = mv.training_run_id
         AND a.path = mv.checkpoint_path
        LEFT JOIN models m
          ON m.id = mv.model_id
        JOIN runs r
          ON r.id = mv.training_run_id
         AND r.run_type = 'training'
        WHERE a.checksum IS NOT NULL
          AND LOWER(a.checksum) ~ '^[0-9a-f]{64}$'
    ),
    exact_candidates AS (
        SELECT
            candidates.*,
            jsonb_build_object(
                'checkpoint_artifact_id', mv.checkpoint_artifact_id,
                'artifact_sha256', mv.artifact_sha256,
                'artifact_size_bytes', mv.artifact_size_bytes,
                'model_name', mv.model_name,
                'framework', mv.framework,
                'framework_version', mv.framework_version,
                'lineage_status', mv.lineage_status
            ) AS before_values
        FROM artifact_candidates candidates
        JOIN model_versions mv
          ON mv.id = candidates.model_version_id
        WHERE candidates.candidate_count = 1
          AND (
              mv.checkpoint_artifact_id IS NULL
              OR mv.checkpoint_artifact_id = candidates.checkpoint_artifact_id
          )
          AND (
              mv.artifact_sha256 IS NULL
              OR LOWER(mv.artifact_sha256) = candidates.artifact_sha256
          )
    ),
    updated_versions AS (
        UPDATE model_versions mv
        SET checkpoint_artifact_id = exact.checkpoint_artifact_id,
            artifact_sha256 = exact.artifact_sha256,
            artifact_size_bytes = exact.artifact_size_bytes,
            model_name = COALESCE(mv.model_name, exact.catalog_model_name),
            framework = COALESCE(mv.framework, exact.catalog_framework),
            framework_version = COALESCE(
                mv.framework_version,
                exact.observed_framework_version
            ),
            lineage_status = 'resolved'
        FROM exact_candidates exact
        WHERE mv.id = exact.model_version_id
          AND (
              mv.checkpoint_artifact_id IS DISTINCT FROM exact.checkpoint_artifact_id
              OR mv.artifact_sha256 IS DISTINCT FROM exact.artifact_sha256
              OR mv.artifact_size_bytes IS DISTINCT FROM exact.artifact_size_bytes
              OR (mv.model_name IS NULL AND exact.catalog_model_name IS NOT NULL)
              OR (mv.framework IS NULL AND exact.catalog_framework IS NOT NULL)
              OR (
                  mv.framework_version IS NULL
                  AND exact.observed_framework_version IS NOT NULL
              )
              OR mv.lineage_status IS DISTINCT FROM 'resolved'
          )
        RETURNING
            mv.id,
            exact.checkpoint_artifact_id,
            exact.before_values,
            jsonb_build_object(
                'checkpoint_artifact_id', mv.checkpoint_artifact_id,
                'artifact_sha256', mv.artifact_sha256,
                'artifact_size_bytes', mv.artifact_size_bytes,
                'model_name', mv.model_name,
                'framework', mv.framework,
                'framework_version', mv.framework_version,
                'lineage_status', mv.lineage_status
            ) AS after_values
    )
    INSERT INTO model_governance_backfill_audit (
        batch_id,
        event_type,
        table_name,
        record_id,
        before_values,
        after_values,
        resolution_rule,
        candidate_ids,
        result_status,
        metadata
    )
    SELECT
        governance_batch_id,
        'apply',
        'model_versions',
        updated.id,
        updated.before_values,
        updated.after_values,
        'same_training_run_exact_checkpoint_path_valid_sha256_unique',
        ARRAY[updated.id, updated.checkpoint_artifact_id]::UUID[],
        'applied',
        jsonb_build_object('migration', '027_model_governance_backfill_constraints.sql')
    FROM updated_versions updated;

    WITH lineage_candidates AS (
        SELECT
            lineage.id AS lineage_id,
            mv.id AS model_version_id,
            mv.checkpoint_artifact_id,
            COUNT(*) OVER (PARTITION BY lineage.id) AS candidate_count
        FROM run_lineage lineage
        JOIN model_versions mv
          ON mv.training_run_id = lineage.parent_run_id
         AND mv.checkpoint_path = lineage.checkpoint_path
        JOIN artifacts a
          ON a.id = mv.checkpoint_artifact_id
         AND a.run_id = lineage.parent_run_id
         AND a.path = lineage.checkpoint_path
         AND LOWER(a.checksum) = mv.artifact_sha256
        WHERE lineage.relationship_type IN (
                  'evaluates_checkpoint_from',
                  'explains_checkpoint_from'
              )
          AND mv.lineage_status = 'resolved'
          AND mv.artifact_sha256 ~ '^[0-9a-f]{64}$'
    ),
    exact_lineage AS (
        SELECT
            candidates.*,
            jsonb_build_object(
                'model_version_id', lineage.model_version_id,
                'checkpoint_artifact_id', lineage.checkpoint_artifact_id,
                'confidence', lineage.confidence
            ) AS before_values
        FROM lineage_candidates candidates
        JOIN run_lineage lineage
          ON lineage.id = candidates.lineage_id
        WHERE candidates.candidate_count = 1
          AND (
              lineage.model_version_id IS NULL
              OR lineage.model_version_id = candidates.model_version_id
          )
          AND (
              lineage.checkpoint_artifact_id IS NULL
              OR lineage.checkpoint_artifact_id = candidates.checkpoint_artifact_id
          )
    ),
    updated_lineage AS (
        UPDATE run_lineage lineage
        SET model_version_id = exact.model_version_id,
            checkpoint_artifact_id = exact.checkpoint_artifact_id
        FROM exact_lineage exact
        WHERE lineage.id = exact.lineage_id
          AND (
              lineage.model_version_id IS DISTINCT FROM exact.model_version_id
              OR lineage.checkpoint_artifact_id IS DISTINCT FROM exact.checkpoint_artifact_id
          )
        RETURNING
            lineage.id,
            exact.model_version_id,
            exact.checkpoint_artifact_id,
            exact.before_values,
            jsonb_build_object(
                'model_version_id', lineage.model_version_id,
                'checkpoint_artifact_id', lineage.checkpoint_artifact_id,
                'confidence', lineage.confidence
            ) AS after_values
    )
    INSERT INTO model_governance_backfill_audit (
        batch_id,
        event_type,
        table_name,
        record_id,
        before_values,
        after_values,
        resolution_rule,
        candidate_ids,
        result_status,
        metadata
    )
    SELECT
        governance_batch_id,
        'apply',
        'run_lineage',
        updated.id,
        updated.before_values,
        updated.after_values,
        'parent_training_run_exact_checkpoint_path_version_artifact_sha256_unique',
        ARRAY[
            updated.id,
            updated.model_version_id,
            updated.checkpoint_artifact_id
        ]::UUID[],
        'applied',
        jsonb_build_object('migration', '027_model_governance_backfill_constraints.sql')
    FROM updated_lineage updated;
END;
$backfill$;

-- Las FKs históricas permitían borrar o desvincular evidencia central. Se
-- reemplazan por RESTRICT; el bloque solo actúa si la semántica aún es otra.
DO $delete_protection$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'model_versions_training_run_id_fkey'
          AND confdeltype <> 'r'
    ) THEN
        ALTER TABLE model_versions
            DROP CONSTRAINT model_versions_training_run_id_fkey;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'model_versions_training_run_id_fkey'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT model_versions_training_run_id_fkey
            FOREIGN KEY (training_run_id)
            REFERENCES runs(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'model_versions_model_id_fkey'
          AND confdeltype <> 'r'
    ) THEN
        ALTER TABLE model_versions
            DROP CONSTRAINT model_versions_model_id_fkey;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'model_versions_model_id_fkey'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT model_versions_model_id_fkey
            FOREIGN KEY (model_id)
            REFERENCES models(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'run_lineage_parent_run_id_fkey'
          AND confdeltype <> 'r'
    ) THEN
        ALTER TABLE run_lineage
            DROP CONSTRAINT run_lineage_parent_run_id_fkey;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'run_lineage_parent_run_id_fkey'
    ) THEN
        ALTER TABLE run_lineage
            ADD CONSTRAINT run_lineage_parent_run_id_fkey
            FOREIGN KEY (parent_run_id)
            REFERENCES runs(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'run_lineage_child_run_id_fkey'
          AND confdeltype <> 'r'
    ) THEN
        ALTER TABLE run_lineage
            DROP CONSTRAINT run_lineage_child_run_id_fkey;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'run_lineage_child_run_id_fkey'
    ) THEN
        ALTER TABLE run_lineage
            ADD CONSTRAINT run_lineage_child_run_id_fkey
            FOREIGN KEY (child_run_id)
            REFERENCES runs(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;
END;
$delete_protection$;

-- Toda constraint NOT VALID de 024/026 ya admite NULL legacy. Tras el backfill
-- exacto se valida la población existente sin inventar IDs para filas no resueltas.
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_status;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_lineage_status;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_resolved_training;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_governed_hash;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_sha256;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_artifact_size;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_version_number;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_profile_objects;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT chk_model_versions_artifact_requires_training;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT fk_model_versions_checkpoint_artifact_owner;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT model_versions_training_run_id_fkey;
ALTER TABLE model_versions
    VALIDATE CONSTRAINT model_versions_model_id_fkey;

ALTER TABLE artifacts
    VALIDATE CONSTRAINT chk_artifacts_governance_status;

ALTER TABLE run_lineage
    VALIDATE CONSTRAINT fk_run_lineage_model_version_owner;
ALTER TABLE run_lineage
    VALIDATE CONSTRAINT fk_run_lineage_checkpoint_artifact_owner;
ALTER TABLE run_lineage
    VALIDATE CONSTRAINT fk_run_lineage_version_artifact;
ALTER TABLE run_lineage
    VALIDATE CONSTRAINT run_lineage_parent_run_id_fkey;
ALTER TABLE run_lineage
    VALIDATE CONSTRAINT run_lineage_child_run_id_fkey;

ALTER TABLE run_checkpoint_policy
    VALIDATE CONSTRAINT fk_run_checkpoint_policy_model_version_owner;
ALTER TABLE run_checkpoint_policy
    VALIDATE CONSTRAINT fk_run_checkpoint_policy_artifact_owner;
ALTER TABLE run_checkpoint_policy
    VALIDATE CONSTRAINT fk_run_checkpoint_policy_version_artifact;

ALTER TABLE run_threshold_calibration
    VALIDATE CONSTRAINT chk_run_threshold_calibration_score_name;
ALTER TABLE run_threshold_calibration
    VALIDATE CONSTRAINT chk_run_threshold_calibration_positive_label;
ALTER TABLE run_threshold_calibration
    VALIDATE CONSTRAINT chk_run_threshold_calibration_status;
ALTER TABLE run_threshold_calibration
    VALIDATE CONSTRAINT fk_run_threshold_calibration_model_version;
ALTER TABLE run_threshold_calibration
    VALIDATE CONSTRAINT fk_run_threshold_calibration_artifact_owner;

ALTER TABLE runs
    VALIDATE CONSTRAINT chk_runs_configuration_object;

ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_probability_parasitized;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_probability_uninfected;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_predicted_class;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_class_label;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_threshold_used;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_scope;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_bbox;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_quality_status;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_confidence_level;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_review_status;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_reviewed_label;
ALTER TABLE predictions
    VALIDATE CONSTRAINT chk_predictions_cell_requirements;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_analysis_job;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_model_version;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_deployed_model_version;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_inference_run;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_classifier_model_version;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_detector_model_version;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_source_image;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_crop_artifact;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_explanation_artifact;
ALTER TABLE predictions
    VALIDATE CONSTRAINT fk_predictions_job_provenance;

CREATE OR REPLACE FUNCTION enforce_model_version_governance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    owner_run_type TEXT;
BEGIN
    IF NEW.training_run_id IS NOT NULL THEN
        SELECT run_type
        INTO owner_run_type
        FROM runs
        WHERE id = NEW.training_run_id;

        IF owner_run_type IS DISTINCT FROM 'training' THEN
            RAISE EXCEPTION
                'model_versions.training_run_id debe referenciar un run training; recibió % (%)',
                NEW.training_run_id,
                owner_run_type
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF TG_OP = 'UPDATE'
       AND (
           OLD.status IN (
               'candidate', 'validated', 'approved', 'deployed', 'rejected', 'retired'
           )
           OR NEW.status IN (
               'candidate', 'validated', 'approved', 'deployed', 'rejected', 'retired'
           )
       )
       AND ROW(
           NEW.model_id,
           NEW.model_name,
           NEW.version_number,
           NEW.checkpoint_path,
           NEW.final_model_path,
           NEW.best_model_path,
           NEW.training_run_id,
           NEW.checkpoint_artifact_id,
           NEW.artifact_uri,
           NEW.artifact_sha256,
           NEW.artifact_size_bytes,
           NEW.artifact_hash_reuse_justification,
           NEW.framework,
           NEW.framework_version,
           NEW.preprocessing_profile_snapshot,
           NEW.class_mapping,
           NEW.input_signature,
           NEW.output_signature
       ) IS DISTINCT FROM ROW(
           OLD.model_id,
           OLD.model_name,
           OLD.version_number,
           OLD.checkpoint_path,
           OLD.final_model_path,
           OLD.best_model_path,
           OLD.training_run_id,
           OLD.checkpoint_artifact_id,
           OLD.artifact_uri,
           OLD.artifact_sha256,
           OLD.artifact_size_bytes,
           OLD.artifact_hash_reuse_justification,
           OLD.framework,
           OLD.framework_version,
           OLD.preprocessing_profile_snapshot,
           OLD.class_mapping,
           OLD.input_signature,
           OLD.output_signature
       ) THEN
        RAISE EXCEPTION
            'El payload de una model_version gobernada es inmutable (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION enforce_run_lineage_governance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    parent_type TEXT;
    child_type TEXT;
BEGIN
    SELECT run_type INTO parent_type FROM runs WHERE id = NEW.parent_run_id;
    SELECT run_type INTO child_type FROM runs WHERE id = NEW.child_run_id;

    IF NEW.relationship_type = 'evaluates_checkpoint_from'
       AND (parent_type IS DISTINCT FROM 'training' OR child_type IS DISTINCT FROM 'evaluation') THEN
        RAISE EXCEPTION
            'evaluates_checkpoint_from exige parent training y child evaluation; recibió % -> %',
            parent_type,
            child_type
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type = 'explains_checkpoint_from'
       AND (parent_type IS DISTINCT FROM 'training' OR child_type IS DISTINCT FROM 'explainability') THEN
        RAISE EXCEPTION
            'explains_checkpoint_from exige parent training y child explainability; recibió % -> %',
            parent_type,
            child_type
            USING ERRCODE = '23514';
    END IF;

    IF NEW.relationship_type IN (
           'evaluates_checkpoint_from', 'explains_checkpoint_from'
       )
       AND (
           NEW.model_version_id IS NULL
           OR NEW.checkpoint_artifact_id IS NULL
       ) THEN
        IF TG_OP = 'INSERT' THEN
            RAISE EXCEPTION
                'El linaje gobernado % exige model_version_id y checkpoint_artifact_id',
                NEW.relationship_type
                USING ERRCODE = '23514';
        ELSIF ROW(
            NEW.relationship_type,
            NEW.parent_run_id,
            NEW.child_run_id,
            NEW.model_version_id,
            NEW.checkpoint_artifact_id
        ) IS DISTINCT FROM ROW(
            OLD.relationship_type,
            OLD.parent_run_id,
            OLD.child_run_id,
            OLD.model_version_id,
            OLD.checkpoint_artifact_id
        ) THEN
            RAISE EXCEPTION
                'Cambiar la identidad de linaje % exige model_version_id y checkpoint_artifact_id',
                NEW.relationship_type
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

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
BEGIN
    SELECT
        mv.status,
        mv.artifact_sha256,
        mv.artifact_size_bytes,
        LOWER(a.checksum),
        a.file_size_bytes,
        a.artifact_status
    INTO
        version_status,
        version_sha256,
        version_size,
        artifact_checksum,
        artifact_size,
        physical_status
    FROM model_versions mv
    JOIN artifacts a
      ON a.id = mv.checkpoint_artifact_id
     AND a.run_id = mv.training_run_id
    WHERE mv.id = NEW.model_version_id
      AND mv.checkpoint_artifact_id = NEW.checkpoint_artifact_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Deployment sin par version/artifact gobernado: version %, artifact %',
            NEW.model_version_id,
            NEW.checkpoint_artifact_id
            USING ERRCODE = '23503';
    END IF;

    IF NEW.artifact_size_bytes IS NULL THEN
        NEW.artifact_size_bytes := version_size;
    END IF;

    IF LOWER(NEW.artifact_sha256) IS DISTINCT FROM version_sha256
       OR version_sha256 IS DISTINCT FROM artifact_checksum THEN
        RAISE EXCEPTION
            'SHA-256 de deployment, model_version y artifact no coincide'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.artifact_size_bytes IS DISTINCT FROM version_size
       OR version_size IS DISTINCT FROM artifact_size THEN
        RAISE EXCEPTION
            'Tamaño de deployment, model_version y artifact no coincide'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.threshold_calibration_id IS NOT NULL THEN
        SELECT threshold_selected
        INTO calibrated_threshold
        FROM run_threshold_calibration
        WHERE run_threshold_calibration_id = NEW.threshold_calibration_id
          AND model_version_id = NEW.model_version_id;

        IF calibrated_threshold IS DISTINCT FROM NEW.threshold_value THEN
            RAISE EXCEPTION
                'threshold_value (%) no coincide con calibración % (%)',
                NEW.threshold_value,
                NEW.threshold_calibration_id,
                calibrated_threshold
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.status = 'active' THEN
        IF version_status NOT IN ('approved', 'deployed') THEN
            RAISE EXCEPTION
                'Solo una model_version approved/deployed puede activarse; estado actual %',
                version_status
                USING ERRCODE = '23514';
        END IF;
        IF physical_status IS DISTINCT FROM 'available' THEN
            RAISE EXCEPTION
                'El artifact debe estar available para activar; estado actual %',
                physical_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION protect_deployed_model_version_payload()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'UPDATE'
       AND ROW(
           NEW.model_version_id,
           NEW.checkpoint_artifact_id,
           NEW.threshold_calibration_id,
           NEW.deployment_name,
           NEW.environment,
           NEW.alias,
           NEW.artifact_sha256,
           NEW.artifact_size_bytes,
           NEW.threshold_value,
           NEW.threshold_profile_snapshot,
           NEW.preprocessing_profile_snapshot,
           NEW.image_quality_policy_snapshot,
           NEW.label_mapping_snapshot,
           NEW.positive_label,
           NEW.score_name,
           NEW.supersedes_deployment_id,
           NEW.rollback_of_deployment_id,
           NEW.created_at
       ) IS DISTINCT FROM ROW(
           OLD.model_version_id,
           OLD.checkpoint_artifact_id,
           OLD.threshold_calibration_id,
           OLD.deployment_name,
           OLD.environment,
           OLD.alias,
           OLD.artifact_sha256,
           OLD.artifact_size_bytes,
           OLD.threshold_value,
           OLD.threshold_profile_snapshot,
           OLD.preprocessing_profile_snapshot,
           OLD.image_quality_policy_snapshot,
           OLD.label_mapping_snapshot,
           OLD.positive_label,
           OLD.score_name,
           OLD.supersedes_deployment_id,
           OLD.rollback_of_deployment_id,
           OLD.created_at
       ) THEN
        RAISE EXCEPTION
            'El payload de deployed_model_versions es inmutable; cree una nueva revisión (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION validate_run_model_deployment()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    inference_type TEXT;
    deployment_status TEXT;
BEGIN
    SELECT run_type INTO inference_type FROM runs WHERE id = NEW.run_id;
    IF inference_type IS DISTINCT FROM 'inference' THEN
        RAISE EXCEPTION
            'run_model_deployments.run_id debe ser inference; recibió %',
            inference_type
            USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'INSERT'
       OR NEW.run_id IS DISTINCT FROM OLD.run_id
       OR NEW.deployed_model_version_id IS DISTINCT FROM OLD.deployed_model_version_id
       OR NEW.model_version_id IS DISTINCT FROM OLD.model_version_id THEN
        SELECT status
        INTO deployment_status
        FROM deployed_model_versions
        WHERE id = NEW.deployed_model_version_id
          AND model_version_id = NEW.model_version_id;

        IF deployment_status IS DISTINCT FROM 'active' THEN
            RAISE EXCEPTION
                'Un inference run solo puede vincular un deployment active; recibió %',
                deployment_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION validate_image_analysis_job()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    inference_type TEXT;
    deployment_status TEXT;
    deployment_threshold NUMERIC;
BEGIN
    SELECT run_type
    INTO inference_type
    FROM runs
    WHERE id = NEW.inference_run_id;

    IF inference_type IS DISTINCT FROM 'inference' THEN
        RAISE EXCEPTION
            'image_analysis_jobs.inference_run_id debe ser inference; recibió %',
            inference_type
            USING ERRCODE = '23514';
    END IF;

    SELECT status, threshold_value
    INTO deployment_status, deployment_threshold
    FROM deployed_model_versions
    WHERE id = NEW.deployed_model_version_id
      AND model_version_id = NEW.model_version_id;

    IF TG_OP = 'INSERT'
       OR NEW.inference_run_id IS DISTINCT FROM OLD.inference_run_id
       OR NEW.deployed_model_version_id IS DISTINCT FROM OLD.deployed_model_version_id
       OR NEW.model_version_id IS DISTINCT FROM OLD.model_version_id THEN
        IF deployment_status IS DISTINCT FROM 'active' THEN
            RAISE EXCEPTION
                'Un image_analysis_job nuevo exige deployment active; recibió %',
                deployment_status
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.status IN ('running', 'completed') THEN
        IF NEW.threshold_used IS NULL
           OR NEW.threshold_used IS DISTINCT FROM deployment_threshold THEN
            RAISE EXCEPTION
                'threshold_used del job debe coincidir con threshold_value del deployment (%)',
                deployment_threshold
                USING ERRCODE = '23514';
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION protect_governed_artifact_identity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM model_versions
        WHERE checkpoint_artifact_id = OLD.id
    )
       AND ROW(
           NEW.run_id,
           NEW.path,
           NEW.checksum,
           NEW.file_size_bytes
       ) IS DISTINCT FROM ROW(
           OLD.run_id,
           OLD.path,
           OLD.checksum,
           OLD.file_size_bytes
       ) THEN
        RAISE EXCEPTION
            'No se puede mutar path/checksum/tamaño de un artifact ligado a model_version (%)',
            OLD.id
            USING ERRCODE = '55000';
    END IF;
    RETURN NEW;
END;
$function$;

DO $triggers$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'model_versions'::regclass
          AND tgname = 'trg_model_versions_governance'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_model_versions_governance
        BEFORE INSERT OR UPDATE ON model_versions
        FOR EACH ROW
        EXECUTE FUNCTION enforce_model_version_governance();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'run_lineage'::regclass
          AND tgname = 'trg_run_lineage_governance'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_run_lineage_governance
        BEFORE INSERT OR UPDATE ON run_lineage
        FOR EACH ROW
        EXECUTE FUNCTION enforce_run_lineage_governance();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'deployed_model_versions'::regclass
          AND tgname = 'trg_deployed_model_versions_10_immutable'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_deployed_model_versions_10_immutable
        BEFORE UPDATE ON deployed_model_versions
        FOR EACH ROW
        EXECUTE FUNCTION protect_deployed_model_version_payload();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'deployed_model_versions'::regclass
          AND tgname = 'trg_deployed_model_versions_20_validate'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_deployed_model_versions_20_validate
        BEFORE INSERT OR UPDATE ON deployed_model_versions
        FOR EACH ROW
        EXECUTE FUNCTION validate_deployed_model_version();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'run_model_deployments'::regclass
          AND tgname = 'trg_run_model_deployments_validate'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_run_model_deployments_validate
        BEFORE INSERT OR UPDATE ON run_model_deployments
        FOR EACH ROW
        EXECUTE FUNCTION validate_run_model_deployment();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'image_analysis_jobs'::regclass
          AND tgname = 'trg_image_analysis_jobs_validate'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_image_analysis_jobs_validate
        BEFORE INSERT OR UPDATE ON image_analysis_jobs
        FOR EACH ROW
        EXECUTE FUNCTION validate_image_analysis_job();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'artifacts'::regclass
          AND tgname = 'trg_artifacts_protect_governed_identity'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_artifacts_protect_governed_identity
        BEFORE UPDATE ON artifacts
        FOR EACH ROW
        EXECUTE FUNCTION protect_governed_artifact_identity();
    END IF;
END;
$triggers$;

COMMENT ON FUNCTION enforce_run_lineage_governance() IS
    'Impide linaje materialmente falso y exige version/artifact para evaluación y explicabilidad nuevas.';

COMMENT ON FUNCTION validate_deployed_model_version() IS
    'Verifica version/artifact/hash/tamaño/threshold; active exige versión aprobada y artifact disponible.';

COMMENT ON FUNCTION validate_image_analysis_job() IS
    'Valida run inference, deployment/version y threshold congelado para jobs gobernados.';
