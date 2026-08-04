# Matriz de seguridad de mutaciones legacy

> **HISTORICAL_SNAPSHOT / NOT_RUNTIME (2026-07-26).** Esta matriz preserva el
> inventario observado en esa fecha y no debe usarse como catálogo de rutas
> actual. Los endpoints `/api/training-runs/{id}/enable-stage2`,
> `/api/model-versions/{id}/publish-technical-production` y
> `/api/training-runs/{id}/publish-technical-production` aquí listados fueron
> retirados. Las rutas vigentes se obtienen del OpenAPI generado por la API y
> de [stage2-workflow.md](../stage2-workflow.md).

Prompt 2.2.1 conserva el inventario y su test fail-closed. RBAC central está PASS. La
atomicidad por familia permanece BLOCKED hasta disponer de E2E de cada repositorio.

Fecha: 2026-07-26. Inventario derivado de todas las rutas FastAPI registradas. No se
encontraron `PUT`, `PATCH`, `DELETE` ni `GET` con efectos laterales.

Abreviaturas: `PG` modifica PostgreSQL; `FS` archivos; `DEP` deployment; `PUB`
publicación; `MOD` modelo. Todas las filas usan autenticación JWT y la dependencia
central `audited_permission`; `audit_events` registra actor, recurso, ruta, resultado y
correlation ID. Los servicios legacy conservan además sus eventos/metadata propios.

|Router|Método|Path|Función|Responsabilidad|PG|FS|DEP|PUB|MOD|Permiso|Auth|Auditoría/código|Tests|Faltante|Clasificación/estado|
|---|---|---|---|---|:---:|:---:|:---:|:---:|:---:|---|:---:|---|---|---|---|
|auth|POST|`/api/v1/auth/login`|login|Crear JWT/last login|Sí|No|No|No|No|público|credenciales|`USER_LOGIN_*`|foundation|PG real|AUTHENTICATED_WRITE / PASS|
|governance|POST|`/api/training-runs/{id}/prepare-release`|prepare_release|Preparar release|Sí|Sí|No|No|Sí|models.publish|Sí|MODEL_RELEASE_PREPARED|policy|E2E PG|PRIVILEGED_WRITE / PASS|
|governance|POST|`/api/model-versions/{id}/stage2-publications`|publish_stage2_model|Publicar Etapa 2|Sí|No|No|Sí|Sí|models.publish|Sí|MODEL_PUBLISHED_STAGE2|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/stage2-publications/{id}/deactivate`|deactivate_stage2_publication|Desactivar publicación|Sí|No|No|Sí|Sí|models.deactivate|Sí|MODEL_PUBLICATION_DEACTIVATED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/training-runs/{id}/enable-stage2`|enable_stage2|Cambiar default|Sí|Sí|Sí|Sí|Sí|models.set_default|Sí|STAGE2_DEFAULT_CHANGED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/model-versions/{id}/publish-technical-production`|publish_model_technical_production|Publicación técnica|Sí|Sí|Sí|Sí|Sí|models.publish|Sí|MODEL_PUBLISHED_TECHNICAL|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/training-runs/{id}/publish-technical-production`|publish_training_technical_production|Publicación técnica|Sí|Sí|Sí|Sí|Sí|models.publish|Sí|MODEL_PUBLISHED_TECHNICAL|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/training-runs/{id}/build-production-model-version`|build_production_model_version|Construir versión|Sí|Sí|No|No|Sí|models.publish|Sí|MODEL_VERSION_BUILT|policy|E2E PG|PRIVILEGED_WRITE / PASS|
|governance|POST|`/api/model-versions/{id}/complete-contract`|complete_model_version_contract|Completar contrato|Sí|No|No|No|Sí|models.publish|Sí|MODEL_CONTRACT_COMPLETED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/model-versions/{id}/build-production-package`|build_production_package|Construir paquete|Sí|Sí|No|No|Sí|models.publish|Sí|MODEL_PACKAGE_BUILT|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/model-versions/{id}/publish-to-production`|publish_to_production|Publicar formal|Sí|Sí|Sí|Sí|Sí|models.publish|Sí|MODEL_PUBLISHED_PRODUCTION|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/model-versions/{id}/validate`|validate_model_version|Validar versión|Sí|No|No|No|Sí|models.publish|Sí|MODEL_VALIDATED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/model-versions/{id}/approve`|approve_model_version|Aprobar versión|Sí|No|No|No|Sí|models.publish|Sí|MODEL_APPROVED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/model-versions/{id}/reject`|reject_model_version|Rechazar versión|Sí|No|No|No|Sí|models.publish|Sí|MODEL_REJECTED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/deployments`|create_deployment|Crear deployment|Sí|No|Sí|No|No|system.admin|Sí|DEPLOYMENT_CREATED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/deployments/{id}/activate`|activate|Activar deployment|Sí|No|Sí|No|No|system.admin|Sí|DEPLOYMENT_UPDATED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/deployments/{id}/smoke-test`|smoke_test|Smoke persistente|Sí|Sí|Sí|No|No|system.admin|Sí|DEPLOYMENT_SMOKE_TESTED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/deployments/{id}/rollback`|rollback|Rollback inmutable|Sí|No|Sí|No|No|system.admin|Sí|DEPLOYMENT_ROLLED_BACK|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/deployments/{id}/deactivate`|deactivate|Desactivar deployment|Sí|No|Sí|No|No|system.admin|Sí|DEPLOYMENT_UPDATED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/deployments/{id}/retire`|retire|Retirar deployment|Sí|No|Sí|No|No|system.admin|Sí|DEPLOYMENT_UPDATED|policy|E2E PG|ADMIN_ONLY / PASS|
|governance|POST|`/api/image-analysis-jobs`|create_image_job|Inferencia persistente legacy|Sí|Sí|No|No|No|predictions.execute|Sí|TRACEABLE_INFERENCE_REQUESTED|policy|E2E PG|AUTHENTICATED_WRITE / PASS|

La prueba `test_every_legacy_mutation_has_central_audited_policy` falla si aparece una
mutación nueva sin política registrada. La auditoría genérica es fail-closed respecto
de disponibilidad previa, pero no es atómica con las transacciones internas legacy;
esa limitación impide declarar cierre operacional hasta ejecutar la integración real.
