# CAPSTONE-DATA-01A — Materialización, versionado e identidad de datasets

Estado documental: `HISTORICAL_AUDIT` — diagnóstico del estado observado el 2026-10-14; no autoriza migraciones ni eliminaciones.

Base de código: `a94fd266eafe772532d809791829c0c22ad67b78`. PostgreSQL consultado: servicio Compose `db`, base `malaria_experiments`, PostgreSQL 17.9. No se consultó la instancia de pruebas `exec1-postgres` como fuente científica.

## 1. Resumen ejecutivo

**Dictamen A: A2 — Eliminable tras correcciones y preservación del linaje histórico.** `malaria_physical_split` no es una segunda copia intercambiable de la versión `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. Son las mismas 27.558 imágenes a nivel de píxeles RGB y dimensiones, pero con nombres y bytes distintos y **9.287 cambios de partición**. La carpeta antigua conserva tres manifiestos propios y sigue referenciada por código y por 27.558 filas de inventario. No se autoriza su eliminación actual. Las cuatro CLI científicas públicas ya resuelven la versión gobernada y no necesitan esa carpeta como fallback.

**Dictamen B: B3 — Versionado insuficiente de la cadena preparación–entrenamiento.** Full Smear sí tiene identidad científica: `f0c1f636-715c-54e2-8e46-ed150f9d8791`, FROZEN, 965 imágenes, 193 pacientes, 17 checks PASS. Los 4.620 tiles YOLO actuales corresponden a sus 165 imágenes Polygon y respetan sus particiones. Sin embargo, la preparación no tiene registro en `dataset_materializations`, manifiesto sellado de transformaciones ni vínculo persistido desde un entrenamiento YOLO. La identidad de la fuente es sólida; la del derivado y su consumo no está cerrada.

Corrección mínima: mantener las versiones científicas existentes; retirar dependencias del directorio global y preservar el baseline histórico en 01B; registrar preparaciones y su consumo utilizando `dataset_materializations`, `runs`, `run_io_records` y `artifacts` en 01C. **No se necesitan nuevas tablas para representar inicialmente esas identidades.** Debe evitarse el selector genérico «último intento READY» cuando puedan coexistir preparaciones distintas.

### Método y límites de la evidencia

Se inspeccionaron código, configuraciones, archivos físicos y el catálogo/filas de PostgreSQL actual. Todas las sesiones SQL usaron `PGOPTIONS="-c default_transaction_read_only=on"`; solo se ejecutaron SELECT y consultas de catálogo. No se ejecutaron entrenamientos, evaluaciones, CLI de preparación, generación de splits, conversión de anotaciones ni creación de tiles. Se leyeron imágenes con Pillow para comparar píxeles; no se guardaron imágenes. No se cargaron checkpoints mediante pickle/PyTorch ni caches YOLO. Los extractos de trabajo se guardaron temporalmente fuera del repositorio; este informe contiene los resultados y las consultas reproducibles relevantes.

Las afirmaciones «activo» significan alcanzable en el código/configuración actual; no prueban tráfico de usuarios. Los conteos SQL corresponden al momento de cada consulta, no a un snapshot único de toda la auditoría. No se usa documentación previa como sustituto de verificación actual. No se auditó el contenido semántico de cada polígono contra cada etiqueta YOLO: se verificaron procedencia nominal de tiles, particiones, pares imagen/etiqueta, dimensiones y formato de etiquetas.

## 2. Responsabilidades reales de `malaria_dataset_split_project`

El subsistema gobierna población, identidad, asignaciones, validación y congelamiento. No entrena clasificadores ni detectores. Sus responsabilidades reales exceden «crear carpetas»:

| Función y archivo, relativos al repositorio | Responsabilidad observada |
|---|---|
| `malaria_dataset_split_project/src/malaria_split/persistence/bootstrap.py::prepare_scientific_population` | Reconstruye identidad Single-cell a partir del manifiesto TFDS histórico, coincidencia exacta de píxeles, originales NIH y CSV oficiales de pacientes. |
| `.../splitting/optimizer.py::optimize_patient_split` y `.../persistence/split_generation.py::prepare_split_generation`, `persist_split_generation` | Asigna pacientes completos; persiste el split aprobado. |
| `.../persistence/materialization.py::build_materialization_plan`, `materialize_dataset_version` | Copia originales, reconcilia SHA-256 y promueve staging a la ruta versionada. |
| `.../sources/thin_blood_smears_pf.py::inspect_thin_blood_smears_pf` y `.../persistence/smear_source_ingest.py` | Inspecciona e ingresa población Full Smear y anotaciones. |
| `.../persistence/same_split.py::preflight`, `persist_same_split` | Hereda asignaciones por identidad NLM desde la versión Cell; no genera un split aleatorio nuevo. |
| `.../persistence/smear_validation.py::prepare_smear_validation` y `.../governance/freeze.py::_freeze_governed_source` | Valida y sella población/asignaciones Full Smear sin exigir copia física de originales. |

La descarga RAW está en `malaria_dl_local_project/scripts/prepare_datasets.py::main`, que llama `data/cell_source.py::prepare_cell_source` y `data/full_smears_download.py::prepare_full_smear_source`. El exportador TFDS antiguo también pertenece a `malaria_dl_local_project`, no a Dataset Split. Los tiles pertenecen a `smear_segmentation_project`. Por tanto, el diagrama conceptual debe distinguir productor de particiones lógicas, descargador y materializador de derivados.

La instrucción del usuario de inspeccionar Dataset Split prevaleció sobre la skill local que normalmente lo excluye. Se aplicaron los contratos pertinentes de auditoría documental, PostgreSQL, ejecución híbrida, linaje backend y almacenamiento de imágenes, sin introducir cambios funcionales.

## 3. Flujo Single-cell

### Fuente y baseline antiguo

`malaria_dl_local_project/scripts/create_physical_dataset_split.py` implementa:

1. `collect_tfds_records`: `tfds.load('malaria', split='train', shuffle_files=False)` desde `get_tfds_data_dir()`.
2. `stratified_split_records`: dos `train_test_split` estratificados por clase, seed 42, proporciones 80/10/10; no agrupa por paciente.
3. `export_images`: `Image.fromarray(image).save(output_path)`, nombres secuenciales por split/clase (`000001_uninfected.png`, etc.). Primera escritura de imágenes: el `--output-dir`, por defecto `malaria_physical_split`.
4. `write_outputs`: `metadata.json`, `files_manifest.csv`, `split_summary.csv`. El manifiesto físico observado fecha la creación en `2026-06-26T23:58:31.893326+00:00`.

TFDS y NIH no son aquí dos poblaciones independientes: `cell_source.py` declara la distribución técnica `malaria:1.0.0` y valida la procedencia NIH aprobada. El YAML `malaria_dataset_split_project/config/current_split.yaml` localiza los originales en:

```text
data/tensorflow_datasets/downloads/extracted/
ZIP.data.lhnc.nlm.nih.gov_publ_Mala_cell_imagCpSVVrJBQVm1EAGSYJgFN2ZUxCZtjRh76bGSL61Dxmg.zip/cell_images
```

También localiza los CSV oficiales `patientid_cellmapping_{parasitized,uninfected}.csv` en `malaria_dataset_split_project/var/audit/source/`. El bootstrap resuelve cada registro histórico contra esos originales y guarda SHA de archivo, SHA RGB, dimensiones, identidad y `tfds_index`. No basta el nombre TFDS ni la cantidad de células para acreditar identidad.

### Versión por paciente

El flujo gobernado es población acreditada → optimización por paciente → `dataset_split_assignments` → validación → materialización → FROZEN. La versión de referencia conserva seed 42, algoritmo `patient_group_stratified_v1` y 201 pacientes. El optimizador construye candidatos y realiza búsqueda local (`splitting/optimizer.py`); el baseline greedy de `patient_group_stratified_v1.py` no debe confundirse con el resultado aprobado persistido.

`cli.py::materialize_patient_split_v1` toma `tfds_original_images_root` y llama `build_materialization_plan`. Este último usa `source_root / class_name.capitalize() / source_filename`, **no copia desde `malaria_physical_split`**. `materialize_dataset_version` escribe primero:

```text
malaria_dl_local_project/data/malaria_dataset_versions/.<UUID>.attempt-<N>.staging/
```

Usa `shutil.copyfile`, reconcilia todos los hashes y después `os.replace(staging, final_root)`. El destino final es `malaria_dataset_versions/<UUID>`. Un destino existente sin registro READY/PASS provoca error. Si ya existe un READY, exige reconciliación coincidente. El manifiesto se persiste en `dataset_materializations.manifest_metadata`; no existe `manifest.json` dentro de la versión actual.

**No hay una ejecución actual que escriba primero la carpeta global y después clone esa carpeta a la versión.** Hay dos procesos y dos particiones de momentos distintos. Sí hay dependencia histórica de la carpeta global para `bootstrap.py::prepare_scientific_population` y los auditores `cli.py::audit_current_split`, `audit_patient_identity`. La materialización desde asignaciones ya persistidas no depende de ella.

### Límite para nuevos datasets

La estructura admite otro UUID, pero el productor no es todavía genérico: `split_generation.py` fija `V1_ID`, fingerprints aprobados; `materialization.py::build_materialization_plan` exige 27.558 registros, 12 checks y los digests v1. Los comandos de materialización/freeze v1 no reciben una identidad arbitraria. Incorporar nuevas fuentes exige parametrizar estas invariantes por versión sin debilitar las de la versión congelada. Cambiar únicamente el nombre de carpeta no resuelve el problema.

## 4. Comparación física de ambas materializaciones

Abreviaturas: A = `malaria_dl_local_project/data/malaria_physical_split`; B = `malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.

