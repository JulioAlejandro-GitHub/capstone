# Reporte final del flujo de producción

Fecha: 2026-07-23. Datasource: `malaria`.

## Resultado por paso

| Paso | Acción | Endpoint | Estado inicial | Estado final | Resultado |
|------|--------|----------|----------------|--------------|-----------|
| 1 | Resolver contrato con evidencia | `GET /api/model-versions/{id}/contract-candidates` | `03bf43fa…` discovered, snapshots vacíos | Cinco candidatos únicos verificados | PASS |
| 1 | Guardar contrato | `POST /api/model-versions/{id}/complete-contract` | discovered | No ejecutado | PARTIAL |
| 2 | Validar | `POST /api/model-versions/{id}/validate` | discovered | No ejecutado | PARTIAL |
| 3 | Aprobar | `POST /api/model-versions/{id}/approve` | no validado | No ejecutado | PARTIAL |
| 4 | Crear/reutilizar production | `POST /api/deployments` | sin production active | No ejecutado | PARTIAL |
| 4 | Smoke | `POST /api/deployments/{id}/smoke-test` | pendiente | No ejecutado | PARTIAL |
| 4 | Activar champion | `POST /api/deployments/{id}/activate` | sin confirmación ejecutada | No ejecutado | PARTIAL |
| 4 | Inferencia E2E | `POST /api/image-analysis-jobs` | sin champion activo | No ejecutado | PARTIAL |

La prueba mutante fue solicitada al entorno, pero la autorización de seguridad
fue rechazada antes de cualquier escritura. No se intentó eludir esa decisión.

## Criterios de producción

| Criterio de producción | Estado | Evidencia | Bloqueador |
|------------------------|--------|-----------|------------|
| Contrato resoluble | PASS | `03bf43fa…`: preprocessing, mapping, input, output y threshold con candidato único | Ninguno técnico |
| Convención clínica | PASS | 0 uninfected; 1/positive parasitized | Ninguno |
| Evaluación formal | PASS | `a98b5bf4…`, completed, split test, sin colapso | Ninguno |
| Contrato persistido | PARTIAL | Endpoint y servicio implementados | Escritura real no autorizada |
| Estado approved | PARTIAL | Transición existente reutilizada | Pasos 1–2 no ejecutados |
| Deployment production | PARTIAL | Creación/reutilización implementada | Promoción no ejecutada |
| Smoke PASS | PARTIAL | Servicio y secuencia implementados | No ejecutado |
| Active champion | FAIL | Consulta previa no mostró champion production active | Promoción no ejecutada |
| Visible en selector | FAIL | Requiere active approved/deployed | No hay champion active |
| Inferencia y linaje | PARTIAL | Script E2E y servicio existentes | No hay deployment active |
| Rollback disponible | PARTIAL | Servicio existente crea revisión pending | Requiere champion active |
| Gate Etapa 2 | FAIL | No se cumplen active, selector e inferencia | Producción no activada |

## Elementos entregados

Servicios reutilizados: lifecycle, deployment, cache e inferencia. Servicio
nuevo y acotado: `ModelContractService`. Componentes nuevos:
`ProductionStepIndicator`, `TechnicalContractModal` y `ModelApprovalModal`;
`DeploymentReviewPanel`, `Deployments`, API y tipos fueron extendidos.

Modelo seleccionado para evidencia: densenet121,
`model_version_id=03bf43fa-7e8a-4b3c-84ec-686238325322`,
`training_run_id=8dca1f53-bcb6-443e-8130-f654e6e518ae`.
No existe `deployment_id` production final ni smoke final porque la ejecución
mutante no fue autorizada.

Riesgos pendientes:

- las versiones legacy ya `candidate/approved` con contrato vacío no pueden
  corregirse en sitio; hacerlo rompería la inmutabilidad;
- la verificación E2E debe ejecutarse con autorización operacional explícita;
- el sistema actual no expone autenticación/RBAC de dominio en estas rutas; no
  se inventaron roles.

Conclusión:

**MODELO NO ACTIVO EN PRODUCCIÓN — ETAPA 2 BLOQUEADA**
