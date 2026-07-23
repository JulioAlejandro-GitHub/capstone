# Reporte final: Ejecuciones → producción

Fecha de validación: 2026-07-23  
Resultado global: **bloqueado para producción**

## 1. Resumen ejecutivo

El flujo está correctamente integrado hasta la preparación o reutilización de una
`model_version` y la navegación gobernada desde Ejecuciones. También existe y fue
probada la arquitectura persistente:

```text
training_run_id
  → model_version_id
  → deployed_model_version_id
  → inference_run_id
  → image_analysis_job_id
  → prediction_id
```

No existe despliegue directo desde el Run ID, no se envían paths físicos desde el
frontend y `best_model.keras` no se usa como identidad. Las migraciones PostgreSQL
17 y el linaje extremo a extremo pasan en una base aislada.

El flujo completo no puede habilitarse en producción porque todavía faltan cuatro
controles operativos: autenticación/autorización, creación de deployment desde la
UI autorizada, smoke test persistido como gate de activación y rollback como nueva
revisión inmutable. Tampoco existe confirmación reforzada de producción.

No se activó production ni se modificó `malaria_experiments`. La prueba PostgreSQL
se ejecutó en `capstone_codex_test`, base desechable creada para la validación y
eliminada al terminar.

## 2. Arquitectura final observada

### Preparación

`PrepareModelReleaseService` recibe `training_run_id`, resuelve el training,
artifact, hash, metadata clínica y linaje, y reutiliza o crea una model version con
`model_governance.repository.create_model_version`.

La creación:

- toma un advisory lock por training run;
- vuelve a consultar por training/artifact dentro de la transacción;
- no duplica model versions;
- no crea artifacts ni manifests;
- no crea deployments;
- no degrada estados existentes;
- registra el POST en `execution_logs`.

### Deployment

`ModelDeploymentService` y `deployed_model_versions` son la única arquitectura de
deployment. La activación:

- revalida versión, artifact, SHA-256, mapping, preprocessing, firmas, evaluación,
  threshold y carga del modelo;
- bloquea el slot mediante transacción;
- desactiva el activo anterior del mismo
  `(deployment_name, environment, alias)`;
- activa la revisión seleccionada;
- invalida caché por model version.

El índice parcial `uq_deployed_model_versions_active_slot` impide dos deployments
activos en el mismo slot.

### Inferencia

`TraceableInferenceService` exige un deployment activo, crea un run de inferencia,
lo enlaza por `run_model_deployments`, crea `image_analysis_jobs` y registra
predicciones con version/deployment/run/job. La caché usa
`(model_version_id, sha256)`.

## 3. Flujo de usuario verificado

1. “Modelo IA → Ejecuciones” muestra grupos TRAIN/EVALUATE/EXPLAIN.
2. Sólo TRAIN consulta `promotion-status`.
3. “Preparar despliegue” ejecuta `prepare-release`.
4. La respuesta entrega el `model_version_id` y abre Modelos liberados.
5. Modelos liberados enfoca la ficha y muestra evidencia/bloqueadores.
6. Si ya existe deployment, el estado permite abrir Despliegues por
   `deployed_model_version_id`.
7. Despliegues enfoca la revisión seleccionada.

Los pasos “crear deployment”, “smoke”, “activar” y “rollback” no están disponibles
como flujo UI autorizado. Los endpoints backend existentes permiten crear/activar
sin autenticación y no tienen smoke gate, por lo que no deben exponerse en
producción todavía.

## 4. Endpoints utilizados

### Integrados en el flujo

- `GET /api/training-runs/{training_run_id}/promotion-status`
- `POST /api/training-runs/{training_run_id}/prepare-release`
- `GET /api/model-versions`
- `GET /api/model-versions/{model_version_id}`
- `GET /api/model-versions/{model_version_id}/lineage`
- `GET /api/deployments`
- `GET /api/deployments/{deployed_model_version_id}`

### Existentes, pero no habilitados en UI

- `POST /api/deployments`
- `POST /api/deployments/{id}/activate`
- `POST /api/deployments/{id}/deactivate`
- `POST /api/deployments/{id}/retire`
- `POST /api/image-analysis-jobs`
- `GET /api/image-analysis-jobs/{id}`
- `GET /api/image-analysis-jobs/{id}/predictions`
- `GET /api/inference-runs/{id}`

