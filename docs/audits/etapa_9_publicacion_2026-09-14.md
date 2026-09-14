# E9 — Auditoría de publicación manual: con hallazgos

No se ejecutó publicación, promoción ni baja operativa. Se preserva la regla TRAIN completado + EVALUATE completado con relaciones/artefactos válidos; sensibilidad, EXPLAIN y objetivos científicos no se añaden como barreras funcionales.

## Flujo inspeccionado

`frontend/src/pages/Runs.tsx::publishStage2` obtiene model_version_id del estado del TRAIN y requiere interacción del usuario, con confirmación de reemplazo si hay otra selección. `api.publishStage2Model` envía la versión al POST `/model-versions/{id}/stage2-publications`. El actor efectivo es el principal autenticado; se persisten motivo y eventos.

`backend_api/app/routes/governance.py::publish_stage2_model` invoca publicación y luego disponibilidad técnica. Ambas fábricas usan `mutation_connection`; `audited_permission` mantiene la transacción compartida. Por tanto, dos llamadas no demuestran dos commits independientes. Falta prueba aislada del endpoint completo con fallo de deployment y concurrencia para acreditar también efectos de archivos/caché y atomicidad de extremo a extremo.

`Stage2PublicationService.publish` toma lock asesor por datasource, bloquea selección distinta salvo replace_existing, conserva inactividad histórica, e implementa idempotencia. La prueba E9 verificó versión/checkpoint explícitos, una sola publicación/evento ante repetición y baja manual en esquema sintético con rollback comprobado desde otra conexión. No es prueba de deployment ni del conjunto de restricciones operativas: usa padres simplificados y DDL 029. La prueba legacy E2E está deshabilitada por escrituras sin rollback; no se habilitó.

## Hallazgos que impiden dar el flujo por cerrado

1. **Selección implícita de versión.** `Stage2PublicationService.status_for_training` ordena por created_at y toma LIMIT 1. `Stage2ModelAvailabilityService.preview` ordena versiones por estado/fecha y usa versions[0]. El POST recibe una versión exacta, pero luego llama enable con sólo training_run_id: puede resolver una versión diferente. Requiere pasar y validar model_version_id/checkpoint_artifact_id de extremo a extremo; con varias versiones, rechazar ambigüedad en entradas legacy. No se debe escoger por fecha ni carpeta.
2. **EVALUATE no acredita aquí el checkpoint exacto.** `_context` consulta un hijo legacy de TRAIN, elige completed y fecha, sin contrastar versión/checksum de esa evaluación contra el checkpoint solicitado. La existencia de un hijo completado no basta para una segunda versión del mismo TRAIN.
3. **E6 y publicación usan identidades distintas.** E6 persiste en assessment_attempts/results; publicación exige evaluation_run_id con FK a runs y consulta run_lineage legacy. Una evaluación E6 verificada no es automáticamente un run legacy. Resolver este contrato requiere una referencia explícita y aditiva a assessment_attempts, validación de identidad y adaptación de lectura/UI. No crear EVALUATE ni TRAIN ficticios ni rellenar referencias históricas por suposición.
4. **Documentación de ámbito contradictoria.** ADR-002 describe catálogo multi-modelo, mientras el servicio vigente serializa y sustituye selección por datasource. Se debe documentar el ámbito funcional efectivo sin ampliar reglas silenciosamente. La unicidad de un deployment por slot y la selección de publicaciones son conceptos distintos.
5. **Inmutabilidad completa y concurrencia pendientes.** Hay referencias inmutables/paquetes con hashes en servicios de contrato y deployment; la prueba realizada no acredita copia física, rechazo de alteración, rollback de archivos/caché, liberación y concurrencia del endpoint completo. No se afirma que un test del servicio cubra todo el flujo.

No se aplicó un parche apresurado a esas relaciones durante una campaña con fuente congelada. La corrección debe cubrir API, resolución técnica, lectura E6 y restricciones mediante pruebas aisladas; el esquema legado no admite representar esa relación exacta sólo cambiando un filtro. La publicación real permanece fuera del alcance autorizado.

## Ensemble: propuesta pendiente, sin TRAIN ficticio

Añadir un tipo explícito de candidato ensemble que referencie el evento de configuración E8 y el manifiesto final E9 aprobado para revisión, junto con evaluaciones exactas de sus miembros. El paquete debe congelar tres referencias modelo/versión/checkpoint con SHA, orden clínico de clases, preprocessing individual, pesos predeclarados, calibradores explícitos o ausencia, regla de combinación y umbral. La inferencia requiere un consumidor de ese paquete y prueba de igualdad contra probabilidades persistidas, inmutabilidad y carga de los tres miembros. Publicación/deployment deben discriminar individual/ensemble y mantener una única selección manual en el ámbito vigente. Esa ampliación no está implementada ni validada; no reutilizar model_version_id individual ni fabricar TRAIN para simularla. La ciencia puede concluir sin publicación de ensembles.

## Estado operativo leído antes y después de pruebas

Publicación activa `81d69942-17eb-4999-a6bd-2b05779a65a4`; versión `172b7031-9f79-44e3-a7ad-2dc10a9ffd08`; deployment `cf2f20d3-a1e0-499c-b5ab-501b7c1ae198` en stage2/default. Mismos IDs después de pruebas. No se infiere integridad física del artefacto sólo de esos IDs. Publicación manual: **con hallazgos**; publicación real: **no ejecutada**.
