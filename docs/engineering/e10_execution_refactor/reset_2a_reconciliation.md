# RESET.2A — Reconciliación del inventario y acreditación del código final

**RESET.2A — APROBADO PARA RETOMAR PREPARACIÓN.** Se resolvieron los dos hallazgos. Esto permite retomar la preparación RESET.2; no autoriza el reset operativo ni sustituye su backup nuevo, ventana sin escritores o revisión humana.

## A. Inventario: EXPECTED_AUTHENTICATION_DRIFT

Se restauró el backup histórico de RESET.1 en dos PostgreSQL 17.9 desechables. Antes de cualquier reset aislado, cada restauración coincidió con los conteos y SHA-256 de las 97 tablas del golden. Se comparó contra `malaria_experiments.public` mediante transacciones READ ONLY, cluster `7668020338728398886`, rol `julio`, revisión `20260915_01`.

La comparación completa confirmó exclusivamente:

- Una nueva fila de `audit_events`: `7615cb3c-6fc3-44ac-bdae-5c6462105c56`, `USER_LOGIN_SUCCEEDED`, acción `login`, éxito verdadero, timestamp `2026-09-28T22:09:08.839616+00:00`. Actor `admin`, ID `9fdddd0f-e485-4c18-b75d-df3869917f41`. Recurso `login`, resource_id NULL, petición `POST /api/v1/auth/login`. Las 2.629 filas anteriores permanecen exactamente iguales; ahora hay 2.630.
- Un único campo cambiado en `users`: `last_login_at`, de `2026-09-28T20:57:19.276621+00:00` a `2026-09-28T22:09:08.825693+00:00`. Se compararon todas las columnas. ID, username, email, password_hash, status, created_at, updated_at y disabled_at permanecen iguales. Los valores de email/password_hash no se publican.

La separación entre actualización y evento es 13,923 milisegundos. El flujo existente en `backend_api/app/routes/auth.py` actualiza `last_login_at` después de verificar credenciales y emite `USER_LOGIN_SUCCEEDED`; concuerda con los datos observados. Las otras **95 tablas** no presentan diferencias de contenido. No se borró ni revirtió el login.

| Tabla | Conteo original → nuevo | SHA-256 original | SHA-256 nuevo |
|---|---|---|---|
| audit_events | 2.629 → 2.630 | `cfce0b2d3211cee591f977c796f187e100dc94470bb6a764b15868ee1234a152` | `043f729af5f7a9149594a3547d97a081d06ec84af5a853cc30c9897c127e442c` |
| users | 1 → 1 | `6d864c5f3ef3529fcf40abaa0c41f7f9e35b90ec84b04c65627fa4bdd3a2b426` | `482db5f6eeb6cf4853686d016505a95b508936633618c792d421c987d4c8fc93` |

Conteos y hashes de las **97 tablas**, antes y después, constan en [reset_2a_evidence.json](reset_2a_evidence.json). El total actual es **1.192.668 filas**.

### Línea base explícita v1

[reset_2a_operational_baseline_v1.json](reset_2a_operational_baseline_v1.json), SHA-256 `cb6179585f8324d31d71b92b258994ac258140c389e6ec061f3a190510e7f29b`. Es un artefacto versionado por nombre y contenido, no un commit Git nuevo. El golden original conserva su archivo y SHA-256 `9c31c7ebcb3c21ad3c74841ab0e52507212c454bafd94ef2799495ba5c8c3efc`.

Cambios de datos reflejados exclusivamente en `tables.audit_events` (current, sha256_before, keep) y `tables.users.sha256_before`. Se añade metadata explícita de reconciliación. No cambia ninguna PK, predicado ni cantidad autorizada para DELETE. La nueva fila de autenticación queda protegida: audit retenido **1.103**, total protegido **139.587**. Los apartados heredados del manifiesto, incluido el backup, conservan el contexto histórico; no presentan ese backup como una copia nueva de la línea base reconciliada.

## B. Procedencia y código definitivo

HEAD: `0f1fe179dba89ccd45e6bca6a1105758a0dcaf9d`. Los scripts RESET.1B siguen sin cambios; se mantiene su separación estricta de public. Git status y SHA-256 completos de los archivos revisados/ejecutados están en JSON. Se contrastaron los archivos cargados realmente en ambos clones con los archivos entregados y el sello previo al ensayo.

El [diff de procedencia RESET.2](../../../scripts/reset/reset2/reset1b_execution.diff) conserva la diferencia entre la copia retenida del ensayo anterior y el código final. `rehearsal.py` incorporó después de aquel ensayo la distinción `commit_requested`: antes de solicitar COMMIT, rollback y recuperación de archivos; tras solicitarlo, excepción → `COMMIT_UNCERTAIN`, sin asumir rollback ni restaurar archivos. `run.py` agregó la automatización de controles antes ejecutados separadamente. Los hashes publicados antes no acreditaban por sí solos ese flujo integral.

Ahora se ensayó el **nodo AST exacto del bloque final de reset/cuarentena/COMMIT** extraído de `rehearsal.main`, ejecutando `reset()` y las funciones guard originales, SQL real y movimientos reales de copias. SHA-256 de `rehearsal.py`: `5c132b2475b25066d3610e3f7ebde46951197ed2120bfc66ef79798aa6b9a49d`; SHA-256 del bloque: `ad1fa2dd19416b6e1d6ac345c3dcd4854c0a9ef9e9e6f863e7c2a22aade913e1`.

No se ejecutó todo el `main` anterior: incluye migración E10 y ésta no se invocó. El driver nuevo sustituye sólo la orquestación del ensayo y las comprobaciones posteriores. No se afirma haber revalidado la sección E10 ni una vía operativa todavía inexistente. Las anteriores pruebas con dobles quedan como antecedentes; la acreditación de esta etapa procede de los ensayos reales siguientes.

