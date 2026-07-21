-- Representa una revisión auditable de un modelo autorizado para inferencia.
-- Cada promoción o rollback crea una nueva fila inmutable.
CREATE TABLE IF NOT EXISTS deployed_model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID NOT NULL,
    checkpoint_artifact_id UUID NOT NULL,
    threshold_calibration_id UUID,
    deployment_name TEXT NOT NULL,
    environment TEXT NOT NULL,
    alias TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    artifact_size_bytes BIGINT,
    threshold_value NUMERIC NOT NULL,
    threshold_profile_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    preprocessing_profile_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    image_quality_policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    label_mapping_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    positive_label TEXT NOT NULL DEFAULT 'parasitized',
    score_name TEXT NOT NULL DEFAULT 'probability_parasitized',
    status TEXT NOT NULL DEFAULT 'pending',
    supersedes_deployment_id UUID,
    rollback_of_deployment_id UUID,
    deployed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    deployed_by TEXT,
    retired_by TEXT,
    deployment_reason TEXT,
    retirement_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE deployed_model_versions IS
    'Revisiones auditables de modelos autorizados para inferencia. Cada fila es un snapshot inmutable.';

-- Tabla puente para vincular un inference run con el/los deployment(s) usados.
-- Soporta ensembles mediante el campo `role`.
CREATE TABLE IF NOT EXISTS run_model_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    deployed_model_version_id UUID NOT NULL,
    model_version_id UUID NOT NULL,
    role TEXT NOT NULL DEFAULT 'primary',
    ordinal INTEGER NOT NULL DEFAULT 0,
    weight NUMERIC,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE run_model_deployments IS
    'Vínculo auditable entre un inference run y el deployment (o deployments, en un ensemble) que utilizó.';

DO $constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'deployed_model_versions'::regclass
          AND conname = 'chk_deployed_model_versions_status'
    ) THEN
        ALTER TABLE deployed_model_versions
            ADD CONSTRAINT chk_deployed_model_versions_status
            CHECK (status IN ('pending', 'active', 'inactive', 'retired', 'failed'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'deployed_model_versions'::regclass
          AND conname = 'chk_deployed_model_versions_names'
    ) THEN
        ALTER TABLE deployed_model_versions
            ADD CONSTRAINT chk_deployed_model_versions_names
            CHECK (deployment_name <> '' AND environment <> '' AND alias <> '');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'deployed_model_versions'::regclass
          AND conname = 'chk_deployed_model_versions_sha256'
    ) THEN
        ALTER TABLE deployed_model_versions
            ADD CONSTRAINT chk_deployed_model_versions_sha256
            CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'deployed_model_versions'::regclass
          AND conname = 'chk_deployed_model_versions_threshold'
    ) THEN
        ALTER TABLE deployed_model_versions
            ADD CONSTRAINT chk_deployed_model_versions_threshold
            CHECK (threshold_value >= 0 AND threshold_value <= 1);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'deployed_model_versions'::regclass
          AND conname = 'chk_deployed_model_versions_clinical_convention'
    ) THEN
        ALTER TABLE deployed_model_versions
            ADD CONSTRAINT chk_deployed_model_versions_clinical_convention
            CHECK (positive_label = 'parasitized' AND score_name = 'probability_parasitized');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'deployed_model_versions'::regclass
          AND conname = 'chk_deployed_model_versions_active_mapping'
    ) THEN
        ALTER TABLE deployed_model_versions
            ADD CONSTRAINT chk_deployed_model_versions_active_mapping
            CHECK (status <> 'active' OR label_mapping_snapshot = '{"0": "uninfected", "1": "parasitized"}'::jsonb);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'run_model_deployments'::regclass
          AND conname = 'chk_run_model_deployments_role'
    ) THEN
        ALTER TABLE run_model_deployments
            ADD CONSTRAINT chk_run_model_deployments_role
            CHECK (role IN ('primary', 'classifier', 'detector', 'ensemble_member', 'explainer'));
    END IF;
END;
$constraints$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_deployed_model_versions_active_slot
    ON deployed_model_versions(deployment_name, environment, alias)
    WHERE status = 'active';

CREATE UNIQUE INDEX IF NOT EXISTS uq_deployed_model_versions_id_version
    ON deployed_model_versions(id, model_version_id);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_model_version
    ON deployed_model_versions(model_version_id);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_checkpoint_artifact
    ON deployed_model_versions(checkpoint_artifact_id);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_threshold_calibration
    ON deployed_model_versions(threshold_calibration_id);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_slot_history
    ON deployed_model_versions(deployment_name, environment, alias, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_status
    ON deployed_model_versions(status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_model_deployments_binding
    ON run_model_deployments(run_id, role, ordinal);

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_model_deployments_run_deployment_version
    ON run_model_deployments(run_id, deployed_model_version_id, model_version_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_model_deployments_primary
    ON run_model_deployments(run_id)
    WHERE role = 'primary';

CREATE INDEX IF NOT EXISTS idx_run_model_deployments_deployment
    ON run_model_deployments(deployed_model_version_id);

CREATE INDEX IF NOT EXISTS idx_run_model_deployments_model_version
    ON run_model_deployments(model_version_id);

DO $foreign_keys$
BEGIN
    ALTER TABLE deployed_model_versions
        ADD CONSTRAINT fk_deployed_model_versions_version_artifact
        FOREIGN KEY (model_version_id, checkpoint_artifact_id)
        REFERENCES model_versions(id, checkpoint_artifact_id)
        ON DELETE RESTRICT;

    ALTER TABLE deployed_model_versions
        ADD CONSTRAINT fk_deployed_model_versions_threshold_version
        FOREIGN KEY (threshold_calibration_id, model_version_id)
        REFERENCES run_threshold_calibration(run_threshold_calibration_id, model_version_id)
        ON DELETE RESTRICT;

    ALTER TABLE run_model_deployments
        ADD CONSTRAINT fk_run_model_deployments_run
        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE RESTRICT;

    ALTER TABLE run_model_deployments
        ADD CONSTRAINT fk_run_model_deployments_deployment_version
        FOREIGN KEY (deployed_model_version_id, model_version_id)
        REFERENCES deployed_model_versions(id, model_version_id)
        ON DELETE RESTRICT;
END;
$foreign_keys$;