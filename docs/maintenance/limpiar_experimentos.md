# Limpieza reutilizable de experimentos (MAINTENANCE.3)

Los tres comandos ejecutan una limpieza real, sin preguntas ni opciones para omitir controles. Deben invocarse desde la raíz del proyecto, con Python 3.11+ y Docker Compose disponibles. Python del host sólo orquesta; SQL, Alembic y dependencias del backend se ejecutan en Docker. No se inicia ningún stage científico.

```sh
make limpiar-experimentos-bd
make limpiar-artefactos
make limpiar-experimentos
```

| Comando | Alcance | Resultado cuando ya está limpio |
| --- | --- | --- |
| `limpiar-experimentos-bd` | Reconstruye la base lógica con esquema oficial E10 y copia íntegra de datos protegidos. No borra archivos experimentales. | `ALREADY_CLEAN` |
| `limpiar-artefactos` | Borra archivos históricos acreditados por manifiesto. No purga filas SQL. Rechaza publicaciones activas. | `NO_ARTIFACTS_FOUND` |
| `limpiar-experimentos` | BD, validación, archivos, validación final. Un fallo de BD impide la fase física. | `ALREADY_CLEAN` |

Código de salida **0**: `COMPLETED`, `ALREADY_CLEAN` o `NO_ARTIFACTS_FOUND`. Código **2**: error o resultado `PARTIAL`. Make propaga el fallo. Una fase incompleta nunca se considera completada. No ejecutar estos comandos para comprobar la instalación: los ensayos se realizan con el ejecutor aislado descrito más abajo.

## Implementación reutilizada

Se conserva el método validado en [RESET.3](../engineering/e10_execution_refactor/reset_3_clean_rebuild.md): respaldo completo, restauración comprobada, base candidata, DDL oficial, importación por columnas mediante COPY, transiciones oficiales del dataset y sustitución transaccional de nombres. Se reutilizan `fingerprint`, `catalog` y `qi` de `scripts/reset/reset1b/common.py`, los SQL originales y la cadena Alembic. No se modifican migraciones históricas ni se deshabilitan triggers.

La fase física sigue [STORAGE.CLEAN.1](storage_clean_1_execution.md): inventario de rutas físicas, acreditación de pertenencia, congelación de identidad/hash y `unlink` individual. Reutiliza las raíces de `scripts/reset/reset3/artifact_plan.py`. No ejecuta `TRUNCATE CASCADE`, `DROP DATABASE`, `docker system prune`, ni elimina volúmenes PostgreSQL o respaldos.

Los módulos permanentes están en `scripts/maintenance/`: tres puntos de entrada, `orchestrator.py`, `docker_transport.py`, `runtime.py`, `database.py`, `protected_resources.py` y `verification.py`. La política contiene exactamente las 97 tablas aprobadas: 17 protegidas, 3 técnicas y 77 históricas. Una tabla desconocida exige revisar la política y produce error automático.

## Protecciones y preflight

- Configuración Compose canónica, contenedores únicos, coincidencia del `DATABASE_URL` configurado e instalado, base/usuario y system identifier del PostgreSQL real. Sólo PostgreSQL 17, esquema public y capacidades E10. No admite parámetros para elegir arbitrariamente otra base.
- Bloqueo de archivo en `var/maintenance/.lock` y advisory lock PostgreSQL específico de mantenimiento, sostenido por una conexión al catálogo `postgres`. No cambia GlobalGate ni sus reglas.
- Rechazo de runs pendientes/en curso, campañas activas, intentos/sesiones sin cerrar, jobs reservados y GlobalGate ocupado. Detección complementaria de procesos científicos y contenedores escritores ajenos.
- Detención ordenada de frontend/backend que estaban encendidos y rechazo de conexiones externas. Durante la reconstrucción y la fase física se bloquean nuevas conexiones a la base mediante `ALLOW_CONNECTIONS false`.
- Backend/frontend sólo se reinician tras verificar integridad. Se comprueba readiness HTTP sin iniciar sesión ni cambiar credenciales. Si el resultado no es demostrable, quedan detenidos y se registra revisión necesaria.

Se preservan todas las columnas/filas de `users`, `roles`, `user_roles`; las trece tablas de dataset/versionado, fuentes, identidad/evidencia, asignaciones, imágenes, materializaciones, estadísticas, validaciones y activaciones; y las definiciones técnicas `models`. No se recalcula el split. `alembic_version`, `schema_migrations` y la fila técnica del gate se inicializan por los mecanismos oficiales en la candidata. Si no existe historial, no se crea candidata ni respaldo ni se agregan filas técnicas artificiales.

