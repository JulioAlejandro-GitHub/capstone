# STORAGE.CLEAN.1 — Eliminación definitiva de artefactos históricos

**STORAGE.CLEAN.1 — LIMPIEZA EJECUTADA Y VERIFICADA.**

Ejecución: 28-09-2026, hora de Chile (29-09 UTC). Se eliminaron definitivamente **6.405 archivos**, **5.025.380.652 bytes lógicos**. El espacio libre observado del Mac aumentó **5.039.439.872 bytes (4.69 GiB)** durante la eliminación. No se eliminó ningún volumen Docker, backup SQL, dato científico, archivo de aplicación o configuración.

## 1. Alcance e inventario

Se inspeccionó el workspace completo, los bind mounts efectivos, los directorios temporales conocidos `/private/tmp/reset*`, la configuración Compose, todos los contenedores y los siete volúmenes Docker. Se inspeccionaron también `docker diff` del backend y, mediante streaming tar sin extracción, `/tmp` y `/app/var` del contenedor detenido. No se hizo un borrado global del Mac ni una afirmación sobre copias remotas/offline.

Referencias utilizadas: [RESET.1](../engineering/e10_execution_refactor/reset_1_full_history_manifest.json), [RESET.1B](../engineering/e10_execution_refactor/reset_1b_file_classification.json), [E10.OP3](../engineering/e10_execution_refactor/e10_op3_operational_migration.md), su evidencia y el manifiesto exacto de cuarentena de RESET.3. Los hashes de esas referencias y de los productores de artefactos están en [la evidencia JSON](storage_clean_1_evidence.json).

Se buscaron `.keras`, `.h5`, `.hdf5`, `.ckpt`, `.pt`, `.pth`, `.npy`, `.npz`, `.pkl` y `.parquet`, pero se clasificaron por procedencia y función. Las extensiones no determinaron la eliminación. Bibliotecas/fixtures de los entornos Python, descargas originales del dataset, TFRecords, código y evidencia de auditoría se conservaron.

La mayoría del peso correspondía a `backups/reset3_final/artifact_quarantine`, que contenía los derivados ya retirados de las rutas activas por RESET.3. Se encontraron además **36 copias idénticas de manifiestos y metadatos de publicaciones históricas**, 12.625 bytes, bajo `.claude/worktrees/agent-a9f62aff737e8006b/malaria_dl_local_project/releases/`. Cada copia coincidía por SHA-256 con su bundle histórico; no era configuración del registry ni código del worktree.

## 2. Protección, escritores y manifiesto congelado

Se detuvieron ordenadamente backend/frontend con `docker compose stop --timeout 45 frontend backend`. No había procesos Python/TRAIN locales, experimentos, campañas, attempts, sessions o local jobs activos; sus tablas estaban vacías y GlobalGate libre. El contenedor temporal de auditoría no tenía API ni puertos; sus montajes eran READ ONLY y no montaba el volumen PostgreSQL.

Antes de borrar se verificaron **todos** los tamaños y SHA-256, rutas canónicas, ausencia de symlinks en cada componente, `nlink=1`, inodos/dispositivos y ausencia de archivos seleccionados abiertos. Finder sólo mantenía directorios y tres `.DS_Store` excluidos; la primera comprobación se detuvo antes de borrar nada y se precisó para evaluar la intersección con las rutas seleccionadas.

Manifiesto congelado: `backups/storage_clean_1/evidence/deletion_manifest.json`.

**SHA-256:** `6b379e22c0f754d9e6ead614c63f0d723ea215f94b71e7e45911a43a7f364ed8`.

Ninguna de las 6.405 rutas intersecta las familias protegidas. Se excluyeron además `data/` del proyecto, `.git`, bibliotecas, backups PostgreSQL y archivos de mantenimiento/evidencia. Los aliases del bind local (`/app/var/local_artifacts` y `/app/malaria_dl_local_project/local_execution_artifacts`) se trataron como una sola ubicación física; `/app/backups` y `/host_mnt/.../backups` no se contaron otra vez.

