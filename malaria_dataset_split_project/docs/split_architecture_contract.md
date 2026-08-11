# Contrato arquitectónico definitivo del sistema Dataset/Split

Estado: **APPROVED para implementación SPLIT 2–6**. Este documento es normativo para
las siguientes etapas. No crea schema, assignments ni materializaciones.

## 1. Executive summary

PostgreSQL será la fuente de verdad científica. Una `dataset_source` describe procedencia;
una `dataset_version` captura población, identidad, metodología y assignments inmutables.
Los exports son derivados. El filesystem contiene materializaciones verificables, nunca
la identidad histórica de una versión. Patient-ID es la unidad de agrupación.

El flujo obligatorio es:

```text
Dataset Source → Source Records → Clinical Identity/Evidence → Dataset Version
→ Split Assignments → Logical Validation → Statistics → Versioned Materialization
→ SHA-256 Reconciliation → FROZEN → Activation → TRAIN/EVALUATE + version lineage
```

## 2. Evidencia consolidada 1A/1B/1C

- TFDS malaria 1.0.0, 27.558 células; split legacy 80/10/10, seed 42, image-level.
- Identidad oficial NLM verificada al 100 % mediante mapping oficial y pixel hash.
- 201 pacientes; los 201 aparecen en train, val y test; 100 % de células afectadas.
- Cero duplicados exactos observados; Patient-ID está listo como grouping field.
- PostgreSQL inventaría las 27.558 imágenes, pero no Patient-ID/dataset_version.
- TRAIN/EVALUATE leen filesystem; comparten root y layout `train/val/test`.
- 12 TRAIN y 12 EVALUATE históricos carecen de dataset_version explícita; EVALUATE sí
  conserva lineage hacia TRAIN.

## 3. Problema científico confirmado

El split legacy no es independiente por paciente. Las métricas históricas pueden estar
influidas por correlación intra-paciente, sin que esto demuestre memorización ni mida la
magnitud del efecto. El nuevo dataset debe garantizar disjointness por paciente y archivo
exacto sin alterar la evidencia histórica.

## 4. Principios arquitectónicos e invariantes

1. PostgreSQL es source of truth; CSV/JSON son exports; filesystem es materialización.
2. Fuente original y versiones FROZEN son inmutables.
3. Dentro de una versión, cada source record tiene exactamente un assignment.
4. Dentro de una versión, un paciente pertenece exactamente a un split.
5. Patient overlap y duplicate exact-file cross-split deben ser cero.
6. Para Patient Split v1, identity coverage debe ser 100 % y conflictos cero.
7. Assignments se persisten antes de materializar.
8. `val`, nunca test, selecciona checkpoint y calibra threshold/probabilidades.
9. La ruta activa no identifica históricamente una versión.
10. Cambiar población, identidad, assignments o metodología crea una nueva versión.
11. La regla de producción de modelos no cambia: TRAIN completed + EVALUATE completed.

Prioridades de SPLIT 3: (1) patient disjointness HARD; (2) duplicate exact-file
disjointness HARD; (3) representatividad clínica; (4) balance de clase; (5) balance de
fuente; (6) aproximación 80/10/10. Nunca se sacrifica un hard constraint por ratios.

## 5. Source of truth

Los registros normalizados PostgreSQL son canónicos para source, identity, version,
assignment, checks, statistics, materializations, activation y lineage. Los manifests
CSV/JSON se regeneran desde ellos y llevan version/checksum. Un archivo por sí solo no
puede activar, congelar ni cambiar una versión.

## 6. Dataset Source

Decisión: **EXTEND `datasets`** como catálogo de fuentes/datasets, preservando filas
legacy. Debe ganar semántica explícita o campos equivalentes para `provider`,
`source_type`, `source_reference`, `source_version`, licencia/provenance, estado de
ingesta, timestamps y metadata. Puede representar NLM/LHNCBC como proveedor y TFDS
malaria 1.0.0 como distribución/adaptador. No representa assignments.

Cardinalidad: Dataset Source 1→N Dataset Versions y 1→N Source Records. Múltiples
sources podrán componer una versión futura mediante una relación N↔N version-source.

## 7. Dataset Version

