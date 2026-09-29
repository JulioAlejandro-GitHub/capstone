# RESET.3 — Reconstrucción limpia: ejecución detenida

**RESET.3 — DETENIDO.** La sustitución operativa no comenzó. Se completó un prototipo E10 aislado, pero la revisión automática rechazó el mecanismo de congelación previo al backup obligatorio. El login real del administrador tampoco quedó acreditado.

## 1. Autorización y bloqueo

La instrucción autoriza una reconstrucción lógica condicionada a backup restaurado, integridad del nuevo estado y recuperación. No exige RESET.2B ni una secuencia de DELETE; no se reutilizó esa barrera como motivo de rechazo.

La acción propuesta suspendía los procesos descendientes de la API mediante SIGSTOP y mantenía locks SHARE en public y los nueve schemas incluidos en el backup, con liberación y watchdog de 15 minutos. **La revisión automática la rechazó antes de crear el proceso**: consideró la interrupción amplia del servicio y solicitó autorización explícita para ese mecanismo y alcance concretos. Se pidió esa aprobación específica; no se recibió durante esta ejecución. No se intentó eludir el rechazo mediante otro mecanismo.

Se conservó la propuesta como `scripts/reset/reset3/freeze_backup_window.py`, con una barrera incondicional que impide ejecutarla. No se suspendieron procesos, congelaron escritores ni tomaron esos locks. Por ello no se generó el backup operativo nuevo ni se inició sustitución o cuarentena.

Se pidió además validación humana del login real, sin solicitar contraseña en el chat. El hash de credenciales y los identificadores del administrador fueron preservados exactamente en el candidato, pero eso **no sustituye un login real exitoso**. El validador requiere terminal interactivo y verifica el contenedor aislado antes de pedir contraseña. El entorno fue retirado al cierre; debe reconstruirse antes de usarlo.

## 2. Construcción aislada acreditada

PostgreSQL 17.9 desechable, sin puertos PostgreSQL ni volúmenes operativos compartidos. Base `reset3_candidate`, cluster `7690728158762438700`. El origen operativo nunca fue destino de estos DDL.

La raíz Alembic `20260726_00` es stamp-only y requiere las definiciones legacy. Se aplicaron los SQL originales 001–029 presentes en el repositorio, **omitiendo explícitamente 004_seed.sql**, que fabrica un experimento y un split 22.046/2.756/2.756 incompatible con este objetivo. Se registraron los checksums de los 22 SQL aplicados y se ejecutó Alembic oficial mediante su conexión suministrada hasta **20260922_01**. No se editó ninguna migración ni se invocó el comando operativo retirado de init_db.py; se reutilizaron sus funciones de ledger.

Resultado: **97 tablas** en el candidato E10. La ejecución fue una comprobación previa de construcción antes de afectar disponibilidad operativa; no reemplaza el backup/restauración obligatorios anteriores al cutover.

## 3. Allowlist y datos conservados en el candidato

La [allowlist explícita](reset_3_import_allowlist.json) contiene PK y SHA-256 de preimagen por fila, predicados y hashes agregados. SHA-256 del archivo: `0873eb4a50ef2c20d82dbeb1a9c8c9aa5c50ad6c30c4eb54eea5d909c10856c1`. Se deriva del dataset oficial, sus asignaciones, fuentes, evidencias de identidad y cierre de FK, además de acceso y tres definiciones de modelos. No es todavía un inventario definitivo bajo congelación.

