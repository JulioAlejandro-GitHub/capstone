# Preparación de fuentes científicas — S1.D

Estado documental: `CURRENT_DOC`. Alcance: descargar/verificar fuentes RAW; no crear splits, versiones, tiles ni datasets YOLO.

## Después de clonar

Desde la raíz `capstone`, instalar las dependencias del entorno ML según `malaria_dl_local_project/requirements.txt` (o el entorno local fijado en `requirements-local-train.txt`) y ejecutar:

```sh
python malaria_dl_local_project/scripts/prepare_datasets.py
```

El orquestador llama a las mismas funciones Python reutilizables de los dos downloaders. No ejecuta scripts por subprocess, no importa servicios PostgreSQL y no necesita Docker, backend ni frontend. Para ejecutar cada fuente por separado:

```sh
python malaria_dl_local_project/scripts/download_malaria_dataset.py
python malaria_dl_local_project/scripts/download_full_smears_dataset.py
```

Full Smears requiere solo biblioteca estándar de Python cuando no existe `.env`. Si se utiliza la configuración local opcional, requiere también `python-dotenv`, dependencia ya utilizada por el proyecto. Cell y el orquestador requieren el entorno TensorFlow/TFDS existente.

## SOURCE y ROOT

SOURCE identifica el origen esperado; ROOT identifica la ubicación física local. La resolución central está en `malaria_dataset_split_project/src/malaria_split/source_config.py`.

| Configuración | Default |
|---|---|
| `MALARIA_CELL_DATASET_SOURCE` | `https://data.lhncbc.nlm.nih.gov/public/Malaria/cell_images.zip` |
| `MALARIA_CURRENT_SPLIT_ROOT` | `malaria_dl_local_project/data/malaria_physical_split` |
| `THIN_BLOOD_SMEARS_PF_SOURCE` | `https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/index.html` |
| `THIN_BLOOD_SMEARS_PF_ROOT` | `malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf` |

Precedencia de Full Smear ROOT: `--root` > variable del proceso > `malaria_dataset_split_project/.env` > default. SOURCE: variable del proceso > ese `.env` > default. Las rutas relativas se resuelven desde `capstone`, independientemente del directorio de trabajo. Se conserva `--root` de `malaria-split inspect-source` / `ingest-source`; S1.D no ejecuta ingest. El auditor del split existente conserva también el fallback de su configuración YAML.

No se crea `.env` automáticamente ni se lee `.env.example` como configuración activa. Para overrides opcionales:

```sh
cp malaria_dataset_split_project/.env.example malaria_dataset_split_project/.env
```

El archivo `.env` está ignorado por Git. Se reutiliza `dotenv_values` sin expansión de variables, sin ejecutar instrucciones de shell y sin alterar `os.environ`. `MALARIA_CURRENT_SPLIT_ROOT` mantiene su significado de split físico existente: no selecciona ni reemplaza una Dataset Version.

`TFDS_DATA_DIR` conserva su contrato anterior: variable del proceso o `capstone/data/tensorflow_datasets`. El downloader celular mantiene TFDS y fija el builder aprobado `malaria:1.0.0`. SOURCE no se pasa como una URL arbitraria a `tfds.load`. Una URL celular diferente provoca `SOURCE_MISMATCH` antes de usar TFDS; una nueva procedencia requiere una integración y gobernanza explícitas. La procedencia aprobada se basa en S1.1, sin depender de atributos privados del builder instalado.

## Full Smears RAW e integridad

El índice oficial es HTML, no el archivo del dataset. El downloader descubre dentro de él el ZIP completo y los enlaces de `ReadMe.pdf`, `Dataset_statistics.xlsx` y `Data License Agreement.docx`, restringidos a HTTPS y al mismo origen. Conserva imágenes, GT, IDs/directorios, nombres, bytes y auxiliares `Thumbs.db` tal como están publicados.

La estructura aprobada procede del ReadMe y workbook NLM auditados en S1.1: Polygon 33 IDs/165 imágenes; Point 160 IDs/800 imágenes; cinco imágenes y cinco GT asociados por stem en cada directorio. Se comprueban presencia, encabezado y cuerpo no vacío del GT, sin interpretar geometría ni crear máscaras. Un cambio de estructura falla con `DATASET_STRUCTURE_MISMATCH`.

