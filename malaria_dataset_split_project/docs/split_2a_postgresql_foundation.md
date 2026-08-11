# Fundación PostgreSQL del sistema Dataset/Split — SPLIT 2A

Estado: implementada sobre la historia Alembic canónica. Esta etapa crea estructura y
no incorpora datos científicos, identidades, assignments ni materializaciones.

## Preflight y migration

La conexión verificada corresponde a PostgreSQL 17.9, base `malaria_experiments`, schema
`public`. Antes del cambio, Alembic current y su único head eran `20260810_05`. La
migration aditiva `20260811_01_scientific_dataset_versioning_foundation.py` desciende de
ese head. No modifica revisiones anteriores, no ejecuta downgrade/stamp y no crea otra
base de datos.

Baseline observado antes de migrar: 2 filas en `datasets`, 27.558 en
`dataset_split_images`, 37 en `runs`, 12 TRAIN y 12 EVALUATE.

## Schema y ERD

```text
datasets ──< dataset_version_sources >── dataset_versions ──< runs
    │                                         │
    ├──< clinical_identities                  ├──< dataset_split_statistics
    │          │                              ├──< dataset_split_validation_checks
    │          └──< identity_evidence         ├──< dataset_materializations
    │                       >── source records │             ├──< activations
    └──< dataset_source_records ──< assignments              └──< split images
                                           >── dataset_versions

run_io_records ──> dataset_versions / dataset_materializations
```

Las diez tablas nuevas son `dataset_versions`, `dataset_version_sources`,
`dataset_source_records`, `clinical_identities`, `identity_evidence`,
`dataset_split_assignments`, `dataset_split_statistics`,
`dataset_split_validation_checks`, `dataset_materializations` y
`dataset_materialization_activations`.

`datasets` incorpora provenance nullable (`provider`, `source_type`,
`source_reference`, `source_version`). `runs` gana la FK nullable
`dataset_version_id`. `dataset_split_images` y `run_io_records` ganan FKs nullable hacia
versión y materialización. No existe backfill; toda fila histórica conserva sus valores.

## Constraints e índices

La base restringe estados científicos y físicos, roles de source, identidad, splits y
resultado de validation. Los ratios individuales están en `[0,1]` y su suma debe ser
exactamente 1.0. Se garantiza unicidad de nombre+versión, source record por source,
assignment por version+record e intento por version+número. Los hashes opcionales sólo
aceptan 64 caracteres hexadecimales.

Todas las FK científicas usan `RESTRICT`, sin cascadas destructivas. Un índice UNIQUE
parcial sobre `dataset_family WHERE deactivated_at IS NULL` limita a una activación
vigente por familia. Índices específicos cubren las FK y búsquedas por status, hashes,
version, identity y materialization sin duplicar los índices creados por PK/UNIQUE.

Las nuevas raíces físicas se almacenan como claves relativas. No se alteran ni reinterpretan
los paths absolutos legacy.

## Compatibilidad legacy

La migration es sólo aditiva y las columnas nuevas en tablas existentes son nullable.
Las 27.558 filas de inventario y los 12 TRAIN/12 EVALUATE permanecen intactos y con
`dataset_version_id IS NULL`. No se crea `Malaria Patient Split v1`, no se importan los
201 Patient-ID ni source records, y no se modifica el filesystem o el comportamiento de
TRAIN/EVALUATE.

## Contrato de selección y TRAINABLE

La única unidad seleccionable futura es `dataset_version_id`; el usuario no selecciona
source, split, seed, método, materialization, path, validation, reconciliation ni
activation. La materialización READY se resuelve internamente para la versión elegida.

`TRAINABLE` es una condición derivada, no un estado persistido:

```text
dataset_version.status = FROZEN
AND logical_validation_status = PASS
AND materialization_status = READY
AND reconciliation_status = PASS
```

Una versión DRAFT no es TRAINABLE. `ACTIVE` permanece ortogonal: sirve para default,
compatibilidad y root físico activo, pero no es requisito para TRAIN.

## Alcance diferido

SPLIT 2B incorporará los datos fuente e identidad/evidencia verificable conforme al
contrato de importación que se apruebe, sin generar aún el nuevo split.

SPLIT 2C implementará invariantes transaccionales complejos: coherencia entre source
record/identity/assignment, patient-disjoint por versión, transiciones lifecycle e
inmutabilidad FROZEN, correspondencia activation↔materialization↔version y resolución
completa de TRAINABLE. La foundation de una sola activación vigente ya está implementada
como índice parcial; 2C añadirá la lógica coordinada de activación/desactivación.

## Pruebas

Las pruebas estructurales inspeccionan las diez tablas y la nulabilidad legacy. Las
pruebas de escritura usan la misma base dentro de transacciones/savepoints revertidos
para validar ratios y unicidad sin dejar fixtures. También se validan tablas nuevas
vacías, conteos legacy y que una versión DRAFT no es TRAINABLE.