Decisión: **NEW `dataset_versions`**. Una versión es una composición científica
reproducible, no una carpeta.

Campos mínimos conceptuales:

- UUID interno, nombre, semantic version, lifecycle status;
- source population fingerprint y relación a uno o más datasets/sources;
- grouping strategy/field; stratification policy; algorithm name/version; seed;
- ratios target; balance objectives; hard constraints;
- positive class y class mapping versionado;
- source record count y methodology JSONB extensible;
- software version/git commit; created/generated/validated/frozen/archived timestamps;
- immutable fingerprint de todos los componentes de freeze.

Primera versión: `Malaria Patient Split v1`, semantic version `1.0.0`, metodología
`patient_group_stratified_v1`. No se asigna UUID en 1D.

## 8. Identidad clínica

Decisión: dos entidades **NEW**:

- `clinical_identities`: UUID interno, dataset source, identity type, source identifier
  (`patient_id`), status y metadata. Patient-ID no es PK global ni se interpreta como PII
  operativa; se preserva como identificador científico de fuente.
- `identity_evidence`: identity, source record, evidence type/level/reference,
  mapping method, source filename, source file hash, decoded pixel hash, status,
  ambiguity/conflict details y timestamp.

Separar identidad de evidencia permite varias pruebas, precedencia y revisión sin
duplicar Patient-ID. La identidad usada por una versión queda fijada en su población.

## 9. Source Record

Decisión: **NEW `dataset_source_records`**. `dataset_split_images` no se fuerza a asumir
esta semántica porque representa materialización/split.

Cada source record contiene UUID, source ID, source-native record ID/filename, clase y
mapping, storage key original relativo, tamaño/dimensiones, `source_file_sha256`,
`decoded_pixel_sha256`, TFDS index/key cuando exista, identity FK y metadata. Un paciente
1→N source records. El mismo source record puede participar en N versiones mediante
assignments independientes.

## 10. Split Assignment

Decisión: **NEW `dataset_split_assignments`** con UUID o PK compuesta estable,
`dataset_version_id`, `source_record_id`, `clinical_identity_id`, split, class/index,
orden determinista opcional y timestamp.

Constraints futuros:

- UNIQUE(dataset_version_id, source_record_id);
- split limitado a train/val/test para versiones internas;
- protección transaccional/normalizada que garantice un único split por
  `(dataset_version_id, clinical_identity_id)`;
- clase coherente con source record.

El assignment existe antes de cualquier copia. External validation se modela como un
evaluation dataset/version con purpose propio, no como cuarto split interno.

## 11. Statistics

Decisión: **NEW `dataset_split_statistics`**, un snapshot oficial por versión y revisión
de cálculo. Columnas normalizadas para total records/patients, records/patients por split,
clases por split, target/actual ratios, overlaps, duplicates, coverage y resumen de
células/paciente; JSONB sólo para percentiles/métricas extensibles. El snapshot usado al
freeze es inmutable y forma parte del fingerprint.

## 12. Validation Checks

Decisión: **NEW `dataset_split_validation_checks`** con version FK, check name,
PASS/FAIL/WARNING, observed/expected tipados o textuales, details JSONB, blocking scope
(VALIDATION/FREEZE), execution/version y timestamp.

Checks mínimos: identity coverage/conflicts; tres patient overlaps; duplicate cross-split;
split completeness; class presence por split; assignment/source counts; materialization
count; missing/unexpected files; checksum reconciliation.

Bloquean VALIDATED: identity !=100 %, identity conflicts, patient overlap, duplicate
cross-split, missing/duplicate assignments, source-count mismatch, split/class absence.
Bloquean FROZEN: todo lo anterior más materialization missing/unexpected, count mismatch,
checksum mismatch o reconciliation != PASS.

## 13. Materialization

Decisión: **NEW `dataset_materializations`** y detalle/manifest normalizado o derivable.
Una versión 1→N attempts; pueden coexistir FAILED y READY. Campos: attempt UUID, version,
versioned root/storage namespace, status, started/finished, expected/actual counts,
manifest checksum, error y metadata.

Lifecycle físico separado: `NOT_MATERIALIZED → MATERIALIZING → READY` o `FAILED`.
READY exige archivos completos y materialized hashes, pero no activa por sí mismo.