| Split | A uninfected | A parasitized | B uninfected | B parasitized |
|---|---:|---:|---:|---:|
| train | 11.023 | 11.023 | 11.043 | 11.137 |
| val | 1.378 | 1.378 | 1.368 | 1.325 |
| test | 1.378 | 1.378 | 1.368 | 1.317 |
| Total | 13.779 | 13.779 | 13.779 | 13.779 |

| Comprobación exhaustiva | Resultado |
|---|---|
| Archivos | A: 27.565; B: 27.558 |
| Imágenes PNG | 27.558 en cada raíz |
| Bytes de imágenes | A: 330.989.870; B: 331.987.597 |
| Bytes de todos los archivos | A: 332.995.629; B: 331.987.597 |
| Extras de A | Tres manifiestos y cuatro `.DS_Store`; B no tiene extras |
| Rutas relativas y nombres de archivo coincidentes entre raíces | 0 |
| SHA-256 de archivo compartidos | 0; todos los bytes codificados son exclusivos de cada raíz |
| Symlinks de archivos / archivos con `st_nlink > 1` | 0 / 0 en ambas raíces; no son hardlinks |
| Claves únicas `(ancho, alto, SHA256(RGB))` | 27.558 por raíz; coincidencia 27.558/27.558 |
| Claves RGB exclusivas / duplicadas dentro de cada raíz | 0 / 0 |
| Diferencias de clase para la misma clave RGB | 0 |
| Archivos B conciliados con SHA fuente de PostgreSQL | 27.558/27.558 |

La comparación de píxeles usó `PIL.Image.open(...).convert('RGB')`, dimensiones y SHA-256 de `rgb.tobytes()`. No reescribió PNG. La identidad de píxeles no significa igualdad de bytes ni de asignaciones.

Matriz de transición, identificando cada célula por su clave RGB única:

| Split A → split B | train B | val B | test B |
|---|---:|---:|---:|
| train A | 17.730 | 2.168 | 2.148 |
| val A | 2.236 | 262 | 258 |
| test A | 2.214 | 263 | 279 |

Permanecen en el mismo split 18.271 células; cambian 9.287. Reemplazar una ruta antigua por B sin conservar su identidad histórica cambiaría el experimento. El algoritmo antiguo tampoco garantiza aislamiento por paciente; el nuevo sí lo valida. No se ejecutó una nueva medición de overlap de pacientes del baseline antiguo.

Hashes de los manifiestos exclusivos de A:

| Archivo | SHA-256 |
|---|---|
| `metadata.json` | `4245d8fd3c3b07583eb742c7d967f22dc075c6c9d064f9c4e7e03a0682580388` |
| `files_manifest.csv` | `e92c2a6cc35c6841d51ae176261082c0ab76225f906d7fdd0e3d048738344dac` |
| `split_summary.csv` | `833774381e352e72a80846e40b2c90258b17000fad555603de497e86029b6179` |

PostgreSQL conserva 55.116 filas `dataset_split_images`, 27.558 por raíz. **Todas tienen `dataset_version_id`, `dataset_materialization_id` y `checksum_sha256` NULL.** La reconciliación de B se acreditó mediante `dataset_split_assignments JOIN dataset_source_records`, no mediante ese inventario. Se observaron cero referencias a filas de A en `run_dataset_images`, `run_image_predictions`, `predictions` e `image_analysis_jobs`; esto acota el riesgo actual, pero no convierte A en un duplicado binario.

## 5. Consumidores Single-cell

Se siguieron los entrypoints actuales; los parsers internos antiguos no definen la CLI pública.