Primera preparación: descarga a `.NIH-NLM-ThinBloodSmearsPf.download`, usa archivos `.part`, valida Content-Length cuando está disponible, CRC del ZIP, estructura y hashes SHA-256, y publica la carpeta RAW por rename una vez completa. El manifiesto `.capstone_download_manifest.json` registra SOURCE, URLs efectivas, fechas UTC, hashes, tamaños, estructura y versiones documentales. El ZIP y receipts completados quedan en staging como caché verificable para recuperar interrupciones; no hay una segunda copia extraída.

NLM no publica checksum de este ZIP en el índice inspeccionado. Los hashes son **LOCAL_BASELINE_SHA256**, no OFFICIAL_CHECKSUM. Sirven para comprobar estabilidad local después de adquirir por HTTPS la distribución oficial; no constituyen una firma del custodio. Una segunda ejecución válida recalcula el inventario/hashes, valida estructura, devuelve `ALREADY_DOWNLOADED` y no abre la red.

El ReadMe dentro del ZIP difiere del publicado por separado. Ambos se preservan explícitamente: el del ZIP queda en `ROOT/ReadMe.pdf`, y el documento standalone en `ROOT/.capstone_source_documents/ReadMe.pdf`. `document_versions` registra las URLs y ambos hashes. Esta política solo se aplica durante una nueva adquisición; una copia RAW previa nunca se sobrescribe silenciosamente.

## Verificación sin descarga

```sh
python malaria_dl_local_project/scripts/download_full_smears_dataset.py --verify-only
python malaria_dl_local_project/scripts/download_malaria_dataset.py --verify-only
python malaria_dl_local_project/scripts/prepare_datasets.py --verify-only
```

No escriben en los datasets ni necesitan red con entradas locales completas. Full Smear verifica todos los archivos contra el manifiesto, incluidos archivos adicionales o faltantes. Cell lee y decodifica todos los TFRecords existentes y comprueba versión, etiquetas y 27.558 ejemplos (13.779 por clase); esta comprobación no repite la comparación científica SHA-256 de S1.1. No repara una caché existente ni recodifica imágenes. Un error produce exit code distinto de cero.

La importación de TensorFlow puede crear cachés auxiliares de bibliotecas en ubicaciones de usuario/temporales; esto no modifica los datos científicos. Se puede fijar `MPLCONFIGDIR` a un directorio temporal si el entorno lo requiere.

## Interrupciones y conflictos

Una transferencia incompleta nunca se publica como archivo final. Al repetir, se conservan archivos completados con receipt válido y solo se repiten las transferencias pendientes. Una extracción incompleta se reconstruye exclusivamente dentro del staging propio. Si un proceso muere sin liberar `active.lock`, verificar primero que no exista un downloader activo antes de retirar ese archivo técnico y repetir. No eliminar ROOT ni los archivos científicos para desbloquear.

ROOT existente sin manifiesto válido, hash diferente, SOURCE diferente, enlace ambiguo, autenticación inesperada o estructura distinta: detenerse e investigar. No existe `--overwrite` ni adopción automática de copias antiguas. Las futuras variaciones de SOURCE requieren validación independiente; no son autorización para reutilizar una identidad científica o Dataset Version.

La ruta default y staging están ignorados por Git. Si se configura un ROOT alternativo dentro del repositorio, añadir su ruta concreta al ignore local antes de descargar; nunca versionar imágenes/GT/manifiestos generados. Las copias RAW se tratan como inmutables y las derivaciones futuras deben ir a otra raíz.

## Punto de entrada futuro para splits

```sh
python malaria_dl_local_project/scripts/prepare_datasets.py --split 80 10 10
```

En S1.D devuelve exit code 2 con `SPLIT_NOT_ENABLED` y `Smear Segmentation: PENDING_S2`, **antes de preparar fuentes**. No produce un split parcial ni toca `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.

El módulo oficial ya ofrece `prepare_split_generation(connection, ...)` y `persist_split_generation(...)`, más el optimizador patient-level. Estos contratos operan sobre versiones y estado gobernados; no son un API genérico para nuevos porcentajes/familias. S2 deberá integrar ese mecanismo de gobernanza y reutilizar versiones compatibles, sin invocar el exportador histórico por imagen ni implementar otro algoritmo en este orquestador. Los porcentajes futuros serán objetivos patient-level; nunca autorización para sobrescribir versiones existentes.

## Tests offline

```sh
make test-dataset-sources
make test-dataset-source-regression
```

`SOURCE_PYTHON` permite seleccionar el intérprete. Por autorización explícita de S1.D, estos targets corren localmente sin Docker/PostgreSQL; solo utilizan fixtures temporales y funciones puras.

Evidencia de la adquisición real: [reporte S1.D](../audits/s1_d/REPORT.md).
