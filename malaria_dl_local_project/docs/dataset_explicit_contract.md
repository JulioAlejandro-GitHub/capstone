# Dataset explícito — Etapa 1

Contrato de uso para nuevas ejecuciones. No acredita el estado actual de una
versión operativa; el UUID debe ser designado por el responsable de la ejecución.

## Entradas

Desde `malaria_dl_local_project`, con el entorno existente y PostgreSQL autorizado
por Compose (`db:5432`):

```sh
# Sustituya el marcador por el UUID designado; no es un valor por defecto.
DATASET_VERSION_ID='<UUID designado>'
python -m src.train --model custom_cnn --dataset-version-id "$DATASET_VERSION_ID" --track-db
python run_train_all_models.py --dataset-version-id "$DATASET_VERSION_ID"
python run_train_all_models.py --dataset-version-id "$DATASET_VERSION_ID" --dry-run
python run_evaluate_all_trainings.py --dataset-version-id "$DATASET_VERSION_ID"
python run_explain_all_trainings.py --dataset-version-id "$DATASET_VERSION_ID"
```

Los ejemplos no ordenan ejecutar una campaña durante la auditoría. Se mantienen
los parámetros de modelos y TEST existentes; su protocolo científico se cierra
en etapas posteriores.

TRAIN y los tres ejecutores masivos rechazan UUID ausente, vacío o malformado.
Los UUID se normalizan. No se completa el identificador desde entorno, fecha ni
ruta legacy. `resolve_governed_dataset(None)` también falla programáticamente.

Para EVALUATE/EXPLAIN individuales, el dataset se hereda del TRAIN de la versión:

```sh
MODEL_VERSION_ID='<UUID de la versión exacta>'
python -m src.evaluate --model-version-id "$MODEL_VERSION_ID" --require-lineage --track-db
python -m src.explain --model-version-id "$MODEL_VERSION_ID" --method all --require-lineage --track-db
```

Se puede añadir `--dataset-version-id "$DATASET_VERSION_ID"` como comprobación,
pero debe coincidir con el padre. Un TRAIN sin UUID o snapshot completo acreditado
bloquea nueva ejecución gobernada; sus resultados históricos permanecen consultables.

`--dataset-dir` queda como comprobación opcional: sólo se acepta la raíz exacta de
la materialización. Si se omite, se usa la raíz gobernada. No se acepta una ruta
legacy distinta, aunque contenga archivos iguales. `--data-source tfds` no reemplaza
el dataset de TRAIN/EVALUATE/EXPLAIN. El helper general de datos y los flujos legacy
ajenos a esta etapa no se han eliminado.

## Verificación y persistencia

El consumidor verifica FROZEN, últimos checks requeridos PASS y ausencia de otros
checks bloqueantes FAIL. Consulta la materialización por el UUID del sello, no
por fecha: debe pertenecer a la versión, estar READY/PASS y tener raíz accesible.

Se recalculan las cuatro huellas con las reglas de `malaria_split` freeze v1:
asignaciones sin salto final, población/identidades con salto final por fila.
Los SHA-256 de los bytes consumidos se contrastan con los registros fuente, que
forman parte de la huella de población sellada. La ruta de cada archivo sigue la
regla upstream de prefijo por source_record_id ante colisiones de nombre. Se
rechazan archivos ausentes, inesperados, alterados y rutas fuera de la raíz.
No se generan asignaciones, materializaciones ni hashes esperados nuevos.

La función `resolve_governed_dataset` realiza sólo lectura (transacción
REPEATABLE READ READ ONLY). Los entrypoints operativos llaman
`verify_dataset_for_execution`, que además registra la evidencia en PostgreSQL.
No confundir el resolver de lectura con un preflight operativo persistido.

Se reutiliza `audit_events` del esquema vigente, con evento
`ml.dataset_verification`. `after_state` conserva snapshot, versión del verificador,
estado, consumidor, TRAIN padre si aplica y referencia de evidencia del lote.
Los rechazos verificables también se registran; UUID sintácticamente inválido se
rechaza antes de conectar. No se guarda ningún CSV ni JSON lateral de evidencia.
La escritura debe hacer commit y superar lectura posterior de igualdad; error de
BD o round-trip bloquea la operación. Sin conexión no se puede registrar el rechazo:
se devuelve `DATASET_EVIDENCE_PERSISTENCE_FAILED`, sin fallback de archivo.

Esta evidencia es obligatoria incluso si no se usa `--track-db`. Con tracking, el
run queda vinculado mediante `runs.metadata.dataset_verification_evidence_id`;
si no se logra vincular, no comienza fit/predict. Sin tracking, la evidencia
permanece identificada como auditoría de esa invocación, no como TRAIN registrado.
Los escritores legacy de historia/métricas quedan pendientes de etapas posteriores;
no se usan para recuperar esta nueva evidencia.

El lote TRAIN verifica una vez y obtiene el ID de evidencia. Propaga
`--expected-dataset-evidence-id` a cada hijo. Cada hijo vuelve a contrastar bytes,
identidad, raíz y huellas antes de consumir; no puede sustituir snapshot aunque
aparezca otra versión entrenable. No se ha creado `campaign_id`.
Los lotes EVALUATE/EXPLAIN filtran por ámbito UUID obligatorio y contrastan cada
TRAIN con el snapshot; mantienen sus mecanismos existentes de selección de
model_version, cuyo cierre de ambigüedad corresponde a Etapa 6.

## Dry-run

TRAIN dry-run valida la sintaxis del UUID y muestra comandos, sin consultar ni
escribir BD y sin ejecutar hijos. Declara **integridad NO VERIFICADA**.
EVALUATE/EXPLAIN dry-run necesitan lectura de inventario en BD, filtrada por UUID,
pero tampoco verifican contenido ni ejecutan hijos. Sin acceso a BD no hay inventario
ni preflight operativo aprobado. Ningún modo selecciona automáticamente un dataset.

## Pruebas y restricciones

`tests/test_dataset_stage1.py` usa filas sintéticas y bytes temporales; no conecta
a BD ni ejecuta entrenamientos/evaluaciones científicas. `test_dataset_evidence_postgres.py`
es opt-in dentro del entorno Compose autorizado (`RUN_STAGE1_POSTGRES_TESTS=1`):
escribe sólo eventos sintéticos dentro de una transacción externa revertida y
comprueba su ausencia después. No crea otra base ni modifica servicios.

No se han alterado constantes, datos o comandos del sistema split ni publicación
manual. La verificación es de preflight: el almacenamiento del dataset debe seguir
inmutable durante el consumo. No proporciona locks de filesystem contra un proceso
externo que modifique bytes después de verificarlos.
