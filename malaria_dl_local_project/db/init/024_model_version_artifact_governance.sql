-- Identidad inmutable de versiones y ownership entre training, version y bytes.
-- Las columnas históricas checkpoint_path/final_model_path/best_model_path se
-- conservan; checkpoint_artifact_id + SHA-256 son la identidad gobernada.

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS model_name TEXT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS version_number INTEGER;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS checkpoint_artifact_id UUID;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS artifact_uri TEXT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS artifact_sha256 TEXT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS artifact_size_bytes BIGINT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS artifact_hash_reuse_justification TEXT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS framework TEXT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS framework_version TEXT;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS preprocessing_profile_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS class_mapping JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS input_signature JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS output_signature JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'discovered';

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS lineage_status TEXT NOT NULL DEFAULT 'unresolved';

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS validated_at TIMESTAMPTZ;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;

ALTER TABLE model_versions
    ADD COLUMN IF NOT EXISTS retired_at TIMESTAMPTZ;

ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS artifact_uri TEXT;

ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS artifact_status TEXT;

-- Las filas previas al cutover no se declaran disponibles sin verificar bytes.
UPDATE artifacts
SET artifact_status = 'unknown'
WHERE artifact_status IS NULL;

ALTER TABLE artifacts
    ALTER COLUMN artifact_status SET DEFAULT 'available';

ALTER TABLE artifacts
    ALTER COLUMN artifact_status SET NOT NULL;

ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

ALTER TABLE run_checkpoint_policy
    ADD COLUMN IF NOT EXISTS model_version_id UUID;

ALTER TABLE run_checkpoint_policy
    ADD COLUMN IF NOT EXISTS checkpoint_artifact_id UUID;

ALTER TABLE run_threshold_calibration
    ADD COLUMN IF NOT EXISTS model_version_id UUID;

ALTER TABLE run_threshold_calibration
    ADD COLUMN IF NOT EXISTS calibration_artifact_id UUID;

ALTER TABLE run_threshold_calibration
    ADD COLUMN IF NOT EXISTS score_name TEXT NOT NULL DEFAULT 'probability_parasitized';

ALTER TABLE run_threshold_calibration
    ADD COLUMN IF NOT EXISTS label_mapping_version TEXT NOT NULL DEFAULT 'clinical_v1_parasitized_positive';

ALTER TABLE run_threshold_calibration
    ADD COLUMN IF NOT EXISTS positive_label TEXT NOT NULL DEFAULT 'parasitized';

ALTER TABLE run_threshold_calibration
    ADD COLUMN IF NOT EXISTS calibration_status TEXT NOT NULL DEFAULT 'recorded';

