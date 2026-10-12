# CAPSTONE EXEC.1 — Ejecución independiente e historial

Estado documental: `CURRENT_DOC`.
Fecha: 2026-10-12.
Estado técnico: implementado; validación con fixtures sintéticos. No acredita desempeño clínico.

## Inspección inicial y matriz de cambios

| Operación / entradas | Estado inicial | Cambio EXEC.1 |
| --- | --- | --- |
| TRAIN: script y módulo | Script por campaña; módulo por configuración; repetición continuaba miembros pendientes | Orquestador común por campaña y/o TRAIN de referencia, siempre con nuevo RUN |
| EVALUATE: script y módulo | Motor compartido; selección y argumentos distintos; reutilización de identidad | Selección común; VAL/development internos; ejecución independiente |
| EXPLAIN: script y módulo | Motor y persistencia existentes; selección distinta; reutilización | Misma selección; VAL/development; nuevos artefactos por ejecución |
| TEST: script y módulo | Entradas ausentes; bloqueos Python y PostgreSQL | Dos entradas al evaluador existente; TEST/final; sin autorización final |
| PostgreSQL | Tablas existentes suficientes; dos funciones exigían final lock | Solo retirar las dos condiciones administrativas; conservar triggers e integridad |
| Historial / SCC | Una tentativa visible por identidad; detalle por ID existente | Todos los intentos visibles, etiquetas TEST y selección explícita de evidencia |

TRAIN, EVALUATE y EXPLAIN conservan sus repositorios y motores. No se reconstruyó su persistencia ni se repitió una auditoría científica exhaustiva.

## Ocho comandos

Desde `malaria_dl_local_project`, usando el entorno Python local del proyecto:

```bash
python run_train_all_models.py --campaign-id "$CAMPAIGN_ID"
python run_evaluate_all_trainings.py --campaign-id "$CAMPAIGN_ID" --threshold 0.4
python run_explain_all_trainings.py --campaign-id "$CAMPAIGN_ID" --method gradcam --layer "$LAYER" --threshold 0.4
python run_test_all_models.py --campaign-id "$CAMPAIGN_ID" --threshold 0.4 --seed 11 --batch-size 64

python -m src.train --source-training-run-id "$TRAIN_ID"
python -m src.evaluate --source-training-run-id "$TRAIN_ID" --threshold 0.4
python -m src.explain --source-training-run-id "$TRAIN_ID" --method gradcam --layer "$LAYER" --threshold 0.4
python -m src.test --source-training-run-id "$TRAIN_ID" --threshold 0.4 --seed 11 --batch-size 64
```

Los identificadores son variables del usuario, no constantes del código. Cada script acepta exactamente la misma selección que su módulo. Ambos identificadores juntos comprueban pertenencia y ejecutan exclusivamente ese TRAIN. Sin identificadores se rechaza la petición. Una campaña selecciona todos sus TRAIN; no el último ni un único miembro aceptado.

TRAIN por campaña consume las configuraciones y semillas persistidas. TRAIN por Run-ID copia la configuración completa disponible, conserva `execution_parameters.source_training_run_id`, crea otro UUID y otro directorio de artefactos. Una configuración ausente/incompleta falla explícitamente; no se reconstruye mediante defaults.

`--dataset-version-id` es una aserción opcional. El dataset se resuelve desde PostgreSQL. `--inspect` consulta sin reservar trabajo; TRAIN también admite `--dry-run`/`--plan`.

Los antiguos argumentos públicos `--split`, `--purpose` y `--protocol` se sustituyen por valores internos. No existe una opción para convertir EVALUATE en TEST. EXPLAIN necesita método y sus parámetros técnicos. El umbral predeterminado `auto` recupera el valor registrado por TRAIN: calibración VAL válida cuando existe, o el valor fijo persistido cuando la calibración estaba desactivada. Si no hay evidencia suficiente, falla sin inventar un valor. `--threshold clinical` exige calibración VAL; un umbral numérico explícito tiene prioridad y no requiere EVALUATE ni EXPLAIN. Nunca se ajusta el umbral o el checkpoint con TEST.

## Separación y persistencia

Se consumen exclusivamente las rutas existentes `data/malaria_dataset_versions/<dataset_version_id>/{train,val,test}`. TRAIN abre TRAIN/VAL; EVALUATE y EXPLAIN abren VAL; TEST abre TEST. No se invoca Split ni se descargan, copian o modifican datasets.

`assessment.service.run` agrega un UUID de ejecución a la identidad antes de reservar. Repetir parámetros produce evidencia nueva; no selecciona un intento anterior. `assessment_attempts` conserva estado y fechas; `assessment_identities` conserva TRAIN, campaña, checkpoint/hash, dataset, preprocessing, split, propósito, umbral, seed y batch size. `assessment_results` guarda cada muestra, paciente, etiqueta, score, umbral y predicción. Los artefactos de EXPLAIN conservan directorios separados por intento.

La verificación TEST guarda count, TP/TN/FP/FN, accuracy, precision, recall, specificity, F1, F2, balanced accuracy, ROC-AUC y PR-AUC. Las tasas sin denominador y AUC sin ambas clases son `null`. PR-AUC conserva la definición de average precision del evaluador existente. Los hashes y métricas históricas VAL permanecen con su definición anterior.

La API conserva `/assessments/{attempt_id}`, `/results` y `/artifacts`. La lista permite filtrar TRAIN/campaña y paginar; muestra todos los intentos. La página de ejecuciones ofrece acceso individual al historial. Comparación de modelos permite seleccionar varias ejecuciones expresamente, sin seleccionar automáticamente la última o mezclar sus métricas. La ausencia de evidencia se representa explícitamente. No se implementaron análisis SCC avanzados adicionales.

