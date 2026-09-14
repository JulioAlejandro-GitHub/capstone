# Campañas — Decisión de alcance y procedimiento pendiente

Decisión explícita del usuario, registrada 2026-09-14: no se requiere compatibilidad del flujo de campañas con corridas sin asociación demostrable. Conservar íntegros esos registros/resultados; no inferir campañas por fechas, arquitectura o nombre; no incorporarlos a la actual. Todo ID no nulo requiere padre existente. Obligatoriedad en creación de nuevos experimentos del flujo, sin NOT NULL global en históricos. Preservar TRAIN/versión/checkpoint/evaluación.

**Aplicación documental completada; cambio de esquema/escritores preparado, no ejecutado.** No se altera el coordinador activo ni su fuente/configuración congelada. No se aplicaron migraciones, backfills, UPDATE, DELETE, reasignaciones ni cambios de nulabilidad.

## Lo que existe realmente

No existe columna `runs.campaign_id` en la base inspeccionada. La asociación actual es:

`runs.id ← campaign_attempts.training_run_id → campaign_attempts.member_id → campaign_members.campaign_id → experimental_campaigns.id`.

No confundir `runs.experiment_id`/tabla `experiments` con campaign_id/experimental_campaigns: son entidades distintas; no poner experiment_id en NULL para acomodar esta decisión.

`ExecutionRepository.claim(campaign_id,...)` valida campaña, toma miembro de esa campaña, crea intento y TRAIN y vincula ambos dentro de una sola transacción. La asociación es persistente desde el primer commit; nunca se descubre por fechas. `_create_run` no inserta una columna directa campaign_id porque no existe. Los campos campaign_id actuales están en campaign_members/configurations/execution_events y assessment_campaign_consumers; son tablas exclusivamente de campaña, con FK y NOT NULL válidos. **No retirar esos NOT NULL legítimos**: la prohibición global se refiere a corridas que deben admitir historia sin campaña.

Para cumplir además la representación explícita solicitada en `runs`, preparar columna nullable + FK y pasar campaign_id validado al INSERT del escritor de campaña. Hasta desplegar ese cambio, no declarar que `runs.campaign_id` ya existe o está poblado.

## Evidencia de integridad observada

Consultas de catálogo antes de consultar columnas; conexiones REPEATABLE READ, READ ONLY del proyecto mediante Compose existente. `referencias.json` conserva hora UTC, columnas/nulabilidad, FK reales y convalidated.

- Cero miembros sin campaña, intentos sin miembro, intentos con TRAIN inexistente, sesiones sin TRAIN o desalineadas con intento.
- Cero versiones con TRAIN/checkpoint no nulo inexistente y cero linajes con padre/hijo ausente.
- Cero TRAIN vinculados a más de una campaña por la cadena inspeccionada.
- Cero campaign_id no nulos huérfanos en las cuatro tablas que contienen actualmente esa columna.
- Ocho TRAIN ya asociados inequívocamente por intentos/miembros: cuatro en antecesora y cuatro en actual. No son corridas legacy sin asociación; cualquier proyección futura debe conservar **su propia campaña**, no moverlas a la vigente.
- 88 corridas sin asociación a intento de campaña: 24 TRAIN,36 EVALUATE,25 EXPLAIN (24 completed,1 failed),3 inference. Se describen como sin asociación observada, sin inferir pertenencia retrospectiva.

A partir de 2026-09-14 16:22:38 UTC (13:22:38 America/Santiago) se obtuvieron dos snapshots separados de huellas opacas de filas históricas: coinciden en runs88,artifacts4007,run_metrics2796,training_history926,classification_reports120,confusion_matrices60,run_image_predictions98364,explainability_results3600,model_versions36,run_lineage61. No se recuperaron valores de rendimiento ni predicciones para decisión científica; PostgreSQL sólo devolvió conteos y hashes. Esto acredita preservación de esos registros entre observaciones, **no una nueva validación física de cada binario** ni integridad de relaciones fuera del alcance enumerado. No se tocó ningún archivo de resultado.

No se encontró referencia inconsistente que justifique una reparación. No se preparó una puesta masiva a NULL. Si aparece una inconsistencia futura: identificar PK, FK, padre esperado y nulabilidad; retener evidencia; corregir sólo si relación exacta está demostrada o si nulabilidad/ausencia de asociación están verificadas. Ante ambigüedad, bloquear esa operación; no inventar padre ni borrar datos.

## Rutas revisadas y cambio necesario

| Ruta | Comportamiento actual / cambio preparado |
| --- | --- |
| `src/campaign.py` → CampaignService.create/freeze | Crea campaña real y matriz; conservar validación UUID/protocolo/dataset, sin inventar una para corridas históricas |
| `run_train_all_models.py` → execution.campaign.main/execute_campaign | ID requerido; consulta por ID explícito; mantener sin fallback a última campaña o TRAIN standalone |
| `ExecutionRepository.claim` | Pasar campaign_id obligatorio al escritor de TRAIN desde la campaña bloqueada; persistirlo en INSERT, nunca post-commit |
| `_create_run` compartido | Separar contrato de creación de campaña del standalone: helper de campaña con argumento keyword obligatorio y validación de padre; no optional=None que permita omisión silenciosa en claim |
| `ExecutionRepository.standalone` / entrenamiento individual | Fuera del flujo de campañas; no usar como fallback. Su existencia no obliga a asignar campaña ficticia. Registros sin vínculo siguen fuera de consultas de campaña |
| `CampaignRepository.create_attempt` y `update_attempt` | Mantener pertenencia miembro/campaña explícita. Al asociar TRAIN, exigir campaña directa igual y relación/configuración/dataset/semilla acreditadas; rechazar TRAIN legacy sin campaña, no reinterpretarlo |
| `ExecutionRepository.get/summary`, reconciliation y worker | Mantener filtros por miembro.campaign_id; tras cambio verificar igualdad con runs.campaign_id. Excluir NULL mediante INNER JOIN/filtro explícito, no COALESCE ni OR campaign_id IS NULL |
| assessment.campaign/CLI y AssessmentRepository.consume | Mantener consumidores con FK campaña/miembro y TRAIN aceptado exacto. No inventar EVALUATE legacy; identidad E6 puede ser compartida mediante consumidores, no asignar arbitrariamente una única campaña a resultados compartidos |
| `/assessments` y science.cli/repository | Distinguir consulta general de consulta de campaña. La consulta de campaña exige ID y consumidores/miembros asociados. El modo general existente no se usa para rellenar faltantes de campaña |