| Comando público | Selección admitida | Resolución efectiva y split |
|---|---|---|
| `python -m src.train` | `--campaign-id` y/o `--source-training-run-id`; **no** `--dataset-version-id` directo | `src/train.py` → `execution/operations.py::training_plan`: UUID de campaña o TRAIN origen. `training/trainer.py` llama `verify_dataset_for_execution(required_splits=('train','val'))`, reemplaza `args.dataset_dir` por la raíz acreditada y carga con `include_test=False`. |
| `python -m src.evaluate` | Campaña y/o TRAIN origen; no UUID directo ni split configurable | `assessment/cli.py::_execute`: `val`, propósito `development`; `assessment/lineage.py` hereda snapshot del TRAIN. |
| `python -m src.explain` | Campaña y/o TRAIN origen, selección de muestra/cantidad/método; no UUID directo | Mismo linaje, exclusivamente `val`. El background de SHAP también debe pertenecer al split autorizado. |
| `python -m src.test` | Campaña y/o TRAIN origen; no UUID directo | `test`, propósito `final`; mismo checkpoint e identidad acreditada del TRAIN. |

Si se proporcionan ambos selectores se usa `execution/selection.py::select_trainings`, que acota la selección al vínculo solicitado. Los modelos Custom CNN, VGG16 y DenseNet121 comparten esta ruta de datos; no se encontraron materializaciones específicas por arquitectura.

`data/governed_dataset.py::_resolve` consulta la versión explícita, exige FROZEN, contrato `malaria_patient_split_freeze_v1`, materialización sellada concreta READY/PASS y checks aprobados. Resuelve `relative_root` bajo `malaria_dl_local_project/data`, valida confinamiento y verifica los splits pedidos. `training_dataset_metadata` exige un snapshot completo; `assert_run_dataset_snapshot_unchanged` impide combinar identidades, huellas o raíces distintas. `local_dataset_root` adapta el prefijo Docker/Mac manteniendo la ubicación relativa acreditada; no cambia la versión por disponibilidad de otra carpeta.

`assessment/service.py` selecciona muestras por `dataset_version_id` y `split_name`. `assessment/runtime.py::KerasRuntime.images` comprueba autorización de muestra, split, confinamiento, ausencia de symlink y SHA antes de leerla para el modelo. Por inspección estática se cumple TRAIN/VAL sin TEST, EVALUATE/EXPLAIN en VAL, TEST en TEST. No se afirma ejecución end-to-end en esta auditoría.

Los parsers de `training/cli.py`, `evaluation/evaluator.py` y `explainability/pipeline.py` todavía contienen `--dataset-version-id`; no lo exponen los cuatro entrypoints actuales. `science/cli.py` también lo admite para su protocolo específico. No documentar esos flags como si fueran aceptados por `python -m src.evaluate` actual.

Dependencias residuales: `config/settings.py::PHYSICAL_DATASET_DIR`, `data/loaders.py::resolve_physical_dataset_dir(None)`, `data/registry.py`, scripts de registro/exportación y `backend_api/app/services/dataset_browser.py`. El loader conserva el default antiguo, aunque TRAIN gobernado le pasa explícitamente B. El backend legacy permite servir archivos **solo** bajo `PHYSICAL_DATASET_ROOT`; una fila versionada es rechazada por esa función. Cambiar exclusivamente el default dejaría sin resolver permisos de ruta, metadatos e identidad.

## 6. Flujo Full Smear real

```text
prepare_full_smear_source → RAW NIH-NLM-ThinBloodSmearsPf
  → inspección Polygon y Point / registro de fuentes y pacientes
  → persist_same_split: asignaciones lógicas heredadas de Cell por paciente
  → validación / freeze de fuente y asignaciones (sin copiar RAW a train/val/test)
  → load_polygon_records(dataset_version_id): solo Polygon
  → materialize_dataset / materialize_smear: tiles JPEG + etiquetas YOLO
  → YAML data → train_yolo.py → Ultralytics y artefactos locales
```

El eslabón TRAIN/VAL/TEST antes de YOLO es **lógico en PostgreSQL**, no un árbol Full Smear adicional verificado. Las carpetas físicas por split aparecen al preparar tiles. No debe introducirse una copia completa de originales únicamente para hacer coincidir el diagrama conceptual.

`smear_segmentation_project/src/smear_segmentation/dataset.py::load_polygon_records` acepta un UUID con default Full Smear actual y filtra además el `POLYGON_DATASET_ID` fijo. `validate_physical_records` compara población, paciente, hash/dimensiones de imagen y hash/ruta de anotación. Estas funciones aportan validación reutilizable, pero `materialize_dataset` por sí misma recibe registros y no invoca automáticamente ese verificador. No se encontró un driver versionado que encadene validación, filtrado RBC, materialización, manifiesto y registro DB. La llamada histórica exacta que creó la carpeta actual no queda demostrada por un script de producción conservado; sí se localizaron las funciones productoras y se contrastó su producto físico.

## 7. Fuente y particiones Full Smear

Ruta local efectiva según `.env` del splitter y archivos presentes: `malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf`. Contiene `Polygon Set/<paciente>/Img`, `GT`, `Point Set/<paciente>/Img`, `GT`, documentos de origen y `.capstone_download_manifest.json`. `THIN_BLOOD_SMEARS_PF_ROOT` selecciona esa fuente; `THIN_BLOOD_SMEARS_PF_SOURCE` expresa procedencia, no destino del split.

`source_config.py::resolve_source_config` aplica override `--root`, entorno, `.env`, defaults para la fuente. **`MALARIA_CURRENT_SPLIT_ROOT` sigue apuntando al baseline Single-cell** y alimenta `audit_current_split`; no selecciona Full Smear ni una versión gobernada. Su nombre es ambiguo fuera de contexto, su uso actual no lo es.

| Población / fuente PostgreSQL | Pacientes | train | val | test |
|---|---:|---:|---:|---:|
| Polygon `3ea11683-fddb-5ed5-8fa1-c41000a9ebd1` | 33 | 140 imágenes / 28 pacientes | 10 / 2 | 15 / 3 |
| Point `d957fa3b-276d-5d6b-8eba-518276ad3bd7` | 160 | 630 / 126 | 85 / 17 | 85 / 17 |
| Versión Full Smear completa | 193 | 770 / 154 | 95 / 19 | 100 / 20 |

Cada paciente aporta cinco imágenes. `same_split.py::preflight` exige ambas fuentes, 965 registros, imágenes sin hashes duplicados, pacientes no compartidos entre sets y correspondencia canónica con Cell; `splitting/same_split.py::inherit_patient_assignments` hereda el split, no optimiza otro. El criterio es correspondencia técnica de nombres NLM, **no verificación clínica de identidad biológica**, como advierte el contrato congelado. `scripts/audit_s2/worker.py::main` es un invocador histórico de `apply_same_split`; `prepare_datasets.py --split` continúa deshabilitado y su mensaje PENDING_S2 no describe el estado FROZEN actual.