-- CHECK no dispone de IF NOT EXISTS en PostgreSQL; los bloques consultan el
-- catálogo para que la migración también sea segura al ejecutarse directamente.
DO $constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_status'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_status
            CHECK (
                status IN (
                    'discovered',
                    'candidate',
                    'validated',
                    'approved',
                    'deployed',
                    'rejected',
                    'retired'
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_lineage_status'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_lineage_status
            CHECK (
                lineage_status IN (
                    'unresolved',
                    'resolved',
                    'ambiguous',
                    'artifact_missing',
                    'checksum_mismatch',
                    'legacy_unresolved'
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_resolved_training'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_resolved_training
            CHECK (lineage_status <> 'resolved' OR training_run_id IS NOT NULL)
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_governed_hash'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_governed_hash
            CHECK (
                status NOT IN (
                    'candidate', 'validated', 'approved', 'deployed',
                    'rejected', 'retired'
                )
                OR (
                    checkpoint_artifact_id IS NOT NULL
                    AND artifact_sha256 IS NOT NULL
                )
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_sha256'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_sha256
            CHECK (
                artifact_sha256 IS NULL
                OR artifact_sha256 ~ '^[0-9a-f]{64}$'
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_artifact_size'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_artifact_size
            CHECK (artifact_size_bytes IS NULL OR artifact_size_bytes >= 0)
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_version_number'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_version_number
            CHECK (version_number IS NULL OR version_number > 0)
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_profile_objects'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_profile_objects
            CHECK (
                jsonb_typeof(preprocessing_profile_snapshot) = 'object'
                AND jsonb_typeof(class_mapping) = 'object'
                AND jsonb_typeof(input_signature) = 'object'
                AND jsonb_typeof(output_signature) = 'object'
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'chk_model_versions_artifact_requires_training'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT chk_model_versions_artifact_requires_training
            CHECK (checkpoint_artifact_id IS NULL OR training_run_id IS NOT NULL)
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'artifacts'::regclass
          AND conname = 'chk_artifacts_governance_status'
    ) THEN
        ALTER TABLE artifacts
            ADD CONSTRAINT chk_artifacts_governance_status
            CHECK (
                artifact_status IN (
                    'unknown', 'available', 'missing', 'mutated', 'archived'
                )
            )
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_threshold_calibration'::regclass
          AND conname = 'chk_run_threshold_calibration_score_name'
    ) THEN
        ALTER TABLE run_threshold_calibration
            ADD CONSTRAINT chk_run_threshold_calibration_score_name
            CHECK (score_name = 'probability_parasitized') NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_threshold_calibration'::regclass
          AND conname = 'chk_run_threshold_calibration_positive_label'
    ) THEN
        ALTER TABLE run_threshold_calibration
            ADD CONSTRAINT chk_run_threshold_calibration_positive_label
            CHECK (positive_label = 'parasitized') NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_threshold_calibration'::regclass
          AND conname = 'chk_run_threshold_calibration_status'
    ) THEN
        ALTER TABLE run_threshold_calibration
            ADD CONSTRAINT chk_run_threshold_calibration_status
            CHECK (calibration_status IN ('recorded', 'validated', 'rejected', 'retired'))
            NOT VALID;
    END IF;
END;
$constraints$;

-- Claves candidatas para FKs compuestas de ownership. El UUID id sigue siendo
-- globalmente único; los pares hacen demostrable la pertenencia al run/artifact.
CREATE UNIQUE INDEX IF NOT EXISTS uq_artifacts_id_run_id
    ON artifacts(id, run_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_id_training_run
    ON model_versions(id, training_run_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_id_checkpoint_artifact
    ON model_versions(id, checkpoint_artifact_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_name_number
    ON model_versions(model_name, version_number)
    WHERE model_name IS NOT NULL AND version_number IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_training_version_name
    ON model_versions(training_run_id, version_name)
    WHERE training_run_id IS NOT NULL AND version_name IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_checkpoint_artifact
    ON model_versions(checkpoint_artifact_id)
    WHERE checkpoint_artifact_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_unjustified_sha256
    ON model_versions(artifact_sha256)
    WHERE artifact_sha256 IS NOT NULL
      AND NULLIF(BTRIM(artifact_hash_reuse_justification), '') IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_threshold_calibration_id_version
    ON run_threshold_calibration(run_threshold_calibration_id, model_version_id);

CREATE INDEX IF NOT EXISTS idx_model_versions_training_run
    ON model_versions(training_run_id);

CREATE INDEX IF NOT EXISTS idx_model_versions_model
    ON model_versions(model_id);

CREATE INDEX IF NOT EXISTS idx_model_versions_checkpoint_artifact
    ON model_versions(checkpoint_artifact_id);

CREATE INDEX IF NOT EXISTS idx_model_versions_sha256
    ON model_versions(artifact_sha256);

CREATE INDEX IF NOT EXISTS idx_model_versions_status_lineage
    ON model_versions(status, lineage_status);

CREATE INDEX IF NOT EXISTS idx_artifacts_checksum
    ON artifacts(checksum);

CREATE INDEX IF NOT EXISTS idx_artifacts_governance_status
    ON artifacts(artifact_status);

CREATE INDEX IF NOT EXISTS idx_artifacts_uri
    ON artifacts(artifact_uri)
    WHERE artifact_uri IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_run_lineage_model_version
    ON run_lineage(model_version_id);

CREATE INDEX IF NOT EXISTS idx_run_lineage_checkpoint_artifact
    ON run_lineage(checkpoint_artifact_id);

CREATE INDEX IF NOT EXISTS idx_run_checkpoint_policy_model_version
    ON run_checkpoint_policy(model_version_id);

CREATE INDEX IF NOT EXISTS idx_run_checkpoint_policy_artifact
    ON run_checkpoint_policy(checkpoint_artifact_id);

CREATE INDEX IF NOT EXISTS idx_run_threshold_calibration_model_version
    ON run_threshold_calibration(model_version_id);

CREATE INDEX IF NOT EXISTS idx_run_threshold_calibration_artifact
    ON run_threshold_calibration(calibration_artifact_id);

-- Las FKs se crean NOT VALID: comienzan a proteger escritores nuevos sin exigir
-- que cada fila legacy esté resuelta. 027 realiza backfill y validación separada.
DO $foreign_keys$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'model_versions'::regclass
          AND conname = 'fk_model_versions_checkpoint_artifact_owner'
    ) THEN
        ALTER TABLE model_versions
            ADD CONSTRAINT fk_model_versions_checkpoint_artifact_owner
            FOREIGN KEY (checkpoint_artifact_id, training_run_id)
            REFERENCES artifacts(id, run_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'fk_run_lineage_model_version_owner'
    ) THEN
        ALTER TABLE run_lineage
            ADD CONSTRAINT fk_run_lineage_model_version_owner
            FOREIGN KEY (model_version_id, parent_run_id)
            REFERENCES model_versions(id, training_run_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'fk_run_lineage_checkpoint_artifact_owner'
    ) THEN
        ALTER TABLE run_lineage
            ADD CONSTRAINT fk_run_lineage_checkpoint_artifact_owner
            FOREIGN KEY (checkpoint_artifact_id, parent_run_id)
            REFERENCES artifacts(id, run_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_lineage'::regclass
          AND conname = 'fk_run_lineage_version_artifact'
    ) THEN
        ALTER TABLE run_lineage
            ADD CONSTRAINT fk_run_lineage_version_artifact
            FOREIGN KEY (model_version_id, checkpoint_artifact_id)
            REFERENCES model_versions(id, checkpoint_artifact_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_checkpoint_policy'::regclass
          AND conname = 'fk_run_checkpoint_policy_model_version_owner'
    ) THEN
        ALTER TABLE run_checkpoint_policy
            ADD CONSTRAINT fk_run_checkpoint_policy_model_version_owner
            FOREIGN KEY (model_version_id, run_id)
            REFERENCES model_versions(id, training_run_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_checkpoint_policy'::regclass
          AND conname = 'fk_run_checkpoint_policy_artifact_owner'
    ) THEN
        ALTER TABLE run_checkpoint_policy
            ADD CONSTRAINT fk_run_checkpoint_policy_artifact_owner
            FOREIGN KEY (checkpoint_artifact_id, run_id)
            REFERENCES artifacts(id, run_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_checkpoint_policy'::regclass
          AND conname = 'fk_run_checkpoint_policy_version_artifact'
    ) THEN
        ALTER TABLE run_checkpoint_policy
            ADD CONSTRAINT fk_run_checkpoint_policy_version_artifact
            FOREIGN KEY (model_version_id, checkpoint_artifact_id)
            REFERENCES model_versions(id, checkpoint_artifact_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_threshold_calibration'::regclass
          AND conname = 'fk_run_threshold_calibration_model_version'
    ) THEN
        ALTER TABLE run_threshold_calibration
            ADD CONSTRAINT fk_run_threshold_calibration_model_version
            FOREIGN KEY (model_version_id)
            REFERENCES model_versions(id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_threshold_calibration'::regclass
          AND conname = 'fk_run_threshold_calibration_artifact_owner'
    ) THEN
        ALTER TABLE run_threshold_calibration
            ADD CONSTRAINT fk_run_threshold_calibration_artifact_owner
            FOREIGN KEY (calibration_artifact_id, run_id)
            REFERENCES artifacts(id, run_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;
END;
$foreign_keys$;

COMMENT ON COLUMN model_versions.checkpoint_artifact_id IS
    'Identidad gobernada de los bytes; checkpoint_path permanece únicamente como referencia histórica/operacional.';

COMMENT ON COLUMN model_versions.status IS
    'Estado funcional de la versión, separado del estado de resolución de linaje.';

COMMENT ON COLUMN model_versions.lineage_status IS
    'Estado de resolución de training run, artifact, path y checksum.';

COMMENT ON COLUMN model_versions.artifact_hash_reuse_justification IS
    'Justificación explícita y auditable cuando otra versión ya registra el mismo SHA-256.';

COMMENT ON COLUMN artifacts.artifact_status IS
    'Estado físico observado sin modificar el checksum histórico: available, missing, mutated o archived.';
