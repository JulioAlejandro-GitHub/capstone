# S1.D — Downloader Full Smears y preparación de fuentes

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-03.
Resultado: **S1.D implementada y verificada**, incluido el addendum `prepare_datasets.py`. Distribución RAW completa disponible; no se implementó S1.2, S2 ni YOLO. Criterios operacionales cumplidos después de corregir y probar un enlace NLM con espacios sin codificar. No se hizo commit ni push.

## A. Inspección inicial

```text
malaria_dataset_split_project/.env exists = NO
.env ignored by git = YES
existing env loader for split project = NONE (os.getenv only)
existing dotenv pattern elsewhere = dotenv_values / python-dotenv
THIN_BLOOD_SMEARS_PF_ROOT consumer = malaria_split.cli._resolve_source_root
consumer commands = inspect-source / ingest-source
initial git status = clean
```

El CLI anterior conservaba ROOT explícito/env y devolvía la ruta expandida sin default. Se incorporó resolución central SOURCE/ROOT y `.env` opcional, sin crear un `.env` real. Se conservó la función pública existente y `--root`. La ruta canónica no existía y no había override local que apuntara a una copia anterior; no se adoptó ni reemplazó ninguna copia S1.

El archivo ML `common/paths.py` ya contenía las rutas base. La resolución de TFDS se trasladó allí sin cambiar el contrato; el loader existente la delega. La descarga celular ahora expone una función reutilizable y conserva TFDS, fijando su versión aprobada 1.0.0. La evidencia de procedencia S1.1 no se reabrió.

## B. Archivos creados/modificados

Lista exacta al cierre (el dataset RAW y el staging no aparecen porque están ignorados):

- `.gitignore`
- `Makefile`
- `docs/README.md`
- `malaria_dataset_split_project/.env.example`
- `malaria_dataset_split_project/pyproject.toml`
- `malaria_dataset_split_project/src/malaria_split/cli.py`
- `malaria_dl_local_project/scripts/download_malaria_dataset.py`
- `malaria_dl_local_project/src/malaria_dl/common/paths.py`
- `malaria_dl_local_project/src/malaria_dl/data/loaders.py`
- `docs/audits/s1_d/REPORT.md`
- `docs/audits/s1_d/acquisition_summary.json`
- `docs/audits/s1_d/first_run.log`
- `docs/audits/s1_d/full_verify_stdlib.log`
- `docs/audits/s1_d/git_status.txt`
- `docs/audits/s1_d/prepare_default.log`
- `docs/audits/s1_d/prepare_verify_only.log`
- `docs/audits/s1_d/protected_after.json`
- `docs/audits/s1_d/protected_before.json`
- `docs/audits/s1_d/resume_run.log`
- `docs/audits/s1_d/second_run.log`
- `docs/audits/s1_d/tests_new.log`
- `docs/audits/s1_d/tests_regression.log`
- `docs/operations/dataset_source_preparation.md`
- `malaria_dataset_split_project/src/malaria_split/source_config.py`
- `malaria_dl_local_project/scripts/download_full_smears_dataset.py`
- `malaria_dl_local_project/scripts/prepare_datasets.py`
- `malaria_dl_local_project/src/malaria_dl/data/cell_source.py`
- `malaria_dl_local_project/src/malaria_dl/data/full_smears_download.py`
- `malaria_dl_local_project/tests/source_preparation/test_sources.py`

## C. Configuración y operación

SOURCE = origen publicado/esperado; ROOT = ruta física local. Defaults:

```dotenv
MALARIA_CELL_DATASET_SOURCE=https://data.lhncbc.nlm.nih.gov/public/Malaria/cell_images.zip
MALARIA_CURRENT_SPLIT_ROOT=malaria_dl_local_project/data/malaria_physical_split
THIN_BLOOD_SMEARS_PF_SOURCE=https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/index.html
THIN_BLOOD_SMEARS_PF_ROOT=malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf
```

