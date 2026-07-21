-- Este script es el último de la secuencia de gobernanza.
-- 1. Ejecuta un backfill conservador y auditable.
-- 2. Valida las constraints creadas como NOT VALID en migraciones anteriores.
-- 3. Reemplaza políticas de borrado destructivas por RESTRICT.

-- El backfill real se implementa en Python y se ejecuta por separado.
-- Esta sección es un marcador de posición para el plan de ejecución.
-- REGLAS DE BACKFILL:
-- - model_versions: por same_training_run_exact_checkpoint_path_valid_sha256_unique.
-- - run_lineage: por parent_training_run_exact_checkpoint_path_version_artifact_sha256_unique.
-- - No se debe elegir "el último" ni asociar por basename.
-- - Cada cambio se registra en model_governance_backfill_audit.

-- Después de un backfill exitoso, se validan las constraints.
-- Si una fila histórica incumple una regla, VALIDATE fallará y la migración
-- transaccional se revertirá, exigiendo investigar la anomalía.
-- El runner de init_db.py ejecuta esto dentro de una transacción.

-- VALIDATE CONSTRAINT model_versions_chk_model_versions_status;
-- VALIDATE CONSTRAINT model_versions_chk_model_versions_lineage_status;
-- ... (y así para todas las constraints NOT VALID)

-- Reemplazo de políticas de borrado peligrosas.
-- Esto protege el linaje contra borrados en cascada accidentales.

-- En model_versions:
-- training_run_id: de SET NULL a RESTRICT
-- model_id: de CASCADE a RESTRICT
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'model_versions_training_run_id_fkey' AND confdeltype <> 'r') THEN
        ALTER TABLE model_versions DROP CONSTRAINT model_versions_training_run_id_fkey;
        ALTER TABLE model_versions ADD CONSTRAINT model_versions_training_run_id_fkey
            FOREIGN KEY (training_run_id) REFERENCES runs(id) ON DELETE RESTRICT;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'model_versions_model_id_fkey' AND confdeltype <> 'r') THEN
        ALTER TABLE model_versions DROP CONSTRAINT model_versions_model_id_fkey;
        ALTER TABLE model_versions ADD CONSTRAINT model_versions_model_id_fkey
            FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT;
    END IF;
END;
$$;

-- En run_lineage:
-- parent_run_id: de CASCADE a RESTRICT
-- child_run_id: de CASCADE a RESTRICT
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'run_lineage_parent_run_id_fkey' AND confdeltype <> 'r') THEN
        ALTER TABLE run_lineage DROP CONSTRAINT run_lineage_parent_run_id_fkey;
        ALTER TABLE run_lineage ADD CONSTRAINT run_lineage_parent_run_id_fkey
            FOREIGN KEY (parent_run_id) REFERENCES runs(id) ON DELETE RESTRICT;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'run_lineage_child_run_id_fkey' AND confdeltype <> 'r') THEN
        ALTER TABLE run_lineage DROP CONSTRAINT run_lineage_child_run_id_fkey;
        ALTER TABLE run_lineage ADD CONSTRAINT run_lineage_child_run_id_fkey
            FOREIGN KEY (child_run_id) REFERENCES runs(id) ON DELETE RESTRICT;
    END IF;
END;
$$;