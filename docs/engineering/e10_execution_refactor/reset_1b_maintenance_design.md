# RESET.1B — Mantenimiento excepcional y ensayo integral

**RESET.1B APROBADO — exclusivamente el diseño y ensayo aislado.** No autoriza reset, migración, baja de publicaciones ni borrado físico operativo. Trabajo detenido para revisión humana.

El ensayo eliminó íntegramente el historial del clon y verificó **70 tablas históricas vacías**, **139.586 filas protegidas idénticas**, **208 FK sin huérfanos** y restauración exacta tras un fallo SQL posterior a todos los DELETE. Después confirmó el reset solamente en el clon, restauró los guards originales y migró el esquema vacío a `20260922_01`: OP1 aprobó Docker y Local. No se ejecutó TRAIN, TEST, inferencia, reanudación ni backfill E10.

## 1. Alcance y referencias

Se leyeron [auditoría RESET.1](reset_1_full_history_audit.md), [manifiesto RESET.1](reset_1_full_history_manifest.json), los SQL `full_history_reset_preview.sql` y `full_history_reset_plan.sql`, y [OP3](e10_op3_operational_migration.md). Se conserva su contenido: los nuevos archivos no desbloquean retrospectivamente el plan de producción.

Backup verificado: `/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backups/reset1/capstone_20260928T211019Z.dump`; SHA-256 `d9ab67dbbdbdb19d2df8500152d2b0f97c7e58d4aa48b26b420e21042356a927`. Se restauraron 311 bloques COPY sin cambiar valores; sólo se remapearon referencias de esquema en DDL fuera de COPY. Los 97 hashes/conteos del clon coincidieron con el inventario aprobado: **1.192.667 filas**. No se usaron tablas supuestas.

Clon: `capstone-reset1b-14908ae0b3f5` / `reset1b_rehearsal` / `capstone_test_reset1b_14908ae0b3f5`, cluster `7690704040535207974`. Contenedor PostgreSQL 17.9 creado para esta operación, sin puertos publicados, bind mounts ni volúmenes compartidos con `capstone_db`. La identidad operativa `7668020338728398886` está explícitamente prohibida como destino de mantenimiento.

## 2. B1 — Alternativas y selección

| Alternativa | Evaluación |
|---|---|
| Deshabilitar triggers, cambiar replication role o retirar FK | Prohibida; no utilizada. |
| Añadir una excepción permanente por GUC o editar migraciones históricas | Rechazada: superficie accesible por la aplicación y cambio retrospectivo del contrato. |
| Restaurar un subconjunto en una base nueva y hacer cutover | No demuestra un reset transaccional del esquema existente; requiere otro diseño/despliegue y conservación adicional de identidades. |
| Sustitución transaccional acotada de funciones, con allowlist y restauración antes de commit | **Seleccionada para el clon**. Conserva triggers/FK y admite sólo las preimágenes autorizadas durante la transacción privada. |

Se localizaron **23 funciones** usadas por los BEFORE DELETE de tablas candidatas, incluidas tablas actualmente vacías. Se mantienen INSERT/UPDATE y los AFTER triggers originales. Funciones afectadas temporalmente:

`assessment_attempt_guard`, `assessment_immutable`, `assessment_result_guard`, `campaign_attempt_guard`, `campaign_configuration_guard`, `campaign_guard`, `campaign_member_guard`, `campaign_technical_guard`, `execution_event_immutable`, `prevent_audit_event_mutation`, `prevent_model_governance_audit_mutation`, `prevent_stage2_publication_event_mutation`, `prevent_validation_annotation_event_mutation`, `prevent_validation_membership_mutation`, `protect_cell_classification_run`, `protect_cell_detection_run_identity`, `protect_cell_explanation`, `protect_validation_annotation`, `protect_validation_snapshot`, `reject_cell_analysis_row_mutation`, `reject_cell_classification_row_mutation`, `train_record_guard`, `train_session_guard`.

Mecanismo implementado:

