-- Disponibilidad técnica, no clínica, de versiones inmutables para Etapa 2.
-- La publicación referencia la identidad gobernada existente; no copia ni
-- modifica artefactos y admite múltiples candidatos activos.

CREATE TABLE IF NOT EXISTS stage2_model_publications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    datasource TEXT NOT NULL,
    model_version_id UUID NOT NULL,
    training_run_id UUID NOT NULL,
    evaluation_run_id UUID NOT NULL,
    checkpoint_artifact_id UUID NOT NULL,
    scope TEXT NOT NULL DEFAULT 'stage2',
    status TEXT NOT NULL DEFAULT 'active',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_by TEXT NULL,
    deactivated_at TIMESTAMPTZ NULL,
    deactivated_by TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT fk_stage2_publication_version_artifact
        FOREIGN KEY (model_version_id, checkpoint_artifact_id)
        REFERENCES model_versions(id, checkpoint_artifact_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_stage2_publication_training
        FOREIGN KEY (training_run_id) REFERENCES runs(id) ON DELETE RESTRICT,
    CONSTRAINT fk_stage2_publication_evaluation
        FOREIGN KEY (evaluation_run_id) REFERENCES runs(id) ON DELETE RESTRICT,
    CONSTRAINT chk_stage2_publication_scope CHECK (scope = 'stage2'),
    CONSTRAINT chk_stage2_publication_status CHECK (status IN ('active', 'inactive')),
    CONSTRAINT chk_stage2_publication_state CHECK (
        (status = 'active' AND is_active AND deactivated_at IS NULL)
        OR (status = 'inactive' AND NOT is_active AND deactivated_at IS NOT NULL)
    ),
    CONSTRAINT chk_stage2_publication_metadata CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_stage2_publication_active_version
    ON stage2_model_publications(model_version_id, scope)
    WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_stage2_publication_candidates
    ON stage2_model_publications(datasource, scope, is_active, published_at DESC);

CREATE TABLE IF NOT EXISTS stage2_model_publication_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_id UUID NOT NULL REFERENCES stage2_model_publications(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL,
    actor TEXT NULL,
    event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version_id UUID NOT NULL,
    training_run_id UUID NOT NULL,
    evaluation_run_id UUID NOT NULL,
    datasource TEXT NOT NULL,
    previous_status TEXT NULL,
    new_status TEXT NOT NULL,
    reason TEXT NULL,
    correlation_id TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_stage2_publication_event_type CHECK (
        event_type IN (
            'MODEL_STAGE2_PUBLISHED',
            'MODEL_STAGE2_DEACTIVATED',
            'MODEL_STAGE2_REACTIVATED'
        )
    ),
    CONSTRAINT chk_stage2_publication_event_status CHECK (
        new_status IN ('active', 'inactive')
        AND (previous_status IS NULL OR previous_status IN ('active', 'inactive'))
    ),
    CONSTRAINT chk_stage2_publication_event_metadata CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_stage2_publication_events_publication
    ON stage2_model_publication_events(publication_id, event_at);

CREATE OR REPLACE FUNCTION prevent_stage2_publication_event_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $function$
BEGIN
    RAISE EXCEPTION 'stage2_model_publication_events es append-only';
END;
$function$;

DROP TRIGGER IF EXISTS trg_stage2_publication_events_append_only
    ON stage2_model_publication_events;
CREATE TRIGGER trg_stage2_publication_events_append_only
BEFORE UPDATE OR DELETE ON stage2_model_publication_events
FOR EACH ROW EXECUTE FUNCTION prevent_stage2_publication_event_mutation();

COMMENT ON TABLE stage2_model_publications IS
    'Disponibilidad técnica reversible de una model_version inmutable para nuevos trabajos de Etapa 2.';
COMMENT ON TABLE stage2_model_publication_events IS
    'Historial append-only de publicación, baja y reactivación de candidatos de Etapa 2.';