Precedencia: `--root` > env del proceso > `.env` existente > default. SOURCE no tiene flag CLI: env > `.env` > default. Paths relativos anclados a la raíz capstone; sin dependencia del cwd. `MALARIA_CURRENT_SPLIT_ROOT` sigue describiendo el split físico previo y no cambia la versión protegida. En su auditor, el YAML existente permanece como fallback si no hay override.

Cambiar SOURCE no cambia ni autoriza reutilizar una Dataset Version. Full Smear rechaza una SOURCE diferente a la del manifiesto local. Cell rechaza una URL distinta a la NLM aprobada con `SOURCE_MISMATCH`; no pasa URLs arbitrarias a TFDS ni afirma que otro origen sea equivalente. No se usan internals privados del builder para simular esa validación.

Comando unificado:

```sh
python malaria_dl_local_project/scripts/prepare_datasets.py
```

Comandos individuales y modo offline:

```sh
python malaria_dl_local_project/scripts/download_malaria_dataset.py
python malaria_dl_local_project/scripts/download_full_smears_dataset.py
python malaria_dl_local_project/scripts/prepare_datasets.py --verify-only
```

El orquestador llama directamente a `prepare_cell_source` y `prepare_full_smear_source`; no usa subprocess ni duplica descargas. Se probó el comando unificado tanto normal como `--verify-only`: ambos acabaron en `DATASET SOURCES: READY`, con las dos fuentes ya presentes y sin descargar.

`--split 80 10 10` queda reservado y devuelve exit code 2 / `SPLIT_NOT_ENABLED` antes de preparar datos. Informa Cell gobernado AVAILABLE y Smear PENDING_S2. Se inspeccionaron `prepare_split_generation`, `persist_split_generation` y el optimizador patient-level: requieren contexto de gobernanza/versión y no son una API de porcentajes libre para nuevas familias. La integración futura deberá delegar allí, mantener la unidad paciente y no sobrescribir versiones. No se llama al split histórico por imagen.

Guía de clone limpio, recuperación y uso: [preparación de fuentes](../../operations/dataset_source_preparation.md).

## D. Distribución NLM y URLs utilizadas

Se inspeccionó el [índice oficial](https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/index.html), sus enlaces y el directorio central ZIP mediante HTTP Range antes de implementar. El ZIP tiene 2.601 entradas (incluidos directorios), 965 JPG, 965 TXT, 87 Thumbs.db y tres documentos raíz. Los nombres del ZIP empiezan directamente por Point Set/Polygon Set, sin un directorio externo adicional. No fue necesario recorrer ni descargar imágenes una a una.

Las siguientes cinco transferencias son las utilizadas por el downloader. Los hashes son **LOCAL_BASELINE_SHA256**, no checksums oficiales NLM. El índice inspeccionado no publica checksum del ZIP. Se validan TLS, Content-Length disponible, CRC ZIP, inventario SHA-256 y estructura.

| URL efectiva | Bytes | SHA-256 local |
|---|---:|---|
| `https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/index.html` | 1,783 | `74f53d1e65c45ad057be90425e7c284e44f0d44b7ffbf9b7db7d7bf4f7c75e1e` |
| `https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/NIH-NLM-ThinBloodSmearsPf.zip` | 690,355,704 | `3d86af70b3a80d7ecdcc07f8fee0d0d9c9c197cccd907e239abb92c0357c3ea9` |
| `https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/ReadMe.pdf` | 200,535 | `2fe6ab9b218b5b840a6979947b2dbc548f5ca244024e909cf0bf543d7a83b3f1` |
| `https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/Dataset_statistics.xlsx` | 66,112 | `f4e8abe005763b97c0480c347ec19e016d6138b1f9dec37d2cc8aab53bc7b974` |
| `https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/Data%20License%20Agreement.docx` | 22,625 | `e7617a7206967e1806ba335f8b986880c959fbb4d81295dc71049c8639d4b86f` |

El índice enlaza `Data License Agreement.docx` con espacios literales; ahora se codifican como `%20` sin doble codificación. El caso está cubierto por test offline.

