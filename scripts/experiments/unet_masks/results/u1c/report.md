# U1C — Generación gobernada de pseudo-máscaras derivadas de tinción

- Generador: `stain_morph` v2 (`u1b-lab-1`, `stain_delta = 0.20`), congelado en U1B.1 (`dc97fb1`). En U1C no se modificó.
- Entry point: `masks.generate_frozen_pseudo_mask(image)`. Solo píxeles; la clase nunca llega al generador.
- Script: `scripts/experiments/unet_masks/generate_pseudo_masks.py`, con tres subcomandos:
  - `precheck`
  - `generate`: escribe en `*.staging` y renombra al terminar.
  - `verify`
- Evidencia: `precheck.json`, `verify.json` y `generator.json`.
- Dataset fuente: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` (Malaria Patient Split v1). No se creó otra `dataset_version`: las pseudo-máscaras son **artefactos derivados**.

## Evidencia sellada

```
dataset_version_id     d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
generator              stain_morph v2 (implementation_version u1b-lab-1), entry point masks.generate_frozen_pseudo_mask(image)
stain_delta            0.20
implementation_sha256  65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9
spec_sha256            4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b
manifest_sha256        b79d701753b35e183e28316251f0b72268607cba3a86b231cd16e6c746548f7c
relative_root          derived/pseudo_masks/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2/stain_morph_v2   (bajo malaria_dl_local_project/data/)

TRAIN = 22180   VAL = 2693   TEST = 2685   TOTAL = 27558   (pseudo-máscaras 27558 / 27558)
missing = 0   duplicates = 0   invalid_binary = 0   dimension_mismatch = 0   hash_failures = 0
reproducibilidad: 300 registros (100 por split) regenerados, 0 diferencias
```

- El manifiesto (`manifest.csv`, ≈ 11 MB) y las 27.558 PNG **no se versionan**. El manifiesto queda sellado por `manifest_sha256`, que figura en este informe y en `generator.json`. `results/u1c/generator.json` es una copia idéntica byte a byte del `generator.json` del conjunto.
- U1C consume la especificación congelada en U1B.1 (`dc97fb1`) sin recalcularla ni modificarla.

## A. Precheck (`precheck.json`)

| Verificación | Resultado |
|---|---|
| `dataset_version_id` | d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 |
| Conteos (`dataset_split_assignments` + `dataset_source_records`) | train 22.180 · val 2.693 · test 2.685 · **total 27.558** = esperado |
| `source_record_id` únicos | 27.558 |
| Splits válidos | solo train / val / test |
| RGB faltantes | 0 |
| SHA-256 del RGB frente a `dataset_source_records.source_file_sha256` | 0 diferencias |
| `sha256(masks.py)` | `65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9` ✓ |
| `spec_sha256` | `4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b` ✓ |
| Destino fuera de la materialización gobernada | ✓ |

El destino **tiene que** estar fuera de `malaria_dataset_versions/<id>/`: `dataset_integrity.verify_integrity` exige que esa raíz contenga exactamente los archivos gobernados. Una máscara escrita ahí haría fallar la resolución gobernada de TRAIN.

Prueba previa (`--limit 20` por split, en el scratchpad, luego borrada): 60 máscaras, todas las verificaciones en cero y regeneración idéntica. No se cambió ningún parámetro.

## B. Estructura física

```
malaria_dl_local_project/data/                      (ignorado por git; mismo data root que la resolución gobernada)
├── malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2/{train,val,test}/{class}/<filename>.png   RGB gobernado (sin tocar)
└── derived/pseudo_masks/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2/stain_morph_v2/
    ├── generator.json        identidad del generador, record_count, manifest_sha256
    ├── manifest.csv          una fila por source_record_id
    ├── train/<source_record_id>.png   (22.180)
    ├── val/<source_record_id>.png     (2.693)
    └── test/<source_record_id>.png    (2.685)
