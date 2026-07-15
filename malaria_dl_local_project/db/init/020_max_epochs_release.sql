-- Release Max Epochs: resumen reproducible de seleccion por validation.
-- Migracion incremental e idempotente que no elimina ni reemplaza datos previos.

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS max_epochs INTEGER;

-- completed_epochs fue introducida en 019. Se declara de nuevo para que esta
-- migracion tambien sea segura en instalaciones que no hayan aplicado 019.
ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS completed_epochs INTEGER;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS stopped_epoch INTEGER;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS best_epoch INTEGER;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS checkpoint_monitor TEXT;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS checkpoint_mode TEXT;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS best_validation_value DOUBLE PRECISION;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS early_stopping_enabled BOOLEAN;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS early_stopping_patience INTEGER;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS early_stopping_min_delta DOUBLE PRECISION;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS restore_best_weights BOOLEAN;

COMMENT ON COLUMN runs.max_epochs IS
    'Presupuesto maximo de epocas base recibido mediante --max-epochs (o --epochs legado); los maximos por fase y total se conservan en execution_parameters.';

COMMENT ON COLUMN runs.completed_epochs IS
    'Cantidad total de epocas efectivamente completadas por la ejecucion.';

COMMENT ON COLUMN runs.stopped_epoch IS
    'Epoca 1-based en que termino el entrenamiento, incluida una detencion temprana cuando aplica.';

COMMENT ON COLUMN runs.best_epoch IS
    'Mejor epoca 1-based seleccionada exclusivamente con metricas de validation.';

COMMENT ON COLUMN runs.checkpoint_monitor IS
    'Metrica de validation usada para seleccionar el mejor checkpoint.';

COMMENT ON COLUMN runs.checkpoint_mode IS
    'Direccion de optimizacion del checkpoint monitor: min o max.';

COMMENT ON COLUMN runs.best_validation_value IS
    'Valor del checkpoint monitor en la mejor epoca de validation.';

COMMENT ON COLUMN runs.early_stopping_enabled IS
    'Indica si EarlyStopping estuvo habilitado para la ejecucion.';

COMMENT ON COLUMN runs.early_stopping_patience IS
    'Numero de epocas sin mejora permitido por EarlyStopping.';

COMMENT ON COLUMN runs.early_stopping_min_delta IS
    'Mejora minima requerida por EarlyStopping.';

COMMENT ON COLUMN runs.restore_best_weights IS
    'Indica si EarlyStopping restauro los pesos correspondientes a su mejor epoca.';