1. El orquestador sólo crea destinos nuevos con prefijo/label RESET.1B; comprueba volumen aislado y ausencia de puertos/bind mounts. El ejecutor comprueba base, schema, session_user, cluster y `session_replication_role=origin`, además de GlobalGate libre. No acepta un destino operacional ni un flag que lo habilite.
2. Una transacción toma locks `SHARE ROW EXCLUSIVE` sobre las 97 tablas, con lock_timeout 3 s y statement_timeout 300 s por sentencia de reset. La cuenta autorizada es `reset1b_maintenance`, credencial aleatoria privada exclusiva del clon. No se otorgan privilegios operativos ni se pretende proteger contra un superusuario hostil: se impide uso accidental o desde el rol de aplicación.
3. Se materializan en `pg_temp` las **PK exactas y SHA-256 de la preimagen completa** de las filas seleccionadas. Los tres conjuntos grandes derivados de run IDs se convierten también en PK individuales. La allowlist no es un predicado de borrado universal.
4. El contexto fija operación, `pg_current_xact_id()` y backend PID. La función de decisión comprueba cluster, base, session_user, ausencia de SET ROLE, operación y contexto transaccional; una fila cambiada deja de coincidir con su hash. OIDs de relaciones atan la autorización al esquema restaurado. Las tablas protegidas no tienen entradas autorizadas.
5. Un trigger adicional `a_reset1b_delete_scope` en cada tabla rechaza DELETE fuera de la allowlist, incluso en tablas que originalmente no tenían un guard de borrado. El wrapper insertado en cada función original sólo permite `TG_OP='DELETE'` de una preimagen autorizada. Ninguna FK se desactiva, elimina ni modifica.
6. Se difieren únicamente constraints que ya eran deferrable mediante el mecanismo normal de PostgreSQL. Se respeta el orden hijo→padre de RESET.1. Antes de confirmar: `SET CONSTRAINTS ALL IMMEDIATE`, anti-joins de las 208 FK, cero historial y comparación de hashes protegidos.
7. Se reinstalan las definiciones originales obtenidas con `pg_get_functiondef`, incluidos propietarios, ACL y propiedades; se retiran **sólo los triggers/funciones de scope creados por este ensayo** y sus tablas temporales. El catálogo debe coincidir exactamente con el catálogo anterior antes del commit. No se retira ningún trigger original/constraint. Fallo o desconexión antes del commit revierte conjuntamente DDL y DML.

Las funciones nuevas no sobreviven al mantenimiento. El catálogo final tiene **0 funciones `_reset1b_*`, 0 triggers deshabilitados —incluidos FK— y 0 constraints sin validar**. `public` dentro del clon tiene cero tablas; nunca fue destino de la restauración operativa.

Controles negativos reales:

| Control | Resultado | SQLSTATE |
|---|---|---|
| protected_source | RESET1B_DELETE_NOT_IN_APPROVED_MANIFEST | P0001 |
| preserved_audit | RESET1B_DELETE_NOT_IN_APPROVED_MANIFEST | P0001 |
| wrong_role | RESET1B_DELETE_NOT_IN_APPROVED_MANIFEST | P0001 |
| wrong_operation | RESET1B_DELETE_NOT_IN_APPROVED_MANIFEST | P0001 |
| wrong_transaction | RESET1B_DELETE_NOT_IN_APPROVED_MANIFEST | P0001 |
| unchanged_update_rules | TRAIN_RECORD_IMMUTABLE | P0001 |
| changed_row_hash | preimagen alterada rechazada | boolean false |


Se probaron 24 tablas con guards y datos antes del mantenimiento. Tras el rollback completo, las mismas operaciones volvieron a producir **los mismos errores originales**. Tras el commit del estado vacío, DELETE de la auditoría preservada volvió a rechazar con `audit_events is append-only`; el catálogo completo seguía idéntico. No se fabricaron runs para aparentar pruebas sobre un estado vacío.

## 3. B2 — Resolución de las 414 ubicaciones

[Manifiesto actualizado por ubicación](reset_1b_file_classification.json): overlay del manifiesto aprobado, unido por `canonical_location` y ligado a su SHA-256. Cada ubicación conserva ruta, tamaño, hash observado, evidencia de reporte/manifest cuando acredita un ID, propietarios, referencias a runs y acción. Las otras 6.124 ubicaciones mantienen la política original.

| Clasificación | Ubicaciones |
|---|---|
| HISTORICAL_OWNER_IDENTIFIED | 18 |
| NO_DEMONSTRABLE_RELATION | 288 |
| SHARED_COORDINATION_FILE | 3 |
| SHARED_MODEL_OUTPUT_ALIAS | 99 |
| SHARED_PROJECT_MARKER | 6 |


