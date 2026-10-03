# S3 — Validation + Dataset Version

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-03.

**S3: APPROVED.** La misma Dataset Version de S2, `f0c1f636-715c-54e2-8e46-ed150f9d8791`, pasó de **GENERATED → VALIDATED → FROZEN**. Se conservan exactamente los 965 assignments. **S4 authorized: YES**, mediante selección explícita de este UUID; S4 aún no se ha ejecutado.

## Estado inicial y alcance

Rama `s1-smear-segmentation-source-adapter`, HEAD `0d440a58d472427a1ff64409870e458406039874`, parent `e082c8bd7d47a1a3acbf371a2f57ff8d2fbeafc7`; árbol limpio antes de S3. S2 estaba committeada. Se inspeccionaron el lifecycle, validation, freeze, fingerprints, repositorios, manifests/materialización y las pruebas existentes. No se hizo commit ni push.

La operación valida la población persistida: no invoca la ingesta S1 ni la persistencia del split S2, no crea otra versión y no repara ni redistribuye assignments. El cálculo read-only de la política S2 se reutiliza exclusivamente para comparar cada assignment existente contra la referencia Cell `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.

## Arquitectura reutilizada y extensión por familia

La preparación específica reside en `persistence/smear_validation.py`, integrada con los mecanismos existentes:

- `preflight` S2, canonical identity S1.2, adaptador S1 Polygon/Point y serialización `prepare_smear_rows` para comparación SELECT-only de sources, identities, records y evidence.
- `ScientificBootstrapRepository` y `DatasetVersionRepository` para reconciliar el contenido persistido; `audit_persisted_assignments` y `compute_final_fingerprints` para los digests existentes.
- `FormalValidationPreparation`, `persist_formal_validation`, `dataset_split_statistics` y `dataset_split_validation_checks` para la validación formal.
- `freeze_dataset_version` y `transition_dataset_version` para el seal y las transiciones oficiales.

La lista de checks se resuelve por familia: Cell conserva sus 12 checks y su requisito histórico de materialización READY/reconciliada; Smear utiliza 17 checks de población, procedencia y SAME SPLIT. No se aplican a full smears los checks de presencia de clases de clasificación Cell. La semántica `full_smear_image` no es un diagnóstico.

El freeze histórico estaba ligado a 27.558 imágenes Cell ya materializadas. El servicio existente ahora distingue el freeze de **población fuente y assignments** de Smear, antes de S4, sin fingir que existe una materialización. Se conserva la persistencia de checks y freeze contract en las tablas/metadatos actuales. **Sin migraciones ni esquema paralelo.**

El manifest histórico de materialización representa copias físicas byte-exactas; S3 no lo instancia ni crea filas de materialización. El manifest de fuente se incorpora al mismo freeze contract, usando los serializadores y primitivas canónicas de hashing existentes, y exporta referencias verificadas a RAW para S4.

## Validación desde PostgreSQL y fuentes reales

**FACT:** 193 pacientes, 193 claves canónicas distintas, 965 source records, 965 imágenes, 965 assignments; exactamente cinco imágenes por paciente. Los conteos se recalculan y se comparan con los criterios aprobados, que actúan como barreras y nunca generan el resultado.

| Split | Pacientes Full Smear | Imágenes / assignments | Polygon pacientes / imágenes | Point pacientes / imágenes |
|---|---:|---:|---:|---:|
| TRAIN | 154 | 770 | 28 / 140 | 126 / 630 |
| VAL | 19 | 95 | 2 / 10 | 17 / 85 |
| TEST | 20 | 100 | 3 / 15 | 17 / 85 |
| TOTAL | 193 | 965 | 33 / 165 | 160 / 800 |

Polygon: 165 GT; Point: 800 GT. El parser Polygon vuelve a leer las anotaciones reales. Point conserva su semántica de puntos y validación de inventario/hashes; no se convierte a máscaras ni se considera población Polygon.

**17/17 checks PASS**, todos blocking for validation y freeze:

1. Cobertura de identidad.
2. Ausencia de conflictos de identidad.
3. TRAIN∩VAL vacío.
4. TRAIN∩TEST vacío.
5. VAL∩TEST vacío.
6. Ausencia de duplicados de imagen entre splits.
7. 965 assignments.
8. 965 source records.
9. Completitud y distribución de assignments.
10. Conteo y distribución de pacientes.
11. Cinco imágenes por paciente.
12. SAME SPLIT cross-family.
13. Población Polygon 33/165/165 y 28/2/3.
14. Población Point 160/800/800.
15. Procedencia de fuentes/GT y contenido persistido coincidentes.
16. Digests S2 sin cambios.
17. Fingerprints reproducibles.

**NO_ASSIGNMENT = 0; patient overlaps = 0; cross-family mismatches = 0/193.** Los 193 pacientes coinciden con Cell, incluidos los 160 Point; Polygon coincide 33/33. Cualquier desvío provoca STOP, sin corrección automática ni freeze.

## Fingerprints, manifiesto y procedencia

Fingerprint principal del manifiesto fuente:

```text
69fe60e20576632a25b37501fa76342ea1b2855b39c1bb1049f97942a87bb67a
```

**Reproducible: YES.** Es también el SHA-256 de los bytes de `source_manifest.json`: JSON canónico mediante `_canonical_json`, seguido de newline, hasheado con `_canonical_digest` existente. El archivo se verifica contra ese hash antes del freeze, y se recalcula en la repetición idempotente.

Fingerprints existentes de la versión:

| Tipo | SHA-256 |
|---|---|
| Source population | `fc7705cffd4befbb17a63c56879e06b9831325fa97d9188b39c85ac7bdcc39c3` |
| Clinical identity | `3d9735a29aa0e112e70adc21b2ff8b3f31f69b61936486e36d628c07384f61d0` |
| Patient assignment | `3e523015e3f93ec0e92d958561172ab39588fb8f6c2d9701ba717e823a67df16` |
| Record assignment | `ac5d935ad5b35bbf308efbe84da0d8357e6108a7fe274a48eab1f9828fa98d4f` |

Los dos digests de assignment coinciden exactamente con `docs/audits/s2/persistence.json`. El digest record incorpora source record, clinical identity y split. El manifest amplía la evidencia a referencias y hashes de imagen/GT y procedencia; no reemplaza ni redefine esos fingerprints históricos.

`source_manifest.json` contiene las 965 entradas ordenadas por source record: ID del registro, identidad persistida, Patient-ID original, clave canónica, split, annotation set, rutas relativas y SHA-256 de imagen y GT. Incluye UUID, familia, estrategia, versión de la regla de identidad, referencia Cell y hashes de procedencia de ambas fuentes.

Cadena sellada: NIH/NLM Full Smear → regla canónica S1.2 → SAME SPLIT → Cell `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` → Smear `f0c1f636-715c-54e2-8e46-ed150f9d8791`. El matching nominal sigue siendo técnico; no certifica identidad biológica clínicamente verificada.

## Lifecycle, atomicidad e idempotencia

**FACT:** transición real `GENERATED → VALIDATED → FROZEN` mediante `transition_dataset_version`. La validación y el freeze de Smear se ejecutan dentro de un único `engine.begin()`, con bloqueo de la versión, advisory lock compartido con S2 y bloqueo de lectura de la referencia Cell.

Antes de FROZEN se repite la preparación y se ejecuta dentro de la transacción la comprobación completa de integridad Cell/RAW/S2. Un fallo revierte también las filas de validación y el estado VALIDATED. Se probó ese rollback con un fallo inyectado después de validar y antes de congelar.

La segunda ejecución real devuelve **ALREADY_FROZEN_MATCH_NO_OP**: misma versión, manifest, fingerprints, timestamps, checks y estadísticas. No duplica ni sobrescribe filas. Un objeto existente con contenido divergente provoca conflicto. No hay UPDATE directo de status fuera del servicio de lifecycle; únicamente se añade el freeze contract a `methodology_json` antes de FROZEN.

Estado derivado de entrenamiento: **TRAINABLE = false**, motivo `NO_READY_RECONCILED_MATERIALIZATION`. La validación lógica sí pasa. Congelar la fuente habilita su consumo por S4, sin simular un dataset YOLO/materialización entrenable.

## Cambios reales en PostgreSQL

Registrados en `database_changes.json` y las filas before/after de `freeze.json`:

- Una Dataset Version existente cambia solo `status`, `validated_at`, `frozen_at` y `methodology_json` (se añade `freeze_contract`).
- Una fila nueva en `dataset_split_statistics`, con el mecanismo y métrica formal existentes.
- 17 filas nuevas en `dataset_split_validation_checks`, todas PASS y blocking.
- Cero versiones nuevas, cero assignments modificados, cero fuentes/identidades/source records/evidence modificados, cero materializaciones nuevas.

La segunda ejecución no altera ninguno de esos objetos. Los metadatos originales S2 permanecen como procedencia histórica; su campo `phase` describe S2. El estado vigente está en la columna `status=FROZEN`, los timestamps S3 y el `freeze_contract` de fuente.

## Integridad before/after

**Cell changed: NO. RAW changed: NO. S2 assignments changed: NO.**

`integrity_before.json` y `integrity_after.json` coinciden. Se compararon todos los hashes de los 2.022 archivos RAW, los 27.558 archivos Cell y los dos CSV oficiales contra los inventarios detallados de S2. Estos archivos de S3 conservan conteos/digests y referencian el inventario S2 ya versionado, evitando duplicarlo. RAW está montado read-only en Docker.

Se comparan las filas completas de la versión Cell y las fuentes, datasets, clinical identities, records, evidence, assignments y materializaciones protegidos de Cell y Smear contra `docs/audits/s2/db_after.json.gz`, mediante serialización canónica. La definición de la versión Smear se contrasta con `docs/audits/s2/postgresql_final.json`, excluyendo únicamente los campos de lifecycle autorizados y el nuevo freeze contract. Los datos de pacientes y sus assignments no cambian.

## Tests ejecutados

| Make target | Resultado |
|---|---|
| `test-smear-validation` | 13 passed |
| `test-smear-validation-regression` | 19 passed |
| `test-smear-same-split` | 16 passed |
| `test-canonical-nlm-identity` | 32 passed |
| `test-dataset-source-regression` | 35 passed, 1 skipped |
| `test-canonical-nlm-regression` | 19 passed |
| Total de ejecuciones | **134 passed, 1 skipped, 0 failed** |

El skip existente corresponde al filesystem macOS no sensible a case. Los logs se conservan en esta carpeta. Las pruebas PostgreSQL usan versiones aisladas y rollback; no modifican la versión S2 real.

Cobertura nueva: counts, disjointness, constraint PostgreSQL contra overlap, SAME SPLIT real 193/193, separación Polygon/Point, GT alterado en cada set, assignment faltante, paciente movido de split sin reparación, digest S2 mutado, fingerprint no reproducible, GENERATED/VALIDATED→FROZEN, guard de integridad con rollback, idempotencia FROZEN, ausencia de materialización y repetición del freeze Cell sin cambiar su contrato ni entrenabilidad.

La primera ejecución detectó que el constraint real `uq_dataset_versions_name_semver` impedía clonar versiones con el mismo nombre. Se corrigieron únicamente los nombres de fixtures y su definición esperada. La regresión S2 requirió el mismo aislamiento de nombre al existir ya su versión real. No se relajó el constraint ni se cambió la definición productiva.

## Limitación científica y autorización para S4

**SCIENTIFIC LIMITATION:** Polygon conserva solo **2 pacientes VAL y 3 TEST**. Sus 10/15 imágenes son observaciones correlacionadas dentro del paciente. Generar más tiles no aumenta el número de pacientes independientes. La concentración de positivos documentada en S2 continúa vigente: un paciente aporta aproximadamente el 86% de los positivos de cada evaluación. Es una limitación científica, no un error técnico que autorice rebalanceo.

El freeze no demuestra generalización clínica robusta, suficiencia estadística ni rendimiento de YOLO26-seg. No se entrenó ni evaluó ningún modelo.

**S4 authorized: YES.** Debe recibir explícitamente `dataset_version_id=f0c1f636-715c-54e2-8e46-ed150f9d8791`, verificar el freeze contract/manifiesto y seleccionar exclusivamente las 165 imágenes Polygon para el futuro adapter de segmentación. Cada representación derivada debe conservar el split del source record/paciente. Point permanece gobernado y excluido de la población Polygon.

S3 no genera YOLO, tiles, polygon clipping, masks, pseudo-masks, entrenamiento ni nuevos TRAIN/VAL/TEST. S4 podrá cambiar la representación; no volver a decidir el split.

## Reproducción y Git final

`make audit-smear-validation` ejecuta las comprobaciones read-only. `make audit-smear-validation FLAGS=--apply` utiliza el servicio de freeze y verifica una segunda ejecución idempotente. Ambos regeneran evidencias en esta carpeta; conservar las anteriores si se desea retener la evidencia de primera transición. Se requiere el backend Docker y la fuente RAW local.

`git_final.txt` registra rama, HEAD, parent y archivos cambiados; `code_hashes.json` identifica la implementación ejecutada. `git diff --check` sin errores. No hubo commit ni push.
