# RESET.2 — Preparación del reset operativo controlado

**RESET.2 PREPARACIÓN — NO LISTO.** Preparación detenida por divergencia del inventario aprobado, conforme a «Cualquier diferencia no autorizada produce STOP». No se solicita autorización para ejecutar el reset con esta evidencia incompleta.

## 1. Bloqueo e inventario observado

SELECT en `malaria_experiments.public`, cluster `7668020338728398886`, rol `julio`, transacciones READ ONLY. Revisión: **20260915_01**. Se observaron **97 tablas y 1,192,668 filas**. Este inventario es diagnóstico, **no definitivo**, porque no se congelaron escritores tras detectar el STOP.

| Tabla | Filas aprobadas | Filas observadas | SHA-256 aprobado | SHA-256 observado |
|---|---:|---:|---|---|
| `audit_events` | 2629 | 2630 | `cfce0b2d3211cee591f977c796f187e100dc94470bb6a764b15868ee1234a152` | `043f729af5f7a9149594a3547d97a081d06ec84af5a853cc30c9897c127e442c` |
| `users` | 1 | 1 | `6d864c5f3ef3529fcf40abaa0c41f7f9e35b90ec84b04c65627fa4bdd3a2b426` | `482db5f6eeb6cf4853686d016505a95b508936633618c792d421c987d4c8fc93` |

La fila de auditoría más reciente es `7615cb3c-6fc3-44ac-bdae-5c6462105c56`, evento `USER_LOGIN_SUCCEEDED`, del 2026-09-28 a las 22:09:08.839616 UTC. `users.last_login_at` muestra 22:09:08.825693 UTC. La coincidencia explica plausiblemente el cambio; no demuestra que sea el único campo modificado ni autoriza actualizar el manifiesto. No se imprimieron contraseñas, hashes de contraseña, correos ni payloads personales.

**Resolución pendiente:** revisar y autorizar la actualización del inventario protegido, manteniendo `users` íntegro y el nuevo evento de login fuera del conjunto borrable. No incorporar nuevas filas a la allowlist de DELETE por inferencia. El manifiesto RESET.1 sigue intacto; su SHA-256 es `9c31c7ebcb3c21ad3c74841ab0e52507212c454bafd94ef2799495ba5c8c3efc`.

## 2. Identidad del código y diff completo

HEAD: `0f1fe179dba89ccd45e6bca6a1105758a0dcaf9d` (`RESET.1 — Auditoría y preparación de limpieza integral`). No hubo cambios tracked al iniciar. Los documentos y scripts RESET.1B estaban sin seguimiento; sus contenidos coinciden con los hashes publicados por RESET.1B. No se creó commit.

Se recuperaron las copias retenidas en `/tmp/reset1b_14908ae0b3f5` del backend. Su comparación completa está en [reset1b_execution.diff](../../../scripts/reset/reset2/reset1b_execution.diff). El diff de HEAD y la representación íntegra de los archivos RESET.1B no versionados están en [reset1b_worktree.diff](../../../scripts/reset/reset2/reset1b_worktree.diff). Git status, SHA-256 de ambos diffs y de todos los ejecutables revisados constan en [la evidencia JSON](reset_2_preparation_evidence.json).

Cambios posteriores al ensayo SQL:

- `rehearsal.py`: ahora distingue una excepción anterior a COMMIT de una respuesta incierta después de solicitarlo. El ensayo SQL anterior restauraba archivos incluso en esa segunda situación; el código final conserva la cuarentena y registra `COMMIT_UNCERTAIN`.
- `run.py`: automatiza la prueba del flujo de COMMIT y la barrera SQL de producción que antes se habían ejecutado por separado.

La copia retenida permite identificar esas diferencias, pero no constituye un sello inmutable de toda la ejecución histórica. Los hashes publicados representan el código final, **no prueban que ese código final haya pasado el ensayo SQL integral**. Las pruebas con dobles de transacción no sustituyen esa repetición. Debe repetirse el ensayo afectado con el procedimiento final y backup nuevo; quedó pendiente por el STOP. No se ejecutó el runner anterior, que también incluye una migración prohibida en esta etapa.

## 3. Prechecks acreditados y pendientes

El precheck final terminó con **exit 2 / STOP_INVENTORY_DRIFT**, reproduciendo ambas divergencias. Sus SELECT comprobaron:

