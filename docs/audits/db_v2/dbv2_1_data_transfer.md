# DBV2.1 — Mapa de transferencia posterior: dataset y usuario

Sólo estructura, dependencias y orden para DBV2.4. No hay migración, INSERT ejecutado, regeneración de dataset ni framework de adopción experimental. El origen permanece intacto. Esquemas de columnas se conservan para estos dominios; RESTRICT adicional no cambia los datos a copiar. Usar listas explícitas de columnas conservando IDs, timestamps, hashes, JSONB y valores NULL.

## Dataset: trece tablas receptoras

| Orden | Legacy → BD-v2 (mismo nombre) | Dependencias FK |
|---|---|---|
| 1 | datasets | ninguna |
| 2 | dataset_versions | ninguna; nota de estado FROZEN abajo |
| 3 | clinical_identities | datasets |
| 4 | dataset_source_records | datasets; clinical_identities opcional |
| 5 | identity_evidence | dataset_source_records; clinical_identities |
| 6 | dataset_version_sources | dataset_versions; datasets |
| 7 | dataset_split_assignments | dataset_versions; dataset_source_records; clinical_identities |
| 8 | dataset_split_statistics | dataset_versions |
| 9 | dataset_split_validation_checks | dataset_versions |
| 10 | dataset_splits | datasets opcional |
| 11 | dataset_materializations | dataset_versions |
| 12 | dataset_materialization_activations | dataset_versions; dataset_materializations de esa misma versión |
| 13 | dataset_split_images | datasets, dataset_versions y dataset_materializations opcionales |

Estas trece tablas representan la población científica, identidades acreditadas, asignaciones, evidencia de calidad del split e inventario/materialización física. No requieren users, runs, campaigns, models ni pacientes clínicos de frotis. `research_subjects` no sustituye `clinical_identities`: son dominios distintos. `run_dataset_images`, `run_image_predictions`, artifacts y run_io_records no forman parte de la transferencia del dataset oficial.

No inventar clinical_identities para filas sin evidencia ni alterar las referencias existentes. Conservar exactamente class_mapping, source keys, agrupación, fingerprints, sha256 de fuente/píxeles, methodology_json, source_record_count, semilla, proporciones y asignaciones. Las columnas ya están definidas en las [fichas](dbv2_1_table_details.md) y el [CSV](dbv2_1_columns.csv); no hay renombrados ni casts transformadores necesarios.

El inventario documental E10.10.4 identifica versión oficial `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, total 27.558, TRAIN 22.180, VAL 2.693 y TEST 2.685. Son cifras de la evidencia histórica inspeccionada, no una nueva consulta operativa. Los 55.116 registros de dataset_split_images corresponden a dos raíces físicas y no a una población científica duplicada. Preservar ambas raíces; nunca sustituir assignments por el conteo del directorio antiguo.

### Orden de carga y protección FROZEN

Un INSERT directo de dataset_versions con status FROZEN seguido de assignments/sources es rechazado por `enforce_dataset_assignment_consistency` y `protect_frozen_dataset_version_sources`. No basta con diferir FK: son triggers BEFORE. No se propone desactivarlos ni cambiar permisos del runtime.

DBV2.4 podrá realizar una carga simple en una única transacción del **destino vacío**, con escritores excluidos: copiar una versión cuyo estado origen sea FROZEN inicialmente como VALIDATED, conservando todos los demás campos; insertar sources y assignments existentes; terminar con transición VALIDATED→FROZEN antes del COMMIT. `frozen_at` original se conserva porque el trigger usa COALESCE y no lo reemplaza. Las versiones con otro estado se copian con ese estado. Es estado temporal de carga del destino, no regeneración/validación científica nueva, modificación del origen, cambio de split ni cálculo de hashes. Comparar al final todas las columnas con el origen, incluido status y timestamps.

La transacción debe abortar si la evidencia de origen es incoherente o si faltan identidades, nunca completar datos con valores inventados. Los triggers de source/assignment se mantienen. La operación especial queda limitada al orden de carga de estas tablas, no introduce un adaptador experimental.

Forma posterior esperada (sólo ilustración): `INSERT INTO destino.datasets (columnas_explícitas) SELECT columnas_explícitas FROM origen.datasets`. Si las bases están separadas, el transporte de filas lo resolverá DBV2.4; esta forma no presume un enlace SQL entre bases. No se adjuntan credenciales ni dumps con usuarios reales.

## Usuario funcional

| Orden | Tabla | Datos y dependencias |
|---|---|---|
| 1 | roles | Copiar IDs/nombres de los roles efectivamente asignados al usuario; UNIQUE(name) |
| 2 | users | Copiar id, username, email, password_hash completo, status, timestamps y disabled_at; sin FK saliente |
| 3 | user_roles | Copiar `(user_id,role_id,created_at)`; PK compuesta; FK a users y roles |

roles y users son independientes y pueden intercambiar orden; user_roles siempre se carga al final. Copiar al menos un usuario existente activo con rol reconocido por `backend_api/app/security.py`. Se conserva el hash de password sin descifrarlo, sustituirlo ni recalcularlo. No se activa una cuenta deshabilitada ni se inventa una contraseña. El login real consulta estas tres tablas, verifica password_hash y status; permisos por nombre de rol se resuelven en código.

`audit_events` debe existir para que futuros login y acciones escriban auditoría, pero no requiere copiar eventos históricos para que una cuenta funcione. Sesiones JWT y secretos del despliegue pertenecen a configuración SW-v2; no hay tabla adicional de sesión/token en este contrato. No se debilita autenticación ni se trasladan claves de servicio como datos de usuario.

## Límites de transferencia

No copiar schema_migrations, alembic_version antiguo, backfills, eventos de entrenamiento, modelos ni resultados experimentales. No usar adoption_v2 para fabricar evidencia faltante. Los checksums documentales no son nuevos fingerprints del dataset. La comprobación posterior deberá comparar filas por PK y valores originales sin alterar ninguna asignación ni usar TEST como selección.