## C. Ensayo integral y recuperación

Dos clones sin puertos ni volúmenes operativos compartidos, restaurados desde el backup histórico verificado. En cada clon se reprodujeron sólo las dos diferencias autenticadas y se comprobó igualdad exacta con las 97 tablas operativas antes del ensayo. No se creó el backup operativo RESET.2.

| Escenario | Resultado acreditado |
|---|---|
| Error SQL después de todos los DELETE | Reset integral, cuarentena real de copias y `RAISE EXCEPTION` real. Rollback con igualdad de las 97 tablas, catálogo y errores de guards originales; archivos restaurados exactamente; caché intacta. |
| Commit exitoso | Reset integral y COMMIT real; conexión física nueva verifica postcondiciones; sólo después se invalida caché desechable. |
| Confirmación de COMMIT perdida | COMMIT real termina; un proxy Python lanza una excepción al llamador. El bloque final registra `COMMIT_UNCERTAIN`, no solicita rollback ni restaura archivos; preserva cuarentena y caché. |
| Reconciliación del resultado incierto | Conexión física nueva, PID distinto, valida todas las tablas, datos protegidos, catálogo, guards, FK y ausencia de historial borrable. Se confirma COMMIT y se invalida caché. |

Cada reset completo eliminó **1.053.178 filas en el clon**, incluidas 97 filas producidas durante el mantenimiento por servicios/triggers. Resultado confirmado: **70 tablas históricas vacías**, auditoría protegida conservada, **139.587 filas protegidas intactas**, **208 FK sin huérfanos**, catálogo y guards originales restituidos. El guard append-only volvió a rechazar DELETE de auditoría después del commit.

Se copiaron y verificaron **6.458 archivos** por escenario; **5.988** candidatos se movieron sólo dentro de la cuarentena desechable, conservando **470 copias protegidas** en su ubicación. Se revalidaron los archivos originales; ninguno fue movido. En el caso incierto hubo **cero llamadas de restauración** después de solicitar COMMIT. Se invalidaron 36 entradas de caché de prueba únicamente después de confirmar SQL. `SIN_MODELO_PRODUCTIVO` quedó verificado en ambos clones con los servicios existentes; no se alteró ninguna publicación o deployment operativo.

**Alcance de la simulación:** PostgreSQL y filesystem son reales; el proxy sólo inyecta una excepción tras el retorno del COMMIT real. No fue una interrupción de red real, corte de energía ni caída del proceso. No se utilizaron dobles para sustituir SQL o movimientos de archivos. Tampoco se acredita durabilidad del journal ante caída del host: el journal heredado no usa fsync.

Si la conexión nueva no permite demostrar el resultado, debe mantenerse `COMMIT_UNCERTAIN`, la cuarentena y el bloqueo de escritores. Una respuesta perdida no prueba rollback. La vía operativa futura deberá implementar esa reconciliación y recuperación persistente; este ensayo confirma el escenario en que el servidor sí había completado el commit.

## D. Estado operativo y protección

El precheck SELECT de RESET.2, ejecutado contra la nueva línea base, terminó con **exit 0 / DATABASE_PRECHECK_ONLY_PASSED**, sin divergencias. Un primer intento concurrente terminó con exit 137 y no se consideró válido; se repitió por separado. No se establece concluyentemente la causa de ese cierre.

Estado operativo final: 99 runs (88 completed, 10 failed, 1 interrupted); 2 campañas paused; 72 miembros; 11 attempts; 11 sessions; 1 job Local released; 0 assessment attempts. GlobalGate libre. Sin estados activos de TRAIN/EVALUATE/EXPLAIN, análisis o colas en el precheck. Publicaciones y deployments operativos coinciden con el golden; sus identidades y estados están en JSON.

Los snapshots READ ONLY de apertura/cierre de ambos ensayos coinciden en las 97 tablas y en el catálogo de public. Los **nueve schemas históricos** conservan sus fingerprints. Esto acredita invariancia observada, no una ventana congelada contra escrituras futuras.

Los fingerprints de **82.744 entradas protegidas** —dataset/fuentes, materialización, configuración, registro de modelos y migraciones— coinciden con RESET.1B antes y después. Se verificaron adicionalmente los 42 archivos científicos/runtime listados por el golden. Los hallazgos históricos de archivos ausentes o ambiguos no se reinterpretan: conservan la clasificación y protección aprobadas.

No hubo reset, retiro de publicaciones, cambios de deployments ni movimientos de archivos operativos. No se ejecutó TRAIN, TEST, nueva campaña ni migración, ni siquiera en los clones. Public y ambos clones conservaron `20260915_01` durante las pruebas. Se retiraron sólo contenedores, volúmenes y copias desechables marcados como propios; la evidencia y el backup histórico permanecen.

## Cambios entregados y siguiente límite

Se añaden este documento, `reset_2a_evidence.json`, la línea base v1 y `scripts/reset/reset2a/` (`reconcile.py`, `recovery.py`, README). No se modifica código de aplicación, migraciones, configuración científica, scripts RESET.1B, documento histórico RESET.2 ni su barrera operativa.

Para retomar RESET.2 debe seleccionarse explícitamente la línea base v1 y comprobar su SHA-256. Todavía faltan congelar escritores, fijar inventario definitivo, crear/restaurar/verificar el backup nuevo y completar/acreditar el ejecutor operacional y cuarentena persistente. Una divergencia nueva exige detenerse; esta aprobación no autoriza absorberla silenciosamente. El reset real requiere autorización humana separada.

**RESET.2A — APROBADO PARA RETOMAR PREPARACIÓN.**