```

- Formato: PNG lossless, modo `L`, **0 = fondo, 255 = foreground** (lógico 0/1).
- Resolución: la de la imagen fuente. No hay versión a 200×200 como maestro.
- Tamaño total: 128 MB.
- El nombre del archivo es el `source_record_id`. La identidad no depende del filename, y la ruta de la máscara no codifica la clase.
- El resize para U-Net ocurrirá en el loader, con **nearest-neighbor**.

## C. Manifiesto

`manifest.csv`: 27.558 filas, `sha256 = b79d701753b35e183e28316251f0b72268607cba3a86b231cd16e6c746548f7c`, registrado en `generator.json`.

| Campo | Función |
|---|---|
| `dataset_version_id`, `source_record_id` | Identidad lógica, junto con `method_name` + `method_version` |
| `source_filename`, `patient` | Inspección humana y trazabilidad por paciente |
| `split_name`, `class_name` | Metadata gobernada existente. `class_name` es solo auditoría y no llega al generador |
| `source_path`, `source_sha256` | Vínculo verificable con el RGB, relativo a `data/` |
| `mask_path`, `mask_sha256` | Archivo de máscara y hash de sus bytes PNG |
| `mask_pixel_sha256` | Hash de los píxeles decodificados (+ shape). Permite verificar la reproducibilidad aunque cambie el encoder PNG |
| `mask_width`, `mask_height` | Igual a las dimensiones fuente |
| `foreground_pixels`, `foreground_fraction`, `empty_mask` | Descriptivos para el loader y los reportes |
| `method_name`, `method_version`, `stain_delta`, `implementation_sha256`, `spec_sha256` | Identidad del generador por fila |

## D. Cobertura

| Split | RGB esperados | Máscaras | Faltantes | Duplicadas |
|---|---:|---:|---:|---:|
| TRAIN | 22.180 | 22.180 | 0 | 0 |
| VAL | 2.693 | 2.693 | 0 | 0 |
| TEST | 2.685 | 2.685 | 0 | 0 |
| **TOTAL** | **27.558** | **27.558** | **0** | **0** |

No hay archivos de máscara sin fila en el manifiesto, ni filas que no correspondan a una asignación gobernada.

## E. Integridad (`verify.json`, sobre las 27.558)

| Chequeo | Fallas |
|---|---:|
| Archivo faltante | 0 |
| Duplicados de `source_record_id` / `mask_path` | 0 / 0 |
| Hash de la máscara (bytes) | 0 |
| Máscara no binaria o modo distinto de `L` | 0 |
| Dimensiones frente a la fuente (PostgreSQL `image_width/height`) | 0 |
| `foreground_pixels` frente al archivo | 0 |
| Split, clase, source SHA y paths frente a PostgreSQL | 0 |
| Identidad del generador por fila | 0 |
| SHA del manifiesto frente a `generator.json` | coincide |

**Estado: PASS.** La relación RGB ↔ máscara es 1:1.

## F. Estadísticas descriptivas (TRAIN y VAL; no se usan para cambiar el método)

| Split | Máscaras | Vacías | Tasa de vacías | fg mediana (no vacías) | fg p10–p90 (no vacías) |
|---|---:|---:|---:|---:|---|
| TRAIN | 22.180 | 11.546 | 52,1 % | 0,0097 | 0,0043–0,0217 |
| VAL | 2.693 | 1.451 | 53,9 % | 0,0093 | 0,0037–0,0213 |

Las máscaras vacías se conservan como pseudo-máscaras válidas: no se eliminaron, reemplazaron ni sustituyeron por un fallback. Los valores coinciden con lo observado en U1B y U1B.1. TEST se limita a cobertura e integridad.

## G. Reproducibilidad

Se regeneraron 300 registros (100 por split, orden `sha256('u1c-repro-2026-10-02' || source_record_id)`) con RGB → `generate_frozen_pseudo_mask` → SHA-256. **0 diferencias**, tanto en los bytes PNG como en el hash de píxeles.

## H. PostgreSQL

**No se escribió nada.** La base solo se usó en transacciones `READ ONLY`.

Estructuras revisadas:

- **`dataset_materializations` / `dataset_materialization_activations`.** Representan la materialización física del RGB de una versión clínica (`attempt_number` único por versión, reconciliación, activación). Registrar ahí las máscaras las haría pasar por otra materialización de la misma versión. Semánticamente incorrecto.
- **`artifacts`.** Tiene `run_id` nullable, `artifact_type`, `path`, `checksum`, `metadata` y `artifact_status`. Pero hoy solo contiene checkpoints de runs y la consumen unos 20 módulos de gobernanza, linaje, release y backend. Un artefacto de dataset sin run mezclaría semánticas en una tabla crítica, y además hay una campaña activa.

**Persistencia mínima propuesta** (para una etapa aprobada aparte, con migración Alembic). Una fila **por conjunto**, no por máscara; el detalle por máscara queda en `manifest.csv`, cuyo hash queda sellado:

```
dataset_derived_artifact_sets
  id                      uuid PK
  dataset_version_id      uuid NOT NULL FK → dataset_versions(id)
  artifact_kind           text NOT NULL            -- 'stain_pseudo_mask'
  generator_name          text NOT NULL            -- 'stain_morph'
  generator_version       int  NOT NULL            -- 2
  generator_spec          jsonb NOT NULL           -- parámetros congelados
  implementation_sha256   text NOT NULL
  spec_sha256             text NOT NULL
  relative_root           text NOT NULL            -- derived/pseudo_masks/<id>/stain_morph_v2
  manifest_sha256         text NOT NULL
  record_count            bigint NOT NULL
  status                  text NOT NULL            -- READY / INVALID
  created_at              timestamptz NOT NULL
  UNIQUE (dataset_version_id, artifact_kind, generator_name, generator_version, spec_sha256)