Las 288 entradas antiguamente no asociadas inequívocamente a un run y los 99 aliases compartidos de outputs de RESET.1B se acreditaron por su función generada, hashes archivados, namespaces de runs/releases y contratos productores (`trainer.py`, `cell_crop_storage.py`, `cell_explanation_storage.py`). No había consumidores vigentes de modelos/publicaciones, referencias protegidas ni inodos compartidos. La atribución no dependió de encontrar sus filas en PostgreSQL después del reset.

## 3. Eliminación física realizada

Se utilizó `unlink` individual únicamente sobre el manifiesto congelado. Se revalidó el conjunto completo antes del primer borrado y se comprobó cada identidad de archivo antes de retirarlo. El journal registra cada confirmación. No se usaron `rm -rf`, comandos recursivos sobre raíces compartidas, purga por extensión ni `docker system prune --volumes`.

| Categoría | Archivos eliminados | Bytes lógicos |
|---|---:|---:|
| DERIVED_CELL_CROPS | 2,280 | 9,892,699 |
| E9_CHECKPOINTS | 27 | 139,053,174 |
| HISTORICAL_GRADCAM | 2 | 40,539 |
| HISTORICAL_RELEASES | 42 | 103,775,984 |
| HISTORICAL_RELEASE_WORKTREE_COPIES | 36 | 12,625 |
| TRAINED_MODELS | 80 | 3,451,664,301 |
| TRAIN_EVALUATE_EXPLAIN_OUTPUTS | 3,938 | 1,320,941,330 |
| **Total** | **6.405** | **5.025.380.652** |

Las rutas físicas completas, tamaño, SHA-256, inodo y clasificación figuran en `deleted_physical_files` de [la evidencia](storage_clean_1_evidence.json); el manifiesto congelado añade la procedencia individual. El journal durable está en `backups/storage_clean_1/evidence/deletion_journal.jsonl`.

Quedan sólo directorios vacíos y marcadores técnicos/OS en las antiguas raíces. Se preservaron `.gitkeep`, `.training.lock` y `.DS_Store`; no son modelos ni outputs científicos. Las 36 eliminaciones del worktree son exclusivamente archivos de releases históricos: `git diff` de ese worktree no muestra cambios de código. El checkout principal mantiene intactos sus **1.306 archivos previamente versionados**; sólo se añadieron los dos entregables de esta intervención.

Esta decisión elimina la recuperación física de esos experimentos prevista por la antigua cuarentena de RESET.3, de acuerdo con la autorización actual. Los dumps PostgreSQL, la base anterior retenida y la evidencia histórica se conservaron íntegros; no se reescribió el informe histórico de RESET.3 como si la cuarentena aún existiera.

## 4. Docker: ubicación física y exclusiones

| Volumen | Clasificación / acción: conservar | Archivos inventariados | Bytes inventariados |
|---|---|---:|---:|
| `6e7177a0427e9d65af0b8ca098797550ffc73d829fc16e13e978ef2910322c79` | UNATTRIBUTED_EMPTY_VOLUME_RETAINED | 0 | 0 |
| `555e12b04348ae702c59c28d693bcce224965c06a75fdeb55c5461fabd6c72f5` | OTHER_APPLICATION_RABBITMQ_RETAINED | 35 | 70085 |
| `capstone-development_storage` | OLD_CAPSTONE_VOLUME_EMPTY_RETAINED | 0 | 0 |
| `capstone-malaria_postgres_data` | PROTECTED_OPERATIONAL_POSTGRESQL | no inspeccionado físicamente | protegido |
| `capstone-malaria_scientific_storage` | PROTECTED_ORIGINAL_SCIENTIFIC_IMAGES | 75 | 24183870 |
| `docker_minio_data` | OTHER_APPLICATION_MINIO_VIGILANTE_RETAINED | 169535 | 20934460744 |
| `eef52fa049aeeb563e12f5a1ee56a871adbee51160db719312dcbced32277c03` | OTHER_APPLICATION_RABBITMQ_RETAINED | 42 | 778292 |