## Ajuste PostgreSQL aplicado

Migración activa: `alembic_v2/versions/20261012_01_exec1.py`, revisión `exec1_independent_test`.

La inspección del PostgreSQL local demostró las condiciones `TEST_FINAL_LOCK_REQUIRED` en `assessment_attempt_guard()` y `v2_evaluation_complete()`. La migración reemplaza solo sus cuerpos, quitando esas condiciones. Mantiene la tabla `assessment_final_locks`, todos los triggers, constraints, reglas de propietario, transiciones, inmutabilidad e integridad relacional.

Aplicada al servicio Docker local `db`, base `malaria_experiments`, mediante:

```bash
python3 scripts/db/migrate_exec1.py --database malaria_experiments
```

El lanzador verifica el destino explícito y utiliza `alembic -c /app/alembic_v2.ini -x exec1=true upgrade exec1_independent_test`. No hay consulta de revisiones ni preflight de compatibilidad en los comandos de ejecución ML.

La comprobación anterior/posterior confirmó filas sin cambios: 15 RUN, 15 artefactos, 1 versión de modelo, 5 identidades, 5 intentos y 13.465 predicciones, además de publicaciones/despliegues. La primera solicitud automática fue rechazada por destino insuficientemente delimitado; se identificó la base mediante lectura y se incorporó la aserción de nombre antes de repetir la revisión. La segunda solicitud fue aceptada.

## Pruebas reproducibles

```bash
make test-exec1
make test-exec1-train-regression
make test-exec1-postgres
make test-exec1-backend
make test-exec1-frontend
```

La integración PostgreSQL utiliza **solo** `exec1-postgres/exec1_fixture`, creado mediante `docker-compose.exec1-test.yml`. Para preparar por primera vez una instancia vacía:

```bash
make prepare-exec1-postgres
```

La preparación copia únicamente DDL del esquema vigente; no copia datos. Se ejecuta una vez por instancia vacía. Las pruebas pueden repetirse y conservan sus registros sintéticos en esa instancia. No borran tablas ni registros. No se ejecutan migraciones históricas para crear fixtures. Las restricciones permanecen habilitadas.

La prueba de integración persiste cuatro predicciones sintéticas con TP=TN=FP=FN=1, realiza lectura confirmada desde otro PID PostgreSQL, repite TEST, compara intacta la primera ejecución y comprueba errores SQL reales. También verifica nuevos RUN de referencia, configuración conservada, directorios independientes, selección de todos los TRAIN de campaña, pertenencia incorrecta y campaña en estado draft sin bloqueo administrativo.

Resultados: 108 pruebas de comandos/inferencia/splits (incluida la corrección de umbral); 21 de regresión TRAIN; 3 PostgreSQL sintéticas; 20 backend/API; 268 frontend. Compilación TypeScript/Vite aprobada. Las advertencias de dependencias TensorFlow/SHAP y tamaño de bundle no impiden las pruebas.

## Archivos y justificación

- `execution/selection.py`, `execution/operations.py`: selección PostgreSQL común y adaptación TRAIN al motor existente.
- `src/{train,evaluate,explain,test}.py`, `run_train_all_models.py`, `run_test_all_models.py`: puntos de entrada comunes y carga perezosa para ayuda CLI.
- `assessment/{cli,service,contracts,repository}.py`, `data/governed_dataset.py`: operación fija, nuevo historial, métricas TEST y retiro del lock administrativo.
- `execution/{train,repository}.py`: conservar referencia de origen/campaña al crear otro TRAIN; devolver resultado verificado.
- `alembic_v2/{env,exec1}.py`, migración EXEC.1 y `scripts/db/{apply_exec1,migrate_exec1}.py`: ajuste transaccional acotado con comprobación de conservación histórica.
- Backend `repositories/{assessment_lineage,assessments}.py`, `services/assessments.py`, `routes/assessments.py`: historial completo y consulta por ID, separando rutas/servicio/repositorio.
- Frontend componentes `AssessmentComparison`, `AssessmentEvaluationCard`, páginas `AssessmentDetail`, `ModelComparison`, `Runs`, hook `useAssessmentChoices`, cliente API y tipos: selección explícita y métricas por ejecución. `RunSummaryRow` corrige el texto preexistente `No registrado 2`, detectado por regresión.
- Pruebas EXEC.1, suites de historial/splits, `Makefile`, compose y preparador de fixtures: evidencia automática reproducible sin experimentos reales.

## Límites

No se ejecutó TRAIN completo ni TEST sobre el dataset oficial. La validación acredita ejecución, persistencia e integridad del contrato mediante fixtures; no acredita rendimiento científico o clínico. El servicio PostgreSQL de fixtures permanece aislado en Docker para repetir las pruebas; no contiene evidencia oficial.

### Corrección de resolución de umbral (2026-10-12)

Se corrigió el valor predeterminado que exigía calibración aun cuando TRAIN había registrado un umbral fijo. Se añadieron regresiones para umbrales fijos (incluido cero), calibrados, evidencia ausente/inválida, prioridad numérica y TEST por campaña sin `--threshold`. La comprobación del TRAIN reportado fue de solo lectura: se recuperó 0,5 del checkpoint seleccionado (época 4). `make test-exec1`: 108 pruebas aprobadas. No se ejecutó TEST oficial.