- Runs: 99 (88 completed, 10 failed, 1 interrupted); ningún TRAIN/EVALUATE/EXPLAIN activo según estados persistidos.
- Campañas: 2 paused; miembros: 72 (63 pending, 7 failed, 1 interrupted, 1 verified).
- Attempts y sessions: 11 cada uno (9 failed, 1 interrupted, 1 verified).
- Job Local: 1 released; assessment attempts: 0.
- Análisis de frotis: 45 ready_for_analysis, 17 review_required, 11 blocked; detección, clasificación y colas de calidad sin estados de ejecución activos.
- GlobalGate sin owner, db_pid ni blocked_reason; process_evidence vacío. No transacciones ajenas activas en el precheck. Actividad y locks concretos en JSON.
- Los fingerprints de las otras 95 tablas coinciden con RESET.1. Los nueve schemas históricos coinciden con RESET.1B y no se modificaron. La protección del dataset se acredita aquí para sus tablas, no para una nueva revisión física de sus archivos.

Espacio observado: host 435 GiB disponibles; almacenamiento Docker 835.088.204 KiB disponibles. Estas cifras no acreditan todavía una ubicación de cuarentena operativa ni su capacidad efectiva. No se completaron una ventana sin escritores, un nuevo inventario físico ni la validación de todos los procesos externos Local. No declarar esos controles aprobados.

## 4. Backup nuevo y restauración

**No generados ni ensayados**, por el STOP anterior. SHA-256 de backup RESET.2: **no disponible**. No se reutiliza el backup RESET.1 como si fuera nuevo.

Una vez autorizada la reconciliación, congelar todos los escritores y entradas de trabajo de forma reversible, registrar procesos/conexiones y fijar el inventario definitivo. Ejecutar el wrapper aprobado `scripts/db/backup.sh` / `make db-backup` con `CAPSTONE_BACKUP_DIR` en `backups/reset2/<UTC>/`, persistente, directorio 0700 y dump 0600. Registrar UTC, cluster, origen Alembic, tamaño, SHA-256, TOC y control de acceso. Mantener el backend disponible para el SELECT de identidad que realiza el wrapper: pausar el contenedor completo impediría ese paso.

Restaurar en PostgreSQL 17.9 desechable sin puertos ni volúmenes compartidos con el origen. Comparar tablas, conteos, hashes por tabla y datos protegidos contra el inventario congelado; verificar también los nueve schemas. El éxito de pg_dump, el TOC o el checksum por sí solos no validan el backup. Conservar dump y evidencia verificada hasta el cierre humano del reset y de la migración futura; nunca eliminar el único backup válido.

## 5. Vía operacional independiente

`operational.py` es **sólo una barrera**, probada con exit 2 antes de abrir conexiones. **No es el ejecutor solicitado terminado**. El STOP impidió construir y acreditar ese ejecutor; no se debilitó ninguna guarda RESET.1B.

El futuro ejecutor deberá enlazar cluster exacto, `malaria_experiments.public`, rol autorizado, HEAD y hashes del código aprobado, manifiesto aprobado, backup nuevo restaurado, IDs de operación/autorización y evidencia de ventana sin escritores, GlobalGate libre y publicaciones congeladas. No bastará HEAD mientras existan scripts ejecutables sin seguimiento. Ningún flag genérico debe habilitar limpieza sobre otra base. La presente preparación no contiene autorización operativa.

Conservar la allowlist de PK explícitas y hashes de preimagen, controles de filas nuevas emitidas por servicios y triggers, FK activas y validación de constraints. Usar sustitución transaccional acotada de guards, con comprobación exacta de funciones, propietarios, ACL, triggers y catálogo antes de COMMIT. Rechazar cualquier fila fuera del conjunto aprobado; no introducir excepciones permanentes ni modificar migraciones históricas.

## 6. Publicaciones y deployments

Los fingerprints de estas tablas permanecen iguales al manifiesto aprobado. Publicación activa `81d69942-17eb-4999-a6bd-2b05779a65a4`; deployment activo `cf2f20d3-a1e0-499c-b5ab-501b7c1ae198`; modelo versión `172b7031-9f79-44e3-a7ad-2dc10a9ffd08`. Estado observado completo en JSON. No se llamó a servicios mutantes sobre public.

Preparar `Stage2PublicationService` y `Stage2ModelAvailabilityService` con una conexión transaccional compartida. Acumular invalidaciones de caché y aplicarlas sólo tras confirmar SQL. El resultado `SIN_MODELO_PRODUCTIVO` fue acreditado en RESET.1B; falta repetirlo con el procedimiento final. No usar el endpoint vivo como sustituto de la transacción coordinada.

## 7. Cuarentena recuperable

Clasificación previa, **no revalidada físicamente en RESET.2**: 5.988 archivos candidatos; preservar 108 compartidos, 288 ambiguos y 74 imágenes fuente. Preservar además dataset original, materialización oficial, configuración científica, directorios y raíces de mounts. No se movió ningún archivo operativo.