## Respaldo y sustitución

Cuando existe historial, el comando escribe `backups/maintenance/<ejecución>/source.dump` en formato custom, con permisos privados, tamaño y SHA-256 registrados. Restaura **ese mismo archivo** con `pg_restore --exit-on-error --single-transaction` en una nueva base lógica `capstone_m3_<id>_restore`. No basta con que pg_dump termine: se comparan conteos/hashes de todas las tablas y schemas del respaldo, definiciones SQL, índices, constraints, triggers, propietarios y ACL, normalizando únicamente OID/nombres internos generados y casts equivalentes ya validados en RESET.3.

La candidata `capstone_m3_<id>_new` recibe el esquema oficial hasta `20260922_01` y sólo los datos protegidos. Se verifican hashes exactos, todas las FK mediante anti-joins, constraints validados, triggers habilitados, capacidades E10 y cero filas en las 77 tablas históricas. Los schemas de ensayo preexistentes permanecen íntegros en el respaldo/base anterior; no se importan al nuevo public.

La base anterior se conserva como `capstone_m3_<id>_old`, bloqueada para nuevas conexiones. La confirmación de la sustitución se realiza consultando los OID desde una conexión física nueva. Una respuesta de COMMIT perdida no significa rollback. Antes de intentar el cambio se persiste `COMMIT_UNCERTAIN`, junto con nombres/OID. No hay restauración automática de archivos ni reversión improvisada de nombres. Backups, restauraciones y bases anteriores se retienen: su eliminación requiere un procedimiento de retención separado.

## Alcance físico

Se inspeccionan outputs, releases, checkpoints locales, artifacts y los directorios derivados cell-crops/cell-explanations/model-explanations. Los bind mounts se traducen a su ruta del host; el almacenamiento científico Docker se inspecciona en su volumen real. Inodos/dispositivos evitan contar dos veces el mismo archivo. Ningún montaje de PostgreSQL puede entrar en el plan.

Las extensiones `.keras`, `.h5`, `.hdf5`, `.ckpt`, `.pt`, `.pth`, `.npy`, `.npz`, `.pkl` y `.parquet` no autorizan un borrado por sí mismas. Se requiere una ruta registrada en evidencia histórica, un manifiesto de release o un contrato de productor en una raíz experimental conocida. Se verifican tamaño, inode, device, mtime y SHA-256 antes de borrar. Symlinks, hardlinks, archivos especiales, pertenencia desconocida y layouts no revisados se rechazan; no se borran directorios completos.

Se conservan dataset, imágenes y materializaciones originales, fuentes, configuraciones, migraciones, respaldos, código y marcadores técnicos. `.staging` y microscopy-images son fuentes protegidas. La capa interna no montada del backend se inspecciona sin extraerla: fixtures sintéticos ya acreditados se excluyen; archivos históricos reales allí requieren revisión y provocan un resultado incompleto. No se recrea un contenedor para destruir silenciosamente su capa interna. Bind mounts externos o volúmenes desconocidos también fallan cerrados.

Los bytes lógicos borrados, bloques asignados liberados por unlink y variación de espacio disponible se informan por separado. La variación del filesystem puede incluir otras actividades y no se suma entre raíces del mismo dispositivo. Ausencias previas no se contabilizan como espacio recuperado.

## Evidencia y reanudación

Cada ejecución crea `var/maintenance/YYYYMMDD_HHMMSS/` (UTC), fuera de las rutas limpiadas:

- `db_cleanup.json`, `artifact_cleanup.json`, `summary.json`, `execution.log`.
- Identidad sin contraseña, snapshots con conteos/hashes, manifiesto y su SHA-256, fingerprints protegidos, reporte del respaldo y journal de cada unlink confirmado.
- Duración, estados, registros/archivos eliminados, integridad y errores con códigos públicos. No se almacenan filas de usuarios, credenciales, URLs con contraseña ni variables de entorno en los reportes.

El archivo temporal privado con la configuración del helper se elimina al iniciarse éste y en el cierre normal. No se imprime ni se incorpora a reportes. Los inventarios privados y los respaldos no se versionan.