- **18** ubicaciones tienen referencias exactas a propietarios aprobados en reportes/manifests; sólo sus copias son candidatas adicionales de cuarentena.
- **108** son compartidas: 99 aliases de outputs por modelo, 6 markers/metadatos de directorio y 3 locks de coordinación. Se preservan aunque algún contenido coincida con un resultado histórico.
- **288** no acreditan un propietario dentro del conjunto de IDs aprobado. Se resuelve su tratamiento como **PRESERVE_AMBIGUOUS**, tal como ordena RESET.1B. No se inventó propietario ni se autorizó borrado por estar en outputs. Puede existir procedencia histórica en esos archivos; esta prueba no permite atribuirles exclusividad para borrarlos.

La conservación de ambiguos es una decisión explícita y verificada de protección, no una declaración de que se hayan eliminado. Cualquier futura ampliación del borrado de esos archivos necesita nueva evidencia y autorización. No se confunde “cero historial en PostgreSQL” con “todo directorio de outputs físicamente vacío”.

Los 43 checkpoints E9 previamente ausentes mantienen `ALREADY_MISSING`, sin fabricación ni sustitución de hashes. El manifiesto base también conserva referencias fuente ausentes; ninguna ausencia se materializó artificialmente para el ensayo.

## 4. B3 — Retirada atómica y estado sin modelo productivo

La investigación confirmó un mecanismo compartido utilizable: `Stage2PublicationService` y `Stage2ModelAvailabilityService` aceptan `connection_factory`. Se inyectó una factory que devuelve **la misma conexión/transacción** y no confirma al salir de cada servicio. Se utilizaron los servicios existentes; no se llamó ningún endpoint operativo.

La secuencia del clon fue:

1. Desactivar la publicación activa `81d69942-17eb-4999-a6bd-2b05779a65a4` y el deployment `cf2f20d3-a1e0-499c-b5ab-501b7c1ae198` dentro de la transacción del reset, con actor/razón/correlación de ensayo.
2. Diferir invalidación de caché usando un adaptador privado; todavía no aplicar efectos no transaccionales.
3. Verificar que no quedan publicaciones/deployments activos; borrar hijos, predicciones, asociaciones, eventos, publicaciones, deployments, model_versions y runs según el grafo real.
4. Mantener los AFTER audit triggers originales. Se generaron **96 eventos de auditoría de DELETE** de members/configurations y **1 evento de baja de publicación**. Cada ID nuevo se capturó y validó contra su publicación aprobada o la preimagen exacta de la fila eliminada. Se incorporaron individualmente a la allowlist; no hubo DELETE por prefijo ni supresión de auditoría. La evidencia externa de esta operación se conserva en el JSON.
5. Confirmar sólo tras todas las postcondiciones y restauración de guards; después invalidar las **36 model versions** en una caché privada sembrada para la prueba. Se verificó cero entradas residuales. Si SQL falla, se descarta la cola; no se aplica invalidación.

Total de filas eliminadas en cada secuencia íntegra: **1.053.178** = 1.053.081 históricas aprobadas + 97 eventos creados por el propio procedimiento. El resultado tiene 139.586 filas protegidas; no queda evidencia E10 ni evento de mantenimiento insertado artificialmente en el ledger científico.

Estado SIN MODELO PRODUCTIVO comprobado sin inferencia: `Stage2PublicationService.models()` devuelve `[]`; resolver el alias retirado devuelve `GovernanceConflictError` controlado, sin referencias huérfanas ni modelo cacheado disponible. Las arquitecturas siguen en el registry. No se promete disponibilidad de inferencia hasta entrenar y publicar un modelo nuevo.

El endpoint operativo actual continúa usando factories independientes: **no se modificó ese endpoint ni se afirma que ya tenga atomicidad compartida**. La vía demostrada es el coordinador de mantenimiento aislado con una conexión compartida. Su despliegue/uso operativo requiere una autorización posterior distinta.

## 5. Ensayo completo, fallo y recuperación

Se ejecutaron dos secuencias completas sobre la restauración, no sólo DELETE individuales:

| Fase | Resultado |
|---|---|
| Restauración del backup | 97/97 tablas, 1.192.667 filas y hashes coincidentes con RESET.1 |
| Reset íntegro dentro de transacción | 70 tablas históricas en cero; 208 FK sin huérfanos; fuentes iguales |
| Fallo inyectado después de todos los DELETE y de cuarentena | Error SQL real `RESET1B_INJECTED_FAILURE_AFTER_FULL_DELETE` |
| ROLLBACK y recuperación de archivos | 97/97 hashes/conteos originales, catálogo original y todas las copias restauradas |
| Repetición íntegra y commit sólo en clon | 70 tablas históricas en cero; 139.586 filas protegidas conservadas |
| Final del mantenimiento | Guards originales restaurados; no excepción disponible para la aplicación |
| Migración posterior del clon vacío | Head `20260922_01`, OP1 READY, cero backfill |