Verificación de esta auditoría: 965/965 imágenes fuente y 965/965 archivos de anotación coinciden con los SHA de PostgreSQL. Las anotaciones Point no se convierten implícitamente en máscaras. Polygon guarda formato, ruta, SHA, tamaño, clases y número de polígonos en `dataset_source_records.metadata.annotation`; Point tiene alcance de inventario según `datasets.metadata.annotation_validation`.

El freeze Full Smear tiene `version=governed_source_freeze_v1`, `scope=source_population_and_assignments`, referencia al UUID Cell y manifiesto lógico con SHA `69fe60e20576632a25b37501fa76342ea1b2855b39c1bb1049f97942a87bb67a`. No promete una materialización YOLO congelada. La pequeña población Polygon VAL/TEST (2/3 pacientes) limita inferencias estadísticas; los tiles no son pacientes independientes.

## 8. Preparación y materialización YOLO

Productor: `smear_segmentation_project/src/smear_segmentation/materialization.py::{materialize_dataset,materialize_smear,write_materialized_tile}`. Recibe UUID de registro fuente, split, ruta, polígonos y dimensiones. Abre la imagen, comprueba dimensiones, calcula tiles y guarda JPEG quality 95 y etiquetas `.txt`.

`tiling.py` fija tamaño 1024, overlap 256, stride 768 y añade el borde final cuando no cae en la malla. `tile_id` usa `<source_record_id>__xNNNN_yNNNN`, **sin tamaño, overlap, digest de anotación ni preparación**. `targets.py::select_rbc_polygons` combina `Uninfected` y `Parasitized` en `RBC=0` y excluye WBC. No es el mapping binario del clasificador. `build_tile_labels` incluye todo polígono completamente contenido en cada tile; un polígono puede estar en varios tiles solapados. `select_tile_for_polygon` existe, pero no es el selector usado por el materializador actual. `materialize_dataset` espera recibir los polígonos ya filtrados; no aplica por sí misma `select_rbc_polygons`.

| Split físico YOLO | JPEG | TXT | Fuentes Polygon |
|---|---:|---:|---:|
| train | 3.920 | 3.920 | 140 |
| val | 280 | 280 | 10 |
| test | 420 | 420 | 15 |
| Total | 4.620 | 4.620 | 165 |

Todos los JPEG miden 1024×1024; los 4.620 UUID de origen se resuelven a registros Polygon, cero tiles en split distinto de su fuente, cero etiquetas faltantes. Hay 51.484 líneas de etiquetas, todas clase 0 y con coordenadas normalizadas/formato estructural válidos. Hay tres `.cache` de labels; no son un manifiesto científico. No se encontró manifiesto de preparación dentro del árbol (solo images, labels y caches).

Huella actual del inventario de los 9.240 JPEG/TXT: `4a8ae6addd4386cb1aabb6f9a0bbcb0b1f076fb555a63a28c4b66952b8eb9c2e`. Método: ordenar archivos por ruta y acumular `relative_path + NUL + sha256(file_bytes) + LF`, UTF-8, luego SHA-256. Esta huella documenta el estado observado; **no es una identidad histórica previamente registrada ni acredita por sí sola la transformación de polígonos**.

`configs/yolo_rbc_1024_v1.yaml` fija `path: smear_segmentation_project/data/yolo_rbc_1024_v1`, con train/val/test bajo images y clase RBC. Por código, ese nombre es una **ruta configurada manualmente**, no un UUID ni una derivación automática de parámetros. `1024` y `v1` son compatibles con la receta, pero no existe función que los derive o garantice que cambien al cambiarla.

`train_yolo.py::main` recibe `--config`, prepara rutas y llama `YOLO(...).train(**train_args)`. Configuración observada: task segment, modelo yolo26n-seg, imgsz 1024, 100 epochs, patience 20, seed 47, deterministic, MPS, batch 8, AMP, `exist_ok: false`. El `args.yaml` del directorio `runs/yolo26_seg/yolo26n_rbc_1024_v1` confirma `split: val` y la ruta al mismo YAML de datos. Hay además directorios de probes de batch/AMP. Es evidencia local de configuración, no vínculo DB dataset–preparación–run. `exist_ok: false` protege la convención del directorio de entrenamiento; no impide modificar el dataset de entrada.

### Segundo dataset y otras preparaciones

- Con otro `output_root` y otro YAML pueden coexistir físicamente dos datasets; hoy requiere elección manual de rutas/configuración.
- Reutilizar la raíz actual con UUID fuente diferentes puede **mezclar poblaciones**: se agregan archivos y no se limpia/reconcilia un inventario esperado.
- Reutilizar los mismos UUID/coordenadas sobrescribe JPEG/TXT: `save` y `write_text` no son exclusivos. Otra receta puede producir colisiones porque el nombre omite la preparación.
- Cambiar de split deja archivos antiguos en el otro directorio si no se gestiona la promoción completa.
- `load_polygon_records` filtra un dataset fuente fijo; pasar únicamente otro UUID de versión puede devolver cero filas o un subconjunto. Debe parametrizarse la fuente autorizada y rechazarse una población vacía/incompleta.
- El entrenamiento conserva argumentos y checkpoints locales, pero un YAML mutable no permite demostrar retrospectivamente qué hashes de tiles/labels consumió.

## 9. `connected_components_v1` y consumidores de inferencia

`backend_api/app/services/detectors/connected_components_v1.py::detect_image` recibe una imagen y un perfil. Aplica orientación EXIF, escala de grises, blur, Otsu, morfología, componentes conexos y filtros geométricos. `_PROFILE` define kernels, áreas, circularidad, solidez, bordes y máximo de componentes; `profile_snapshot` valida overrides.

**No requiere entrenamiento, pesos ni split Full Smear para ejecutarse.** No abre anotaciones ni invoca `load_polygon_records`. Otsu calcula un umbral sobre cada imagen, no ajusta un modelo con un dataset. Los parámetros podrían calibrarse y la calidad podría validarse con anotaciones, pero no se encontró en ese detector un procedimiento automático que consuma los splits para ello. La infraestructura de validación científica del backend administra sesiones/anotaciones aparte; su existencia no convierte este algoritmo en un modelo entrenado.

`detectors/resolver.py` registra connected components como default y YOLO como alternativa. `detectors/yolo26_seg_v1.py` es un adaptador HTTP de **inferencia**: persiste perfil y verifica identidad de checkpoint/runtime. Tiene ruta fija `.../runs/yolo26_seg/yolo26n_rbc_1024_v1/weights/best.pt` y SHA esperado `1a64bc34d188a48b7ed4fcd3276a41aa61d4ab7c037e360ac4beab3e24c31c26`. No selecciona datos de entrenamiento. `smear_segmentation/runtime_api.py` e `inference.py` consumen imágenes y pesos; el pipeline backend produce detecciones/crops para clasificación posterior. No se debe conectar el default algorítmico a una carpeta YOLO para «entrenarlo».

