# S2 — Thin Blood Smear Patient Split v1 / SAME SPLIT

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-03.

**FACT — S2 implementada y persistida.** Se gobiernan 193 pacientes técnicos y 965 source records. La versión provisional permanece `GENERATED`; no se ejecutaron validación formal/freeze S3, materialización YOLO, tiling ni entrenamiento. La coincidencia nominal NLM es una política técnica conservadora contra cross-family leakage, no verificación clínica de identidad biológica.

## A. Estado Git inicial

Rama `s1-smear-segmentation-source-adapter`. HEAD `e082c8bd7d47a1a3acbf371a2f57ff8d2fbeafc7`; parent `1e962fa22770f366f5aef13e5cd55956ee6c5f85`. Árbol limpio antes de S2. Evidencia: `git_initial.txt`. Sin commit ni push.

## B. Arquitectura reutilizada

Se revisaron `datasets`, `dataset_versions`, `dataset_version_sources`, `clinical_identities`, `identity_evidence`, `dataset_source_records`, `dataset_split_assignments`, repositorios, constraints/triggers PostgreSQL v2, lifecycle, fingerprinting, estrategias existentes, ingesta S1 e identidad S1.2.

Se reutilizan `SmearSourceRecord.canonical_nlm_patient_key`, el adaptador `inspect_thin_blood_smears_pf`, el parser Polygon, `prepare_smear_rows`, `ingest_smear_source`, `DatasetVersionRepository.add_draft`, `_bulk_insert`, `audit_persisted_assignments`, `compute_final_fingerprints` y `transition_dataset_version`. El algoritmo puro `splitting/same_split.py` recibe claves opacas y no conoce filenames NLM. La nueva operación transaccional está en `persistence/same_split.py`.

El adaptador acepta opcionalmente `Point Set`: inventaría parejas imagen/GT y hashes, sin interpretar Point como polígonos. La ingesta parametrizada conserva exactamente los UUID y metadatos Polygon S1. Point obtiene una fuente separada de la misma familia, con `annotation.format=nih_nlm_point_set`, `validation=inventory_only` y `segmentation_eligible=false`. No hay tablas, columnas ni migraciones nuevas.

## C. Dataset Cell de referencia