Se corrigieron dos fallos del harness durante su desarrollo (transporte de `%` literal en PL/pgSQL y parámetro JSON en un control negativo); esos intentos abortaron y quedaron revertidos. No se alteraron funciones históricas para ocultar esos fallos. La evidencia de aprobación corresponde a las dos secuencias **completas** de la versión corregida.

Hashes de todos los datos protegidos antes/después del reset:

| Tabla / subconjunto | Filas | SHA-256 anterior | Posterior |
|---|---|---|---|
| alembic_version | 1 | c2002996732bb659de8dea4d6d1baaa21c1b2aa7ca75d39def1f90e653884e34 | IGUAL |
| blood_samples | 73 | 1d731819ef24c877a5dfd3040e6ea0a518f0b05f0bae072146948a1551ccb94b | IGUAL |
| clinical_identities | 201 | e41426a8500e3fbb9f8b70b2119501ce20f3853a5750194cd0a00cf6315a38e4 | IGUAL |
| dataset_materialization_activations | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | IGUAL |
| dataset_materializations | 1 | 6026c9bd22c5c3b7b916b7f6e2e3464cc8cf0050fe5ba4fc6083537e71450458 | IGUAL |
| dataset_source_records | 27558 | d3c6386726b93a435823e8a1a2bc0245a4b892b0b89887f3747a8189425145c3 | IGUAL |
| dataset_split_assignments | 27558 | edda8be9e1e4060caf1d1afc8f34bba161ebe139e24bbb3091f9899eb930f210 | IGUAL |
| dataset_split_images | 55116 | 59528856bd3d413059fbab5c5a02434c71a176883c25af762c2fc5d79ad496e5 | IGUAL |
| dataset_split_statistics | 1 | 1e509f3dc0cc50c3ea20a99207e04e66b617c642fcce49510c64ef8326f63c0d | IGUAL |
| dataset_split_validation_checks | 12 | 29b643727194eb4264de61ad2e93ef0e271b898be4a09ef28ec4fefac0aff4a6 | IGUAL |
| dataset_splits | 0 | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 | IGUAL |
| dataset_version_sources | 1 | bcdd40cbf14cfba8dd5df9c76f76fa6b571d06d294f249dc2284f7e31503ff59 | IGUAL |
| dataset_versions | 1 | c9a99a6f03d324318fe2b1fef2f9566fa8fbef748889dba3f2faf7ba836f82ff | IGUAL |
| datasets | 2 | 7ed1f66ac9ffb3e27d88fc2bd52eea9088791beaa636cc828b37344629342c59 | IGUAL |
| experiment_execution_gate | 1 | f42d8830820bbac71205f4d26300f3711b3fa3fc390b2cc3e45198511853dd67 | IGUAL |
| identity_evidence | 27558 | f49c50ae77ea0aba924116a985bd011691abe6c8815e75b1fbd67e3d4878f396 | IGUAL |
| image_ingestion_batches | 73 | 9716bb881b4f4e93f05924ee534d5a30ee67ed7f526dc4a7b11d69df67231912 | IGUAL |
| microscopy_images | 74 | 362eaef09fce46da2df3d0326d7ea692e2cc639f9a325bde22cf0cc8a9b28049 | IGUAL |
| models | 4 | 6494e0ab530b6d6fec6c8c17742c978456d8f389f7df3f38be8d60b56d3934b6 | IGUAL |
| research_subjects | 73 | 5ceddafbd9f076e852cdf8b66211c95faba6fea34513489b3b34acaa1c51d6a8 | IGUAL |
| roles | 5 | 9963e9d52a13de49af23598244cdb8dd2819edd2459255ff70b58e099153c091 | IGUAL |
| schema_migrations | 23 | fb427ece1bcb38b89e483460f86f75d9f3c88ef0d994c01279489d1b41066f17 | IGUAL |
| scientific_cases | 73 | d3d27a8cac942084408d4b2cb7ef6204e142e272eb343a0d8c4780680f773850 | IGUAL |
| smear_slides | 73 | 111341a9d0d7891f94d21da8c02a3a1e2c45aaebe8844582e24c3cd5f6aa44bc | IGUAL |
| user_roles | 1 | fbfa8d635fe1d196fe4883645e8f7666011c8357d0124d98b4a28e3c9dd5589b | IGUAL |
| users | 1 | 6d864c5f3ef3529fcf40abaa0c41f7f9e35b90ec84b04c65627fa4bdd3a2b426 | IGUAL |
| audit_events_preserved | 1102 | 0169a2dc8e753328666cc835ce317e9850f17b087d37a9477d1ce7d5ee8e8e94 | IGUAL |


