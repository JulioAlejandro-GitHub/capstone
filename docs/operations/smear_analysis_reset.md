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

El único root operativo es el `STORAGE_ROOT` configurado por Compose: `scientific_storage → /app/var/storage`. El reset no descubre raíces alternativas. Los directorios históricos del repositorio `var/storage/` y `backend_api/var/storage/` no se leen, montan, copian ni eliminan desde esta herramienta; su tratamiento corresponde a Storage B.4, después de resolver separadamente la explicación de modelo preservada.

Sólo se admiten `microscopy-images/`, `cell-crops/`, `cell-explanations/`, `.staging/uploads/`, `.staging/cell-detection/` y `.staging/cell-explanations/`. `model-explanations/`, `.staging/model-explanations/` y todos los namespaces no enumerados se preservan. Cada archivo objetivo existente se registra con key, namespace, tabla/fila/columna, clasificación, tamaño, SHA-256, UID/GID, permisos, inode, device y mtime. Se rechazan rutas absolutas, traversal, symlinks, archivos especiales, metadata discordante y archivos compartidos. No se usan globs ni borrado recursivo.

### Clasificación de referencias B.3B.1B

| Clasificación | Condición | Acción BD futura | Acción física futura |
|---|---|---|---|
| `canonical_present` | Key confinada, archivo regular sin symlinks, tamaño y SHA coincidentes cuando BD los aporta | Eliminar fila objetivo | Eliminar únicamente después del commit, revalidando todos los atributos |
| `missing_before_reset` | Key y namespace válidos, sin archivo en el root canónico | Eliminar fila objetivo | Ninguna; evidencia en `storage_missing` |
| `invalid_or_unsafe` | Key NULL/vacía/insegura, namespace incorrecto, symlink, tipo inesperado o metadata discordante | Bloquear | Bloquear |
| `ambiguous` | Identidad compartida o pertenencia no demostrable | Bloquear | Bloquear |

Una explicación aporta dos referencias: `heatmap_storage_key` y `overlay_storage_key`. No se omiten silenciosamente keys NULL. Las referencias ausentes también participan en las guardas de dependencias preservadas y auditoría; su ausencia no autoriza borrar datos preservados. Los tamaños y SHA esperados pueden ser `null` si BD no los proporciona; los archivos presentes siempre reciben tamaño y SHA reales verificados para el cleanup.

Según B.3B.1A, se esperan 2.590 referencias, 40 `canonical_present` y 2.550 `missing_before_reset` respecto del volumen canónico, si el estado sigue igual. Las 165 ausencias en los tres roots son un subconjunto de esas 2.550. El reset no distingue cuáles permanecen físicamente fuera del volumen. Los dos huérfanos clínicos históricos quedan fuera del alcance. Los archivos canónicos no referenciados siguen preservados, salvo el staging clínico explícitamente permitido por el contrato anterior.

Las imágenes y crops runtime están excluidos de los contextos nuevos mediante `.gitignore`/`.dockerignore`; la operación no agrega contenido científico a Git. Los binarios históricos que ya estén versionados no son alterados por esta fase.

## Contrato operacional Docker-only

Plan seguro (predeterminado):

```sh
make smear-reset-plan
```

El plan corre dentro del contenedor backend, abre una transacción `READ ONLY`, configura timeouts, valida identidad, Alembic y administrador, cuenta filas, construye el plan en memoria y siempre hace rollback. No necesita backup ni opt-in destructivo, no escribe manifiestos persistentes ni modifica storage. Acepta `missing_before_reset > 0` sólo cuando no existen referencias inválidas o ambiguas. Los comandos operacionales de esta sección son para una fase posterior autorizada; B.3B.1B no los ejecuta contra el runtime.

| Campo del resultado JSON | Significado |
|---|---|
| `clinical_database_references` | Referencias físicas BD; cuenta heatmap y overlay por separado |
| `canonical_present` | Referencias BD con archivo canónico validado |
| `missing_before_reset` | Referencias BD sin archivo canónico |
| `invalid_or_unsafe`, `ambiguous` | Ambos cero en un plan aprobado; el primer rechazo impide aprobar y devuelve código de salida 2 |
| `physical_delete_targets` | Archivos canónicos concretos, incluido staging clínico permitido; no incluye ausentes |
| `database_delete_targets` | Suma de filas de `DELETE_ORDER` y eventos de auditoría clínica seleccionados, independientemente de la existencia del archivo |
| `preserved_storage_files` | Archivos del inventario canónico ajenos al objetivo físico |
| `missing_references` | Evidencia sanitizada por tabla, fila, columna, key, metadata esperada, clasificación y motivo |