## Migración y despliegue: preparados, NO ejecutados

1. **No desplegar mientras continúa este coordinador.** Puede releer fuente antes de nuevos claims; modificar Python o configs invalida su source_sha256. Añadir una columna no hace que el worker antiguo la escriba. No reiniciar/recrear servicios para sortearlo. Ventana posterior autorizada, sin propietario activo, o procedimiento explícito de transición compatible.
2. Revisar HEAD/current/heads y asignar una revisión Alembic nueva conforme al repositorio. No reescribir migraciones instaladas. SQL conceptual de la nueva revisión:

```sql
ALTER TABLE public.runs ADD COLUMN campaign_id uuid NULL;
ALTER TABLE public.runs ADD CONSTRAINT fk_runs_campaign
  FOREIGN KEY (campaign_id) REFERENCES public.experimental_campaigns(id)
  ON DELETE RESTRICT NOT VALID;
ALTER TABLE public.runs VALIDATE CONSTRAINT fk_runs_campaign;
CREATE INDEX ix_runs_campaign ON public.runs(campaign_id)
  WHERE campaign_id IS NOT NULL;
```

Este bloque no constituye una migración desplegada y requiere comprobar nombres/ausencia de columna en la ventana. No tiene DEFAULT de campaña actual ni NOT NULL global. NOT VALID no se deja como cierre: validar constraint. En tablas de campañas se conservan FK existentes.

3. Preparar inventario de proyección **exclusivamente demostrada**: join runs→attempts→members→campaign, agrupar por Run ID, exigir una sola campaña y snapshot/linaje coherentes. Los ocho vínculos observados son candidatos a proyección, no autorización para inferir otros. Si se decide materializarlos, revisar lista exacta y hacerlo transaccionalmente con auditabilidad. Sin fechas, sin `max(created_at)`, sin reubicar antecesora. Todos los no asociados quedan NULL. La migración puede limitarse a esquema; no efectuar backfill automático dentro de ella.
4. Implementar y probar escritor nuevo atómico. Defensa SQL complementaria en asociación de nuevos intentos/sesiones: al crear una sesión de campaña o vincular TRAIN al intento, exigir runs.campaign_id=miembro.campaign_id y no NULL. Las actualizaciones de progreso de sesiones históricas no deben volverse inválidas por un NOT NULL indiscriminado. Una FK sola rechaza padre inexistente, **no** obliga a proporcionar ID en el punto de creación: se necesitan ambas capas.
5. Resolver compatibilidad de la fuente congelada **antes de reanudar**. No actualizar environment/source_sha256 en PostgreSQL para ocultar cambio. Esta decisión no autoriza inventar una campaña para superar la guarda. Si no hay transición compatible acreditable conservando la campaña, mantener despliegue pendiente y diseñar autorización de revisión explícita en etapa posterior.
6. En ventana autorizada, ejecutar el wrapper vigente: `make db-migrate-check`, revisar SQL de la nueva revisión con `docker compose exec -T backend python -m alembic upgrade REVISION_ACTUAL:REVISION_NUEVA --sql`, y sólo después `make db-migrate` (backup/preflight/rollback/upgrade). Marcadores REVISION_* deben reemplazarse por revisiones reales revisadas. **Ninguno ejecutado aquí.** No usar upgrade directo saltando wrapper.
7. Releer FK/huérfanos, comparar huellas/IDs de historia, verificar asociación exacta de nuevos TRAIN y linaje. No promover ni alterar publicación.

## Aceptación pendiente de implementación

Pruebas aisladas a preparar con la revisión, sin registros reales: (a) histórico NULL conserva campos/resultados; (b) creación campaña sin ID/malformado falla antes de INSERT; (c) UUID inexistente falla FK; (d) ID válido persiste en primer commit y se relee desde conexión nueva; (e) fallo de vínculo revierte toda creación; (f) campaña distinta rechazada en sesión/intento; (g) consulta explícita no devuelve NULL ni otra campaña; (h) standalone no entra por fallback; (i) histórico con versión/checkpoint/EVALUATE conserva linaje; (j) actualización legítima de progreso funciona; (k) carrera mantiene ownership y no crea duplicados; (l) rollback y limpieza del esquema sintético.

**No se declaran esas pruebas futuras aprobadas.** La inspección actual acredita asociación transaccional por tablas existentes y cero huérfanos en el alcance consultado. La obligatoriedad de la nueva columna directa aún requiere implementación y pruebas. Decisión incorporada; despliegue pendiente por protección del coordinador activo.