| Tabla seleccionada | Filas importadas | SHA-256 de filas origen seleccionadas |
|---|---:|---|
| roles | 5 | `9963e9d52a13de49af23598244cdb8dd2819edd2459255ff70b58e099153c091` |
| users | 1 | `482db5f6eeb6cf4853686d016505a95b508936633618c792d421c987d4c8fc93` |
| user_roles | 1 | `fbfa8d635fe1d196fe4883645e8f7666011c8357d0124d98b4a28e3c9dd5589b` |
| datasets | 2 | `7ed1f66ac9ffb3e27d88fc2bd52eea9088791beaa636cc828b37344629342c59` |
| models | 3 | `e1d169f311a11ef716a178e88554b0ee01e3f016e963ec38e4992815b1133fef` |
| dataset_versions | 1 | `c9a99a6f03d324318fe2b1fef2f9566fa8fbef748889dba3f2faf7ba836f82ff` |
| dataset_version_sources | 1 | `bcdd40cbf14cfba8dd5df9c76f76fa6b571d06d294f249dc2284f7e31503ff59` |
| clinical_identities | 201 | `e41426a8500e3fbb9f8b70b2119501ce20f3853a5750194cd0a00cf6315a38e4` |
| dataset_source_records | 27558 | `d3c6386726b93a435823e8a1a2bc0245a4b892b0b89887f3747a8189425145c3` |
| identity_evidence | 27558 | `f49c50ae77ea0aba924116a985bd011691abe6c8815e75b1fbd67e3d4878f396` |
| dataset_materializations | 1 | `6026c9bd22c5c3b7b916b7f6e2e3464cc8cf0050fe5ba4fc6083537e71450458` |
| dataset_split_assignments | 27558 | `edda8be9e1e4060caf1d1afc8f34bba161ebe139e24bbb3091f9899eb930f210` |
| dataset_split_images | 27558 | `fad07080264ed3ea3bf820141e9e41608ee8a7556b13f4f524756cd5cbd5dd7f` |
| dataset_split_statistics | 1 | `1e509f3dc0cc50c3ea20a99207e04e66b617c642fcce49510c64ef8326f63c0d` |
| dataset_split_validation_checks | 12 | `29b643727194eb4264de61ad2e93ef0e271b898be4a09ef28ec4fefac0aff4a6` |
| dataset_materialization_activations | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

En particular, se conservan dos datasets por dependencias reales; 201 identidades clínicas; 27.558 registros fuente, evidencias y asignaciones; una versión y una materialización; tres modelos (`custom_cnn`, `vgg16`, `densenet121`). No se conserva el cuarto modelo legacy por contener otra definición útil en la misma tabla.

Los roles sembrados por Alembic se alinearon con los IDs/timestamps originales antes de importar usuario-rol. El administrador conserva ID, username, email, password_hash y demás columnas, excepto `last_login_at`, que se dejó NULL en la copia para no trasladar historial de login. No se alteró el usuario original ni se generó una contraseña nueva.

COPY preservó los valores originales sin serialización que alterase números o timestamps. Las FK y triggers permanecieron activos. Para respetar los guards científicos, la versión se importó temporalmente DRAFT en una única transacción; se copiaron las asignaciones originales y se recorrió el lifecycle permitido hasta FROZEN, conservando los timestamps y todos los campos científicos originales. El hash final de la fila de versión coincide exactamente con el origen. **No se reconstruyó ni recalculó el split.**

## 4. Selección científica y hashes