## E. Resultado físico

| Conjunto | IDs/directorios | Imágenes | GT | Imágenes/ID |
|---|---:|---:|---:|---:|
| Polygon Set | 33 | 165 | 165 | 5 |
| Point Set | 160 | 800 | 800 | 5 |
| Total | 193 | 965 | 965 | 5 |

Hay tres documentos NLM distintos y una segunda versión explícita de ReadMe (cuatro archivos documentales físicos), además de 87 Thumbs.db preservados. El inventario RAW total contiene **2.021 archivos / 798.756.574 bytes**, excluyendo el propio manifiesto. No se renombró, recodificó, redimensionó ni transformó ningún archivo original del ZIP. La extracción lee todos los miembros y comprueba su CRC; el test de estructuras valida asociaciones imagen↔GT, no interpreta polígonos ni produce máscaras.

## F. Ruta canónica y GT

ROOT absoluto:

```text
/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf
```

Representación configurable: `malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf`.

Annotations para la futura fase de segmentación:

```text
ROOT/Polygon Set/<Patient ID>/GT/<ImageName>.txt
```

Imágenes correspondientes: `ROOT/Polygon Set/<Patient ID>/Img/<ImageName>.jpg`. Se verificaron físicamente las 165 parejas. Point Set conserva sus 800 parejas. Esta raíz es RAW inmutable; los futuros derivados deben ubicarse fuera de ella.

## G. Primera preparación real y recuperación

La primera invocación se detuvo después de descargar cuatro recursos debido al enlace de licencia con espacios: **no produjo READY ni publicó ROOT**. La traza original se conserva en `first_run.log`. Se corrigió la codificación, se agregaron tests y se reanudó sin repetir el ZIP ni los documentos completados.

```text
Primera transferencia local creada: 2026-10-03T11:40:59.084355+00:00
Primer intento: 4 recursos / 690.624.134 bytes adquiridos
Reanudación iniciada: 2026-10-03T11:42:34.671709+00:00
Reanudación: 1 recurso / 22.625 bytes nuevos (licencia)
Fin de preparación validada: 2026-10-03T11:42:41.119613+00:00
Duración de la reanudación completa: 6,448 segundos
Total adquisición: 5 recursos / 690.646.759 bytes
Integrity = PASS
Status = READY
```

La hora inicial registrada corresponde a la creación del primer archivo de transferencia en el filesystem, no a una marca inventada del arranque del proceso. `transfers[].retrieved_at` conserva las fechas UTC individuales y permite distinguir lo adquirido antes de la interrupción de lo adquirido al reanudar. `resume_run.log` reporta honestamente solo el recurso nuevo de esa invocación.

La caché de transferencias permanece en `.NIH-NLM-ThinBloodSmearsPf.download/` (ZIP original y receipts). No es una segunda copia extraída. `.part` nunca implica archivo completo y la publicación final solo ocurre tras validar. ROOT previo sin manifest, otro SOURCE o hashes conflictivos provocan error sin sobrescritura. Un lock abandonado tras muerte abrupta exige comprobar que no haya proceso activo antes de retirar exclusivamente ese lock técnico.

## H. Segunda ejecución y verify-only

Segunda invocación posterior a READY, ejecutada sin permisos de red del sandbox:

```text
downloaded files = 0
downloaded bytes = 0
Integrity = PASS
Status = ALREADY_DOWNLOADED
```

Evidencia: `second_run.log`. Se probó también Full Smear `--verify-only` con el Python de sistema, sin entorno TFDS y sin Docker: `full_verify_stdlib.log`. El orquestador normal y el de verificación finalizaron READY (`prepare_default.log`, `prepare_verify_only.log`). Las pruebas offline comprueban además que la verificación no cambia bytes ni mtimes y que el callback de descarga recibe cero llamadas.

## I. Manifiesto y versiones documentales

Manifest local, ignorado por Git:

```text
/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf/.capstone_download_manifest.json
```