## 10. Identificadores y relaciones PostgreSQL actuales

| Concepto | Evidencia actual y capacidad reutilizable |
|---|---|
| Fuente | `datasets`: cuatro filas; NIH Cell, registro legacy physical, Polygon y Point. Full Smear guarda fingerprints de población y procedencia. |
| Versión científica | `dataset_versions`: dos filas FROZEN, Cell 27.558 y Smear 965. `dataset_version_sources` vincula fuentes. |
| Muestra e identidad | `dataset_source_records`, `clinical_identities`, `identity_evidence`; archivos pesados fuera de DB. |
| Split | `dataset_split_assignments` une versión, registro, identidad y split; estadísticas y checks en tablas respectivas. |
| Materialización | Una fila: `e15dc166-1c4b-558e-b77b-727b1783430c`, Cell, READY/PASS, 27.558, raíz relativa versionada. **Cero filas Full Smear/YOLO.** |
| Activación | `dataset_materialization_activations`: cero filas. No es una selección activa que pueda darse por hecha. |
| Inventario de imágenes | `dataset_split_images`: dos raíces × 27.558, identificadores científicos y SHA NULL; no sustituye asignaciones gobernadas. |
| Entrenamiento | `runs`: 16 filas, todas `run_type=training`, UUID Cell. Cero coincidencias YOLO/UUID Smear/preparation_id en nombre, comando, script, parameters y metadata. |
| Snapshot de ejecución | `train_execution_sessions.dataset`, `runs.parameters/execution_parameters/configuration` permiten preservar evidencia. El resolutor científico compara snapshots completos. |
| Vínculo a preparación | `run_io_records.dataset_version_id` y `.dataset_materialization_id` ya tienen FK a versión/materialización; cero filas con materialización no nula. Es infraestructura disponible, hoy no usada para YOLO. |
| Artefactos | `artifacts` tiene run_id, path/URI, checksum, tipo y metadata; sirve para manifiesto/checkpoint asociado al run. |

`datasets` conserva una fila llamada `malaria_physical_split` cuyo `local_path` ahora apunta a B y cuyos counts son los de B, pero metadata aún dice `physical_stratified_split`, seed 42 y manifiestos legacy. **El nombre del dataset tampoco es identidad confiable de una materialización.** Las vistas legacy `vw_dataset_browser_images` y `vw_dataset_browser_summary` incluyen ambas raíces sin filtro de versión; un agregador sin filtro puede sumar poblaciones dos veces. La UI gobernada actual usa otra API por UUID.

Restricciones inspeccionadas directamente en `pg_constraint`/`pg_indexes`:

- `dataset_materializations`: PK UUID, FK `dataset_version_id ON DELETE RESTRICT`, UNIQUE `(dataset_version_id, attempt_number)`, raíz no vacía/no absoluta, estados y JSONB objeto. No hay índice único de un solo READY por versión.
- `dataset_versions`: UNIQUE `(name, semantic_version)`, estados científicos y proporciones válidas.
- `runs`: FK versión/fuente/modelo/experimento; trigger diferido `v2_run_configuration_required`. Registrar YOLO requiere respetar el contrato de configuración, no insertar una fila incompleta.
- `run_io_records`: FK `run_id`, `dataset_version_id` y `dataset_materialization_id`, todas RESTRICT. La igualdad de versión entre esas referencias debe verificarse en el flujo de registro; las FK individuales no la implican.
- `dataset_split_images`: referencias entrantes RESTRICT desde cuatro tablas mencionadas en §4. No eliminarlas por cantidad de imágenes.

No existe una tabla explícita de preparaciones YOLO en el catálogo público consultado. Esto **no obliga a crearla**: una preparación puede representarse como una materialización tipada, con receta y huella en JSONB y vínculo explícito desde el run. Su ID identifica ese derivado, no reemplaza el UUID científico ni el UUID del entrenamiento.

Consultas de control reproducibles, siempre en sesión READ ONLY:

```sql
SELECT id,name,status,source_record_count FROM dataset_versions;
SELECT id,dataset_version_id,status,reconciliation_status,relative_root,record_count
FROM dataset_materializations;
SELECT dataset_version_id,split_name,count(*),count(DISTINCT clinical_identity_id)
FROM dataset_split_assignments GROUP BY 1,2 ORDER BY 1,2;
SELECT dataset_version_id,dataset_materialization_id,dataset_dir,count(*)
FROM dataset_split_images GROUP BY 1,2,3;
SELECT dataset_version_id,run_type,count(*) FROM runs GROUP BY 1,2;
SELECT dataset_version_id,status,count(*)
FROM dataset_split_validation_checks GROUP BY 1,2;
SELECT conrelid::regclass,conname,pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid IN
 ('dataset_materializations'::regclass,'run_io_records'::regclass,'runs'::regclass);
```

Para cotejar B se consultaron `dataset_split_assignments JOIN dataset_source_records` por `source_record_id`; cada ruta se construyó con split/clase/source_filename y se comparó SHA con `source_file_sha256`. Para Smear se usó `relative_source_key` y `metadata.annotation.{relative_path,sha256}` bajo la fuente RAW. Dos consultas exploratorias usaron nombres de columna incorrectos (`dataset_versions.dataset_version_id` y `dataset_split_validation_checks.split_name`); fallaron sin escritura y se corrigieron a `id` y agrupación por `status`, respectivamente. No se introdujeron compatibilidades de esquema.

## 11. Inventario transversal de rutas y consumidores

Búsquedas: `malaria_physical_split`, `malaria_dataset_versions`, `dataset_version_id`, `yolo_rbc_1024_v1`, `MALARIA_CURRENT_SPLIT_ROOT`, `THIN_BLOOD_SMEARS_PF_ROOT`; se incluyeron código, tests, scripts, documentación, `.env` relevantes y Compose. Las rutas abreviadas de la tabla se anclan al subsistema indicado. L = lectura; E = escritura; C = configuración; D = documentación.

