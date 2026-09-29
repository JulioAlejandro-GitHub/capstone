# RESET.3 — Reconstrucción definitiva del estado inicial de Capstone

**RESET.3 — EJECUTADO Y VERIFICADO.** Operación del 28 de septiembre de 2026 (Chile; archivos de backup con fecha UTC 29-09).

La base canónica `malaria_experiments` está en **20260922_01**, con 97 tablas y 138,043 filas. Conserva íntegramente las 16 tablas protegidas (autenticación y las 13 de dataset/split). Las otras 77 tablas de historial están vacías. Backend/frontend funcionan con los mismos contenedores, imágenes, puertos y configuración.

## Alcance definitivo y evidencia anterior

Esta ejecución sigue la última autorización explícita: preservar todas las filas/columnas de `users`, `roles`, `user_roles` y dataset/split, retirar el resto del historial y sustituir la base después de verificar su recuperación. Se conservan `last_login_at` y **las 55.116 filas de `dataset_split_images`**, incluidas las 27.558 del split físico anterior. El split no se recalculó.

El prototipo previo excluía estas filas y limpiaba `last_login_at`; **no se utilizó para la sustitución**. Sus documentos permanecen como `reset_3_prototype_20260928.md`, `reset_3_prototype_evidence_20260928.json` y `reset_3_prototype_allowlist_20260928.json`. No se sustituyeron silenciosamente esos golden. El inventario fuente nuevo es el de esta operación, con 1,192,670 filas public; incorpora el estado actual de autenticación.

## Parada y backup completo

1. `docker compose stop --timeout 45 frontend backend`: parada de los servicios existentes.
2. DBeaver mantenía conexiones; se solicitó su cierre normal con AppleScript dentro de la autorización de detener todos los escritores. Se verificó **cero conexiones externas** en `pg_stat_activity`. No se utilizó SIGSTOP ni el prototipo `freeze_backup_window.py`. No se detectaron procesos Python/uvicorn/TRAIN locales.
3. Se obtuvo un primer backup y se restauró íntegramente. Después de cerrar DBeaver se generó el **backup definitivo**, y se repitió su restauración/verificación. Ambos archivos se conservan.
4. El wrapper oficial `scripts/db/backup.sh` ahora admite `CAPSTONE_BACKUP_STOPPED_BACKEND=1`: exige backend detenido y usa un proceso Python efímero Docker, sin API ni dependencias, para verificar identidad en READ ONLY. El modo normal no cambia. No se guardan credenciales en evidencia.

Backup definitivo: [`capstone_20260929T001919Z.dump`](../../../backups/reset3_final/capstone_20260929T001919Z.dump).

- Tamaño: **86,829,877 bytes**.
- SHA-256: `0feff4ca6b54ba04bf1ba6a45c59fee50678bef3ebc24541e9f7f754e2133e5c`.
- Origen: usuario `julio`, `malaria_experiments`, cluster `7668020338728398886`, revisión **20260915_01**.
- Restauración: `pg_restore --exit-on-error --single-transaction`, base aislada `reset3_definitive_restore`, cluster `7690743288911712299`, sin puertos publicados ni volúmenes operativos compartidos.
- Comparación: hashes/conteos de las **97 tablas public y nueve schemas históricos**, más funciones, triggers, constraints, propietarios y ACL. Los contenidos coinciden íntegramente.
- Normalizaciones documentadas del catálogo restaurado: OID y nombres RI internos regenerados; representación equivalente de cuatro constraints con cast de arrays literales varchar/text. No se ignoraron definiciones o constraints. La verificación inicial detectó esas diferencias y se hizo explícita la normalización antes de aprobar el backup.

No se consideró válido el backup por el mero éxito de pg_dump o pg_restore. Las comparaciones completas constan en `backups/reset3_final/evidence/restore_definitive_verification.json`.

## Construcción e importación

Se creó `reset3_candidate` en el clon. Se aplicaron los 22 DDL legacy originales necesarios y su ledger con checksum, excluyendo `004_seed.sql`, que fabrica experimentos y un split de ejemplo. Después se ejecutó Alembic oficial hasta **20260922_01**, con conexión explícita al clon. Ninguna migración histórica fue modificada ni ejecutada contra la base original.

Se importaron mediante COPY todas las filas/columnas protegidas y tres definiciones técnicas de modelos (`custom_cnn`, `vgg16`, `densenet121`). Las cinco filas de roles sembradas oficialmente se alinearon con sus IDs/timestamps originales y se compararon completas. No se importaron versiones entrenadas, publicaciones, deployments, campañas, runs, resultados o auditoría. El ledger, Alembic y GlobalGate provienen de sus mecanismos oficiales de inicialización; el gate está libre.

La versión científica se importó temporalmente DRAFT para insertar sus relaciones con los guards activos; luego recorrió las transiciones oficiales GENERATED → VALIDATED → FROZEN. El hash final de **toda la fila** coincide con el origen, incluidos estado, fingerprints y timestamps. No se deshabilitaron triggers ni se recalculó ninguna asignación.