**FACT:** `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, `FROZEN`, 27.558 assignments: TRAIN 22.180; VAL 2.693; TEST 2.685. Se leen 201 identidades Cell y sus assignments reales de PostgreSQL, y se contrastan con los CSV oficiales usando el loader S1.2. Los cuatro fingerprints recalculados coinciden con su freeze contract antes y después. No se cambia estrategia, fuentes, identidades, assignments, archivos ni versión Cell.

## D. Full Smear source

**FACT:** RAW local `malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf`: 193 directorios de paciente; 965 JPG y 965 GT, cinco parejas por paciente. Polygon: 33/165; Point: 160/800. Las claves canónicas son distintas y todas tienen assignment Cell. Los registros se descubren del RAW actual; los CSV de auditoría son salidas, no autoridad del assignment.

Se reutiliza el parser del workbook oficial `Dataset_statistics.xlsx`; sus conteos Polygon se concilian por split con los 165 GT parseados por el adaptador. Los conteos Point del informe provienen del workbook; S2 no valida geometría Point, no convierte anotaciones ni genera máscaras.

## E. Política SAME SPLIT

`source record → canonical_nlm_patient_key → protected Cell patient assignment → smear assignment`.

Estrategia: `thin_blood_smear_same_split_v1`, versión `1.0.0`. Unidad: PATIENT. No hay shuffle, estratificación, optimización ni rebalanceo. Se conserva `reference_dataset_version_id`, regla `canonical_nlm_full_smear_patient_key:s1.2:v1`, fingerprints Cell y de ambas fuentes en `methodology_json`; cada assignment registra su clave canónica, set y referencia.

El esquema obliga `random_seed INTEGER NOT NULL`: se almacena 0 con declaración explícita de que no participa y no se invoca RNG. Las ratios nominales 0,8/0,1/0,1 son descriptivas de la referencia; no gobiernan la elección.

## F. Preflight

**FACT — PASS**, antes del primer INSERT de la transacción:

| Invariante recalculada | Resultado |
|---|---:|
| Full Smear patients / canonical IDs | 193 / 193 |
| Canonical collisions | 0 |
| Matches / patients con assignment Cell | 193 / 193 |
| NO_ASSIGNMENT / referencia ambigua | 0 / 0 |
| Imágenes por paciente | exactamente 5 |
| Global TRAIN / VAL / TEST | 154 / 19 / 20 |
| Polygon TRAIN / VAL / TEST | 28 / 2 / 3 |
| Hashes de imagen duplicados entre fuentes Full Smear | 0 |

Los conteos S1.2 son barreras de aceptación, nunca entradas para fabricar assignments. Un desvío produce STOP. `preflight.json` incluye mapping completo y fingerprints; `preflight_run.log` conserva la ejecución inicial sin persistencia. La transacción vuelve a ejecutar el preflight bajo bloqueo antes de escribir.

## G. Persistencia

**FACT:** versión provisional `f0c1f636-715c-54e2-8e46-ed150f9d8791`, estado `GENERATED`. El FK no permite assignments sin Dataset Version. Se utiliza la secuencia existente `DRAFT → GENERATED`; `validated_at` y `frozen_at` permanecen NULL. S2 no declara la versión oficialmente validada, congelada ni entrenable.

193 asignaciones únicas a nivel paciente se expanden a **965 filas** de `dataset_split_assignments`, una por source record, según el contrato existente. No son 193 filas físicas de imagen. Ambas fuentes se enlazan mediante `dataset_version_sources`, rol PRIMARY, conservando sus sets en la procedencia.

Polygon existente: verify-only, sin insertar ni modificar sus registros. Point: una nueva fuente, 160 identidades, 800 source records y 800 identity evidence. Se insertan una versión, dos vínculos y 965 assignments. Todo ocurre en un único `engine.begin()` con advisory lock, constraints, chequeo posterior y rollback ante cualquier error. Evidencia: `persistence.json`.

Se reutiliza el hashing histórico de assignments, incluyendo source record, clinical identity y split. No se introduce otro algoritmo:

- Patient digest: `3e523015e3f93ec0e92d958561172ab39588fb8f6c2d9701ba717e823a67df16`.
- Record digest: `ac5d935ad5b35bbf308efbe84da0d8357e6108a7fe274a48eab1f9828fa98d4f`.

Estos son fingerprints de la generación S2, no un freeze oficial S3.

## H. Distribución global

| Split | Pacientes | % pacientes | Imágenes |
|---|---:|---:|---:|
| TRAIN | 154 | 79,7927% | 770 |
| VAL | 19 | 9,8446% | 95 |
| TEST | 20 | 10,3627% | 100 |
| TOTAL | 193 | 100% | 965 |

Distribución aproximadamente 80/10/10, calculada desde los assignments protegidos. Evidencia: `smear_patient_assignments.csv` (193 filas) y `split_summary.json`.

## I. Distribución Polygon

| Split | Pacientes | Imágenes | Polígonos | RBC P | RBC U | WBC |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 28 | 140 | 28.340 | 1.057 | 27.236 | 47 |
| VAL | 2 | 10 | 2.063 | 35 | 2.026 | 2 |
| TEST | 3 | 15 | 3.861 | 50 | 3.809 | 2 |
| TOTAL | 33 | 165 | 34.264 | 1.142 | 33.071 | 51 |

`polygon_split_summary.csv` contiene una fila por paciente, con identidad original/canónica, split, imágenes y anotaciones. Pacientes con al menos una anotación RBC P: TRAIN 20/28; VAL 2/2; TEST 2/3. Esto describe anotaciones, no diagnósticos.

## J. Distribución Point

| Split | Pacientes | Imágenes | RBC P (Point) | RBC U (Point) | WBC (Point) |
|---|---:|---:|---:|---:|---:|
| TRAIN | 126 | 630 | 5.378 | 123.518 | 171 |
| VAL | 17 | 85 | 730 | 17.059 | 28 |
| TEST | 17 | 85 | 702 | 15.063 | 21 |
| TOTAL | 160 | 800 | 6.810 | 155.640 | 220 |

**FACT:** Point annotation ≠ Polygon annotation. Estos 160 pacientes están gobernados, pero no amplían la población Polygon de entrenamiento. No hay Point→Polygon, weak supervision, pseudo-masks ni entrenamiento con Point.

## K. Patient-level disjointness

**FACT:** intersecciones TRAIN∩VAL, TRAIN∩TEST y VAL∩TEST vacías. Cada clinical identity y cada clave canónica tienen exactamente un split; cada paciente conserva cinco imágenes juntas. El audit SQL devuelve `patient_overlap=0`; los tests verifican 193 grupos de cinco registros y un split. No hay hashes de imagen repetidos cruzando splits.

## L. Cross-family leakage audit

**FACT:** Cell split == Full Smear split para **193/193 pacientes**, incluyendo Point; mismatches **0/193**. Polygon: **33/33**, mismatches 0/33. Se verifica el mapping previo y se vuelve a consultar cada assignment persistido.

Esto demuestra alineación técnica bajo la regla S1.2; no certifica identidad biológica, independencia clínica absoluta ni ausencia de toda posible correlación desconocida.

## M. Scientific consequences of SAME SPLIT

**FACT:** SAME SPLIT preserva el aislamiento por clave técnica entre familias y produce globalmente 154/19/20, pero Polygon hereda 28/2/3. No se cambió Cell ni se movieron pacientes Polygon para mejorar esos números.

**SCIENTIFIC LIMITATION — TRAIN:** 28 pacientes, 140 imágenes y 1.057 RBC P constituyen una base técnicamente utilizable para iniciar un experimento exploratorio de segmentación después de S3/S4. La evidencia positiva abarca 20 pacientes, por lo que la justificación no descansa solo en las imágenes. No se ha demostrado que esa diversidad cubra variaciones clínicas, instrumentales o de adquisición fuera de esta fuente, ni que baste para alcanzar un rendimiento determinado de YOLO26-seg. La suficiencia para convergencia y generalización queda por estudiar; S2 no entrena ni mide modelos.

**SCIENTIFIC LIMITATION — VAL/TEST:** hay solamente 2 pacientes VAL y 3 TEST. Sus cinco imágenes por paciente son observaciones correlacionadas: 10 imágenes VAL no equivalen a 10 pacientes, y 15 TEST no equivalen a 15 pacientes. Solo dos pacientes de cada conjunto aportan positivos. Un paciente TEST tiene cero RBC P anotados; no se descarta ni se redistribuye.

| Split | Canonical patient | RBC P | Fracción de positivos del split |
|---|---|---:|---:|
| VAL | C52P13thinF | 30 | 85,7143% |
| VAL | C57P18thinF | 5 | 14,2857% |
| TEST | C49P10thinF | 43 | 86% |
| TEST | C169P130ThinF | 7 | 14% |
| TEST | C235ThinF | 0 | 0% |

Una sola identidad aporta aproximadamente el 86% de los positivos de cada evaluación. Las futuras métricas agregadas sobre instancias pueden depender fuertemente de esos pacientes; cambiar el desempeño en pocos ejemplos puede alterar apreciablemente los resultados con solo 35/50 positivos. Las observaciones correlacionadas no deben tratarse como muestras independientes para inferencia estadística. La selección de modelos con VAL tan pequeño también puede ser sensible a peculiaridades de esos dos pacientes.

**SCIENTIFIC LIMITATION:** convertir 2 pacientes VAL en 500 tiles mantiene **2 pacientes**, sin añadir diversidad clínica independiente. Ni tiles, augmentations ni Point pueden presentarse como nuevos pacientes Polygon. Este split por sí solo no permite estimar robustamente generalización clínica.

**RECOMMENDATION FOR NEXT PHASE:** conservar SAME SPLIT; describir métricas futuras junto con resultados y conteos por paciente, además de agregados; mantener TEST reservado. Si se estudia incertidumbre, reconocer que el número de pacientes de evaluación es extremadamente pequeño y que remuestrear tiles no subsana esa limitación. Una ampliación futura necesitará nuevos pacientes/Polygon GT compatibles con la gobernanza, sin alterar el Cell protegido. No se calculan mAP, IoU de modelo, precision/recall YOLO, latencias ni benchmarks en S2.

## N. Idempotencia

**FACT:** la segunda ejecución real devuelve `ALREADY_EXISTS_MATCH`; cero fuentes, identidades, evidence, versiones o assignments duplicados. UUID deterministas por fuente/version/source record. La comparación exacta de definición, fuentes, metadatos y assignments rechaza contenido divergente con `CONFLICT`; no sobrescribe. Los tests invierten el orden de las fuentes y comprueban ambos digests idénticos. Evidencia: `idempotency.json`.

## O. Tests

Ejecutados mediante Makefile:

| Comando | Resultado |
|---|---|
| `make test-smear-same-split` | 16 passed |
| `make test-canonical-nlm-identity` | 32 passed |
| `make test-dataset-source-regression` | 35 passed, 1 skipped |
| `make test-canonical-nlm-regression` | 19 passed |
| `make test-smear-same-split-regression` | 22 passed, 1 skipped |
| Total | **124 passed, 2 skipped, 0 failed** |

Skips existentes: sensibilidad a case del filesystem macOS; test S1 real condicionado a `THIN_BLOOD_SMEARS_PF_ROOT` no configurado. S2 sí inspecciona y prueba ambos sets reales mediante su fixture explícito. Logs: `tests.log`, `regression.log`, `persistence_regression.log`.

Cobertura nueva: TRAIN/VAL/TEST heredados; identidad sin assignment; ambigüedad; colisión; split inválido; determinismo; cinco imágenes por paciente; Point sin semántica Polygon; preflight real; distribución alterada detenida antes de cualquier INSERT/UPDATE/DELETE; fuente incompleta; conflictos explícitos; idempotencia; leakage; estado GENERATED sin validación/freeze; fallo inyectado después de insertar 965 assignments con rollback completo de siete tablas. Los fixtures usan una versión de prueba separada y rollback, repetibles también después de persistir S2.

La primera iteración de tests detectó una comparación incorrecta entre el dataclass de fingerprints y su representación JSON; se corrigió usando los nombres del freeze contract, sin modificar datos protegidos ni relajar valores esperados. El log final corresponde al código corregido.

## P. Integridad

**FACT:** igualdad exacta de inventarios SHA-256 antes/después: 2.022 archivos RAW, 27.558 archivos Cell y dos CSV oficiales. `integrity_before.json` y `integrity_after.json` son iguales. RAW permanece montado read-only en Docker.

`db_before.json.gz` / `db_after.json.gz` conservan snapshots SELECT-only bajo REPEATABLE READ, fingerprints y hashes integrales de tablas. Se comparan las filas completas protegidas: versión, fuentes vinculadas, datasets, identities, source records, evidence, assignments y materializaciones Cell. Igualdad exacta. `database_changes.json` confirma cero filas previas modificadas o eliminadas en las siete tablas del snapshot, incluyendo Polygon. `code_hashes.json` identifica la implementación utilizada. Los cambios globales de tablas corresponden a S2; no se exige erróneamente igualdad de toda la BD después de insertar S2.

Sin cambios Cell, RAW, estrategia histórica ni familias fusionadas; sin migraciones, tiles, labels YOLO, materialización ni entrenamiento. El reporte y los artefactos están bajo `docs/audits/s2/`.

## Q. Estado PostgreSQL

**FACT:** PostgreSQL 17.9, base `malaria_experiments`, rol `capstone_v2_runtime`. Se utilizó el backend Docker existente y la conexión configurada, sin exponer credenciales. Cell permanece FROZEN; S2 GENERATED. Polygon continúa como fuente original y Point como nueva fuente de `smear_segmentation`. No hay activación de materialización ni versión S2 entrenable. Estado y operaciones se registran en `persistence.json`, `idempotency.json` y la consulta final read-only `postgresql_final.json`.

## R. Git final

Rama, HEAD y parent iguales al inicio; sin commit ni push. `git_final.txt` registra el estado final y lista de archivos. Cambios acotados al adaptador/ingesta Point, estrategia/persistencia SAME SPLIT, scripts/tests/Makefile y auditoría/documentación. `git diff --check` sin errores.

## S. Recomendación para S3

**RECOMMENDATION FOR NEXT PHASE:** S3 puede comenzar sin modificar el Cell protegido, tomando la versión GENERATED y sus dos fuentes. Debe validar formalmente el contrato de `smear_segmentation` y resolver el freeze conforme a las responsabilidades existentes. El freeze histórico inspeccionado contiene supuestos Cell (27.558 registros y materialización), por lo que no debe invocarse indiscriminadamente para Smear: S3 debe revisar esa compatibilidad sin presentar S2 como validación final. Mantener las cinco imágenes y, posteriormente, todos sus tiles en el split heredado. S4 deberá seleccionar exclusivamente Polygon para el dataset de segmentación; los 193 pacientes gobernados no son 193 pacientes de entrenamiento YOLO.

Respuestas vinculantes:

- **A — YES:** 193 pacientes Full Smear gobernados por SAME SPLIT.
- **B — 0/193:** ningún mismatch cross-family técnico.
- **C — TRAIN 154; VAL 19; TEST 20**, con 770/95/100 imágenes.
- **D — Polygon TRAIN 28; VAL 2; TEST 3**, con 140/10/15 imágenes.
- **E — Sí, técnicamente utilizable para continuar de forma exploratoria**, condicionado a S3/S4; TRAIN incluye 20 pacientes con RBC P. VAL/TEST con 2/3 pacientes y positivos concentrados no sustentan por sí solos generalización clínica robusta.
- **F — YES:** S3 puede comenzar sin modificar Cell; su validación y freeze permanecen pendientes.

Reproducción: `make audit-smear-same-split` recalcula preflight y evidencias sin persistir. `make audit-smear-same-split FLAGS=--apply` aplica la transacción y comprueba una repetición idempotente. Ambos regeneran los archivos de esta carpeta; conservar una copia previa si se requiere retener evidencia histórica de la primera inserción. Tras avanzar S3 fuera de GENERATED, S2 rechaza la reaplicación por conflicto de lifecycle y no retrocede el estado.