Se mantienen `rows_by_table`, `files`, `bytes`, `audit` y `productive_train_id`. La salida no muestra rutas absolutas del host, DSN ni credenciales. Los errores de almacenamiento se reportan como `RESET_REFUSED: invalid_or_unsafe` o `ambiguous`; otras guardas devuelven `RESET_REFUSED: preflight_or_recovery_guard`, sin interpolar excepciones de drivers o filesystem que puedan contener secretos.

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
| `storage_files` | Sólo `canonical_present`: key, namespace, tabla, fila, columna, clasificación, tamaño, SHA-256, UID/GID, modo, inode, device y mtime en nanosegundos. Staging utiliza tabla técnica `clinical_staging` y columna vacía |
| `storage_missing` | Sólo `missing_before_reset`: `table`, `row_id`, `column`, `storage_key`, `expected_size`, `expected_sha256`, `classification` y motivo estable `reason=absent_from_canonical_storage` |
| `storage_targets_sha256` | SHA-256 del JSON canónico de `database_before`, `storage_files`, `storage_missing` y `storage_preserved`; permanece fijo en las transiciones |
| `storage_preserved` | Inventario de archivos ajenos al objetivo, con los mismos atributos físicos; excluye el directorio técnico de operaciones |

Se rechazan rutas absolutas o traversal en storage, namespaces incompatibles con la tabla/columna, entradas duplicadas, tipos incorrectos y archivos no asociados a filas objetivo. Cada referencia `(tabla, fila, columna)` debe aparecer exactamente una vez entre presentes y ausentes; se exige cobertura completa de las filas de almacenamiento en `database_before.target_tables`. Ni una key ni una referencia pueden aparecer en dos categorías o en el inventario preservado. El escritor comprueba que cada objetivo físico existe y coincide con su inventario validado antes de persistirlo. La relectura valida el digest y se compara nuevamente con el documento cargado antes del cleanup; descubrir archivos adicionales nunca amplía los targets.

El digest detecta cambios de contrato; no es una firma que autentique un manifiesto reescrito por un actor con permisos de escritura. Se conservan la privacidad 0600, la confinación y el contrato de custodia del manifiesto. Los documentos que carezcan de los nuevos campos requeridos se rechazan y conservan como evidencia: no se convierten ni se completa su contenido por inferencia, aunque declaren versión 2. No iniciar esta versión con una operación previa pendiente sin revisión separada.

Los registros preservados se recorren para detectar referencias exactas a todas las keys objetivo, presentes y ausentes, antes de crear el manifiesto y antes del cleanup. `storage_missing` nunca almacena rutas de host, otras raíces, credenciales ni contenido de archivos. El campo existente de backup sigue describiendo exclusivamente el dump montado en el contenedor.

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

Antes del primer unlink de un objetivo clínico se persiste `cleanup_pending`. Se recorren ancestros mediante descriptores y `O_NOFOLLOW`; cada archivo `canonical_present` se abre relativo a su padre y se comparan todos los atributos registrados. Un objetivo antes presente y ahora ausente se considera procesado sólo después de verificar DB en after. Una diferencia devuelve `STORAGE_FILE_CHANGED` con ruta relativa, detiene la secuencia y conserva la operación. No amplía targets. Los archivos adicionales ajenos a keys ausentes se conservan y se informan; los archivos preservados registrados no pueden desaparecer ni cambiar.

Para `missing_before_reset` no hay apertura del archivo, lectura de contenido, unlink, glob ni búsqueda por recorrido. Se verifica la ausencia mediante `stat(..., follow_symlinks=False)` sobre componentes exactos y descriptores de los directorios padres, sin enumerarlos para buscar alternativas. Si aparece cualquier entrada en la key —archivo, directorio o symlink— se bloquea conservando archivo y manifiesto. El inventario general también rechaza esa key antes de abrirla, por si aparece después de la comprobación inicial. La comprobación se repite al verificar el estado final y al reanudar, incluido `cleanup_completed`.