SHA-256 del manifiesto: `f9fa9e72cc686a0e3b3e6e30d07abaf713d7c19295960fbf1ef0405e587aafa6`. Contiene 2.021 entradas con path relativo, size y sha256, SOURCE exacta, fechas, URLs efectivas, tres pares de versiones documentales y conteos. Resumen pequeño versionable: `acquisition_summary.json`; no se copia el dataset ni su manifiesto completo a Git.

ReadMe difiere entre el ZIP y el enlace standalone y ambas versiones se preservan explícitamente:

| Archivo | SHA-256 |
|---|---|
| `ROOT/ReadMe.pdf` (ZIP) | `0684e14c188c2ae74aaf5d0da12c7d5c73ee233078e3214f6df652ff1502bd8d` |
| `ROOT/.capstone_source_documents/ReadMe.pdf` (standalone) | `2fe6ab9b218b5b840a6979947b2dbc548f5ca244024e909cf0bf543d7a83b3f1` |

Workbook y licencia coinciden entre ZIP y standalone y tienen una sola copia física en ROOT. No se comparó ni concilió esta adquisición con registros PostgreSQL S1, ni se reemplazó evidencia S1.

## J. Tests y regresión

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Nuevos S1.D (`make test-dataset-sources`) | 27 | 0 | 0 |
| Regresión relevante (`make test-dataset-source-regression`) | 35 | 0 | 1 |

La omisión histórica corresponde al test de colisiones de case en un filesystem case-insensitive (macOS). No se modificó ese test. La suite S1.D cubre defaults/overrides, precedencia ROOT, manifest, idempotencia, modo offline, ausencia de mutación, archivos incompletos/truncados, hash mismatch, estructura, versiones documentales, SOURCE persistida/conflictiva, URL con espacios, reanudación, ZIP traversal y nombres reservados, TFDS cache sin load/download y rechazo temprano de `--split`.

Todos los tests son offline y usan fixtures temporales. No se levantó infraestructura ni se ejecutaron tests PostgreSQL. Se respetó la independencia operacional exigida por S1.D mediante targets Makefile locales explícitos.

## K. Integridad científica

```text
PostgreSQL writes = 0 (no conexiones PostgreSQL)
S1 records changed by this phase = 0
assignments changed by this phase = 0
Dataset Versions created = 0
YOLO datasets created = 0
tiles created = 0
protected cell dataset changed = NO
clinical cross-source hints modified = 0
```

No se ejecutaron bootstrap, ingest, migrations, generación, freeze ni materialization. No se buscó resolver la identidad Cell↔Full Smear. La comprobación PostgreSQL no se repitió: estuvo fuera de esta fase y ninguna ruta ejecutada abre una conexión a ella; los ceros describen las operaciones realizadas, no una auditoría global de procesos externos.

Se recalcularon antes y después los SHA-256 de los **27.558 archivos físicos protegidos** y un digest de `relative_path|file_sha256` en orden lexicográfico:

```text
BEFORE = 477298cc9875bc403b4a83f02e0a1a021c80f4c4ebb32e2f848812be05fc3527
AFTER  = 477298cc9875bc403b4a83f02e0a1a021c80f4c4ebb32e2f848812be05fc3527
BEFORE == AFTER
```

Este digest físico de S1.D **no es** el fingerprint oficial de assignments/BD. Evidencia exacta: `protected_before.json`, `protected_after.json`. No se modificaron filas ni contratos oficiales.

## L. Git

```text
branch: s1-smear-segmentation-source-adapter
HEAD: 1d454c29fd644f36a5544c8a2f256dd0d3da1d92
parent SHA: 080af7d1f819f470639135d456544dd9f2ffd8d5
commit creado en S1.D: NO
push: NO
```

`git_status.txt` contiene el estado final detallado. `git check-ignore` confirma que ROOT, staging y `.env` están excluidos. Solo código, plantilla, tests, documentación y evidencia pequeña de ejecución aparecen como cambios. `git diff --check` pasa.
