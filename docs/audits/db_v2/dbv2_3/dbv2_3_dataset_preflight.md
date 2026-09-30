# Dataset preflight READ ONLY

Versión oficial `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, status FROZEN; frozen_at presente. dataset_split_assignments sigue siendo la autoridad científica.

| Split | Muestras | Pacientes |
|---|---:|---:|
| TRAIN | 22180 | 161 |
| VALIDATION (val) | 2693 | 20 |
| TEST | 2685 | 20 |
| Total | 27558 | 201 |

Cero discrepancias entre assignments y source records (identidad/clase), cero pacientes en varios splits y cero activaciones con versión discordante. Se consultaron agregados SQL; no se abrieron imágenes ni se recalcularon hashes, manifest/fingerprints o splits.

| Tabla autorizada | Filas actuales origen |
|---|---:|
| datasets | 2 |
| dataset_versions | 1 |
| clinical_identities | 201 |
| dataset_source_records | 27558 |
| identity_evidence | 27558 |
| dataset_version_sources | 1 |
| dataset_split_assignments | 27558 |
| dataset_split_statistics | 1 |
| dataset_split_validation_checks | 12 |
| dataset_splits | 0 |
| dataset_materializations | 1 |
| dataset_materialization_activations | 0 |
| dataset_split_images | 55116 |

dataset_split_images contiene dos raíces físicas de 27.558 filas; total 55.116. Ambas tienen dataset_version_id NULL en el origen. Se preservan todas las filas, ambas rutas y esos NULL; filtrar esta tabla por el UUID oficial excluiría incorrectamente todo su inventario. No deduplicar ni inventar asociaciones.

El plan acota la carga a las trece tablas autorizadas; incluye los dos datasets presentes y conserva todas las referencias necesarias. No incluye datos de runs/experimentos/modelos/campañas ni artifacts experimentales. Los conteos se revalidarán en DBV2.4; si cambian, la precondición del plan aborta para revisión.

Manejo técnico de status documentado en compatibilidad; cero transformaciones semánticas. Ninguna fila real se transfirió en esta fase. Fuente de evidencia: data_preflight.json, source_table_counts.json, source_catalog.json.