Una operación que sólo contiene referencias ausentes pasa de `database_committed` a `cleanup_completed` tras verificar BD y storage, sin pasar por `cleanup_pending`. En una operación mixta, ese estado transitorio se debe exclusivamente al cleanup de archivos presentes; la ausencia previa no produce conflictos ni trabajo físico pendiente. Las filas de ambas categorías se eliminan juntas en la misma transacción y cualquier fallo DML hace rollback sin borrar archivos.

Cada unlink hace fsync del padre. Al finalizar se vuelve a comprobar PostgreSQL, el inventario preservado y la ausencia de todos los targets. Sólo se retiran ancestros vacíos exactos de los archivos objetivo, conservando los roots de namespaces, `.staging` y `.staging/smear-reset`.

Cada documento se escribe completo en un temporal único del mismo directorio, con modo 0600, flush y fsync del archivo, rename atómico, fsync del directorio y relectura con validación estricta. La creación de directorios también sincroniza sus padres. No se modifican identidad, backup o targets en una transición.

Tras persistir `cleanup_completed`, se relee y verifica el documento, se elimina sólo `manifest.json`, se sincroniza su padre y se retira el directorio exacto de operación si está vacío, sincronizando también su padre. Una caída antes del retiro permite repetir la verificación final sin borrar targets nuevos. Si la caída ocurre después de retirar el manifiesto, la misma identidad ya no es reutilizable: una nueva recuperación falla por manifiesto ausente. Temporales abandonados se conservan como evidencia y pueden impedir retirar el directorio técnico; no se borran por patrones.

### Pruebas aisladas y límites para B.3B

La suite `backend_api/tests/test_smear_reset_tool.py` usa dobles de PostgreSQL y archivos temporales; bloquea conexiones de red, creación de engines reales y `Engine.connect`. Se ejecuta con el entorno existente `backend_api/.venv`, configuración ficticia `db:5432` y sin instalar dependencias. No requiere Docker ni monta almacenamiento científico:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  backend_api/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  backend_api/tests/test_smear_reset_tool.py
```

| Matriz B.3B.1B | Cobertura aislada |
|---|---|
| Plan | Presente, ausente, mezcla, metadata esperada opcional, conteos BD/físicos y dry-run real con SELECT-only double |
| Rechazos | Key vacía/NULL/absoluta/traversal, namespace ajeno, hash/tamaño incorrecto, symlink de archivo/padre, directorio o padre no directorio, key compartida |
| Manifiesto | Campos estrictos, solapamiento entre categorías, duplicados, referencia omitida, expansión de targets, objetivo físico no validado, digest alterado |
| Transacción | DML simulado incluye filas presentes y ausentes; commit precede al unlink; fallo DML revierte y deja cero borrados físicos |
| Recuperación | Ausencia sin open/unlink, aparición tardía sin abrir el nuevo archivo, cleanup parcial/idempotencia, operación sólo ausente y los seis estados v2 |
| Preservación | Explicaciones de modelo, staging de modelos, namespace desconocido y guarda de referencias preservadas incluso para keys ausentes |
| Aislamiento | Sin red/engine real; salida sanitizada incluso ante errores de driver/filesystem; sin roots históricos en implementación |

Las menciones de roots históricos sólo en documentación y casos de rechazo prueban su exclusión; no habilitan su consumo. Las simulaciones llaman funciones de ejecución/recuperación únicamente con dobles y temporales; no son invocaciones operacionales de `--execute` ni `--resume-cleanup`.

B.3B debe verificar el comportamiento con PostgreSQL desechable y fallos de proceso reales, además de validar la durabilidad del mount del backup y la exclusión de escritores del filesystem. Los locks PostgreSQL no bloquean procesos que escriben directamente en storage: debe existir quiescencia operacional durante cleanup. POSIX no ofrece un unlink condicional por inode; la comparación inmediatamente anterior al unlink reduce la ventana pero no sustituye esa exclusión. La suite simula caídas y fsync; no demuestra resistencia física a cortes de energía. El inventario y los fingerprints completos tienen un costo proporcional al volumen de datos.

El administrador `admin@capstone.local` se valida como único, activo y con rol `administrator` antes y dentro de la transacción. Sus tablas forman parte del fingerprint preservado. Un clon limpio sigue usando `scripts/create_admin.py`; este reset no cambia ese bootstrap.
