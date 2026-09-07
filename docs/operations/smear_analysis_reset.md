# Reset controlado de Análisis de frotis

Esta herramienta vacía exclusivamente el dominio operacional de análisis de frotis. No es una limpieza genérica y no debe usarse para recuperar espacio ni para reinicializar Capstone.

## Alcance revisado

| Grupo | Tablas | Decisión | Dependencia principal |
|---|---|---|---|
| Identidad clínica | `research_subjects`, `scientific_cases`, `blood_samples`, `smear_slides` | reset | jerarquía sujeto → caso → muestra → portaobjeto |
| Ingesta | `image_ingestion_batches`, `microscopy_images` | reset | portaobjetos; imagen también referencia lote |
| Calidad | `microscopy_analysis_runs`, `microscopy_analysis_run_images`, `image_quality_assessments`, `microscopy_analysis_events`, `quality_gate_decisions`, `quality_assessment_queue_items` | reset | lote e imágenes |
| Detección | `cell_detection_runs`, `image_connected_components`, `cell_detections`, `cell_crops`, `cell_detection_events`, `scientific_reviews` | reset | análisis e imágenes |
| Clasificación clínica | `cell_classification_runs`, `cell_classification_inputs`, `cell_predictions`, `cell_explanations`, `smear_analysis_summaries`, `cell_classification_events`, `cell_classification_reviews` | reset | detección; las corridas sólo referencian modelos preservados |
| Ciencia y acceso | `users`, `roles`, `user_roles`, `runs`, `run_lineage`, `model_versions`, `stage2_model_publications`, `deployed_model_versions`, `datasets`, `dataset_versions`, `artifacts`, `predictions`, `image_analysis_jobs` | preservar | TRAIN/EVALUATE/EXPLAIN y autenticación |
| Validación científica | tablas `scientific_validation_*` | preservar y bloquear si referencian el objetivo | pueden apuntar a imagen, detección, clasificación o análisis clínico |

El orden DML exacto, de hijos a padres, está declarado en `DELETE_ORDER`. Se valida en runtime que ninguna FK nueva/desconocida apunte a las tablas objetivo. Las vistas no se borran. En particular, `cell_predictions` es la tabla clínica nueva; `predictions` y sus resultados experimentales se preservan.

## Auditoría, identidad y recuperación

`audit_events` nunca se borra completa. Antes del DML se clasifica cada evento de forma cerrada: se elimina sólo si un `resource_type` clínico exacto y su `resource_id`, una ruta clínica con frontera de segmento, o un valor escalar JSON coincide exactamente con un ID o storage key del manifiesto clínico. Login, roles, administración, TRAIN/EVALUATE/EXPLAIN, modelos, publicaciones, deployments e inferencia experimental se preservan. Cualquier evento clínico potencial sin evidencia exacta bloquea el reset.

La identidad requerida es exactamente una fila lógica con `lower(users.email)='admin@capstone.local'`, `users.username='admin'`, `users.status='active'` y `roles.name='administrator'`, mediante `users` → `user_roles` → `roles`. Sus fingerprints se revalidan antes de commit.

Sólo una nueva ejecución autorizada crea `.staging/smear-reset/<operation_id>/manifest.json` antes del DML. La recuperación usa exclusivamente ese manifiesto versionado. Cualquier marcador de cleanup de formato anterior bloquea: no se lee su contenido, no se convierte y no se elimina. Una operación técnica existente impide iniciar otra ejecución.

Las tablas `scientific_validation_*` se preservan, pero bloquean si una FK directa (`sample_id`, `analysis_run_id`, `cell_detection_id`, imágenes o runs) o un valor escalar JSON en snapshots/eventos coincide con los IDs o keys clínicos. JSON no interpretable bloquea.

La liberación se valida exclusivamente desde `runs` con `run_type='training' AND release_status='productive_stage2'`; se conserva un fingerprint de los campos `release_*`. No se infiere desde publicaciones, deployments ni versiones de modelo.

## Storage

Sólo se admiten `microscopy-images/`, `cell-crops/`, `cell-explanations/`, `.staging/uploads/`, `.staging/cell-detection/` y `.staging/cell-explanations/`. `model-explanations/` y todos los namespaces no enumerados se preservan. Cada archivo referenciado se registra con key, namespace, tabla/fila, tamaño, SHA-256, UID/GID, permisos, inode, device y mtime. Se rechazan rutas absolutas, traversal, symlinks, archivos especiales, metadata discordante y archivos compartidos. No se usan globs ni borrado recursivo.

Las imágenes y crops runtime están excluidos de los contextos nuevos mediante `.gitignore`/`.dockerignore`; la operación no agrega contenido científico a Git. Los binarios históricos que ya estén versionados no son alterados por esta fase.

## Contrato operacional Docker-only