La fuente contiene 55.116 filas en `dataset_split_images`, todas sin dataset_version_id, correspondientes a dos raíces físicas. No se seleccionó toda la tabla ni se inventaron esos vínculos. Se importaron exclusivamente las 27.558 filas cuya raíz exacta es la materialización oficial `malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; se excluyeron las del split físico antiguo.

Asignaciones e imágenes seleccionadas: **TRAIN 22.180, VALIDATION 2.693, TEST 2.685**. Pacientes en múltiples particiones: **0**. Materialización conservada: `e15dc166-1c4b-558e-b77b-727b1783430c`. Las filas científicas seleccionadas, incluyendo contratos/fingerprints, metadatos de materialización y referencias de archivos, coinciden por hash antes/después de importar.

Los fingerprints de las 82.744 entradas de árboles protegidos coinciden con RESET.2A: dataset original y materialización, configuración del split, configuración científica, registry y migraciones. No se modificaron archivos fuente. No se afirma haber recalculado un nuevo contrato ni reparado referencias históricas ausentes.

## 5. Datos excluidos y verificación funcional

No se importaron runs, experiments, campañas, miembros, attempts, sessions, eventos/records de entrenamiento, model_versions, métricas, predicciones, Grad-CAM, análisis, detecciones, clasificaciones, publicaciones, deployments ni auditoría operativa histórica. Las tablas existen y sus conteos iniciales están en cero. El prototipo contiene **110.485 filas** contando datos mínimos, roles, ledger de migraciones, revisión y GlobalGate.

Controles reales del candidato:

- OP1 Docker: **E10_SCHEMA_READY**. Local: READY y detención explícita antes de get/claim/reserva.
- ResultService instanciado con repositorio del candidato; sin publicar resultados/eventos ni reservar ejecuciones.
- Registry de las tres arquitecturas y configuraciones disponible.
- GlobalGate inicializado y libre.
- **208 FK sin huérfanos**, cero triggers deshabilitados y cero constraints sin validar.
- `SIN_MODELO_PRODUCTIVO` mediante servicios existentes: publicaciones vacías y alias ausente controlado.
- API aislada: `/health` **ok**, `/ready` **ready**, con componentes database/migrations/storage ready.

La API auxiliar sólo estuvo conectada a una red interna con alias db apuntando al candidato, puerto loopback 18003, mounts operativos de sólo lectura y almacenamiento escribible en /tmp propio. No se modificó DATABASE_URL de producción. Su montaje/PYTHONPATH y la invocación del constructor ResultRepository se corrigieron durante el desarrollo; los controles finales se repitieron correctamente.

**Pendiente:** login real con contraseña, navegación/frontend y acreditación integral de los cuatro estados vacíos. El código actual presenta estados para ejecuciones, análisis y modelo productivo; no se encontró una vista dedicada de campañas. Esto se registra como inspección de código, no como una prueba de interfaz completada. No se modificó el frontend.

## 6. Backup, cuarentena y sustitución

Backup operativo nuevo: **NO CREADO**. SHA-256: **no disponible**. Restauración de ese backup: **NO REALIZADA**. No se tomó el backup RESET.1 como sustituto ni se declaró suficiente el archivo del candidato.

Sólo se archivó el prototipo antes de retirar sus recursos: `/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backups/reset3_candidate/isolated_candidate_20260928.dump`, 11231865 bytes, SHA-256 `c115d41272e57787bf71b6cb43a675251a09137a8d7bfca2f2ea84d2e5d538c8`. Archivo privado 0600, directorio 0700, fuera de Git. Su TOC pudo leerse; **no se verificó la restauración íntegra de este archivo y no es un backup operativo**.

Cuarentena operativa: **0 archivos movidos**. Se mantiene como referencia la clasificación RESET.1B: 5.988 candidatos, protección de compartidos/ambiguos, fuentes, dataset, configuraciones y mounts. Esa clasificación no acredita por sí sola una nueva cuarentena ni permite moverlos antes de cumplir los requisitos pendientes. No se borró físicamente ningún artefacto operativo.

Sustitución lógica: **NOT_STARTED**. No se renombró, eliminó ni reconstruyó `malaria_experiments`; no se ejecutaron DELETE históricos ni migraciones sobre public. Se retiraron sólo la API, PostgreSQL desechable, su red y su volumen identificados como propios. Quedó una sola instalación PostgreSQL operativa.

## 7. Estado final y recuperación

SELECT READ ONLY de `2026-09-28 23:28:35.694127+00:00`: cluster `7668020338728398886`, base `malaria_experiments.public`, revisión **20260915_01**, **99 runs, 2 campañas, 72 miembros, 11 attempts, 11 sessions**. Las 97 cantidades y el catálogo coinciden con RESET.2A; los nueve schemas históricos siguen presentes. No se recalcularon los hashes de todas las filas operativas: la comparación exacta de contenido de esta etapa corresponde a la allowlist científica importada y los árboles de archivos protegidos.

El backend operativo respondió `/health: ok`; PostgreSQL, backend y frontend continúan en sus contenedores originales. Autenticación operativa: no se modificaron credenciales ni se realizó login; no se presenta una validación nueva. Estado OP1 operativo: no actualizado; sigue el esquema anterior, mientras READY fue acreditado únicamente en el prototipo E10.

No hace falta restaurar la base original porque no fue sustituida ni modificada por esta intervención. Permanece disponible y recuperable en su volumen original. Para continuar: resolver la aprobación de la congelación concreta; reconstruir el entorno aislado y validar login/UI; congelar escritores; generar el backup con el wrapper Docker-only; restaurar exactamente ese archivo y comparar inventario/hash; repetir selección/importación contra el inventario definitivo; preparar/ensayar sustitución y reversión; revalidar backup y fuentes antes del cambio. No se autoriza automáticamente TRAIN ni una campaña.

El plan de sustitución debe conservar el original como punto de recuperación hasta validar el nuevo estado y no destruir el último backup. Una discrepancia obliga a detener el cambio y volver al origen preservado según un procedimiento previamente ensayado; no ejecutar restores destructivos improvisados. **Ese procedimiento operativo todavía no fue implementado ni acreditado en esta ejecución detenida.**

## 8. Entregables y procedencia

HEAD: `acd7ea3ec50bffa07478beefca751bb2dd66d790`. Se añaden este informe, [evidencia JSON](reset_3_execution_evidence.json), allowlist y `scripts/reset/reset3/`. Hashes del código y de SQL legacy aplicado, conteos por tabla origen/candidato, comparación científica, checks funcionales, archivo candidato y limpieza figuran en JSON. No se alteraron migraciones históricas, configuración científica, código de aplicación ni documentación anterior.

**RESET.3 — DETENIDO. Fase: backup operativo obligatorio; mecanismo de congelación rechazado por revisión automática. Login real pendiente. Base original conservada.**
