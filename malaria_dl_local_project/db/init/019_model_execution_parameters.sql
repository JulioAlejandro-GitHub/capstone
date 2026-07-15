-- Tracking incremental de ejecuciones parametrizadas de modelos.
-- La migracion conserva las columnas historicas runs.parameters y
-- training_history.loss/accuracy para compatibilidad con scripts existentes.

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS execution_type TEXT;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS execution_parameters JSONB;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS fine_tuning_start_epoch INTEGER;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS total_epochs INTEGER;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS completed_epochs INTEGER;

-- Copia inicial no destructiva: los runs previos ya guardaban sus argumentos
-- en parameters. Solo se completan filas que aun no tienen el nuevo payload.
UPDATE runs
SET execution_parameters = COALESCE(parameters, '{}'::jsonb)
WHERE execution_parameters IS NULL;

UPDATE runs
SET completed_epochs = 0
WHERE completed_epochs IS NULL;

ALTER TABLE runs
    ALTER COLUMN execution_parameters SET DEFAULT '{}'::jsonb;

ALTER TABLE runs
    ALTER COLUMN execution_parameters SET NOT NULL;

ALTER TABLE runs
    ALTER COLUMN completed_epochs SET DEFAULT 0;

ALTER TABLE runs
    ALTER COLUMN completed_epochs SET NOT NULL;

ALTER TABLE training_history
    ADD COLUMN IF NOT EXISTS phase TEXT;

ALTER TABLE training_history
    ADD COLUMN IF NOT EXISTS train_loss NUMERIC;

ALTER TABLE training_history
    ADD COLUMN IF NOT EXISTS train_accuracy NUMERIC;

-- Recupera la fase que versiones anteriores guardaban dentro de metadata y
-- materializa aliases claros para las metricas de entrenamiento.
UPDATE training_history
SET phase = COALESCE(NULLIF(metadata->>'phase', ''), 'training')
WHERE phase IS NULL;

UPDATE training_history
SET train_loss = loss
WHERE train_loss IS NULL
  AND loss IS NOT NULL;

UPDATE training_history
SET train_accuracy = accuracy
WHERE train_accuracy IS NULL
  AND accuracy IS NOT NULL;

ALTER TABLE training_history
    ALTER COLUMN phase SET DEFAULT 'training';

ALTER TABLE training_history
    ALTER COLUMN phase SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_runs_execution_type
    ON runs(execution_type);

CREATE INDEX IF NOT EXISTS idx_runs_execution_parameters_gin
    ON runs USING GIN(execution_parameters);

CREATE INDEX IF NOT EXISTS idx_training_history_run_phase_epoch
    ON training_history(run_id, phase, epoch);

COMMENT ON COLUMN runs.execution_type IS
    'Tipo canonico de ejecucion: train_base, fine_tuning, train_combined, evaluate, threshold_calibration, explainability, inference, tta o ensemble.';

COMMENT ON COLUMN runs.execution_parameters IS
    'Snapshot JSONB de los parametros efectivos recibidos para la ejecucion.';

COMMENT ON COLUMN runs.fine_tuning_start_epoch IS
    'Epoca limite usada para marcar visualmente el inicio de fine-tuning (base completada - 1); NULL cuando no aplica.';

COMMENT ON COLUMN runs.total_epochs IS
    'Cantidad total de epocas planificadas para la ejecucion.';

COMMENT ON COLUMN runs.completed_epochs IS
    'Cantidad de epocas efectivamente persistidas o completadas.';

COMMENT ON COLUMN training_history.phase IS
    'Fase canónica de la época, por ejemplo train_base o fine_tuning.';

COMMENT ON COLUMN training_history.train_loss IS
    'Alias explicito de loss para consumo de reportes combinados.';

COMMENT ON COLUMN training_history.train_accuracy IS
    'Alias explicito de accuracy para consumo de reportes combinados.';
