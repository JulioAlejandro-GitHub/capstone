# Auditoría del split físico actual — SPLIT 1A

## 1. Objetivo

Identificar con evidencia del repositorio y filesystem la fuente, materialización,
distribución y algoritmo del split que consumen los procesos actuales, sin crear un
split nuevo.

## 2. Alcance no destructivo

La auditoría fue de solo lectura. No se modificaron el dataset fuente, el split físico,
PostgreSQL, TRAIN ni EVALUATE. No se resolvió Patient-ID ni se calculó leakage clínico.

## 3. Fuente actual

- Tipo: `TFDS`.
- Referencia: `tensorflow_datasets/malaria`, split TFDS único `train`.
- Ruta estable que devuelve el generador sin `TFDS_DATA_DIR` en el proceso:
  `/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/data/tensorflow_datasets`.
- Dataset materializado: `data/tensorflow_datasets/malaria/1.0.0` (TFRecords y metadata
  TFDS). También existe un caché bajo `malaria_dl_local_project/data/tensorflow_datasets`;
  no se atribuye históricamente la ejecución a ese duplicado porque el artefacto final
  no registra el `data_dir` resuelto.

## 4. Split físico actual

- Root: `/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/data/malaria_physical_split`
- Train: `.../malaria_physical_split/train`
- Validation: `.../malaria_physical_split/val`
- Test: `.../malaria_physical_split/test`

Las cuatro rutas existen y son directorios.

## 5. Layout

```text
malaria_physical_split/
├── metadata.json
├── files_manifest.csv
├── split_summary.csv
├── train/
│   ├── parasitized/
│   └── uninfected/
├── val/
│   ├── parasitized/
│   └── uninfected/
└── test/
    ├── parasitized/
    └── uninfected/
```

La partición de validación se llama realmente `val`, no `validation`.

## 6. Conteos

| Partición | Imágenes | Porcentaje real |
|---|---:|---:|
| train | 22.046 | 79,998549 % |
| val | 2.756 | 10,000726 % |
| test | 2.756 | 10,000726 % |
| **Total** | **27.558** | **100 %** |

Hay además tres artefactos auxiliares en el root; el total de archivos físicos bajo el
root es 27.561.

## 7. Distribución por clase

| Partición | Parasitized | % | Uninfected | % |
|---|---:|---:|---:|---:|
| train | 11.023 | 50 % | 11.023 | 50 % |
| val | 1.378 | 50 % | 1.378 | 50 % |
| test | 1.378 | 50 % | 1.378 | 50 % |

Esto documenta la distribución observada; no constituye por sí solo una evaluación de
calidad científica o balance adecuado.

## 8. Algoritmo histórico

Script: `malaria_dl_local_project/scripts/create_physical_dataset_split.py`.

Funciones relevantes:

- `collect_tfds_records`: recorre TFDS sin barajar y recoge índice y etiquetas;
- `project_label_from_tfds_label`: transforma el mapping TFDS al mapping clínico;
- `stratified_split_records`: hace dos llamadas a `train_test_split`;
- `count_assignments`: calcula conteos;
- `prepare_output_dir` y `export_images`: crean estructura y exportan imágenes;
- `build_metadata`, `split_summary_rows` y `write_outputs`: producen artefactos.

Algoritmo: `sklearn.model_selection.train_test_split`, aplicado dos veces con
`shuffle=True` y `stratify` por `project_label`. Estrategia demostrada:
`image_level_stratified_split`. No aparecen `GroupShuffleSplit`,
`StratifiedGroupKFold` ni una clave de agrupación clínica. Por tanto, el algoritmo
histórico no evidencia agrupación por paciente; esto no prueba todavía patient leakage.

## 9. Seed

El CLI define `--seed` con default `42`; el mismo valor recibido se pasa como
`random_state` a ambas llamadas. `metadata.json` confirma `seed: 42` para el split
materializado.

## 10. Ratios objetivo vs reales

| | Train | Validation (`val`) | Test |
|---|---:|---:|---:|
| Target | 80 % | 10 % | 10 % |
| Actual | 79,998549 % | 10,000726 % | 10,000726 % |