### Faltantes

- `POST /api/deployments/{id}/smoke-test`
- `POST /api/deployments/{id}/rollback`
- lifecycle autorizado de validación/aprobación de model version
- endpoint/capacidad de sesión para permisos

## 5. Componentes modificados o auditados

- `frontend/src/pages/Runs.tsx`
- `frontend/src/components/reports/TrainingRunGroupCard.tsx`
- `frontend/src/components/reports/RunSummaryRow.tsx`
- `frontend/src/components/reports/RunPromotionAction.tsx`
- `frontend/src/components/reports/RunLineageChildCard.tsx`
- `frontend/src/pages/ModelVersions.tsx`
- `frontend/src/pages/Deployments.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/types/api.ts`
- `frontend/src/styles/report-components.css`
- `backend_api/app/routes/governance.py`
- `malaria_dl_local_project/src/prepare_model_release_service.py`

No se duplicaron las páginas Modelos liberados o Despliegues.

## 6. Reglas de negocio verificadas

- Run ID sólo inicia la promoción.
- Model version identifica el release.
- Deployed model version identifica la autorización operativa.
- Un training debe existir, ser `training` y estar `completed`.
- El checkpoint debe ser inmutable, pertenecer al training y tener SHA-256 válido.
- Paths genéricos no resuelven linaje por sí solos.
- `unresolved`, `rejected` y `retired` quedan bloqueados.
- Mapping obligatorio:
  `0=uninfected`, `1=parasitized`, `positive_class=1`,
  `positive_label=parasitized`.
- Preprocessing es obligatorio.
- Deployment requiere evaluación formal y threshold ligado/evaluado.
- Colapso de predicciones bloquea `can_deploy`.
- Prepare-release nunca crea deployment.
- El frontend de Ejecuciones nunca activa.

Existe una divergencia que debe cerrarse: Python admite validar deployments para
versiones `validated`, mientras el trigger PostgreSQL exige `approved/deployed` al
activar. La política de producción debe exigir `approved`.

## 7. Estados del botón

| Estado técnico | Texto | Estado de auditoría |
|---|---|---|
| Training incompleto | No disponible | PASS |
| Bloqueado | No disponible + causas | PASS |
| Sin model version | Preparar despliegue | PASS |
| Candidate | Ver modelo liberado | PASS |
| Validated | Ver modelo liberado | PASS |
| Approved y apto | Continuar despliegue | PASS |
| Deployment pending/failed | Ver despliegue pendiente | PASS |
| Deployment active | Ver despliegue | PASS |
| Unresolved/rejected/retired | No disponible + causa | PASS |

El botón se renderiza sólo cuando `processKind === 'training'`, en la misma celda de
acciones que “Ver detalle”. EVALUATE y EXPLAIN conservan exclusivamente sus acciones
de consulta.

## 8. Seguridad

Estado: **FAIL para producción**.

- FastAPI no tiene autenticación ni autorización.
- `X-Requester` es informativo y controlado por el cliente.
- Los endpoints POST de deployments están expuestos sin roles.
- No existe separación entre releaser, approver y deployment admin.
- No existe confirmación reforzada de production.
- El frontend no presenta acciones administrativas, lo que evita exposición por UX,
  pero ocultar controles no protege la API.

Antes de habilitar:

1. autenticar el principal en backend;
2. autorizar por acción, datasource y environment;
3. obtener actor desde el principal;
4. exigir reason e idempotency key;
5. separar aprobación y activación de production;
6. agregar confirmación reforzada en la UI.

## 9. Auditoría

Prepare-release registra en `execution_logs`:

- training run;
- model version;
- requester;
- timestamp;
- request/correlation ID;
- resultado;
- bloqueadores;
- target environment preliminar.

El GET de estado no escribe, como exige su contrato read-only.

Estado: **PARTIAL**. Falta un actor autenticado y eventos estructurados para smoke,
aprobación, activación, cutover y rollback. Los cambios de deployment añaden metadata
de auditoría, pero no constituyen por sí solos un sistema de autorización/auditoría
de producción.

## 10. Pruebas ejecutadas