Ubicación versionada local:

`malaria_dl_local_project/data/malaria_dataset_versions/<dataset_version_id>/`

Cada storage key es relativo a ese root: `train/<class>/<filename>`, etc. Paths absolutos
sólo se reconstruyen desde configuración local; los existentes se mantienen por
compatibilidad legacy.

## 14. Activation

Decisión: **NEW `dataset_materialization_activations`** (o nombre equivalente). Registra
source family, dataset version/materialization, active root, activated/deactivated time,
status y actor/reason. Un índice parcial/constraint debe permitir máximo una activación
vigente para la familia malaria.

`ACTIVE` es ortogonal a `FROZEN`: puede haber múltiples FROZEN, sólo una ACTIVE. Para
responder “what version is active” se consulta este registro, no se inspecciona la carpeta.

Estrategia: materialización versionada VALIDATED/READY + reconciliation PASS + FROZEN;
preparar staging en el mismo filesystem; comprobar nuevamente manifest; promoción
atómica/controlada al root activo; registrar activación en transacción coordinada. Nunca
se elimina el root activo antes de tener candidato completo y rollback target.

## 15. Lifecycle

Lifecycle científico:

```text
DRAFT → GENERATED → VALIDATED → FROZEN → ARCHIVED
```

- DRAFT: definición mutable, sin assignments oficiales.
- GENERATED: población y assignments completos/persistidos; todavía regenerable sólo
  descartando la versión o volviendo a generar antes de validar mediante transición
  explícita controlada.
- VALIDATED: todos los checks lógicos bloqueantes PASS.
- FROZEN: materialización READY, reconciliation PASS, checks de freeze PASS y fingerprint
  sellado. Irreversible salvo `→ ARCHIVED` lógico.
- ARCHIVED: no activo; permanece consultable/inmutable.

Prohibido: FROZEN→DRAFT/GENERATED/VALIDATED y ARCHIVED→estados mutables. Fallas físicas
no degradan el lifecycle científico; crean otro materialization attempt.

Reconciliation lifecycle separado: `PENDING → PASS | FAIL`; un nuevo attempt empieza en
PENDING. FAIL nunca se convierte silenciosamente en PASS: se ejecuta y registra una nueva
revisión/attempt.

## 16. Inmutabilidad y freeze

Después de FROZEN son inmutables: sources/composición, source population, identity
mapping/evidence seleccionada, assignments, seed, algoritmo/version, grouping,
stratification, ratios/constraints, class mapping, statistics oficiales, checks asociados
al freeze y manifest de materialización. Cualquier cambio produce nueva dataset_version.

## 17. Checksums

SHA-256 es obligatorio y los dominios no se mezclan:

- `source_file_sha256`: bytes del artefacto fuente;
- `decoded_pixel_sha256`: píxeles decodificados para identidad/matching;
- `materialized_file_sha256`: bytes materializados.

Cuando la materialización es copia byte-exacta se exige source file SHA = materialized
file SHA. Si una metodología futura autoriza transformación, debe crear source/derived
records explícitos y una regla de reconciliación versionada; nunca reutilizar el mismo
campo. Duplicados exact-file cross-split se validan con source y materialized SHA; ningún
perceptual hash sustituye integridad exacta.

## 18. Reconciliation

SPLIT 5 comparará assignments PostgreSQL contra filesystem: count total/por split/clase,
split, class, relative storage key, filename, tamaño, SHA-256, missing y unexpected files.
Resultado versionado PASS/FAIL. READY sin checksum completo es inválido; FROZEN y ACTIVE
requieren PASS.

## 19. TRAIN lineage

Decisión futura simple: **EXTEND `runs` con `dataset_version_id`** nullable para histórico
y obligatorio por guard para nuevos training/calibration/evaluation gobernados. TRAIN
también registra materialization attempt/activation usada o snapshot equivalente,
methodology fingerprint, seed y grouping por relación/version.

Pre-TRAIN guard se ejecuta antes de crear/iniciar run:

`status=FROZEN AND logical_validation=PASS AND materialization=READY AND reconciliation=PASS AND active_version_matches_request`.

El guard bloquea TRAIN inválido; no cambia publishing de modelos.

## 20. EVALUATE y calibration lineage