Plan seguro (predeterminado):

```sh
make smear-reset-plan
```

El plan corre dentro del contenedor backend, abre una transacción `READ ONLY`, configura timeouts, valida identidad, Alembic y administrador, cuenta filas, construye el manifiesto y siempre hace rollback.

Una ejecución futura requiere simultáneamente `--execute`, `SMEAR_RESET_ALLOW_EXECUTION=1`, la frase exacta `RESET MALARIA SMEAR ANALYSIS` y un dump PostgreSQL custom-format durable montado de sólo lectura bajo `/app/backups`. El target solicita la frase interactivamente:

```sh
CAPSTONE_BACKUP_DIR="$PWD/backups" make db-backup
make smear-reset-execute BACKUP=/app/backups/capstone_YYYYMMDDTHHMMSSZ.dump
```

La ejecución falla cerrada ante trabajo activo, identidad o migración incorrecta, admin ausente/inactivo/duplicado, dependencia científica preservada, FK desconocida, lock incompatible o backup inválido. Nunca imprime el DSN ni credenciales.

Dentro de una única transacción se toman locks acotados, se revalidan las guardas, se desactivan únicamente triggers de usuario de las tablas clínicas (necesario por su contrato append-only), se ejecutan `DELETE` explícitos, se reactivan los triggers y se verifican vacío y fingerprints preservados. Un error produce rollback y cero eliminaciones físicas. Tras el commit se eliminan únicamente las entradas exactas revalidadas mediante descriptor, `O_NOFOLLOW`, `lstat` y `fsync` del padre.

Si una eliminación física falla, el resultado es `DATABASE_RESET_STORAGE_CLEANUP_PENDING`; se conserva el manifiesto versionado con estado `cleanup_pending`. La recuperación futura dentro del contenedor requiere:

```sh
SMEAR_RESET_ALLOW_EXECUTION=1 /app/scripts/storage/reset_smear_analysis.sh \
  --resume-cleanup --operation-id <UUID-canónico> \
  --backup /app/backups/<backup-registrado>.dump \
  --confirmation 'RESET MALARIA SMEAR ANALYSIS'
```

No se admite una ruta de manifiesto. `--resume-cleanup`, `--execute` y `--dry-run` son mutuamente excluyentes; sin modo explícito se conserva el dry-run. `--operation-id` sólo es válido con recuperación. Se compara la identidad configurada antes de abrir la conexión. El backup debe coincidir en ruta absoluta, tamaño y SHA-256, ser regular sin symlinks en sus ancestros, tener cabecera custom, superar `pg_restore --list` y residir en un filesystem de sólo lectura comprobado con `statvfs`.

### Schema interno v2

Todos los objetos rechazan campos desconocidos o ausentes y claves JSON duplicadas. No se almacenan filas completas, credenciales ni contenido binario.

| Campo | Contrato |
|---|---|
| `manifest_version` | Entero exacto `2` |
| `operation_id` | UUID canónico idéntico al directorio de la operación |
| `state` | Uno de los seis estados de la tabla siguiente |
| `created_at`, `updated_at` | Timestamps UTC ordenados |
| `backup` | `path`, `size`, `sha256` |
| `database_before.database_identity` | Host `db`, puerto `5432`, base, usuario y schema `public`; sin DSN |
| `database_before.alembic_revision` | Revisión esperada del repositorio |
| `database_before.target_tables` | Conjunto exacto de tablas; listas ordenadas de `{id, sha256}` por fila. El conteo es la longitud de cada lista. Para filas sin columna `id`, el digest completo identifica la fila |
| `database_before.audit_events` | IDs y SHA-256 de **todos** los eventos, incluidos los preservados |
| `database_before.preserved_tables` | Fingerprint de cada tabla preservada, incluidas todas las filas administrativas |
| `database_before.admin_fingerprint` | Fingerprint administrativo |
| `database_before.release_fingerprint` | TRAIN productivo exacto y SHA-256 de Liberación |
| `clinical_audit_events` | IDs exactos seleccionados y sus fingerprints de clasificación |
| `storage_files` | Entradas exactas: key, namespace, tabla, fila, tamaño, SHA-256, UID/GID, modo, inode, device y mtime en nanosegundos |
| `storage_preserved` | Inventario de archivos ajenos al objetivo, con los mismos atributos físicos; excluye el directorio técnico de operaciones |

Se rechazan rutas absolutas o traversal en storage, namespaces incompatibles con la tabla, entradas duplicadas, tipos incorrectos y archivos no asociados a filas objetivo. Los registros preservados se recorren para detectar referencias exactas a keys objetivo antes de crear el manifiesto y antes del cleanup.

### Máquina de recuperación