| Subsistema | Archivo / función | Tipo | Dataset / uso | Estado | Dependencia | Riesgo al retirar/cambiar |
|---|---|---|---|---|---|---|
| Split | `src/malaria_split/source_config.py::resolve_source_config`, `.env`, `.env.example`, `config/current_split.yaml` | C/L | Cell auditoría / Smear RAW | Activo | current split global; smear root separado | Confundir variables cruza familias. |
| Split | `cli.py::audit_current_split`, `audit_patient_identity`, `_bootstrap_paths` | L | Cell baseline | Activo, invocación manual | A y manifiestos | Fallan auditoría/bootstrap si se retira A. |
| Split | `persistence/bootstrap.py::prepare_scientific_population` | L/E DB | Cell identidad | Activo, especializado v1 | A + originales + CSV | Pérdida de enlace TFDS/identidad si no se preserva. |
| Split | `persistence/materialization.py::materialize_dataset_version` | L/E | Cell split | Activo | Originales + asignaciones → B | No depende de A; invariantes v1 bloquean otras poblaciones. |
| Split | `persistence/same_split.py::persist_same_split` | L/E DB | Smear split | Activo, especializado fuente actual | UUID Cell, Polygon/Point | Reutilizar UUID/constantes para otra fuente confunde población. |
| Split | `governance/freeze.py::_freeze_governed_source` | L/E DB | Smear identidad | Activo | Huellas y manifiesto lógico | No acredita tiles. |
| Split | `governance/trainability.py::resolve_trainable_materialization` | L | Ambas / disponibilidad | Activo | Último READY por versión | Selección ambigua con varias recetas. |
| DL | `scripts/create_physical_dataset_split.py::main/export_images` | E | Cell split | Legacy alcanzable | Default A | Recrea baseline; `--overwrite` destruye su destino. No ejecutado. |
| DL | `scripts/prepare_datasets.py::main`, `data/cell_source.py`, `data/full_smears_download.py` | L/E | Fuentes RAW | Activo | TFDS y smear root | No generan splits ni tiles; mensaje S2 obsoleto. |
| DL | `src/malaria_dl/config/settings.py`, `data/loaders.py::resolve_physical_dataset_dir` | C/L | Cell carga | Default/fallback residual | A si no hay argumento | Debe quitarse la selección implícita. |
| DL | `data/registry.py`, `data/cli.py`, `scripts/register_physical_split_in_db.py` | L/E DB | Cell inventario | Legacy alcanzable | A por default / nombre físico | Registros sin identidad científica explícita. |
| DL | `persistence/tracking.py::record_run_dataset_images` y usos del nombre legacy | E DB | Cell tracking | Residual | Nombre `malaria_physical_split` | No tratar el nombre como prueba de ruta. |
| DL | `execution/operations.py::training_plan`, `training/trainer.py` | L | Cell TRAIN | Activo | UUID campaña/TRAIN → B | Preservar snapshots; no fallback global. |
| DL | `assessment/cli.py::_execute`, `lineage.py`, `runtime.py::KerasRuntime.images` | L | Cell EVALUATE/EXPLAIN/TEST | Activo | UUID heredado, split y SHA | Cambiar raíz/versión rompe evidencia y debe fallar. |
| DL | `data/governed_dataset.py::_resolve`, `local_dataset_root` | L | Cell cuatro procesos | Activo | ID materialización sellado | No reemplazar por «latest». |
| Backend | `app/services/dataset_browser.py::{dataset_summary,read_metadata_fallback,resolve_dataset_image_file}`, `app/routes/dataset.py` | L | Cell browser/imágenes | Legacy alcanzable | Vistas ambas raíces; allowlist A | 403 para B; pérdida de archivos/metadata si se elimina A. |
| Backend | `app/services/governed_datasets.py::governed_dataset_version_detail` | L | Versiones y estado | Activo | UUID, checks, materialización | Ajustar disponibilidad multirreceta; no mezclar conteos legacy. |
| Frontend | `src/pages/DatasetBrowser.tsx` | L API | Ambas / catálogo | Activo | UUID seleccionado, API datasets | No abre rutas físicas; depende del contrato backend. |
| Frontend | `src/pages/DatasetsModels.tsx` | L API | Catálogo | Activo | Datos de API | Nombres legacy pueden mostrarse, no acreditan identidad. |
| Smear | `src/smear_segmentation/dataset.py::load_polygon_records` | L DB | Smear preparación | Activo | UUID versión + fuente Polygon fija | Otro dataset requiere selección explícita de fuente. |
| Smear | `materialization.py::materialize_dataset/write_materialized_tile` | L/E | Smear preparación | Activo; llamada histórica exacta no verificada | output_root, UUID fuente/coordenadas | Mezcla/sobrescritura sin manifiesto ni promoción. |
| Smear | `configs/yolo_rbc_1024_v1.yaml` | C | Smear TRAIN/VAL/TEST | Activo | Ruta fija | YAML mutable altera input del entrenamiento. |
| Smear | `train_yolo.py::main`, `configs/yolo26n_seg_train_v1.yaml` | L/E | Smear entrenamiento | Activo | YAML + nombre run | Sin vínculo DB a preparación. |
| Backend/Smear | `detectors/yolo26_seg_v1.py`, `runtime_api.py`, `inference.py` | L | Smear inferencia | Activo | Checkpoint y SHA/perfil | Cambiar dataset no debe cambiar pesos del detector desplegado. |
| Backend | `detectors/connected_components_v1.py::detect_image` | L | Imagen de inferencia | Activo | Perfil, sin dataset | No requiere migración de dataset de entrenamiento. |
| Compose | `docker-compose.yml`, `docker-compose.override.yml` | C | Montajes / ejecución | Activo | Mount DL y raíz versionada en override | Preservar resolución Docker/Mac; no usar prefijos como identidad. |
| Tests DL | `test_dataset_resolution.py`, `test_data_loading.py`, `test_canonical_architecture.py`, `test_dataset_registry.py`, `test_dataset_browser_api.py`, `test_dataset_browser_queries.py` | L fixtures | Cell contratos/defaults | Pruebas | A/B, rechazo alternativos | Algunas aserciones fijan legacy; actualizar según nuevo contrato. |
| Tests Split | `tests/unit/test_materialization.py`, `tests/integration/test_postgresql_foundation.py`, `test_smear_source_ingest.py` | L/E fixtures | Cell/Smear | Pruebas | 27.558 legacy; env RAW | No correr integración sobre DB operativa durante 01A. |
| Scripts | `scripts/audit_s1_1`, `audit_s1_2`, `audit_s2`, `audit_s3`, `scripts/reset/reset3/import_probe.py` | L/E según script | Auditorías/importación | Histórico/manual | Rutas y UUID fijos | No ejecutarlos como simples comprobadores: algunos escriben. |

### Documentación separada de código funcional