EVALUATE registra su propio `runs.dataset_version_id`, además de lineage al training. Para
evaluación estándar: evaluation version = training version. Otra versión exige purpose
`external_validation` explícito y no se presenta como evaluación estándar.

Threshold y probability calibration registran la misma dataset_version y materialización,
y sólo pueden consumir assignment `val`. Test sigue prohibido. La versión no se infiere
únicamente a través de training aunque esa relación se preserve.

## 21. Legacy compatibility

El histórico se representa conceptualmente como `Malaria Legacy Image-Level Split`,
strategy `image_level_stratified_split`, seed 42, patient_disjoint false, overlap 201,
historical true. Antes de la primera activación debe preservarse su filesystem/manifests
como materialización legacy versionada y reconciliada.

No se reescriben los 12 TRAIN/12 EVALUATE. Una versión legacy oficial puede crearse con
evidencia 1A–1C. El backfill de `dataset_version_id` será progresivo, sólo para runs cuya
ruta/dataset/manifest permitan asociación inequívoca; los demás permanecen NULL y
marcados legacy/unresolved. Nunca se inventa lineage retroactivo.

El constraint legacy `UNIQUE(dataset_dir,relative_path)` queda orientado a inventario de
materialización. Versioned attempts usan roots únicos, evitando colisión. La identidad
lógica vive en assignments con version FK; el active root mutable no es key histórica.

## 22. REUSE / EXTEND / NEW definitivo

| Componente | Decisión |
|---|---|
| datasets / dataset source | EXTEND |
| dataset_splits | EXTEND como resumen compatible, no assignments canónicos |
| dataset_split_images | EXTEND como inventario de materialización/version FK |
| run_dataset_images | REUSE |
| run_io_records | EXTEND con version/materialization snapshot |
| runs | EXTEND con dataset_version_id |
| run_lineage | REUSE |
| artifacts | REUSE |
| model_versions | REUSE |
| dataset_versions | NEW |
| dataset_source_records | NEW |
| clinical_identities | NEW |
| identity_evidence | NEW |
| dataset_split_assignments | NEW |
| dataset_split_statistics | NEW |
| dataset_split_validation_checks | NEW |
| dataset_materializations | NEW |
| materialization activations | NEW |

No se deprecia ningún componente en esta fase; la evolución es aditiva.

## 23. Modelo relacional conceptual

| Entidad | PK | FK/cardinalidad principal | Inmutabilidad FROZEN | Campos esenciales |
|---|---|---|---|---|
| datasets | UUID | 1→N sources records/versions | source descriptor estable | provider,type,reference,version,license |
| dataset_versions | UUID | N↔N sources; 1→N assignments/checks/materializations/runs | completa | lifecycle,methodology,seed,ratios,fingerprint |
| dataset_version_sources | UUID/compuesta | version→dataset source | sí | role,purpose,source_version |
| dataset_source_records | UUID | N→1 source; N→1 identity | población fijada | native ID,class,storage key,hashes |
| clinical_identities | UUID | 1→N records/evidence | mapping fijado | type,source identifier,status |
| identity_evidence | UUID | N→1 identity/record | evidencia usada fijada | level,method,reference,hash,status |
| dataset_split_assignments | UUID/compuesta | N→1 version/record/identity | sí | split,class,order |
| dataset_split_statistics | UUID | N→1 version | snapshot freeze sí | counts,ratios,overlaps,coverage |
| dataset_split_validation_checks | UUID | N→1 version/attempt | checks freeze sí | name,status,values,details,time |
| dataset_materializations | UUID | N→1 version | attempt READY sellado | root,status,manifest,count,error |
| dataset_materialization_activations | UUID | N→1 materialization | history append-only | root,active interval,reason |
| dataset_split_images | UUID | N→1 materialization/version/source record | inventario sellado | relative key,size,hash |
| runs | UUID | N→1 dataset version | run append/update lifecycle existente | version/materialization linkage |

```text
datasets (source) ──< dataset_source_records >── clinical_identities
     │                         │                         └──< identity_evidence
     └──< dataset_version_sources >── dataset_versions
                                          ├──< dataset_split_assignments >── source_records
                                          ├──< dataset_split_statistics
                                          ├──< dataset_split_validation_checks
                                          ├──< dataset_materializations
                                          │       ├──< dataset_split_images
                                          │       └──< materialization_activations → active root
                                          └──< runs (training/evaluation/calibration)
                                                   └── run_lineage: training 1→N evaluations
```

