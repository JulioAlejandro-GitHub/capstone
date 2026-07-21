-- Ledger para registrar migraciones aplicadas y su checksum.
-- El runner de scripts/init_db.py lo utiliza para evitar reejecuciones
-- y detectar cambios en migraciones ya aplicadas.
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE schema_migrations
    ADD CONSTRAINT chk_schema_migrations_checksum_sha256
    CHECK (checksum ~ '^[0-9a-f]{64}$');

COMMENT ON TABLE schema_migrations IS
    'Ledger administrativo de migraciones SQL aplicadas, con checksum SHA-256 del archivo.';

-- Tabla append-only para registrar cada atribución o reversión del backfill.
-- Esto hace que el proceso sea auditable y reversible sin depender de logs.
CREATE TABLE IF NOT EXISTS model_governance_backfill_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    reversal_of_audit_id UUID,
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    before_values JSONB NOT NULL,
    after_values JSONB NOT NULL,
    resolution_rule TEXT NOT NULL,
    candidate_ids UUID[] NOT NULL,
    result_status TEXT NOT NULL,
    event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_model_governance_audit_batch
    ON model_governance_backfill_audit(batch_id, event_at);

CREATE INDEX IF NOT EXISTS idx_model_governance_audit_record
    ON model_governance_backfill_audit(table_name, record_id, event_at);

CREATE INDEX IF NOT EXISTS idx_model_governance_audit_reversal
    ON model_governance_backfill_audit(reversal_of_audit_id)
    WHERE reversal_of_audit_id IS NOT NULL;

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT fk_model_governance_audit_reversal
    FOREIGN KEY (reversal_of_audit_id)
    REFERENCES model_governance_backfill_audit(id)
    ON DELETE RESTRICT;

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT chk_model_governance_audit_event_type
    CHECK (event_type IN ('apply', 'revert'));

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT chk_model_governance_audit_result_status
    CHECK (result_status IN ('applied', 'reverted', 'exact', 'ambiguous', 'missing', 'checksum_mismatch', 'skipped'));

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT chk_model_governance_audit_before_object
    CHECK (jsonb_typeof(before_values) = 'object');

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT chk_model_governance_audit_after_object
    CHECK (jsonb_typeof(after_values) = 'object');

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT chk_model_governance_audit_metadata_object
    CHECK (jsonb_typeof(metadata) = 'object');

ALTER TABLE model_governance_backfill_audit
    ADD CONSTRAINT chk_model_governance_audit_reversal
    CHECK (
        (event_type = 'revert' AND reversal_of_audit_id IS NOT NULL)
        OR (event_type <> 'revert' AND reversal_of_audit_id IS NULL)
    );

COMMENT ON TABLE model_governance_backfill_audit IS
    'Bitácora append-only de atribuciones y reversiones del backfill de gobernanza.';