| Estado | Transiciones permitidas |
|---|---|
| `prepared` | `aborted_before_commit`, `database_committed`, `blocked` |
| `database_committed` | `cleanup_pending`, `cleanup_completed` |
| `cleanup_pending` | `cleanup_pending`, `cleanup_completed` |
| `cleanup_completed` | Sin transición; sólo verificación final y retiro técnico |
| `aborted_before_commit` | Terminal; conserva evidencia |
| `blocked` | Terminal; conserva evidencia y prohíbe cleanup |

Desde `prepared`, se compara PostgreSQL con la foto exacta anterior y con la foto posterior derivada: todas las tablas objetivo vacías, auditoría objetivo ausente y todo lo preservado idéntico. No se utilizan sólo conteos, fechas ni el último registro.

- **before:** además se exige que el inventario de storage siga idéntico. Persiste `aborted_before_commit` y devuelve `RESET_NOT_COMMITTED_NO_STORAGE_CLEANUP`. No ejecuta DML ni borra archivos. El manifiesto queda como evidencia; no se retira automáticamente.
- **after:** infiere commit y persiste `database_committed` antes de continuar.
- **mixed:** persiste `blocked` y devuelve `DATABASE_STATE_MIXED`. Si una guarda impide obtener una foto válida, se conserva el manifiesto sin borrar archivos.

Si before y after son idénticos porque no había targets, `prepared` se clasifica conservadoramente como before. Un estado committed ya durable sí permite completar una operación vacía.

La recuperación toma un advisory lock transaccional compartido con la ejecución y locks `SHARE` sobre todas las tablas comparadas. Usa `READ COMMITTED` para obtener la foto después de adquirirlos. Estos locks bloquean escritores hasta finalizar cleanup; la transacción de recuperación no ejecuta DML ni DDL. No puede declararse `READ ONLY` en PostgreSQL porque necesita estos locks. El dry-run sigue siendo `READ ONLY`. Los timeouts evitan esperar indefinidamente.

### Cleanup y caídas

Antes del primer unlink se persiste `cleanup_pending`. Se recorren ancestros mediante descriptores y `O_NOFOLLOW`; cada archivo se abre relativo a su padre y se comparan todos los atributos registrados. Un archivo ausente se considera procesado sólo después de verificar DB en after. Una diferencia devuelve `STORAGE_FILE_CHANGED` con ruta relativa, detiene la secuencia y conserva la operación. No amplía targets. Los archivos adicionales se conservan y se informan; los archivos preservados registrados no pueden desaparecer ni cambiar.

Cada unlink hace fsync del padre. Al finalizar se vuelve a comprobar PostgreSQL, el inventario preservado y la ausencia de todos los targets. Sólo se retiran ancestros vacíos exactos de los archivos objetivo, conservando los roots de namespaces, `.staging` y `.staging/smear-reset`.

Cada documento se escribe completo en un temporal único del mismo directorio, con modo 0600, flush y fsync del archivo, rename atómico, fsync del directorio y relectura con validación estricta. La creación de directorios también sincroniza sus padres. No se modifican identidad, backup o targets en una transición.

Tras persistir `cleanup_completed`, se relee y verifica el documento, se elimina sólo `manifest.json`, se sincroniza su padre y se retira el directorio exacto de operación si está vacío, sincronizando también su padre. Una caída antes del retiro permite repetir la verificación final sin borrar targets nuevos. Si la caída ocurre después de retirar el manifiesto, la misma identidad ya no es reutilizable: una nueva recuperación falla por manifiesto ausente. Temporales abandonados se conservan como evidencia y pueden impedir retirar el directorio técnico; no se borran por patrones.

### Pruebas aisladas y límites para B.3B

La suite `backend_api/tests/test_smear_reset_tool.py` usa dobles de PostgreSQL y archivos temporales; bloquea conexiones de red y creación de engines reales. Se ejecuta con el entorno existente `backend_api/.venv`, configuración ficticia `db:5432` y sin instalar dependencias. No requiere Docker ni monta almacenamiento científico.

B.3B debe verificar el comportamiento con PostgreSQL desechable y fallos de proceso reales, además de validar la durabilidad del mount del backup y la exclusión de escritores del filesystem. Los locks PostgreSQL no bloquean procesos que escriben directamente en storage: debe existir quiescencia operacional durante cleanup. POSIX no ofrece un unlink condicional por inode; la comparación inmediatamente anterior al unlink reduce la ventana pero no sustituye esa exclusión. La suite simula caídas y fsync; no demuestra resistencia física a cortes de energía. El inventario y los fingerprints completos tienen un costo proporcional al volumen de datos.

El administrador `admin@capstone.local` se valida como único, activo y con rol `administrator` antes y dentro de la transacción. Sus tablas forman parte del fingerprint preservado. Un clon limpio sigue usando `scripts/create_admin.py`; este reset no cambia ese bootstrap.
