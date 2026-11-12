# Evidencia CAPSTONE-P3-03

Auditoría del 10 de noviembre de 2026 (America/Santiago). [Informe principal](../../../CAPSTONE_P3_03_AUDITORIA_ANALISIS_AUTOMATICO_Y_SOBREAJUSTE.md).

Solo se añadieron informes y artefactos de auditoría. No se ejecutaron entrenamientos, inferencias, evaluaciones nuevas, migraciones ni cambios PostgreSQL/modelo activo. Los cálculos usan registros y scores ya persistidos.

## Resultados de uso directo

| Archivo | Contenido |
|---|---|
| `auto_analysis_rows.csv` | Las 86 filas TRAIN y su categoría usando el helper original |
| `champion_metrics.csv` | Métricas VAL/TEST confirmadas; origen AUC explícito |
| `cohort_60.csv` | 60 entrenamientos comparables con IDs de evaluaciones, hashes, umbrales y brechas |
| `epoch_metrics.csv` | 2.425 épocas; columnas originales, ausencias conservadas |
| `per_run_indicators.csv` | Todos los 86 RUN, incluidos fallidos y zero-shot; checkpoint/final separados |
| `model_matrix.csv` | Resumen descriptivo de 12 RUN por modalidad |
| `optimizer_seed_summary.csv` | 20 grupos, tres semillas por modalidad/optimizador, media y SD ddof1 |
| `champion_curves.png/.pdf` | Curvas TRAIN/VAL; mínimo val_loss12, checkpoint20 y final32 |
| `cohort_gaps.png/.pdf` | Distribuciones de brechas TRAIN–VAL y VAL–TEST |
| `cohort_code_identity.csv` | Revisión Git distinta VAL/TEST; mismo digest de fuente y contrato completo |
| `cohort_population.json` | Coincidencia de población por split y asignaciones gobernadas |
| `checkpoint_hash_verification.json` | Tamaño y SHA-256 del checkpoint local activo |

`*_recall_gap` significa TRAIN−VAL a umbral0,5; `*_loss_gap` significa VAL−TRAIN; `val_minus_test_*` significa VAL−TEST al umbral efectivo congelado. `selected_*` es la época del checkpoint; `final_*`, la última época ejecutada. F2 TRAIN Keras es derivado de precision/recall, no persistido. Torch carece de Recall/F2 TRAIN.

La SD sobre 12 RUN de `model_matrix.csv` combina optimizadores y semillas: no es variabilidad exclusivamente por semilla. La tabla de 20 grupos es la fuente para esa pregunta. Las diferencias VAL–TEST no diagnostican automáticamente sobreajuste.

## Fuentes y reproducción

Cada `*.sql` ejecuta SELECT dentro de `READ ONLY`; su JSON homónimo conserva la captura. `schema_columns` refleja el esquema actual; no se consultó la versión Alembic. `training_summaries_response.json` se obtuvo invocando directamente el servicio backend, que ejecuta su propia transacción de solo lectura. No es una captura HTTP/DOM.

Desde la raíz del repositorio, usando los contenedores existentes y dependencias instaladas:

```sh
python3 docs/audits/CAPSTONE_P3_03/extract_snapshot.py
node docs/audits/CAPSTONE_P3_03/replay_run_report.mjs
PYTHONDONTWRITEBYTECODE=1 malaria_dl_local_project/.venv-local-train/bin/python -B docs/audits/CAPSTONE_P3_03/compute_audit.py
```

El extractor vuelve a leer la BD actual y sobrescribe solo capturas de esta carpeta; para conservar esta evidencia histórica, copiar la carpeta antes de repetirlo. No inicia servicios. Cada consulta tiene un snapshot propio; no se afirma atomicidad global entre archivos. `compute_audit.py` nunca carga un modelo ni consulta una BD: lee snapshots, verifica invariantes y crea CSV/figuras. `replay_run_report.mjs` transpila el helper real en memoria y comprueba 16 casos.

El README y manifest no se regeneran automáticamente. `manifest.json` registra los hashes de esta entrega y de las fuentes importantes. Los JSON de evidencia contienen rutas e identidades experimentales reales del proyecto, sin contraseñas ni cadenas de conexión.

## Comprobaciones realizadas

- 86 filas, categorías: 50 estables, 17 FP, 15 FN, 3 insuficientes, 1 no concluyente, 0 colapsos.
- 140 intentos verificados: matrices coinciden con sus predicciones individuales y threshold constante por intento.
- 60 RUN completos, 1.933 épocas de cohorte; continuidad/completion coincidentes; 131 fases globales con conteos coherentes.
- Mismas muestras VAL2693 y TEST2685 en los 60 intentos por split, sin conflictos de etiquetas/pacientes ni asignaciones ajenas al split gobernado.
- 60 pares VAL–TEST comparten checkpoint, decisión, dataset y definición; grupos de semillas11/29/47.
- AUC del campeón reproducida desde scores; TEST coincide con `verification.metrics`.
- 58 pruebas frontend existentes aprobadas; no se ejercitó navegador autenticado. Comando en el informe.

Los originales quedan preservados. Las raíces de artefactos E6 VAL/TEST del campeón no se encontraron como directorios locales y no se recrearon; los scores PostgreSQL bastan para las métricas auditadas. La presencia del checkpoint seleccionado y su hash sí se verificaron.
