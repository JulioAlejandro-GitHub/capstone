# S1.1 — Procedencia e identidad TFDS ↔ NLM ↔ Capstone

Estado documental: `HISTORICAL_AUDIT`.
Fecha: 2026-10-03. Resultado: **auditoría completada con incertidumbres clínicas explícitas**. No se implementa ni autoriza S2. La aprobación científica queda sujeta a revisión de estas limitaciones; no se declara equivalencia clínica a partir de similitud textual.

## Resultado principal

**TFDS malaria 1.0.0 corresponde al archivo NLM publicado como NLM-Falciparum-Thin-Cell-Images. Maximum demonstrated equivalence level: LEVEL 5 — SAME FILE BYTES**, para las 27.558 imágenes PNG del archivo local cuyo SHA-256 coincide con el checksum oficial del builder instalado. La comparación se hizo contra los bytes del campo `image` de cada TFRecord, no contra los bytes de todo el contenedor TFRecord.

También hay LEVEL 5 entre esas imágenes originales y la materialización protegida `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. La exportación histórica `malaria_physical_split` alcanza LEVEL 4: **same decoded image content, different encoded bytes**, en las 27.558 imágenes. No existe diferencia de píxeles, clase o dimensiones en las comparaciones efectuadas.

**201 identidades:** RESOLVED para la causa técnica: PostgreSQL conserva literalmente los 201 identificadores de los CSV oficiales NLM, hoy descargados de nuevo y byte-idénticos a los usados por Capstone. **Número de personas biológicas y conciliación 200 ↔ 201: UNRESOLVED.** El único par que colapsa bajo el núcleo candidato C/P es C47P8 con sufijos OlympusCX21/Motic; no hay evidencia clínica positiva que autorice fusionarlo.

**Polygon ↔ Cell:** 0 VERIFIED_SAME_PATIENT, 0 VERIFIED_DIFFERENT_PATIENT, 33 UNRESOLVED. Los 33 sufijos candidatos existen en Cell y sus cinco nombres de captura aparecen en los nombres celulares asignados oficialmente al candidato. Esto es evidencia sistemática de procedencia compatible, pero no un mapping clínico publicado ni una comparación de recortes contra frotis. **Scenario C** es el escenario respaldado por el nivel de demostración alcanzado.

## Evidencia y alcance

- [Datasheet oficial NLM](https://lhncbc.nlm.nih.gov/LHC-research/LHC-projects/image-processing/malaria-datasheet.html): el enlace denominado NLM-Falciparum-Thin-Cell-Images apunta literalmente a `https://data.lhncbc.nlm.nih.gov/public/Malaria/cell_images.zip`. El enlace del full smear apunta a NIH-NLM-ThinBloodSmearsPf. La ficha distingue ambos y publica los dos CSV de Patient-ID.
- [Catálogo TFDS](https://www.tensorflow.org/datasets/catalog/malaria), builder **instalado** y checksum preservados en `tfds_malaria_dataset_builder.py.txt`, `tfds_checksums.tsv.txt`, `tfds_image_feature.py.txt`. No se ejecutó `tfds.load`, `download_and_prepare`, ni el downloader histórico.
- `remote_sources.json` contiene URL, fecha UTC, tamaño y SHA-256 de cada fuente pública descargada. Los archivos se guardaron exclusivamente en esta carpeta de auditoría.
- `db_before.json` / `db_after.json` (o sus versiones `.gz`) contienen snapshots de datos científicos, obtenidos mediante SELECT en transacciones REPEATABLE READ con `default_transaction_read_only=on`, verificado por `SHOW transaction_read_only`.
- `image_comparison.csv`: 27.558 comparaciones individuales; `cell_patients.csv`: las 201 identidades completas con sus clases y splits; `polygon_cell_matrix.csv`: los 33 cruces completos; `full_smear_candidates.csv`: los 193 candidatos documentales.
- No se localizó la copia física full-smear de S1 en las rutas exploradas; se solicitó su ubicación. Se auditaron las filas S1 en PostgreSQL y los índices, ReadMe y workbook oficiales. Por ello no se afirma una nueva validación de sus 165 JPEG/GT, ni equivalencia visual célula↔frotis. Los conteos full-smear son documentales/workbook, no un inventario local de imágenes.

## Cadena de procedencia

| Flecha | Estado | Evidencia |
|---|---|---|
| NLM single-cell publicado → cell_images.zip | VERIFIED | Hipervínculo oficial del datasheet |
| cell_images.zip NLM → ZIP local | VERIFIED para identidad del archivo publicado por TFDS | URL de `.INFO`, tamaño 353.452.851, SHA-256 idéntico a checksums.tsv; no se volvió a descargar el ZIP remoto |
| ZIP local → TFDS malaria 1.0.0 | VERIFIED | 27.558 PNG con clase y SHA-256 codificado idénticos a las features de TFRecords |
| TFDS → download_malaria_dataset.py → caché | PARTIALLY_VERIFIED en ejecución histórica | Código y caché coherentes; no existe log inmutable que pruebe qué versión de la librería ejecutó la primera descarga |
| TFDS → export_images → filesystem histórico | VERIFIED en datos y código | Renombrado y PNG por Pillow; 27.558 coincidencias RGB, cero bytes idénticos |
| filesystem histórico → malaria_dataset_split_project → NLM original | VERIFIED | Matching de píxeles+dimensiones+clase y nombre fuente; 27.558 correspondencias revalidadas |
| NLM filename → CSV oficial → clinical_identity | VERIFIED como identificador publicado | Los dos CSV oficiales actuales son idénticos a los históricos; cero errores de mapping en la población |
| source_record → assignment → versión protegida | VERIFIED | 27.558 relaciones, 201 identidades, fingerprints oficiales idénticos |
| NLM original → materialización protegida | VERIFIED | Código `shutil.copyfile` y 27.558 hashes de archivo idénticos |
| Polygon patient → Cell patient | UNRESOLVED | Sufijo y cinco nombres de adquisición coinciden en 33/33; falta demostración de identidad clínica |

## Downloader histórico y transformaciones reales

`malaria_dl_local_project/scripts/download_malaria_dataset.py` importa `src.data`, que reexporta `src.malaria_dl.data.loaders`, y llama únicamente a `get_tfds_data_dir()` para determinar la ruta. Su llamada es:

```python
tfds.load("malaria", split="train", as_supervised=True,
          with_info=True, data_dir=str(data_dir))
```

No fija builder version ni configuración; no pasa `download`, por lo que usa el comportamiento por defecto de TFDS. No itera imágenes, no resizea, no serializa PNG individuales, no renombra, no extrae pacientes. Crea el directorio si falta y muestra metadata. El `data_dir` vigente procede de `TFDS_DATA_DIR` si está definido, o de `<capstone>/data/tensorflow_datasets`. Existe además una caché bajo `malaria_dl_local_project/data/tensorflow_datasets`; la comparación exhaustiva usa **la caché raíz `data/tensorflow_datasets`**. La existencia de dos rutas no demuestra cuál fue la primera históricamente.

La caché auditada declara `malaria/1.0.0`, sin builder config, un split `train`, cuatro shards (6.890/6.889/6.889/6.890), 27.558 ejemplos y features `image`/`label`. Builder instalado en `.venv-local-train`: **tensorflow-datasets 4.9.10**; el requirements de ese entorno fija esa versión, pero el requirements general admite `>=4.9.4`. **Versión exacta de la librería en la primera descarga: UNRESOLVED**; no confundirla con la versión 1.0.0 del dataset, sí comprobada.

El builder descarga y extrae la URL NLM `cell_images.zip`, recorre `Parasitized` y `Uninfected`, acepta `*.png`, usa la key interna `folder_filename` y entrega la ruta a `tfds.features.Image`. El encoder instalado lee los bytes del archivo cuando recibe una ruta: **no re-encodea estos PNG**. El record serializado conserva solo `image` y `label`: no filename, Patient-ID ni key interna. La lectura supervisada decodifica RGB uint8, tamaño variable H×W×3. Las etiquetas originales son 0=parasitized, 1=uninfected.

`create_physical_dataset_split.py` es el exportador separado: lee sin shuffle de shards, enumera ejemplos, asigna el split histórico por imagen, invierte las etiquetas a 0=uninfected/1=parasitized, genera `000001_<clase>.png` con contador por split/clase y guarda con `PIL.Image.fromarray(image).save`. Permite JPEG, pero la metadata real indica PNG. En esa exportación no hay resize: se preservan las dimensiones y los píxeles. El entrenamiento puede transformar imágenes en memoria, fuera de esta procedencia de archivos.

La metadata histórica fecha la exportación el 2026-06-26 y contiene 22.046/2.756/2.756: **no son los splits clínicos protegidos**. El código posterior recupera filenames mediante igualdad de píxeles con originales y obtiene Patient-ID desde CSV NLM, no mediante parser de prefijos. `tfds_index` en DB significa orden del manifest histórico; no es un identificador TFDS estable independiente del orden de lectura. La materialización protegida usa nombres originales y copia los PNG fuente, con splits 22.180/2.693/2.685.

## Equivalencia y conteos

Escala aplicada: LEVEL 0 desconocido; LEVEL 1 mismo origen publicado; LEVEL 2 mismo archivo; LEVEL 3 mismo conjunto lógico; LEVEL 4 mismos píxeles; LEVEL 5 mismos bytes por imagen correspondiente. Los niveles se justifican por comparación, no por igualdad de cardinalidades.

| Fuente | Imágenes | Parasitized | Uninfected | Pacientes/identificadores |
|---|---:|---:|---:|---|
| NLM documentación consultada | No fija total celular en el datasheet | No indicado | No indicado | 193 (148 infectados + 45 no infectados) corresponde al full-smear; no usarlo como conteo single-cell |
| NLM ZIP real + CSV oficiales | 27.558 | 13.779 | 13.779 | 201 identificadores; personas únicas UNRESOLVED |
| TFDS local | 27.558 | 13.779 | 13.779 | No contiene paciente; 201 recuperados mediante mapping exacto al ZIP+CSV |
| Capstone versión protegida | 27.558 | 13.779 | 13.779 | 201 clinical_identities |

La afirmación histórica 150 infectados + 50 no infectados se usa como pregunta de conciliación, no como recuento calculado. El artículo primario referenciado por TFDS no pudo recuperarse en esta sesión (403/429/captcha); no se atribuye a una lectura nueva del artículo.

Hash del ZIP: `0a949556b2414159b5100192609805376654c4266d8d187be9b1922fad43c668`.
Hash canónico de píxeles: SHA-256 de bytes RGB, uint8, orden de filas H×W×3, sin EXIF transpose ni resize. Ancho y alto se comparan separadamente: la clave compuesta es `(width,height,3,sha256)`, coherente con el índice de identidad. El hash de píxeles almacenado en DB no incluye dimensiones; la auditoría sí las valida.

| Comparación contra NLM ZIP | Iguales bytes | Iguales píxeles/dimensiones | Total |
|---|---:|---:|---:|
| TFRecord image+class | 27.558 | 27.558 | 27.558 |
| Capstone protegido | 27.558 | 27.558 | 27.558 |
| Capstone exportación histórica | 0 | 27.558 | 27.558 |
| Hashes/dimensiones registrados PostgreSQL | 27.558 hashes coincidentes | 27.558 | 27.558 |

## Por qué hay 201 clinical_identities

Los CSV oficiales contienen 151 IDs en parasitized y 201 en uninfected; su unión es 201. Hay 151 identificadores con ambas clases y 50 solo con células uninfected. Esto describe clases celulares observadas, no sustituye el diagnóstico del donante. La lista completa está en `cell_patients.csv`.

Cada uno de los 27.558 filenames se asigna exactamente al ID registrado en DB. El parser exploratorio `filename antes de _IMG_`, conservando sufijos y case, produce también 201 grupos y **cero discrepancias** con CSV. No hay IDs nulos, colisiones por case, ni una identidad agregada por Capstone al mapping oficial.

El único núcleo C/P duplicado es:

| ID oficial | UUID clinical_identity | Células | P | U | Split |
|---|---|---:|---:|---:|---|
| C47P8thinOriginalOlympusCX21 | 15612ccb-c11a-5367-8090-9c50fbed208b | 67 | 2 | 65 | train |
| C47P8thin_Original_Motic | 4b152d53-306d-516f-9a62-34df4d87134c | 77 | 8 | 69 | train |

Agrupar exploratoriamente por `C` numérico y eventual `P` numérico produce 200 núcleos y solo ese par de colisión. Los sufijos son compatibles con variantes de adquisición por microscopio, pero **no se demuestra que sean una persona**. Se explica exactamente de dónde surge el identificador adicional; no se declara demostrado que haya 200 seres humanos únicos. Ambos candidatos están en TRAIN: no hay un cruce de split entre ellos actualmente, aun si una fase posterior verifica el alias.

La fuente full-smear contiene ambos nombres: `146C47P8thin_Original_Motic` en Polygon y `148C47P8thinOriginalOlympusCX21` en Point. Esto refuerza la necesidad de distinguir directorios/identificadores de personas únicas en ambos datasets.

## Full smear, Polygon, Point y prefijos

El [ReadMe oficial](https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/ReadMe.pdf) describe 193 pacientes, cinco imágenes por paciente y el layout de directorios por Patient ID. El [workbook oficial](https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/Dataset_statistics.xlsx) aporta 965 filas de imágenes, agrupadas como sigue. Los índices públicos concuerdan con los directorios.

| Conjunto | Directorios de paciente | Imágenes | Imágenes/ID | RBC P | RBC U | WBC |
|---|---:|---:|---:|---:|---:|---:|
| Polygon | 33 | 165 | 5 | 1.142 | 33.071 | 51 |
| Point | 160 | 800 | 5 | 6.810 | 155.640 | 220 |
| Completo | 193 | 965 | 5 | 7.952 | 188.711 | 271 |

El datasheet declara 148 infectados + 45 no infectados para el completo. No se asigna esa condición clínica individual contando etiquetas celulares. Los conteos Polygon coinciden con las metadata S1 de PostgreSQL: 34.264 polígonos, 34.213 RBC y 51 WBC.

Quitar solo dígitos iniciales de los 193 directorios produce 193 sufijos distintos presentes en los 201 IDs celulares. Quedan fuera ocho IDs celulares: `C1_thinF`, `C203ThinF`, `C204ThinF`, `C206ThinF`, `C207ThinF`, `C209ThinF`, `C33P1thinF`, `C37BP2_thinF`. Esto reconcilia **conjuntos de nombres 201 vs 193**, no prueba ocho personas excluidas.

El prefijo numérico tiene 193 valores únicos, rango 142–380 con huecos. Para `228C86P47ThinF`, `228` funciona estructuralmente como parte del nombre de directorio; **su significado semántico es UNRESOLVED**. No hay una definición oficial hallada que permita generalizar `remove_numeric_prefix` como regla de identidad. La transformación solo genera candidatos y no cambia case, sufijos ni nombres.

Además del sufijo, 188/193 candidatos comparten los cinco stems de adquisición del workbook; cinco candidatos Point comparten cuatro. **Los 33 Polygon comparten los cinco.** Los nombres de captura siguen siendo metadata textual; no se ha verificado la derivación espacial de un crop del frotis ni recibido una tabla clínica cross-source del custodio.

## Matriz completa Polygon ↔ Cell

En todas las filas el candidato está presente en Cell; status UNRESOLVED; split vacío intencionalmente. La evidencia por fila es el sufijo del directorio oficial y 5/5 stems de adquisición en los nombres celulares del mapping NLM. `polygon_cell_matrix.csv` añade las clases celulares del candidato; esos conteos no implican paciente compartido verificado.

| Polygon ID | Cell candidate | Estado | Split | Imágenes | RBC | Parasitized | Uninfected |
|---|---|---|---|---:|---:|---:|---:|
| 142C38P3thinF_original | C38P3thinF_original | UNRESOLVED | — | 5 | 1004 | 5 | 999 |
| 146C47P8thin_Original_Motic | C47P8thin_Original_Motic | UNRESOLVED | — | 5 | 948 | 9 | 939 |
| 150C49P10thinF | C49P10thinF | UNRESOLVED | — | 5 | 1151 | 43 | 1108 |
| 153C52P13thinF | C52P13thinF | UNRESOLVED | — | 5 | 916 | 30 | 886 |
| 156C55P16thinF | C55P16thinF | UNRESOLVED | — | 5 | 896 | 3 | 893 |
| 158C57P18thinF | C57P18thinF | UNRESOLVED | — | 5 | 1145 | 5 | 1140 |
| 208C67P28N_ThinF | C67P28N_ThinF | UNRESOLVED | — | 5 | 1195 | 42 | 1153 |
| 209C68P29N_ThinF | C68P29N_ThinF | UNRESOLVED | — | 5 | 992 | 349 | 643 |
| 211C70P31_ThinF | C70P31_ThinF | UNRESOLVED | — | 5 | 500 | 69 | 431 |
| 212C71P32_ThinF | C71P32_ThinF | UNRESOLVED | — | 5 | 1169 | 10 | 1159 |
| 221C79P40ThinF | C79P40ThinF | UNRESOLVED | — | 5 | 771 | 4 | 767 |
| 228C86P47ThinF | C86P47ThinF | UNRESOLVED | — | 5 | 1240 | 4 | 1236 |
| 231C89P50ThinF | C89P50ThinF | UNRESOLVED | — | 5 | 1081 | 58 | 1023 |
| 236C94P55ThinF | C94P55ThinF | UNRESOLVED | — | 5 | 1262 | 10 | 1252 |
| 244C7NthinF | C7NthinF | UNRESOLVED | — | 5 | 1029 | 0 | 1029 |
| 247C99P60ThinF | C99P60ThinF | UNRESOLVED | — | 5 | 847 | 313 | 534 |
| 263C115P76ThinF | C115P76ThinF | UNRESOLVED | — | 5 | 1204 | 13 | 1191 |
| 270C122P83ThinF | C122P83ThinF | UNRESOLVED | — | 5 | 798 | 3 | 795 |
| 274C126P87ThinF | C126P87ThinF | UNRESOLVED | — | 5 | 700 | 22 | 678 |
| 276C128P89ThinF | C128P89ThinF | UNRESOLVED | — | 5 | 839 | 86 | 753 |
| 282C134P95ThinF | C134P95ThinF | UNRESOLVED | — | 5 | 623 | 10 | 613 |
| 302C210ThinF | C210ThinF | UNRESOLVED | — | 5 | 1307 | 0 | 1307 |
| 305C212ThinF | C212ThinF | UNRESOLVED | — | 5 | 1412 | 0 | 1412 |
| 306C213ThinF | C213ThinF | UNRESOLVED | — | 5 | 1303 | 0 | 1303 |
| 309C216ThinF | C216ThinF | UNRESOLVED | — | 5 | 1257 | 0 | 1257 |
| 318C226ThinF | C226ThinF | UNRESOLVED | — | 5 | 1343 | 0 | 1343 |
| 323C231ThinF | C231ThinF | UNRESOLVED | — | 5 | 1081 | 0 | 1081 |
| 327C235ThinF | C235ThinF | UNRESOLVED | — | 5 | 1519 | 0 | 1519 |
| 343C160P121ThinF | C160P121ThinF | UNRESOLVED | — | 5 | 756 | 3 | 753 |
| 354C169P130ThinF | C169P130ThinF | UNRESOLVED | — | 5 | 1189 | 7 | 1182 |
| 362C177P138NThinF | C177P138NThinF | UNRESOLVED | — | 5 | 999 | 30 | 969 |
| 372C187P148NThinF | C187P148NThinF | UNRESOLVED | — | 5 | 794 | 14 | 780 |
| 377C238NThinF | C238NThinF | UNRESOLVED | — | 5 | 943 | 0 | 943 |

## Cross-family y decisión S2

```text
Polygon patients = 33
VERIFIED_SAME_PATIENT = 0
VERIFIED_DIFFERENT_PATIENT = 0
UNRESOLVED = 33
Verified shared patients in TRAIN = 0
Verified shared patients in VAL = 0
Verified shared patients in TEST = 0
```

Los ceros de pacientes verificados **no significan ausencia de solapamiento o leakage**. Expresan ausencia de demostración suficiente. No se trasladan los splits de candidatos a la matriz clínica y no se crean assignments smear.

**Scenario C:** mantener identidades independientes y documentar incertidumbre. No presentar una evaluación cross-family como clínicamente independiente basándose en esa separación técnica. Para elevar un cruce a VERIFIED_SAME_PATIENT hace falta una correspondencia oficial explícita o evidencia positiva reproducible de procedencia del frotis/crop ligada a las identidades oficiales. La ubicación de las imágenes originales permitiría investigar esa segunda vía. Si se resuelve posteriormente, reevaluar A/B, heredar assignments compartidos y medir utilidad de la distribución antes de implementar S2.

## Integridad y hallazgos no corregidos

DB writes = 0; dataset writes = 0; assignments changed = 0, para las acciones de esta auditoría. Se escribieron únicamente scripts/reportes/pruebas y documentación de auditoría. Las conexiones no cargan FastAPI ni llaman bootstrap/ingest/freeze/generación/materialización/migración. El guard Python restringe las consultas; la protección efectiva contra escrituras la impone PostgreSQL READ ONLY desde la apertura de conexión. No se prueba un rechazo DML contra la BD: los tests son offline.

Los snapshots antes/después comparan las filas completas y sus hashes de `datasets`, `dataset_version_sources`, `clinical_identities`, `dataset_source_records`, `identity_evidence`, `dataset_split_assignments` y `dataset_materializations`, además de la fila completa de la versión protegida. `integrity.json` registra el resultado. Los 55.116 archivos físicos comparados se vuelven a hashear al cierre. Esta evidencia acota las acciones de la auditoría y el estado observado; no es un log global de todos los procesos externos.

| Fingerprint oficial | BEFORE | AFTER |
|---|---|---|
| source_population_sha256 | `eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0` | idéntico |
| clinical_identity_sha256 | `d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59` | idéntico |
| patient_assignment_sha256 | `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f` | idéntico |
| record_assignment_sha256 | `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2` | idéntico |

S1 conserva 33 identidades, 165 source records y 165 identity evidence; los hints UNVERIFIED y el resto de campos permanecen byte-equivalentes en su serialización canónica del snapshot. No se modificó ningún registro ni el documento S1.

**Hallazgo documental:** ReadMe.pdf registrado en S1: `0684e14c188c2ae74aaf5d0da12c7d5c73ee233078e3214f6df652ff1502bd8d`; ReadMe remoto actual: `2fe6ab9b218b5b840a6979947b2dbc548f5ca244024e909cf0bf543d7a83b3f1`. No se puede concluir la causa sin la copia S1. Dataset_statistics.xlsx sí coincide: `f4e8abe005763b97c0480c347ec19e016d6138b1f9dec37d2cc8aab53bc7b974`. No se reemplazó ningún hash ni evidencia de S1.

## Tests y reproducción

Los tests offline cubren sufijos de Patient-ID, nombres inválidos, generación de candidatos sin fusionar variantes, hashes RGB independientes de codificación, sensibilidad a dimensiones y rechazo de SQL ajeno al SELECT permitido. Ejecución mediante Makefile:

```sh
make -f scripts/audit_s1_1/Makefile test
```

Resultado: 5 tests PASS. No se ejecutaron tests de integración que pudieran escribir en PostgreSQL.

Desde la raíz del repositorio, para reproducir las lecturas (salidas únicamente dentro del directorio de auditoría):

```sh
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python /scripts/audit_s1_1/db_snapshot.py > docs/audits/s1_1/db_before.json
PYTHONDONTWRITEBYTECODE=1 TF_CPP_MIN_LOG_LEVEL=3 malaria_dl_local_project/.venv-local-train/bin/python scripts/audit_s1_1/inspect_images.py
PYTHONDONTWRITEBYTECODE=1 malaria_dl_local_project/.venv-local-train/bin/python scripts/audit_s1_1/inspect_smears.py
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python /scripts/audit_s1_1/db_snapshot.py > docs/audits/s1_1/db_after.json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/audit_s1_1/verify_evidence.py
```

`fetch_sources.py` refresca únicamente las fuentes documentales oficiales dentro del reporte; una futura ejecución puede encontrar contenido distinto y debe conservarse como otra corrida de auditoría. Los scripts no tienen comandos de mutación de datos. Sus archivos de entrada y código relevante están identificados en `code_hashes.json`, `remote_sources.json`, `image_summary.json` e `integrity.json`.

## Git

Branch auditada: `s1-smear-segmentation-source-adapter`.
Commit HEAD auditado: `080af7d1f819f470639135d456544dd9f2ffd8d5`.
Parent SHA: `0835c82cba6c054bb2132632096b8c33c1a63ed6`.
No se creó commit ni se cambió de branch. El estado inicial no tenía modificaciones tracked; al cierre hay únicamente los nuevos artefactos de auditoría y su entrada de índice documental. `git_status.txt` conserva el estado final exacto. Las fuentes de aplicación, datasets y BD no se versionan como modificaciones de S1.1.
