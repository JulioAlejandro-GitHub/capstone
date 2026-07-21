-- Cada fila es una revisión auditable de deployment. El payload clínico se
-- congela aquí; promover o hacer rollback crea otra fila, nunca copia un model
-- file ni reactiva una revisión histórica.

CREATE TABLE IF NOT EXISTS deployed_model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID NOT NULL,
    checkpoint_artifact_id UUID NOT NULL,
    threshold_calibration_id UUID NULL,
    deployment_name TEXT NOT NULL,
    environment TEXT NOT NULL,
    alias TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    artifact_size_bytes BIGINT NULL,
    threshold_value NUMERIC NOT NULL,
    threshold_profile_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    preprocessing_profile_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    image_quality_policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    label_mapping_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    positive_label TEXT NOT NULL DEFAULT 'parasitized',
    score_name TEXT NOT NULL DEFAULT 'probability_parasitized',
    status TEXT NOT NULL DEFAULT 'pending',
    supersedes_deployment_id UUID NULL,
    rollback_of_deployment_id UUID NULL,
    deployed_at TIMESTAMPTZ NULL,
    retired_at TIMESTAMPTZ NULL,
    deployed_by TEXT NULL,
    retired_by TEXT NULL,
    deployment_reason TEXT NULL,
    retirement_reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT fk_deployed_model_versions_version_artifact
        FOREIGN KEY (model_version_id, checkpoint_artifact_id)
        REFERENCES model_versions(id, checkpoint_artifact_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_deployed_model_versions_threshold_version
        FOREIGN KEY (threshold_calibration_id, model_version_id)
        REFERENCES run_threshold_calibration(
            run_threshold_calibration_id,
            model_version_id
        )
        ON DELETE RESTRICT,
    CONSTRAINT fk_deployed_model_versions_supersedes
        FOREIGN KEY (supersedes_deployment_id)
        REFERENCES deployed_model_versions(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_deployed_model_versions_rollback
        FOREIGN KEY (rollback_of_deployment_id)
        REFERENCES deployed_model_versions(id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_deployed_model_versions_status
        CHECK (status IN ('pending', 'active', 'inactive', 'retired', 'failed')),
    CONSTRAINT chk_deployed_model_versions_names
        CHECK (
            BTRIM(deployment_name) <> ''
            AND BTRIM(environment) <> ''
            AND BTRIM(alias) <> ''
        ),
    CONSTRAINT chk_deployed_model_versions_sha256
        CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_deployed_model_versions_artifact_size
        CHECK (artifact_size_bytes IS NULL OR artifact_size_bytes >= 0),
    CONSTRAINT chk_deployed_model_versions_threshold
        CHECK (threshold_value >= 0 AND threshold_value <= 1),
    CONSTRAINT chk_deployed_model_versions_clinical_convention
        CHECK (
            positive_label = 'parasitized'
            AND score_name = 'probability_parasitized'
        ),
    CONSTRAINT chk_deployed_model_versions_snapshots
        CHECK (
            jsonb_typeof(threshold_profile_snapshot) = 'object'
            AND jsonb_typeof(preprocessing_profile_snapshot) = 'object'
            AND jsonb_typeof(image_quality_policy_snapshot) = 'object'
            AND jsonb_typeof(label_mapping_snapshot) = 'object'
            AND jsonb_typeof(metadata) = 'object'
        ),
    CONSTRAINT chk_deployed_model_versions_active_timestamps
        CHECK (
            status <> 'active'
            OR (
                deployed_at IS NOT NULL
                AND retired_at IS NULL
                AND NULLIF(BTRIM(deployed_by), '') IS NOT NULL
            )
        ),
    CONSTRAINT chk_deployed_model_versions_active_mapping
        CHECK (
            status <> 'active'
            OR label_mapping_snapshot @>
                '{"0":"uninfected","1":"parasitized"}'::jsonb
        ),
    CONSTRAINT chk_deployed_model_versions_retired_timestamp
        CHECK (status <> 'retired' OR retired_at IS NOT NULL),
    CONSTRAINT chk_deployed_model_versions_timestamp_order
        CHECK (
            retired_at IS NULL
            OR deployed_at IS NULL
            OR retired_at >= deployed_at
        ),
    CONSTRAINT chk_deployed_model_versions_distinct_history
        CHECK (
            (supersedes_deployment_id IS NULL OR supersedes_deployment_id <> id)
            AND (rollback_of_deployment_id IS NULL OR rollback_of_deployment_id <> id)
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_deployed_model_versions_id_version
    ON deployed_model_versions(id, model_version_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_deployed_model_versions_active_slot
    ON deployed_model_versions(deployment_name, environment, alias)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_model_version
    ON deployed_model_versions(model_version_id);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_checkpoint_artifact
    ON deployed_model_versions(checkpoint_artifact_id);

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_threshold_calibration
    ON deployed_model_versions(threshold_calibration_id)
    WHERE threshold_calibration_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_slot_history
    ON deployed_model_versions(
        deployment_name,
        environment,
        alias,
        created_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_deployed_model_versions_status
    ON deployed_model_versions(status, created_at DESC);

CREATE TABLE IF NOT EXISTS run_model_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    deployed_model_version_id UUID NOT NULL,
    model_version_id UUID NOT NULL,
    role TEXT NOT NULL DEFAULT 'primary',
    ordinal INTEGER NOT NULL DEFAULT 0,
    weight NUMERIC NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_run_model_deployments_run
        FOREIGN KEY (run_id)
        REFERENCES runs(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_run_model_deployments_deployment_version
        FOREIGN KEY (deployed_model_version_id, model_version_id)
        REFERENCES deployed_model_versions(id, model_version_id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_run_model_deployments_role
        CHECK (
            role IN (
                'primary',
                'classifier',
                'detector',
                'ensemble_member',
                'explainer'
            )
        ),
    CONSTRAINT chk_run_model_deployments_ordinal
        CHECK (ordinal >= 0),
    CONSTRAINT chk_run_model_deployments_weight
        CHECK (weight IS NULL OR (weight >= 0 AND weight <= 1)),
    CONSTRAINT chk_run_model_deployments_metadata
        CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_model_deployments_binding
    ON run_model_deployments(
        run_id,
        deployed_model_version_id,
        role,
        ordinal
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_model_deployments_run_deployment_version
    ON run_model_deployments(
        run_id,
        deployed_model_version_id,
        model_version_id
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_run_model_deployments_primary
    ON run_model_deployments(run_id)
    WHERE role = 'primary';

CREATE INDEX IF NOT EXISTS idx_run_model_deployments_deployment
    ON run_model_deployments(deployed_model_version_id);

CREATE INDEX IF NOT EXISTS idx_run_model_deployments_model_version
    ON run_model_deployments(model_version_id);

COMMENT ON TABLE deployed_model_versions IS
    'Revisión inmutable de una model_version autorizada con artifact, threshold y políticas congelados.';

COMMENT ON COLUMN deployed_model_versions.threshold_value IS
    'Umbral escalar congelado para decisiones de esta revisión; no se vuelve a resolver desde un sidecar mutable.';

COMMENT ON TABLE run_model_deployments IS
    'Puente entre runs de inferencia y uno o más deployments; soporta classifier/detector/ensembles sin duplicar runs.';