Si la BD terminó pero fallaron los archivos, el combinado registra `PARTIAL` y sale con 2. Al repetir el mismo comando, reutiliza el último manifiesto sólo si su hash, identidad, snapshot SQL posterior y recursos protegidos coinciden. Los archivos ya ausentes se reconocen sin contarlos como nuevas eliminaciones. No vuelve a reconstruir la BD. Si hay drift, se detiene. En el comando físico independiente, si el estado posterior ya cambió, el informe antiguo no se reutiliza: se inventaría el estado actual y sólo se autorizan archivos acreditados actualmente. La reanudación del combinado sigue siendo estricta. El comando de sólo BD también conserva un manifiesto para que una posterior limpieza física no pierda la pertenencia histórica al desaparecer las filas SQL.

## Recuperación ante fallos

1. Leer `summary.json`, `db_cleanup.json`, `backup.json` y, si existe, `file_fence.json`. Mantener escritores detenidos si se indica revisión. No ejecutar TRAIN ni inferir rollback por un código de error.
2. Antes de sustituir, el origen se mantiene disponible o se reabre sólo si conserva el OID canónico original y se prueba su integridad. Una candidata incompleta nunca se promueve.
3. En `COMMIT_UNCERTAIN`, comprobar con una conexión nueva a `postgres` los nombres y OID registrados. No renombrar ni restaurar archivos hasta acreditar qué base posee el nombre canónico.
4. Ante una interrupción abrupta con conexiones bloqueadas, verificar system identifier y OID del reporte antes de habilitar conexiones. No existe un flag para saltarse esta comprobación.
5. Si hace falta restaurar datos, restaurar el dump conservado en otro destino, comparar hashes/catálogos y sólo después planificar la sustitución. No borrar la última copia íntegra. El procedimiento no trata un downgrade Alembic como recuperación de datos.
6. Unlink es definitivo: el respaldo PostgreSQL conserva filas, no pesos ni imágenes derivados. Una fase física parcial se reanuda por manifiesto; no se promete recuperar archivos ya eliminados. Dataset y archivos originales están excluidos y verificados.

## Pruebas aisladas

```sh
python3 tests/maintenance/run_isolated.py
```

Este ejecutor crea contenedores con nombres aleatorios `capstone-maintenance-test-*`, red interna propia y un PostgreSQL 17 sin puertos publicados. Usa una copia histórica existente como fixture, aplica E10 **sólo al clon**, crea/restaura su propio dump y ejecuta pytest dentro de la imagen backend. Rechaza el system identifier operativo. Al terminar retira únicamente los contenedores/red de fixture que creó. No ejecuta los tres targets sobre la instalación operativa.

La prueba combinada usa PostgreSQL y archivos temporales reales; el descubrimiento/detención de servicios se sustituye por un adaptador aislado sin escritores. Las pruebas unitarias de errores/reanudación usan dobles explícitos. No se presenta esto como una caída de red real ni como una limpieza operativa ejecutada. La evidencia versionada se encuentra en `reports/maintenance_3_validation.json` y `reports/maintenance_3_junit.xml`.

## Resultado de validación

Se validaron **23 casos distintos**: suite integral de 21 pruebas aprobada y pasada focalizada final de 19 pruebas de archivos/orquestación aprobada, incluyendo el contrato real de releases (`sha256`, `training_run_id`, `signature.json` y resúmenes). La pasada focalizada cubre el ajuste final de ese contrato, la repetición inmediata del CLI y el uso de una nueva línea base en la limpieza física independiente; no hubo cambios posteriores en el código SQL.

En PostgreSQL aislado: **1.054.625 filas históricas → 0**, las **17 tablas protegidas iguales**, autenticación intacta y **208 FK verificadas**. La segunda ejecución combinada devolvió `ALREADY_CLEAN` sin repetir la reconstrucción. Se comprobaron también exclusión por advisory lock, rechazo de un run marcado activo mediante SQL de fixture y conservación del origen ante fallo SQL. No se ejecutó el entrenamiento de ese run.

Se comprobaron con archivos temporales reales la eliminación, ausencias repetidas, rechazo de modificaciones posteriores al inventario, protección de symlinks científicos y pertenencia de releases. Los fallos de orquestación/reanudación y los códigos de salida se verificaron con dobles identificados. No se simuló ni se afirma haber ensayado una caída de red real. El reinicio HTTP de servicios operativos no se ejecutó durante el desarrollo.

**No se ejecutó una nueva purga operativa.** Los servicios originales siguieron levantados. No se ejecutaron TRAIN/TEST científicos, campañas, migraciones operativas ni borrados de archivos operativos. Los únicos recursos Docker retirados fueron los de pruebas aisladas.

**MAINTENANCE.3 — TRES COMANDOS IMPLEMENTADOS Y VALIDADOS.**