Los volúmenes Capstone auditados no tenían derivados históricos restantes: `capstone-development_storage` estaba vacío y `capstone-malaria_scientific_storage` contenía 74 imágenes originales y un marcador OS. Sus hashes se conservaron. MinIO/Vigilante y RabbitMQ pertenecen a otras aplicaciones; se conservaron, al igual que el volumen anónimo vacío de propiedad no acreditada. No se asumió que un volumen sin uso fuera descartable.

La metadata de los siete volúmenes y los mounts de todos los contenedores son iguales antes/después. Los inventarios de los volúmenes no PostgreSQL también coinciden. Para los dos volúmenes Capstone se comparó el hash de cada archivo; en aplicaciones ajenas se inventariaron rutas/tamaños/identidades sin atribuir sus objetos a Capstone. El volumen PostgreSQL no se montó ni se recorrió para buscar artefactos.

En la capa interna del backend se encontraron **12 fixtures de pruebas, 20 bytes cada uno**, con contenido equivalente a `b"synthetic checkpoint"` y SHA-256 `d94f152912894b080bd7a377d2c1c1cc535bd5d1931b0082f3b668ab608a8a2e`. Se acreditó su productor en `tests/test_campaign_executor_e5.py:29`. Se conservaron como datos sintéticos de software: no son checkpoints entrenados, modelos operativos ni copias de E9. No se ejecutó pytest ni ningún stage científico.

No se eliminó ni reconstruyó el backend, frontend o PostgreSQL. Sólo se retiró el contenedor temporal de auditoría, sin eliminar sus volúmenes compartidos.

## 5. Archivos ausentes y excluidos

Los **43 checkpoints E9** documentados en E10.OP3 siguen clasificados **ALREADY_MISSING**. Sus rutas originales no aparecieron en la auditoría del backend y no se encontraron copias adicionales con sus hashes en las ubicaciones Capstone inspeccionadas. No se cuentan como eliminados ni como espacio liberado. La evidencia enumera los 43 con run ID, ruta y hash esperado.

Los **27 checkpoints E9** que sí existían habían sido trasladados a la cuarentena por RESET.3 y se eliminaron ahora. En las rutas autorizadas quedan cero checkpoints E9 operativos.

Se conservaron, con motivo explícito en la evidencia:

- Todos los originales, materialización, split, fingerprints y configuración activa.
- Los **10 archivos PostgreSQL de backup/restauración** encontrados, incluidos dumps y cuatro `restore.sql` temporales. Sus hashes antes/después coinciden; su peso no se atribuye a modelos eliminables.
- Entornos Python y fixtures de dependencias; fuentes y descargas del dataset también fuera de `malaria_dl_local_project/data/`.
- Evidencia y manifiestos históricos, scripts de mantenimiento y archivos de aplicación.
- Los 12 fixtures sintéticos internos, marcadores compartidos y volúmenes ajenos/de propietario desconocido.

No quedan candidatos de **artefactos históricos Capstone** sin clasificar dentro del alcance auditado. Las exclusiones anteriores están protegidas o acreditadas como ajenas/no experimentales; no se borraron para maximizar el espacio libre.

## 6. Integridad antes/después

PostgreSQL se consultó exclusivamente con transacciones READ ONLY. Las **97 tablas y 138.044 filas** del estado inicial de esta intervención conservan exactamente sus hashes después de borrar y después de reiniciar los servicios; también coincide el catálogo completo. No se ejecutó DELETE, TRUNCATE, DROP, migración ni cambio de nombre de base.

Los hashes de las tablas de dataset/split y sus registros científicos constan individualmente en `postgres.tables_before` y `postgres.tables_after`. Se mantuvieron IDs, asignaciones, materialización y fingerprints; no se recalculó el split ni se utilizó un verificador que escribiese auditoría.

Hashes agregados de archivos protegidos, iguales antes/después y tras el reinicio:

| Raíz protegida | Entradas | SHA-256 agregado |
|---|---:|---|
| `malaria_dl_local_project/data` | 82,705 | `4c82e5102b6f8cd1673c670d5dbc6dee03d2117c2d70fb545f1c32f74eea3e08` |
| `malaria_dataset_split_project` | 210 | `66efb975a9b160b8edce3e465cddba4ac98f1f5d0d2ab7d5bb9234bf680bfdd6` |
| `malaria_dl_local_project/configs` | 6 | `ceecb0c7e38f94af23a438be44ca078250e44a445dc31baa7e2783cdfee84862` |
| `malaria_dl_local_project/src` | 485 | `1ce3968e1e0cdc5621a167b33715de97f7c63f6423919137cf3737b7d462ecff` |
| `alembic` | 81 | `f31f479b7f22eeecbe0c4d4f8930ab274c15dfd15da9fbe3742f0ef086e6eff4` |
| `backend_api` | 406 | `d4d6f6456d97e68dd25b5665941df0a78dd1e2966f7f38f482cd3cab5564ec13` |
| `frontend` | 2,893 | `f24df480b272658f7b0a4d37f4d83d491ef4768cb441b33aa5a709284c9e7770` |
| `data` | 27,584 | `ea5c5f76c6e6fccf47cd18fc2c62fc8d3372263bd056795560e832b0fe7f5852` |

El inventario exploratorio inicial precede al congelamiento y contabilizó una entrada menos (6.148 bytes) en `data/`; no se atribuye esa variación previa a la limpieza ni se identifica su autor. La comparación protectora utiliza `protected_before.json` contra `protected_after.json` y `protected_final.json`, que son idénticos; no se sustituyó un hash científico ni se borró ese marcador.

## 7. Espacio eliminado frente a espacio realmente disponible

| Medida | Antes | Después inmediato | Cambio |
|---|---:|---:|---:|
| Mac: bytes disponibles (`statvfs`) | 461,342,404,608 | 466,381,844,480 | **+5,039,439,872** |
| Docker VM: bytes disponibles | 854,785,478,656 | 854,785,478,656 | **0** |
| `Docker.raw`: bloques asignados en el Mac | 74,864,521,216 | 74,864,521,216 | **0** |

Bytes lógicos retirados: **5.025.380.652**. Bloques asignados a esos archivos antes de borrar (`st_blocks × 512`): **5.039.370.240**. Incremento observado del espacio disponible, entre `2026-09-29T01:08:00.025361+00:00` y `2026-09-29T01:08:02.824397+00:00`: **5.039.439.872 bytes**. No se confunden tamaño lógico, bloques asignados y espacio libre observado; la diferencia pequeña puede incluir actividad concurrente de APFS/sistema. La evidencia generada después de esa ventana también ocupa espacio.

Los artefactos habían pasado de sus ubicaciones Docker/host a la cuarentena del Mac en RESET.3; por eso la liberación actual corresponde al Mac. No se atribuye a esta operación una reducción del tamaño virtual de `Docker.raw`, ni se ejecutó compactación/prune para fabricar ahorro Docker.

## 8. Estado final y evidencia

Backend/frontend se reiniciaron y responden HTTP 200; `/health` es `ok` y `/ready` confirma database/migrations/storage `ready`. PostgreSQL permanece E10 y operativo. No se inició campaña, TRAIN, EVALUATE, EXPLAIN o TEST.

- `docs/maintenance/storage_clean_1_execution.md`: este informe.
- `docs/maintenance/storage_clean_1_evidence.json`: inventarios, rutas eliminadas, exclusiones, 43 ausencias E9, hashes, espacio y validaciones.
- `backups/storage_clean_1/evidence/`: manifiesto congelado, journal, snapshots y scripts exactos utilizados, sin credenciales. No contiene copias de los modelos eliminados.

**STORAGE.CLEAN.1 — LIMPIEZA EJECUTADA Y VERIFICADA.**