| Documento | Estado según banner inspeccionado | Tratamiento en 01A |
|---|---|---|
| `docs/operations/dataset_source_preparation.md` | CURRENT_DOC | Distingue RAW de split; variables corroboradas con código. |
| `docs/runbook_split_completo_malaria.md` | CURRENT_DOC / RUNBOOK CIENTÍFICO | Contexto operativo; no ejecutado. |
| `docs/operations/yolo_runtime.md` | CURRENT_DOC | Describe inferencia/checkpoint, no identidad del dataset preparado. |
| `docs/audits/capstone_cli_01_parameter_certification.md` | CURRENT_DOC según índice | Los entrypoints se verificaron directamente, sin asumir flags de parsers antiguos. |
| `docs/dataset_ui_governed_versions.md` | Sin banner explícito en cabecera | Explica separación UI; código actual es la evidencia decisiva. |
| `malaria_dataset_split_project/docs/adr/ADR-003-versioned-materialization.md` | Sin banner explícito | Decisión sobre rutas/attempts, no prueba de estado físico. |
| `docs/codebase_dead_code_and_legacy_audit.md` | Sin banner de estado en cabecera; fecha 2026-08-24 | Contiene clasificación LEGACY_REQUIRED de A; no sustituye este cotejo. |
| `docs/audits/s1_1/REPORT.md`, `docs/audits/e10_10_1_baseline.md`, auditorías S1.D/S2/DBv2 | Evidencia previa; no se recertifica aquí su estado documental completo | Referencias encontradas y contrastadas con nuevos hashes/conteos; no son runtime. |

## 12. Dictamen A — A2, condicionado

La carpeta global puede retirarse **después** de migrar consumidores y preservar la identidad del baseline; no es eliminable hoy. Motivos verificables:

1. El bootstrap y endpoints legacy todavía la usan; el loader la selecciona por defecto (§3, §5, §11).
2. Tiene 27.558 referencias de inventario y tres manifiestos exclusivos (§4, §10).
3. La población RGB es idéntica a B, pero 9.287 asignaciones y todos los hashes codificados son distintos (§4). No se deben redirigir esas filas a B fingiendo identidad de bytes o de split.
4. Las 16 ejecuciones actuales usan la versión Cell gobernada; no se observaron referencias a A en los cuatro consumidores FK de inventario ni en los campos de configuración de runs consultados. Es viable reducir su dependencia, sujeto a revisión final de evidencias externas/locales antes de cualquier eliminación.

A1 queda descartado por dependencias activas y evidencia exclusiva. A3 sería el dictamen de retención permanente si se demostrara un requisito de reproducir exactamente bytes históricos que no se archive; no se acreditó ese requisito en runs actuales. La condición de A2 incluye **archivar o representar de manera verificable manifiestos, mapping muestra/identidad/split antiguo y hashes originales**. Si no se cumple, conservar A. Este informe no convierte esa condición futura en autorización de borrado.

## 13. Dictamen B — B3

No corresponde B1: falta identidad/verificación de preparación y consumo por entrenamiento. B2 describe parcialmente la situación de la fuente, pero no alcanza para la cadena completa solicitada: el ejecutor YOLO no registra su vínculo DB y la raíz permite sobrescrituras o mezcla. B4 tampoco corresponde: hay evidencia suficiente del código, catálogo y tiles para demostrar esa brecha.

La fuente está identificada y sus asignaciones están congeladas. La coincidencia de los UUID de los 4.620 tiles con PostgreSQL permite reconstruir procedencia nominal y split actual, **pero no demuestra qué transformación exacta ni qué bytes consumió un entrenamiento pasado**. No atribuir retroactivamente un manifiesto nuevo a un run antiguo sin evidencia adicional.

## 14. Arquitectura objetivo recomendada

**Cell:** conservar `malaria_dl_local_project/data/malaria_dataset_versions/<dataset_version_id>/{train,val,test}` como materialización canónica de cada versión gobernada. Seleccionar mediante UUID en el contrato de campaña/TRAIN; no hace falta añadir un flag a los cuatro entrypoints públicos. Conservar un solo resolutor gobernado y hacer explícita la separación entre inventario histórico y población científica. La historia de A no es una versión alternativa del mismo split; debe preservarse como baseline distinto antes de retirarse físicamente.

**Smear:** mantener RAW una sola vez y particiones lógicas en PostgreSQL. Representar la preparación como `dataset_materializations.id`, con `metadata.kind='detector_preparation'` (contrato propuesto, no escrito), receta completa y huella en `manifest_metadata`. El `dataset_version_id` identifica población y asignaciones; el ID de materialización identifica el derivado; `runs.id` identifica entrenamiento. No usar `attempt_number` como sustituto de receta: es un intento técnico y el manifiesto debe identificar la receta y sus archivos.

La estructura conceptual `smear_segmentation_project/data/<dataset_version_id>/<dataset_materialization_id>/...` es adecuada para nuevas preparaciones, pero **renombrar el directorio actual no es condición para mejorar trazabilidad**. La intervención menor puede registrar y sellar su raíz existente tras reconciliación, y usar rutas distintas e inmutables para las nuevas. No crear copias de originales Full Smear por split; tiles son derivados necesarios, no réplicas byte-exactas del RAW.

`relative_root` debe tener un ancla de almacenamiento explícita en el contrato por familia. El resolutor Cell actual la interpreta bajo `malaria_dl_local_project/data`; no pasarle una raíz Smear como si compartieran base. Reutilizar primitivas de confinamiento/localización y definir el ancla en la preparación; no duplicar el resolutor científico Cell ni introducir fallbacks entre familias. La interfaz de detector debe pedir la materialización concreta, no la «última READY» de la versión.

## 15. Plan mínimo CAPSTONE-DATA-01B

| Paso | Archivos/componentes concretos | Cambio mínimo propuesto | Riesgo/criterio |
|---|---|---|---|
| Preservar baseline | Manifiestos A; `bootstrap.py`, `identity/source_identity_index.py`, `patient_identity_resolver.py`; inventario DB | Exportar y acreditar mapping histórico muestra→fuente→paciente→split, hashes/manifiestos, sin alterar B. Determinar necesidad de archivo byte-exacto. | Cero pérdida de evidencia exclusiva; no confundir píxeles con bytes. |
| Desacoplar bootstrap | `cli.py::_bootstrap_paths`, `bootstrap.py::prepare_scientific_population` | Separar importación histórica de ingestión de nueva fuente; nuevas poblaciones no requieren A. | Preservar reproducibilidad de v1 y rechazar identidad ambigua. |
| Retirar defaults | `config/settings.py`, `data/loaders.py`, `data/cli.py`, scripts registro/exportación, `.env.example`, `source_config.py` | Pedir identidad/ubicación explícita; mantener archivos históricos consultables bajo su identidad, sin selección silenciosa. | No romper CLI pública; no usar una constante UUID global como nuevo fallback. |
| Corregir browser/inventario | `backend_api/app/services/dataset_browser.py`, `app/routes/dataset.py`; vistas e inventario actual | Servir materializaciones acreditadas por identidad con confines correctos; separar catálogo histórico; completar vínculos solo cuando demostrados. | No redirigir image_id antiguo a otro split ni ampliar allowlist indiscriminadamente. |
| Soportar otra versión | `split_generation.py`, `materialization.py`, `formal_validation.py`, `governance/freeze.py` | Sustituir cantidades/digests v1 hardcoded por contrato acreditado de la versión, conservando los sellos existentes. | No reoptimizar ni reescribir versión FROZEN. |
| Retiro final | A, referencias DB y documentación | Solo tras verificaciones y autorización posterior; retirar carpeta si toda la evidencia y consumidores están cubiertos. | Respaldo/rollback probado; no borrar por igualdad de conteos. |