Cardinalidades normativas: source 1→N versions; version 1→N assignments/checks/
materialization attempts/training runs; patient 1→N source records; training 1→N
evaluations; múltiples FROZEN, máximo una ACTIVE por source family.

## 24. Physical filesystem contract

Versioned root:
`malaria_dl_local_project/data/malaria_dataset_versions/<dataset_version_id>/`.
Active root:
`malaria_dl_local_project/data/malaria_physical_split`.

Layout inmutable de consumo:

```text
train/{parasitized,uninfected}
val/{parasitized,uninfected}
test/{parasitized,uninfected}
```

Los storage keys se guardan relativos al materialization root. Todo sigue local-only.

## 25. API/reporting y exports futuros

Backend podrá exponer nombre/version/status/source, metodología, grouping, seed, targets y
actuales, patient/class counts, overlaps, coverage, validation, materialization,
reconciliation, active status y timestamps. Frontend sólo visualiza; no calcula reglas.

Exports derivados: manifest CSV/JSON, statistics CSV/JSON, methodology JSON y validation
report. La ficha metodológica se genera automáticamente desde PostgreSQL y referencia
version fingerprint; no se mantiene manualmente como verdad paralela.

## 26. Pre-TRAIN guard y regla productiva

El guard comprueba versión solicitada, estado FROZEN, logical PASS, READY, reconciliation
PASS y activación/materialization coherente antes de iniciar el run. Además fija
`dataset_version_id` en el contexto. No añade requisitos a publishing: TRAIN completed +
EVALUATE completed siguen siendo suficientes. Guards técnicos de inferencia son otro
contrato y tampoco cambian esa regla.

## 27. Plan SPLIT 2–6

- SPLIT 2: migrations aditivas, entidades/repositories source/version/records/identity/
  evidence, base assignments/statistics/checks/materializations/activation y constraints.
- SPLIT 3: `patient_group_stratified_v1`, assignment determinista, balance optimizer,
  seed/reproducibility; persiste assignments, no materializa.
- SPLIT 4: validations anti-leakage/duplicates/coverage/completitud, statistics y logical
  PASS/FAIL; promueve GENERATED→VALIDATED.
- SPLIT 5: versioned staging/materialization, hashes, reconciliation, preservación legacy,
  freeze prerequisites y activación atómica con rollback.
- SPLIT 6: freeze orchestration, pre-TRAIN guard, lineage version en TRAIN/EVALUATE/
  calibration, exports, backend report API y frontend mínimo.

## 28. Riesgos

- discrepancia entre catálogos dataset legacy y físico;
- paths absolutos legacy y portabilidad;
- Alembic head sin revisions locales visibles;
- backfill histórico ambiguo;
- fallo entre promoción filesystem y registro de activación (requiere compensación);
- espacio temporal duplicado al preservar legacy/materializar;
- paciente con clase única y pacientes grandes complican balance;
- race de dos activaciones (constraint + lock transaccional);
- checksum costoso (cache regenerable, nunca autoridad).

## 29. Decisiones definitivas

Patient-ID; PostgreSQL-first assignments; entidades separadas source/version/record/
identity/evidence/assignment/materialization; SHA-256 obligatorio; versioned root separado;
active root compatible; una ACTIVE; FROZEN irreversible; lineage explícito en todos los
runs de datos; legacy preservado; test fuera de fit/selection/calibration; publishing sin
cambios.

## 30. Criterios de aceptación de la arquitectura

PASS si el diseño de SPLIT 2 respeta entidades/cardinalidades, lifecycle, constraints,
lineage, separación científico/físico, checks bloqueantes, SHA/reconciliation, legacy,
layout y publishing aquí definidos. Cualquier desviación exige ADR nuevo y revisión antes
de migrar. Revisión de consistencia 1D: **PASS**; no existen assignments sólo-CSV,
versiones identificadas por active path, FROZEN mutable, READY sin hash, calibración con
test ni TRAIN futuro sin version lineage.