```

Cada columna tiene un uso:
- el FK ancla el conjunto a la versión clínica sin crear otra;
- los hashes permiten que un run de U-Net registre exactamente qué pseudo-máscaras usó;
- el `UNIQUE` impide registrar dos veces el mismo generador.

Los runs futuros referenciarían el `id` del conjunto en su configuración. No se propone una tabla por máscara: duplicaría el manifiesto.

## I. Archivos creados o modificados

En la rama `exp/u1b-pseudo-masks`:

- `scripts/experiments/unet_masks/generate_pseudo_masks.py` (nuevo)
- `scripts/experiments/unet_masks/results/u1c/report.md` (nuevo)
- `scripts/experiments/unet_masks/results/u1c/precheck.json` (nuevo)
- `scripts/experiments/unet_masks/results/u1c/verify.json` (nuevo)
- `scripts/experiments/unet_masks/results/u1c/generator.json` (nuevo; copia del `generator.json` del conjunto)

Datos derivados, ignorados por git, en el data root del proyecto:

- `malaria_dl_local_project/data/derived/pseudo_masks/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2/stain_morph_v2/` (27.558 PNG + `manifest.csv` + `generator.json`)

No se modificó:
- `masks.py`, ni la evidencia de U1B o U1B.1;
- el RGB, los splits ni los labels;
- PostgreSQL;
- el registry, los adapters, los loaders ni los modelos;
- la campaña activa.

## J. Git

Commit único de U1C sobre `dc97fb1` (U1B.1) ← `49f8618` (U1B), en la rama `exp/u1b-pseudo-masks`. Sin merge a `main`.

## K. Decisión

**Pseudo-máscaras `stain_morph` v2 listas para entrenar U-Net: SÍ.**

```
27.558 RGB oficiales ──1:1──▶ 27.558 pseudo-máscaras derivadas de tinción
  stain_morph v2 · delta 0.20
  implementation_sha256 65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9
  spec_sha256           4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b
  manifest_sha256       b79d701753b35e183e28316251f0b72268607cba3a86b231cd16e6c746548f7c
  trazables por source_record_id · separadas por split gobernado · integridad verificada (PASS)
```

Pendientes que **no bloquean** U-Net y pertenecen a etapas siguientes:

- el loader TensorFlow de pares (imagen, pseudo-máscara), con resize nearest y augmentation conjunta;
- la persistencia relacional mínima propuesta en H, si se aprueba.

`otsu_intensity` sigue siendo el control experimental de Hard Attention. Se generará cuando se ejecute ese control.