| Tabla | Antes | Final |
|---|---:|---:|
| `users` | 1 | 1 |
| `roles` | 5 | 5 |
| `user_roles` | 1 | 1 |
| `datasets` | 2 | 2 |
| `dataset_versions` | 1 | 1 |
| `clinical_identities` | 201 | 201 |
| `dataset_source_records` | 27,558 | 27,558 |
| `identity_evidence` | 27,558 | 27,558 |
| `dataset_split_assignments` | 27,558 | 27,558 |
| `dataset_split_images` | 55,116 | 55,116 |
| `dataset_materializations` | 1 | 1 |
| `dataset_split_statistics` | 1 | 1 |
| `dataset_split_validation_checks` | 12 | 12 |
| `experiments` | 1 | 0 |
| `experimental_campaigns` | 2 | 0 |
| `campaign_members` | 72 | 0 |
| `campaign_attempts` | 11 | 0 |
| `runs` | 99 | 0 |
| `train_execution_sessions` | 11 | 0 |
| `local_execution_jobs` | 1 | 0 |
| `train_execution_records` | 360 | 0 |
| `audit_events` | 2,632 | 0 |
| `model_versions` | 36 | 0 |
| `stage2_model_publications` | 4 | 0 |
| `deployed_model_versions` | 3 | 0 |

Las restantes tablas y sus hashes están en [la evidencia JSON](reset_3_execution_evidence.json) y [el inventario de importación](reset_3_import_allowlist.json). Hay 208 FK comprobadas sin huérfanos, cero triggers deshabilitados y cero constraints sin validar.

## Dataset, split y archivos originales

- Versión: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, FROZEN.
- Materialización: `e15dc166-1c4b-558e-b77b-727b1783430c`, preservada íntegramente.
- Asignaciones oficiales: **TRAIN 22.180 / VALIDATION 2.693 / TEST 2.685**, 27.558 registros y 201 identidades clínicas. Cero pacientes cruzados entre splits.
- Se conservan también las filas históricas del split físico porque pertenecen a la familia protegida; no se corrigen sus IDs NULL ni se regeneran sus estadísticas.
- Los **82.744 elementos protegidos** de datos, materialización/configuración y código científico/migraciones conservan sus hashes. Dataset/data: SHA-256 agregado `da78138c520e827eb1ff0afd6044701935508aa177054045880cf784fb2979f3`.
- También se verificaron intactos los **74 archivos fuente originales** de microscopía del inventario anterior; se retiraron sólo sus derivados.

## Artefactos históricos

Se inventariaron, copiaron y verificaron por SHA-256 **6,369 archivos (5,025,368,027 bytes)** antes de retirar cualquiera de sus rutas activas. La cuarentena conserva una copia recuperable en `backups/reset3_final/artifact_quarantine`; manifest/journals documentan cada origen, destino y hash.

Raíces retiradas: outputs ML (4.018), releases (42), local execution artifacts (27), cell-crops (2.280), cell-explanations (2). Dataset, fuentes originales, configuración, `.gitkeep`, `.DS_Store` y locks técnicos quedan fuera del retiro. El permiso final de la raíz de backup/cuarentena es 0700.

Tras retirarlos se verificaron otra vez la ausencia en rutas activas, cada copia en cuarentena y los hashes científicos. **36 archivos de releases versionados aparecen eliminados en el working tree**: forman parte del retiro autorizado y sus bytes están en la cuarentena. No se borró permanentemente el último ejemplar de recuperación.

## Sustitución controlada

El candidato se exportó a `backups/reset3_final/clean_candidate_20260929.dump` y se restauró en `malaria_reset3_ready_20260929` del servidor existente. La restauración completa coincidió con los hashes del candidato, las 16 tablas protegidas y los guards E10. El mecanismo transaccional de renombrado se ensayó primero con commit y rollback reales en dos bases vacías del clon.

Justo antes del cambio se volvieron a comparar todas las tablas del origen y los nueve schemas históricos y se exigió cero conexiones a ambas bases. En una transacción se bloquearon nuevas conexiones, se renombró el origen a recuperación y el candidato al nombre canónico, habilitando sólo el nuevo canónico.

| Identidad | Antes | Después |
|---|---|---|
| OID 16384 | `malaria_experiments` | `malaria_pre_reset3_20260929`, conexiones deshabilitadas |
| OID 1600436 | `malaria_reset3_ready_20260929` | `malaria_experiments`, conexiones habilitadas |

Resultado: **COMMIT_CONFIRMED_BY_FRESH_CONNECTION**. Se recibió respuesta de commit y además se verificó el mapeo de OID con conexión nueva. No hubo interrupción de red real ni se afirma haberla probado. El código deja el resultado incierto bloqueado si no puede reconciliarlo; nunca restaura archivos suponiendo rollback.