`audit_events_preserved` son las 1.102 auditorías de fuentes/seguridad excluidas por IDs del reset. No se vació indiscriminadamente audit_events. Todos los demás conjuntos históricos, incluidos los originalmente vacíos, se verificaron en cero; los 70 conteos figuran en `rehearsal.e10.empty_history_counts`.

También se inspeccionaron referencias UUID a las raíces históricas en JSON/texto de las tablas protegidas pequeñas y auditoría retenida: **ninguna referencia exacta retenida a esos IDs**. Los conjuntos grandes de datos fuente mantienen sus hashes íntegros y las FK validadas. Esta comprobación se declara por su alcance, no como una interpretación universal del texto libre.

## 6. Cuarentena recuperable sobre copias

Se copiaron **6458 archivos presentes** a un filesystem privado desechable y se comprobó cada SHA-256 contra el manifiesto. Se ensayaron **5988 movimientos** entre `live/` y `quarantine/`, sólo dentro de ese árbol; **470 copias protegidas** permanecieron en `live/`.

La selección usa ubicaciones canónicas deduplicadas y acciones explícitas; los nombres internos son hashes de ubicación, no paths suministrados a rename. Se comprueban raíz privada, marker/token, ausencia de symlinks, integridad y conflictos de destino. Un journal persistente en el árbol desechable registra PREPARED/QUARANTINING/QUARANTINED/RESTORING/RESTORED/SQL_COMMITTED; su contenido permite recuperar las rutas por ID sin depender de una transacción del filesystem.

El fallo SQL ocurrió **después** del reset íntegro y la cuarentena: se hizo rollback de PostgreSQL, se devolvieron todas las copias y se comparó el snapshot completo. Tras el éxito, la cuarentena quedó registrada como SQL_COMMITTED. Se volvieron a leer los **6458 originales presentes**: todos conservaron SHA-256. Ningún rename/unlink/rmtree recibió una ruta operativa.

Ante pérdida de confirmación de COMMIT, el código conserva la cuarentena con estado `COMMIT_UNCERTAIN`: no interpreta el error del cliente como rollback. Debe reconciliarse en una conexión nueva con conteos/hashes y catálogo antes de restaurar o declarar commit. La rama de error se comprobó con dobles de transacción/filesystem sobre el bloque real del runner; no se inyectó pérdida real de conexión en PostgreSQL; la recuperación demostrada corresponde al error SQL anterior a COMMIT.

El cierre retiró sólo el contenedor/volumen del clon y los árboles de copias desechables con marker válido. No se eliminó un archivo operativo. No existe paso de borrado definitivo productivo en este código.

Además, se calcularon fingerprints de **82,744 entradas** y 1,725,563,715 bytes de datasets originales/materializaciones físicas, configuración del split, configuración científica, registry/arquitecturas y 29 migraciones; las dos lecturas coincidieron:

| Raíz protegida | Entradas | Bytes | SHA-256 del inventario ordenado |
|---|---|---|---|
| malaria_dl_local_project/data | 82696 | 1702913012 | da78138c520e827eb1ff0afd6044701935508aa177054045880cf784fb2979f3 |
| malaria_dataset_split_project/var | 4 | 22268781 | 0f3e3ff0c27fd76d76fc258e33d590ad91b55c1e8dd93077304edb81ca65ab57 |
| malaria_dataset_split_project/config | 2 | 1219 | 9eb72138fffbd94fc718142bf86a1aa4e8d5881a641c07f4a2b7d4efd36264e5 |
| malaria_dl_local_project/configs | 6 | 79312 | ceecb0c7e38f94af23a438be44ca078250e44a445dc31baa7e2783cdfee84862 |
| malaria_dl_local_project/src/malaria_dl/models | 7 | 34183 | 9edec3707c38f94855852284a7685c3bbb84b133d84ce85b62af853860cdf4c9 |
| alembic/versions | 29 | 267208 | d6474bf14195ba182e87422f7be40c54ddd40c99b864237e2b0dfdfedc54eef5 |


