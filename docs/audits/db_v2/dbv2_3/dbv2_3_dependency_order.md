# Orden de transferencia derivado de PostgreSQL

DAG de 16 nodos y 21 FK, sin ciclos ni padres fuera del alcance. Se derivó de pg_constraint del destino real; se comparó también contra origen. FK, UNIQUE/CHECK e índices permanecen activos.

Orden topológico válido utilizado por el plan:

1. `dataset_versions`
2. `datasets`
3. `roles`
4. `users`
5. `clinical_identities`
6. `dataset_materializations`
7. `dataset_split_statistics`
8. `dataset_split_validation_checks`
9. `dataset_splits`
10. `dataset_version_sources`
11. `user_roles`
12. `dataset_materialization_activations`
13. `dataset_source_records`
14. `dataset_split_images`
15. `dataset_split_assignments`
16. `identity_evidence`

Después de insertar todos los hijos se restituye el estado FROZEN original de dataset_versions dentro de la misma transacción. El orden FK por sí solo no resuelve el trigger BEFORE de una versión ya FROZEN; se aplica el manejo técnico aprobado.

| Padre | Hija | FK |
|---|---|---|
| datasets | clinical_identities | clinical_identities_dataset_id_fkey |
| clinical_identities | dataset_source_records | dataset_source_records_clinical_identity_id_fkey |
| datasets | dataset_source_records | dataset_source_records_dataset_id_fkey |
| clinical_identities | identity_evidence | identity_evidence_clinical_identity_id_fkey |
| dataset_source_records | identity_evidence | identity_evidence_source_record_id_fkey |
| datasets | dataset_version_sources | dataset_version_sources_dataset_id_fkey |
| dataset_versions | dataset_version_sources | dataset_version_sources_dataset_version_id_fkey |
| clinical_identities | dataset_split_assignments | dataset_split_assignments_clinical_identity_id_fkey |
| dataset_versions | dataset_split_assignments | dataset_split_assignments_dataset_version_id_fkey |
| dataset_source_records | dataset_split_assignments | dataset_split_assignments_source_record_id_fkey |
| dataset_versions | dataset_split_statistics | dataset_split_statistics_dataset_version_id_fkey |
| dataset_versions | dataset_split_validation_checks | dataset_split_validation_checks_dataset_version_id_fkey |
| datasets | dataset_splits | dataset_splits_dataset_id_fkey |
| dataset_versions | dataset_materializations | dataset_materializations_dataset_version_id_fkey |
| dataset_versions | dataset_materialization_activations | dataset_materialization_activations_dataset_version_id_fkey |
| dataset_materializations | dataset_materialization_activations | dataset_materialization_activations_materialization_id_fkey |
| datasets | dataset_split_images | dataset_split_images_dataset_id_fkey |
| dataset_materializations | dataset_split_images | dataset_split_images_dataset_materialization_id_fkey |
| dataset_versions | dataset_split_images | dataset_split_images_dataset_version_id_fkey |
| roles | user_roles | user_roles_role_id_fkey |
| users | user_roles | user_roles_user_id_fkey |

audit_events no es padre de ninguna tabla autorizada; actor_user_id apunta de audit_events a users. No obliga a copiar auditoría. No hay REQUIRED_DEPENDENCY_DISCOVERED. No se desactivan triggers ni FK y no se usa session_replication_role.
