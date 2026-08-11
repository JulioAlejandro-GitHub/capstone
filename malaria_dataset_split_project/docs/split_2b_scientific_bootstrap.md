# Bootstrap científico e identidad — SPLIT 2B

## 1. Objetivo y preflight

SPLIT 2B persiste la población científica completa y crea `Malaria Patient Split v1`
como DRAFT. No decide assignments ni crea estadísticas, validaciones, materializaciones
o activaciones. El preflight confirmó PostgreSQL 17.9, `malaria_experiments.public`,
Alembic `20260811_01`, las diez tablas de 2A vacías y todas las columnas de lineage
nullable previstas. Había 27.558 imágenes legacy y 12 TRAIN/12 EVALUATE.

## 2. Fuente científica y distribución técnica

Se reutilizó, sin duplicarla, la fila `NIH/NLM Malaria Cell Images`. Su proveedor
científico es NLM/LHNCBC y su referencia canónica es el índice público de Malaria de
LHNCBC. TensorFlow Datasets `malaria:1.0.0` queda documentado como distribución/adaptador
técnico, no como origen clínico primario. Los metadatos preservan los SHA-256 de ambos
CSV oficiales de Patient-ID.

## 3. Identidades y source records

Se persistieron 201 `clinical_identities`, todas `PATIENT/VERIFIED`, con Patient-ID
oficial como `source_identifier` dentro del namespace de la fuente. El Patient-ID
textual no es PK. Cada una de las 27.558 observaciones tiene una FK única a identidad.

`source_record_key` usa
`nlm_lhncbc_malaria_cell_images:<class>/<official_source_filename>` y nunca contiene el
split histórico. `tfds_index` conserva exclusivamente el lineage posicional demostrado
por `files_manifest.csv`. `source_filename` es el filename oficial recuperado. Se dejó
`relative_source_key=NULL`: el caché extraído/audit asset disponible no se promueve a
storage root científico permanente.

## 4. Mapping y evidencia

Se reutilizó el resolver de 1B:

```text
decoded RGB pixel SHA-256 → PNG original → filename oficial
→ CSV oficial NLM/LHNCBC → Patient-ID
```

No se parsearon filenames ni se aplicaron heurísticas. Cada source record tiene una fila
`identity_evidence` que preserva tipo/nivel, método, filename, digest RGB, referencia a
los CSV y la cadena de mapping. Resultado: 27.558 records con identidad y evidencia,
0 unresolved y 0 conflicts.

## 5. Checksums

`source_file_sha256` se calculó leyendo los bytes de cada uno de los 27.558 PNG originales
del caché TFDS extraído de `cell_images.zip`, no los archivos de `train/val/test`.
`decoded_pixel_sha256` se calculó separadamente sobre `Image.convert("RGB").tobytes()`,
idéntica definición a 1B. Ambos campos tienen cobertura 100 % y formato SHA-256 válido.

## 6. Dry-run, transacción e idempotencia

El comando `bootstrap-malaria-v1 --dry-run` completa hashes, resolución y validaciones
antes de abrir cualquier transacción PostgreSQL. Reprodujo 27.558 registros, 201
pacientes, distribución 13.779/13.779 y las métricas de pacientes de 1B.

El apply adquiere un advisory transaction lock, verifica o inserta source, identidades,
records, evidencias, versión y source link mediante batches, comprueba conteos dentro de
la misma transacción y hace un único commit. IDs UUIDv5 determinísticos y comparaciones
de contenido implementan idempotencia estricta: misma key+contenido es NOOP verificado;
Patient-ID, clase, checksum o metodología divergente abortan con rollback. Una segunda
ejecución real conservó exactamente los mismos IDs y conteos.

## 7. Malaria Patient Split v1

La versión `1.0.0` permanece DRAFT, agrupada por `patient_id`, algoritmo declarado
`patient_group_stratified_v1` versión `1.0.0`, seed 42, ratios target 0.80/0.10/0.10,
clase positiva `parasitized` y mapping 0=`uninfected`, 1=`parasitized`. Su único source
link es PRIMARY.

La metodología sólo fija decisiones aprobadas: cobertura de identidad 100 %, hard
constraints de patient/exact-duplicate disjointness y prioridades científicas. No fija
optimizador, pesos, iteraciones, búsqueda, tolerancias ni assignments. DRAFT implica
`TRAINABLE=NO`; ACTIVE sigue sin ser requisito para TRAIN.

## 8. Auditoría final

PostgreSQL reproduce: 201 pacientes; mínimo 65 y máximo 702 células/paciente; 0 sólo
parasitized, 50 sólo uninfected y 151 con ambas clases; 13.779 observaciones por clase.
Hay 27.558 evidencias, cobertura completa de identidad y hashes, y cero assignments,
statistics, validation checks, materializations y activations para v1.

## 9. Compatibilidad legacy

No se modificaron filas de `dataset_split_images`, sus checksums o FKs de versión; no se
modificó `runs.dataset_version_id`. El filesystem `malaria_physical_split`, TRAIN,
EVALUATE, backend y frontend permanecen sin cambios. La regla productiva tampoco cambia.

## 10. Interfaces y alcance diferido

Interfaces:

```text
python -m malaria_split.cli bootstrap-malaria-v1 --dry-run
python -m malaria_split.cli bootstrap-malaria-v1
python -m malaria_split.cli audit-scientific-bootstrap
```

SPLIT 2C conserva los invariantes transaccionales complejos, lifecycle/freeze y guardas
de inmutabilidad. SPLIT 3 implementará optimización determinística y persistirá por
primera vez assignments patient-disjoint; hasta entonces v1 sigue siendo población DRAFT.