Cada fingerprint se construye sobre rutas relativas, tamaños y SHA-256 por archivo; los symlinks se representan por su destino sin moverlos. `__pycache__`/pyc no son configuración científica. Las 74 imágenes de microscopía originales también quedaron protegidas por sus filas y copias verificadas.

## 7. E10 sobre el estado vacío

Se utilizó `alembic.command.upgrade(..., 'head')` y la conexión suministrada soportada por el `alembic/env.py` del proyecto, dentro de la transacción del clon; no se cambió DATABASE_URL, no se llamó el wrapper contra public y no se editó ninguna migración.

- Origen `20260915_01`; destino `20260922_01`.
- OP1 Docker y Local: `E10_SCHEMA_NOT_READY` antes, `E10_SCHEMA_READY` después. Local se detuvo al salir del preflight, antes de get/claim/reserva.
- Columnas event_id/event_sequence, constraint de metadata, índices únicos y trigger de fencing/eventos comprobados por el guard OP1 real.
- Ledger `train_execution_records`: **0 filas antes y después**, sin backfill.
- ResultService y PostgresResultRepository instanciados sobre el clon; un envelope válido de una ejecución no reservada fue rechazado como `WriterNotAuthorized`. No se creó run, attempt, session, resultado ni evento. Esto demuestra disponibilidad del servicio y su frontera de autorización, no una ejecución científica exitosa.
- Registry: `custom_cnn`, `vgg16`, `densenet121`, configuraciones resolubles sin construir modelos ni ejecutar TRAIN/TEST.
- Hashes de fuentes/configuración conservados. Sólo cambia la revisión Alembic entre los datos protegidos; ese cambio está expresamente autorizado en el clon.

El orden ensayado fue **restore → retirada/reset atómico → restauración de guards → commit del clon vacío → migración E10 → verificaciones**. No implementa E10.11 ni modifica ResultService, GlobalGate, heartbeat, retry o reglas de claim. Los blockers propios del despliegue operativo OP3 (por ejemplo propagación efectiva de timeouts en el wrapper) no quedan autorizados ni corregidos por este ensayo.

## 8. Reproducción, barrera operativa y revisión

Código y SQL: `scripts/reset/reset1b/`. Seguir su README desde la raíz del checkout; se necesita Docker y el backup cuyo hash coincide con RESET.1. Usar un directorio privado nuevo:

```sh
python3 scripts/reset/reset1b/run.py prepare --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py classify --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py rehearse --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py finish --work /private/tmp/reset1b_new
```

`production_blocked.sql`: READ ONLY y excepción incondicional `RESET1B_PRODUCTION_NOT_AUTHORIZED`; se probó en el clon con exit 3 antes de DML. No hay COMMIT ni flag de desbloqueo operacional. El template de mantenimiento sólo se instancia con identidad del clon validada. `target.json`/`target.env` contienen credenciales desechables privadas y no forman parte de los entregables.

La revisión humana debe decidir separadamente si autoriza preparar una ejecución operativa con identidad/rol/ventana/backup nuevos, writers detenidos, recuperación y aprobación explícita. No ejecutar este ensayo apuntándolo a public ni quitar sus guardas. Un ensayo aprobado no equivale a autorización de borrado real.

## 9. Estado operativo y entregables

Lecturas operativas `2026-09-28 21:39:32.680137+00:00` → `2026-09-28 21:59:56.952610+00:00`: **public íntegro en `20260915_01`**, 1,192,667 filas y 97 tablas iguales; catálogo igual y nueve schemas sintéticos iguales. No se cambiaron releases/deployments operativos ni se reanudó E9. Todas las acciones de baja, DELETE y Alembic ocurrieron en el clon ya retirado.

- [Diseño de mantenimiento](reset_1b_maintenance_design.md).
- [Evidencia completa](reset_1b_rehearsal_evidence.json): conteos, hashes, controles negativos, recuperación, guards, E10 y comparación operativa.
- [Clasificación de las 414 ubicaciones](reset_1b_file_classification.json).
- `scripts/reset/reset1b/`: orquestador Docker, snapshot SELECT, mantenimiento SQL acotado, reset íntegro, simulador de archivos, verificación, limpieza de copias y barrera operativa.

**RESET.1B APROBADO.** Detenido para revisión humana; sin autorización ni ejecución del reset o migración operativos.