| Suite | Resultado | Evidencia |
|---|---|---|
| Unitarias MLOps/backend | PASS | `unittest discover`: 352 tests, 1 skip opt-in |
| Prepare-release y gobernanza | PASS | Incluidas en las 352; hash, mapping, idempotencia, estados y auditoría |
| API FastAPI | PASS | 36/36 con `pytest backend_api/tests` |
| PostgreSQL 17 | PASS | 1/1 integración opt-in en DB aislada |
| Migraciones | PASS | 21 archivos aplicados; segunda ejecución no-op por checksum |
| Linaje PostgreSQL | PASS | training→version→deployment→inference→job→prediction |
| Unicidad champion | PASS | segundo activo del mismo slot rechazado |
| Frontend unitario/estructural | PASS | 20/20 con Node test runner |
| Componentes en DOM real | NOT APPLICABLE | No hay React Testing Library/Vitest configurado |
| E2E navegador | NOT APPLICABLE | No hay Playwright/Cypress ni servidor E2E configurado |
| Type checking | PASS | `tsc --noEmit` ejecutado por build |
| Build producción | PASS | Vite, 71 módulos |
| Linter Python | NOT APPLICABLE | No hay Ruff/Flake8/Pylint configurado |
| Linter frontend | NOT APPLICABLE | No hay ESLint configurado |
| Smoke test deployment | FAIL | No existe implementación/gate |
| Rollback operativo | FAIL | No existe endpoint/servicio de nueva revisión |

Advertencias no bloqueantes observadas:

- Matplotlib creó cache temporal porque `~/.matplotlib` no es escribible bajo el
  sandbox.
- TensorFlow emitió mensajes informativos de CPU/end-of-sequence.
- Una prueba PostgreSQL aparece skipped en la suite general por diseño opt-in; se
  ejecutó después explícitamente y pasó.

## 11. Limitaciones

1. No hay UI autorizada para crear deployment pending.
2. No hay validación/aprobación de model version desde API/UI.
3. No hay smoke test de deployment.
4. Activación no exige evidencia de smoke PASS.
5. No hay confirmación especial para production.
6. No hay rollback como nueva revisión.
7. `activate` permite reactivar una revisión inactive, contrario a la política de
   rollback inmutable definida en el esquema/documentación.
8. No hay autenticación/permisos.
9. No hay suite E2E de navegador ni tests de componentes en DOM real.
10. El frontend aún navega con `PageKey`, no con URLs recargables reales.
11. No se realizó inferencia con una imagen clínica real en esta validación; la
    persistencia de inferencia fue probada con datos aislados.

## 12. Rollback

La base ya posee:

- `supersedes_deployment_id`;
- `rollback_of_deployment_id`;
- payload inmutable;
- unicidad del alias activo.

Pero no existe la operación correcta. Rollback debe:

1. seleccionar una revisión histórica compatible;
2. revalidar artifact, hash, threshold, preprocessing y mapping;
3. crear una **nueva** fila `deployed_model_versions`;
4. registrar `rollback_of` y `supersedes`;
5. ejecutar smoke PASS;
6. hacer cutover transaccional;
7. conservar la revisión desplazada y todo el linaje.

Reactivar directamente la fila histórica no satisface esta regla.

## 13. Evidencia de linaje

La prueba PostgreSQL confirmó:

```text
runs(training)
  └─ model_versions
      └─ deployed_model_versions(active)
          └─ run_model_deployments
              └─ runs(inference)
                  └─ image_analysis_jobs
                      └─ predictions
```

También confirmó:

- FK y `ON DELETE RESTRICT`;
- model version/artifact del mismo training;
- deployment/model version coherentes;
- job/inference/deployment/version coherentes;
- threshold congelado;
- clase clínica 1=`parasitized`;
- probabilidades y clases fuera de dominio rechazadas;
- un único activo por slot.

## 14. Smoke test requerido

No existe un smoke test operativo. El contrato mínimo pendiente debe devolver:

```json
{
  "deployment_id": "uuid",
  "model_version_id": "uuid",
  "model_loaded": true,
  "hash_validated": true,
  "images_processed": 1,
  "successful_inferences": 1,
  "errors": [],
  "threshold_used": 0.42,
  "result": "PASS"
}
```

`activate` debe consultar evidencia PASS vigente del mismo
`deployed_model_version_id`. Un FAIL, ausencia de evidencia o hash distinto debe
bloquear la activación. No debe reutilizar un smoke de otra revisión.