Pruebas propuestas: contrato de resolución sin A en fixture aislado; versión inexistente/raíz alterada falla sin fallback; hashes y fingerprints v1 invariantes; snapshots de TRAIN histórico; TRAIN no abre TEST; EVALUATE/EXPLAIN solo VAL; TEST solo TEST; API de archivos por identidad y path traversal; dos versiones distintas coexisten. Actualizar pruebas de defaults y las que esperan 27.558 registros legacy según el nuevo contrato. Ejecutar mediante objetivos Makefile adecuados (`make test-ml`, `make test-backend` y suites focalizadas integradas al Makefile), en entorno aislado; no contra producción.

## 16. Plan mínimo CAPSTONE-DATA-01C

| Paso | Archivos/componentes concretos | Cambio mínimo propuesto | Riesgo/criterio |
|---|---|---|---|
| Selección de fuente | `smear_segmentation/dataset.py::load_polygon_records`, contratos de Dataset Split | Recibir UUID versión y fuente autorizada; validar familia, freeze, población no vacía, hashes y asignaciones. | Otra fuente no hereda UUID/constantes NIH sin validación. |
| Sellar preparación | `materialization.py`, `tiling.py`, `targets.py`; `dataset_materializations` | Registrar ID de materialización, receta (tiling, bordes, clases, política de polígonos, JPEG, software), fuentes/anotaciones y hashes de outputs. | No crear nueva tabla ni confundir intento con receta. |
| Publicación física | `materialization.py::write_materialized_tile/materialize_dataset` | Staging, reconciliación y promoción sin sobrescribir preparación sellada; detectar extras/faltantes y mismo destino con otra receta. | IDs de tile aislados bajo ID preparación; preservar split del padre. |
| Entrenamiento | `train_yolo.py`, YAML de datos/train; servicios existentes de registro, `runs`, `run_io_records`, `artifacts` | Exigir preparación concreta READY/PASS; verificar manifiesto y registrar run→versión→materialización; guardar config efectiva y hashes de checkpoint/manifest. | Cumplir configuración obligatoria de runs y reporte al control plane; no injertar YOLO en contrato Keras. |
| Disponibilidad | `governance/trainability.py`, `backend_api/app/services/governed_datasets.py` | Separar catálogo/disponibilidad de selección; varias preparaciones requieren ID explícito. | Nunca elegir otra receta por mayor attempt_number. |
| Preparación existente | Directorio actual, `args.yaml`, checkpoints | Reconciliar estado actual; registrar solo hechos demostrados. Recuperar vínculo de runs históricos si sus evidencias lo permiten. | No certificar retrospectivamente hashes consumidos a partir del estado actual. |

Pruebas propuestas: dos fuentes, dos versiones y dos recetas de una versión; mismo output con contrato distinto falla; repetición idéntica idempotente; imagen/anotación/label alterado falla; archivos extra detectados; paciente y fuente no atraviesan splits; selección Polygon excluye Point/WBC según receta; persistencia de vínculo run/preparación y rollback ante fallo. Integrar suites al Makefile; no generar el dataset real para probar estas condiciones. El runtime YOLO mantiene su checkpoint actual hasta un proceso separado de publicación de modelo; connected components no requiere cambios de entrenamiento.

## 17. Riesgos, pruebas y criterios de aceptación

Comprobaciones realizadas: lectura de código y configuración; esquema/relaciones/filas PostgreSQL en modo lectura; inventario exhaustivo de ambas raíces Cell; SHA de todos sus archivos; RGB/dimensiones de todas las células; conciliación de B con 27.558 registros; hashes de 965 imágenes y 965 anotaciones Full Smear; correspondencia fuente/split de 4.620 tiles, tamaños, etiquetas pareadas y formato de 51.484 anotaciones YOLO. **No se ejecutó ninguna suite científica ni se certificó entrenamiento/evaluación nuevos.**

| Pregunta de aceptación | Respuesta |
|---|---|
| ¿Por qué hay dos materializaciones Cell? | Exportación TFDS estratificada por clase y posterior split gobernado por paciente, con recodificación/nombres distintos (§3–4). |
| ¿Cuál usa cada proceso? | Los cuatro entrypoints usan B por identidad de campaña/TRAIN; TRAIN train+val, EVALUATE/EXPLAIN val, TEST test (§5). |
| ¿Puede eliminarse A? | No ahora; A2 condicionado a preservación y migración, sin autorización de borrado (§12). |
| ¿Qué cambios necesita? | Retirar defaults/allowlist global, desacoplar bootstrap, separar inventario histórico y preservar evidencia (§15). |
| ¿Cómo divide Full Smear? | SAME_SPLIT por paciente, heredado de Cell y persistido en DB; no copia RAW por split (§6–7). |
| ¿Por qué `yolo_rbc_1024_v1`? | Ruta literal en YAML elegida manualmente; no identidad derivada científicamente (§8). |
| ¿Existe identificador Full Smear? | Sí, UUID FROZEN `f0c1f636-715c-54e2-8e46-ed150f9d8791`, además de IDs Polygon/Point (§7, §10). |
| ¿Otro dataset sin sobrescribir? | Físicamente sí con raíz/YAML distintos; no existe protección/identificación suficiente si se reutiliza destino (§8). |
| ¿Cómo se vincula preparación a fuente? | Hoy por UUID fuente en nombres de tile y consulta de asignaciones; falta preparación sellada y vínculo de run (§8, §13). |
| ¿Qué relación tiene connected components? | Inferencia algorítmica parametrizada, sin dependencia directa de Dataset Split ni entrenamiento (§9). |
| ¿Arquitectura mínima? | Versión de población + materialización/preparación + run, aprovechando tablas/FK existentes (§14–16). |

Criterio de cierre posterior: ninguna selección silenciosa de versión/receta; identidad de muestras y particiones preservada; no doble conteo del inventario; ninguna referencia histórica queda apuntando a bytes inexistentes sin una política de archivo explícita; múltiples fuentes/preparaciones coexisten sin mezcla; checkpoint y entrenamiento quedan ligados al manifiesto consumido. Mantener los dos freeze contracts existentes y su alcance, sin promover un freeze de fuente a garantía de tiles.

**Cierre 01A: A2 y B3. Propuesta mínima: 01B consolida consumidores y preserva el baseline antes de cualquier retiro; 01C sella preparaciones y vincula entrenamientos reutilizando PostgreSQL. Se detiene el trabajo en este informe. No se implementaron las correcciones ni se eliminaron archivos.**
