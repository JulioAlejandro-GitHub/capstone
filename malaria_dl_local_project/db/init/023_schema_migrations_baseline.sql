-- Baseline administrativo para migraciones y backfills de gobierno.
-- scripts/init_db.py crea schema_migrations antes de recorrer los SQL; esta
-- definición equivalente permite ejecutar este archivo directamente.

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_schema_migrations_checksum_sha256
        CHECK (checksum ~ '^[0-9a-f]{64}$')
);

COMMENT ON TABLE schema_migrations IS
    'Ledger de migraciones SQL aplicadas; el checksum impide editar retrospectivamente una migración registrada.';

CREATE TABLE IF NOT EXISTS model_governance_backfill_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    reversal_of_audit_id UUID NULL,
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    before_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    after_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolution_rule TEXT NOT NULL,
    candidate_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    result_status TEXT NOT NULL,
    event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor TEXT NOT NULL DEFAULT CURRENT_USER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT fk_model_governance_audit_reversal
        FOREIGN KEY (reversal_of_audit_id)
        REFERENCES model_governance_backfill_audit(id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_model_governance_audit_event_type
        CHECK (event_type IN ('apply', 'revert')),
    CONSTRAINT chk_model_governance_audit_reversal
        CHECK (
            (event_type = 'apply' AND reversal_of_audit_id IS NULL)
            OR (event_type = 'revert' AND reversal_of_audit_id IS NOT NULL)
        ),
    CONSTRAINT chk_model_governance_audit_result_status
        CHECK (
            result_status IN (
                'applied',
                'reverted',
                'exact',
                'ambiguous',
                'missing',
                'checksum_mismatch',
                'skipped'
            )
        ),
    CONSTRAINT chk_model_governance_audit_before_object
        CHECK (jsonb_typeof(before_values) = 'object'),
    CONSTRAINT chk_model_governance_audit_after_object
        CHECK (jsonb_typeof(after_values) = 'object'),
    CONSTRAINT chk_model_governance_audit_metadata_object
        CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_model_governance_audit_batch
    ON model_governance_backfill_audit(batch_id, event_at);

CREATE INDEX IF NOT EXISTS idx_model_governance_audit_record
    ON model_governance_backfill_audit(table_name, record_id, event_at);

CREATE INDEX IF NOT EXISTS idx_model_governance_audit_reversal
    ON model_governance_backfill_audit(reversal_of_audit_id)
    WHERE reversal_of_audit_id IS NOT NULL;

COMMENT ON TABLE model_governance_backfill_audit IS
    'Bitácora append-only de atribuciones exactas y sus reversiones explícitas; nunca se actualizan ni eliminan eventos previos.';

COMMENT ON COLUMN model_governance_backfill_audit.candidate_ids IS
    'Identificadores considerados por la regla; un evento exacto conserva tanto version como artifact cuando corresponde.';

CREATE OR REPLACE FUNCTION prevent_model_governance_audit_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION
        'model_governance_backfill_audit es append-only; registre un evento revert en lugar de %',
        TG_OP
        USING ERRCODE = '55000';
END;
$function$;

DO $block$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgrelid = 'model_governance_backfill_audit'::regclass
          AND tgname = 'trg_model_governance_audit_append_only'
          AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER trg_model_governance_audit_append_only
        BEFORE UPDATE OR DELETE ON model_governance_backfill_audit
        FOR EACH ROW
        EXECUTE FUNCTION prevent_model_governance_audit_mutation();
    END IF;
END;
$block$;