## 15. Matriz de criterios

| Criterio | Estado | Evidencia | Acción pendiente |
|----------|--------|----------|------------------|
| No existe despliegue directo desde training_run_id | PASS | Ejecuciones sólo llama prepare-release/navega | Ninguna |
| Prepare-release es idempotente | PASS | Advisory lock + reconsulta + tests | Añadir prueba concurrente PostgreSQL específica |
| Model version es inmutable | PASS | Trigger y repositorio gobernado | Ninguna |
| Deployment apunta a model_version | PASS | FK compuesta y prueba PostgreSQL | Ninguna |
| Inferencia apunta a deployed_model_version | PASS | `run_model_deployments` + job + predicción | Ninguna |
| Botón aparece sólo en TRAIN | PASS | `processKind === 'training'`; tests frontend | Añadir test DOM cuando exista framework |
| Botón refleja estado real | PASS | promotion-status autoritativo | Monitorear latencia al cargar muchos runs |
| Bloqueadores son visibles | PASS | `details/summary`, ARIA y mensajes por código | Ninguna |
| Producción exige confirmación | FAIL | No existe UI/guard backend | Implementar confirmación y autorización |
| Smoke test bloquea activaciones fallidas | FAIL | No existe smoke gate | Implementar endpoint, evidencia y validación en `activate` |
| Rollback funciona | FAIL | Sólo campos DB; servicio reactiva inactive | Implementar nueva revisión y cutover |
| No se exponen rutas físicas | PASS | Contratos públicos y tests frontend | Mantener regresión |
| No se usa best_model.keras como identidad | PASS | Version/artifact/SHA; nombre retirado de tarjetas | Mantener compatibilidad sólo interna |
| Tests relevantes pasan | PARTIAL | Unit/API/PostgreSQL/frontend/build pasan | Faltan DOM E2E, navegador y smoke/rollback |
| Rutas existentes siguen funcionando | PASS | 36 tests API + 20 frontend + build | Añadir E2E navegador |
| Activación es transaccional | PASS | Locks/cutover en `ModelDeploymentService.activate` | Incorporar smoke dentro de la decisión |
| Un solo champion activo por slot | PASS | Índice parcial + prueba PostgreSQL | Ninguna |
| Mapping clínico correcto | PASS | Resolver, servicio, constraints y tests | Ninguna |
| Threshold correcto | PASS | FK/snapshot/validación actual | Smoke debe reportar threshold usado |
| Preprocessing correcto | PASS | Snapshot requerido por validación | Smoke debe usar el snapshot |
| SHA-256 correcto | PASS | Recalculado en prepare/deploy/inference | Smoke debe volver a comprobarlo |
| Permisos | FAIL | No existen autenticación/roles | Implementar antes de exponer POST |
| Auditoría completa | PARTIAL | Prepare y metadata deployment | Actor autenticado y eventos de lifecycle |
| Crear deployment desde Modelos liberados | FAIL | UI explícitamente read-only | Habilitar sólo después de permisos |
| Inferencia de prueba real | PARTIAL | Persistencia/linaje probados, no imagen clínica real | Incorporar al smoke |

## 16. Riesgos pendientes

- Activación posible sin smoke PASS.
- POST operativos sin autenticación.
- Reutilización de `inactive` como rollback puede contradecir la inmutabilidad
  histórica.
- Ausencia de separación de funciones en production.
- Divergencia `validated` vs `approved` entre servicio y trigger.
- Falta de idempotency key HTTP en deployments.
- Ausencia de prueba concurrente específica de prepare-release sobre PostgreSQL.
- Cobertura frontend estructural, no DOM/browser.
- Sin artifact store compartido para ejecución distribuida.

## Conclusión

**FLUJO DE PROMOCIÓN BLOQUEADO**

Problemas restantes exactos:

1. No existe autenticación/autorización para acciones de release y deployment.
2. No existe creación autorizada de deployment pending desde Modelos liberados.
3. No existe validación/aprobación operativa de model versions desde el flujo.
4. No existe smoke test persistido ni gate que bloquee `activate` ante FAIL.
5. No existe confirmación reforzada para production.
6. No existe rollback como nueva revisión inmutable con `rollback_of` y
   `supersedes`.
7. No existen pruebas E2E de navegador/componentes DOM para el flujo completo.