## 11. Manifests y metadata existentes

- `metadata.json`: configuración y resumen informativo; campos `dataset_source`,
  `split_type`, ratios, `seed`, mappings de etiquetas, formato, fecha y `counts`. Los
  loaders lo consumen para validar el split.
- `split_summary.csv`: seis filas agregadas; columnas `split`, `class_name`,
  `class_index`, `count`, `percentage`. Es informativo.
- `files_manifest.csv`: una fila por imagen; columnas `split`, `class_name`,
  `class_index`, `relative_path`, `original_tfds_label`, `project_label`,
  `image_width`, `image_height`. El registro de dataset puede usarlo como fuente de
  metadata y trazabilidad.

Los registros previos al export contienen `tfds_index`, `original_tfds_label`,
`project_label` y `class_name`; `tfds_index` no se escribe en el manifest final. No hay
campo `patient_id` en estos artefactos.

Soporte de checksum: **PARTIAL**. El manifest no almacena checksum y no existe una base
de checksums junto al split. `src/malaria_dl/data/registry.py` puede calcular SHA-256
opcionalmente y persistirlo en `dataset_split_images.checksum_sha256` al registrar con
`--register-db-compute-checksum`; SPLIT 1A no consultó ni modificó PostgreSQL.

## 12. Integridad estructural básica

- Extensiones de imágenes observadas: `.png`.
- Errores estructurales: ninguno.
- Archivos inesperados: ninguno.
- Archivos de cero bytes: ninguno.
- Archivos/directorios ocultos dentro del split: ninguno.
- Artefactos auxiliares reconocidos: tres.

La CLI real devolvió 27.558 imágenes. Antes y después se obtuvo la misma huella SHA-256
(`e5644c044b3559405f7e2f43cb6523885e1e9690c47a507cf84a1e03ba4142cb`) sobre las
líneas `mtime + path` de todas las imágenes, confirmando que sus mtimes y estructura no
cambiaron por acción del scanner.

## 13. Evidencia de código

- Fuente y recolección: `create_physical_dataset_split.py:115-137` llama
  `tfds.load("malaria", split="train", shuffle_files=False, data_dir=...)` y crea
  registros por índice/label.
- Split: `create_physical_dataset_split.py:140-169` usa dos veces
  `train_test_split(..., random_state=seed, shuffle=True, stratify=...)`.
- Ratios/seed/ruta: `create_physical_dataset_split.py:40-54` declara defaults
  `0.8/0.1/0.1`, `42` y `PHYSICAL_DATASET_DIR`.
- Materialización: `create_physical_dataset_split.py:259-313` construye rutas
  `split/class/filename` y guarda con PIL.
- Manifests: `create_physical_dataset_split.py:323-346` escribe JSON y ambos CSV.
- Contrato físico: `src/malaria_dl/config/settings.py:1-5` define
  `malaria_physical_split/{train,val,test}`.
- Resolución TFDS: `src/malaria_dl/data/loaders.py:259-273` prioriza
  `TFDS_DATA_DIR` y luego `capstone/data/tensorflow_datasets`.

## 14. Limitaciones observadas

- El split se basa en registros de imágenes y labels; no hay agrupación clínica visible.
- El manifest no conserva `tfds_index`, checksum ni identidad de paciente/muestra/slide.
- La ruta TFDS efectiva de la ejecución de 2026-06-26 no quedó grabada en metadata.
- Esta auditoría no valida contenido de imagen ni duplicados por checksum.
- No se consultó PostgreSQL y no se infiere su estado actual.

## 15. Preguntas que debe resolver SPLIT 1B

- ¿De dónde se obtiene Patient-ID?
- ¿Puede asociarse cada célula con un paciente de forma verificable?
- ¿Qué porcentaje tiene identidad clínica recuperable?
- ¿Existen sample_id / smear_id / slide_id?
- ¿Existen conflictos de identidad?
- ¿El mismo paciente aparece actualmente en múltiples splits?

Estas preguntas quedan deliberadamente sin responder en SPLIT 1A.

