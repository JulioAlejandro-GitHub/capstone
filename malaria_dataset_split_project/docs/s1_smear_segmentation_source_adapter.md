# S1 — Dataset Family `smear_segmentation` + Source Adapter ThinBloodSmearsPf

Estado: **implementado; split, tiling y YOLO fuera de alcance (S2+)**.

## 1. Dataset Families

| Family | Source | Registro | Representación |
|---|---|---|---|
| `cell_classification` | NIH/NLM Malaria Cell Images | célula | fila `datasets` histórica **sin modificar**; family resuelta por su nombre congelado |
| `smear_segmentation` | NIH/NLM ThinBloodSmearsPf | imagen completa de frotis | `datasets.metadata.dataset_family` |

Registro en `src/malaria_split/families.py`. **Sin migración**: el schema vigente
(`datasets.metadata`, `dataset_source_records.relative_source_key/metadata`,
`clinical_identities`, `identity_evidence`) representa la nueva fuente.

## 2. Fuente y derivación de Patient-ID

Layout oficial (ReadMe.pdf) verificado sobre la copia real (`Img` con mayúscula en la copia):

```text
<root>/Polygon Set/<Patient ID>/Img/<ImageName>.jpg
<root>/Polygon Set/<Patient ID>/GT/<ImageName>.txt
```

`patient_id` = nombre literal del directorio de paciente. Evidencia por record:
`identity_evidence.evidence_type = OFFICIAL_DIRECTORY_CONVENTION`, `LEVEL_2`,
`mapping_method = polygon_set_patient_directory_name`, con SHA-256 del ReadMe.
Colisiones case-insensitive o asociaciones imagen↔GT por stem no únicas → contrato FAIL.

## 3. Polygon Set

`src/malaria_split/sources/polygon_set.py`. Header `N,width,height`; filas
`cell_no,label,comment,Polygon,n,x1,y1,...`. Labels: `Uninfected`/`Parasitized` (RBC) y
`White_Blood_Cell` (WBC), según ReadMe. Errores con código estable: `GT_MISSING`,
`GT_EMPTY`, `INVALID_HEADER`, `INVALID_ROW`, `UNSUPPORTED_SHAPE`, `UNKNOWN_LABEL`,
`POINT_COUNT_MISMATCH`, `NON_NUMERIC_COORDINATE`, `DEGENERATE_POLYGON`,
`COORDINATE_OUT_OF_BOUNDS`, `HEADER_IMAGE_SIZE_MISMATCH`, `ENTRY_COUNT_MISMATCH`,
`DUPLICATE_CELL_ID`. Imágenes con EXIF orientation ≠ 1 se rechazan (coordenadas ambiguas).
Los polígonos no se convierten, recortan ni rasterizan.

## 4. Source records

Un record = una imagen completa. `relative_source_key` y rutas en metadata son relativas a
la raíz configurada; UUIDs `uuid5` dependen sólo del nombre de la fuente, Patient-ID y ruta
relativa. `class_name = full_smear_image` / `class_index = 0` satisfacen el NOT NULL del
schema y nombran la unidad, **no** un diagnóstico. `decoded_pixel_sha256 = NULL`: la
identidad no depende de pixel matching y el decode JPEG varía entre librerías.
Annotation path/SHA-256/conteos viven en `dataset_source_records.metadata.annotation`.

## 5. CLI

```bash
PYTHONPATH=src "$SPLIT_PYTHON" -m malaria_split.cli inspect-source \
  --dataset-family smear_segmentation --source thin_blood_smears_pf --root <ruta>
PYTHONPATH=src "$SPLIT_PYTHON" -m malaria_split.cli ingest-source \
  --dataset-family smear_segmentation --source thin_blood_smears_pf --root <ruta>
```

`--root` puede venir de `THIN_BLOOD_SMEARS_PF_ROOT`. `inspect-source` no abre conexión a
PostgreSQL. `ingest-source` inspecciona primero, persiste sólo con contrato PASS, en una
transacción con advisory lock; verify-or-insert: un re-ingest idéntico es no-op y cualquier
cambio de contenido (fingerprint de población, hashes) aborta con rollback.

## 6. Resultado real (copia local, 2026-10-02)

```text
patients 33 · images 165 · annotations 165 · valid records 165
images_without_annotation 0 · annotations_without_image 0 · invalid_annotations 0
duplicate_images 0 · ambiguous 0 · ignored Thumbs.db 33
polygons 34.264 = RBC 34.213 (Uninfected 33.071 + Parasitized 1.142) + WBC 51
population_fingerprint fdfce51e79913ea7859ffb5092aef4e88ef4567112fc7b54c22448015f7bf00d
dataset_source_id 3ea11683-fddb-5ed5-8fa1-c41000a9ebd1
```

## 7. Protección de `cell_classification`

Las consultas de población de `bootstrap.py`, `split_generation.py` y
`audit-patient-profiles-v1` eran globales: con una segunda fuente el audit v1 pasaba a FAIL
(234 identidades / 27.723 records). Se restringieron al dataset PRIMARY de v1; con v1 como
única fuente el resultado es idéntico. Fingerprints, assignments, materialización y freeze
de `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` se verificaron idénticos antes/después.

## 8. Hallazgo para S2 — solapamiento de pacientes entre familias

Los 33 Patient-IDs del Polygon Set equivalen, quitando el prefijo numérico, a pacientes de
NIH/NLM Malaria Cell Images (`228C86P47ThinF` → `C86P47ThinF`). Se guarda como
`clinical_identities.metadata.cross_source_hint` con status `UNVERIFIED`; no se crea vínculo
entre identidades. S2 debe decidir si este cruce es identidad real antes de evaluar modelos de
una familia con datos de la otra.

## 9. Fuera de alcance

Point Set, split TRAIN/VAL/TEST, Dataset Version, tiling, clipping, labels YOLO,
`ultralytics`, entrenamiento e inferencia.