El procedimiento pendiente debe validar ubicación canónica, tipo regular, ausencia de symlinks, tamaño y SHA-256 justo antes de cada movimiento, destino persistente por filesystem y permisos reales. Los binds de sólo lectura y el volumen Docker requieren rutas operables específicas; el ensayo anterior sobre copias temporales no prueba esos permisos. Usar journal durable y recuperable por operación; no mover directorios completos ni admitir ubicaciones no enumeradas. No borrar definitivamente la cuarentena.

## 8. Postcondiciones y recuperación pendientes

No se presentan como resultados nuevos las cifras de RESET.1B. Recalcular las filas protegidas tras autorizar el inventario actualizado: el nuevo login no puede desaparecer para conservar artificialmente la cifra anterior de 139.586.

En el nuevo clon deben demostrarse fallos antes del primer DELETE, durante la secuencia y tras todos los DELETE; rollback de todas las tablas por hash, restauración de archivos, catálogo y guards originales, FK sin huérfanos y datos protegidos intactos. Después del éxito: tablas históricas vacías, auditoría protegida conservada, publicaciones/deployments retirados y caché invalidada sólo tras confirmación. Las pruebas con dobles y las de RESET.1B son antecedentes, no cumplimiento de esta etapa.

**COMMIT_UNCERTAIN:** una respuesta perdida no equivale a rollback. Conservar cuarentena y journal, mantener escritores bloqueados, no repetir DELETE ni restaurar archivos automáticamente. Reconectar al cluster exacto y reconciliar el estado completo con las pre/postcondiciones y la identidad de operación. Si se acredita rollback, restaurar archivos; si se acredita commit, completar invalidación y verificación. Ante estado no concluyente, detenerse y requerir recuperación humana sobre backup previamente restaurado y validado. Si tampoco puede confirmarse un rollback anterior a COMMIT, conservar los archivos hasta reconciliar: no presumir su éxito por haber llamado a rollback.

Antes de comenzar, un precheck fallido no exige restauración de datos. Durante la transacción, verificar rollback real y restaurar exclusivamente movimientos propios acreditados. Después de un commit confirmado, la recuperación de SQL requiere restauración verificada; no asumir que downgrade Alembic o rollback de código restaura datos. El procedimiento final y estos escenarios aún no están ensayados con un backup RESET.2.

## 9. Relación con E10.OP3

Orden futuro: reset operativo autorizado → validación vacía → migración E10 autorizada por separado. Incorporar antes de esa migración la corrección pendiente del wrapper oficial para propagar `lock_timeout` y `statement_timeout` al proceso Docker/Alembic y verificar los valores efectivos. No se modificó el wrapper ni se ejecutó migración. Un reset exitoso no autoriza TRAIN, TEST ni una campaña nueva.

## 10. Validaciones y estado final

Se verificaron sintaxis Python, salida 2 de la barrera operacional y salida 2 del precheck ante divergencias reales. Todos los hashes publicados de scripts RESET.1B permanecen iguales. No se ejecutó ensayo integral ni regresión del reset después del STOP.

Dos snapshots READ ONLY, de `2026-09-28 22:20:10.605398+00:00` y `2026-09-28 22:22:01.853100+00:00`, mostraron idénticos fingerprints de public y de los nueve schemas, e idéntico catálogo de public. El precheck final de `2026-09-28 22:22:51.807003+00:00` volvió a obtener los mismos hashes de public. Esto acredita invariancia entre las observaciones; no representa una congelación ni garantiza ausencia de cambios futuros.

Public conserva revisión `20260915_01`, todos sus runs, intentos, sesiones y publicaciones. Las dos diferencias señaladas ya existían en la primera lectura de RESET.2. No hubo DELETE, backup nuevo, congelación, migración, movimientos operativos, TRAIN, TEST ni nueva campaña. Sólo se añadieron artefactos RESET.2 y copias auxiliares privadas de lectura en `/tmp` del backend.

Archivos añadidos: documento presente, evidencia JSON y `scripts/reset/reset2/` (README, precheck, barrera y dos diffs). Los SHA-256 de los scripts y diffs constan en JSON. Riesgos abiertos: divergencia no autorizada, procedencia incompleta del ensayo final, backup nuevo inexistente, ejecutor pendiente, cuarentena operativa sin validar y recuperación integral no repetida.

**Revisión humana pendiente de las diferencias de inventario. No continuar con el reset ni considerar esta preparación lista para GO/NO-GO.**