La base antigua conserva su contenido y los nueve schemas históricos, aislada de conexiones ordinarias. No se utilizó `TRUNCATE CASCADE`, no se aplicó DDL de migración sobre sus tablas y no se eliminó ninguna base operativa anterior.

## Aplicación y autenticación

Se reiniciaron backend/frontend con `docker compose start backend frontend`, manteniendo configuración e imágenes. Frontend `/`, backend `/health` y `/ready` responden **HTTP 200**; readiness indica database/migrations/storage ready.

La API operativa pasó GET autenticados a `/api/v1/auth/me`, `/api/datasets`, detalle de la versión protegida, `/api/dataset/summary`, `/api/dataset/split` y `/api/deployments`. El administrador conserva identidad, rol y **54 permisos**; sin token, `/auth/me` responde 401.

**Límite explícito:** se acreditó autenticación JWT real con un token emitido en memoria por la implementación oficial y las filas preservadas. No se ejecutó login con contraseña ni se conoce la contraseña en claro. Hash de contraseña, estado, asociaciones, IDs y `last_login_at` coinciden exactamente; no se llamó a `/auth/login`, evitando una escritura de login/auditoría.

OP1 Docker y Local devuelven **E10_SCHEMA_READY**. Local se detuvo antes de claim; ResultService sólo se instanció sin publicar eventos. Registry/resolución de configuración están disponibles. El servicio de deployments declara **SIN_MODELO_PRODUCTIVO**; no se publicó ni entrenó un modelo.

Después de arrancar y hacer los GET se repitió la comparación de las 97 tablas: igualdad completa con el candidato, incluidas las 77 tablas vacías. No se creó campaña, intento, run, sesión, job, análisis o auditoría. No se ejecutó TRAIN/TEST.

## Recuperación disponible

Conservar juntos el backup íntegro, esta evidencia, la cuarentena y `malaria_pre_reset3_20260929`. No reejecutar los scripts como una limpieza rutinaria ni sobrescribir datos nuevos.

Si se decide volver al estado anterior:

1. Detener ordenadamente frontend/backend y clientes SQL. Inventariar y respaldar cualquier dato nuevo antes de sustituirlo.
2. Comparar nombres/OID desde una conexión a `postgres`. Si la transacción quedó incierta, reconciliar primero; **no deducir rollback de una respuesta perdida**.
3. Verificar el SHA-256 del backup y todos los archivos de cuarentena. La base original puede recuperarse por intercambio inverso de nombres, conservando también la base nueva; el origen ya tiene los datos íntegros. Habilitar conexiones sólo al canónico elegido. No usar un downgrade de Alembic como sustituto de recuperación de datos.
4. Con escritores detenidos, `artifact_quarantine.py restore` verifica el conjunto completo y rechaza conflictos de archivos nuevos antes de reponer los derivados. Requiere recrear el contenedor temporal con el mismo manifiesto y montajes acotados; los orquestadores exactos están archivados. No eliminar la cuarentena después de copiar.
5. Si no se utiliza la base original, restaurar el **backup definitivo** en una base nueva con el rol/infraestructura Docker oficial; verificar todos los hashes y catálogo como en el ensayo antes de sustituirla. Una restauración fallida no justifica borrar el origen.
6. Revalidar autenticación/dataset/archivos, nombre canónico y readiness antes de habilitar servicios. Una vuelta atrás restaura deliberadamente también publicaciones e historial anteriores: requiere esa decisión explícita, no es una continuación automática del reset.

## Archivos y evidencia

- `scripts/db/backup.sh`: modo de backup con backend detenido y consulta de identidad READ ONLY.
- `scripts/reset/reset3/`: scripts de construcción/importación, verificación de restore, API, fingerprints, cuarentena y sustitución; README con alcances y límites.
- `docs/engineering/e10_execution_refactor/reset_3_clean_rebuild.md`: este informe.
- `reset_3_execution_evidence.json`: hashes definitivos de código, inventarios, backup, sustitución, API y resultado.
- `reset_3_import_allowlist.json`: selección completa de tablas protegidas y dependencias técnicas.
- `reset_3_prototype_*`: evidencia histórica preservada del prototipo descartado.
- `backups/reset3_final/evidence`: salidas exactas, manifiesto de archivos y copia de los scripts/orquestadores ejecutados, sin archivos de credenciales.
- Los 36 archivos retirados de releases están enumerados por Git y recuperables en la cuarentena.

Se comprobó sintaxis Bash y compilación Python de los scripts. La validación principal fue PostgreSQL y HTTP reales, no dobles ni simulación de filesystem. No se ejecutó la suite completa de regresión ni trabajo científico como parte de este reset.

Los contenedores temporales, su red interna y el volumen del PostgreSQL desechable fueron retirados después de archivar la evidencia; sólo permanecen los tres servicios operativos originales, sus volúmenes y las dos bases persistentes de operación/recuperación. No se hizo commit ni push.

**RESET.3 — EJECUTADO Y VERIFICADO.** Sistema listo para crear una campaña nueva; ninguna campaña iniciada por esta intervención.
