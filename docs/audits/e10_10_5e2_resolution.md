# E10.10.5E.2 — E-02 aprobada; continuación detenida por E-03

**Integración incompleta. Gate E bloqueado y no solicitado.**

## Cambio E-02 implementado

PostgresResultRepository selecciona el comportamiento por la revisión reconocida por `require_e10_schema`. En v2, `project_training_result` termina después de proyectar `evaluations` y `run_clinical_metrics` en la misma conexión/transacción raíz del append del ledger. No emite el UPDATE de `runs.parameters.training_results`. Legacy conserva ese UPDATE. No se detecta v2 mediante excepciones del CHECK ni se incorpora otro JSONB de resultados.

`ck_v2_no_result_json`, baseline E.1, E-01, D-01 a D-06 y canonical_event permanecen intactos. No se modifica el contrato de eventos ni se recalculan hashes históricos. La corrección del escritor no acredita la resolución integral de lectores/productores.

## Verificación ejecutada

[Probe reproducible](../../scripts/db/probe_v2_e2_projection.py) · [Evidencia SQL](e10_10_5e2_evidence/route_a/e10_projection.json) · [Pruebas unitarias](e10_10_5e2_evidence/unit_tests.txt).

- 76 pruebas unitarias aprobadas: servicio y dos ramas de proyección. La rama legacy sigue generando el UPDATE histórico; la v2 llama a la proyección tipada y no genera ese UPDATE.
- PostgreSQL real aislado E.1, login runtime auténtico, revisión y capacidades verificadas. La evaluación sintética se acepta sin JSONB legacy; ledger conserva exactamente su canonical_event.
- Reintento del evento y nueva instancia del servicio reconocen duplicados; queda una evaluación y una métrica. Esto prueba recuperación del servicio ante ACK descartado, **no** pérdida de ACK por transporte ni reinicio de proceso/contenedor.
- Fallo SQL `22012` inyectado al ejecutar el INSERT de métricas, después del append y del INSERT de evaluación: excepción, sin ACCEPTED, evaluación y métricas en cero, ledger sólo con la época previa. El mismo evento se acepta al retirar el fallo.
- Procedencia ausente: rechazo y rollback del append. Owner incorrecto: rechazo. Gap, conflicto de secuencia y event_id con payload distinto: rechazo.
- INSERT y UPDATE directos con `training_results`: ambos rechazados por PostgreSQL con `23514 / ck_v2_no_result_json`.
- [Catálogo y archivos protegidos](e10_10_5e2_evidence/route_a/preservation.json): comparación íntegra con catálogo E.1 y archivos Git históricos. No es una nueva recertificación de baseline.

Los padres, checkpoint y contexto del probe son **fixtures sintéticos explícitos**. Sus hashes de contexto no acreditan procedencia producida por TRAIN; ningún resultado representa validación clínica. La comprobación de canonical_event corresponde al nuevo evento sintético; la preservación de archivos históricos se informa por separado.

Incidencias de ejecución: primer pytest sin PYTHONPATH no pudo importar `src`; corregido. La primera inyección desde callback DBAPI escapó al manejo de SQLAlchemy; se cambió a sustitución de SQL con `retval=True`. Se corrigieron expectativas de estado a minúsculas y el status obligatorio del INSERT negativo. Los intentos incompletos dejaron fixtures aislados; los reintentos marcaron sus sesiones como interrupted. Sólo el JSON final y el log de pytest acreditan el resultado. No se sobrescribió evidencia E.1.

## E-03: incompatibilidad arquitectónica confirmada

La baseline impone simultáneamente:

1. `v2_calibration_pair_guard`: la calibración requiere dos evaluaciones VALIDATION del mismo checkpoint/población, con roles `calibration_default` y `calibration_selected`.
2. `v2_evaluations_check_6a2239d39784`:

   ```sql
   CHECK (source_kind <> 'e10' OR evaluation_role = 'training_validation_final')
   ```

Por tanto, una pareja de calibración producida desde eventos TRAIN/E10 no puede conservar `source_kind='e10'` y cumplir los roles obligatorios. PostgreSQL rechazó ambos roles con `23514` y el nombre exacto de ese CHECK. El probe copia las columnas de una evaluación sintética aceptada y cambia sólo identidad, clave de origen y rol. No atribuye el fallo a falta de procedencia ni al CHECK E-02.

El productor de contexto aún no se conectó. Se detuvo su implementación al confirmar esta incompatibilidad, conforme al apartado 9 de E.2. No se etiquetaron eventos nuevos como `legacy`, no se fabricó un assessment y no se relajó la baseline.

### Decisión específica solicitada

**Propuesta E-03:** autorizar que `source_kind='e10'` admita también `calibration_default` y `calibration_selected`, conservando la restricción a VALIDATION, sus vínculos al evento ledger, checkpoint, dataset/población y los dos miembros de la pareja. Para derivar ambos miembros de un evento de calibración, usar claves de proyección distintas, deterministas y vinculadas al mismo source_event_id. Esto requiere revisar el CHECK indicado, su contrato runtime/adopción y recertificar baseline antes de continuar; **no se ha implementado**.

Si se decide conservar la baseline actual, hace falta aprobar explícitamente otro contrato de procedencia para esas dos evaluaciones. `legacy` no se elegirá silenciosamente para hechos nuevos, `external_record` corresponde a external y `assessment` supone una identidad/recorrido distinto de TRAIN.

La autorización E-02 no resuelve esa elección ni permite cambiar esa restricción. Se solicita decisión E-03, no Gate E.

## Pendientes y límites

Continúa pendiente la matriz integral de 20 recorridos, detallada en [estado E](e10_10_5e_integration_results.md). En particular, el validador de finalización todavía exige el JSONB legacy, el resumen TRAIN todavía usa lectores legacy y falta acreditar NULL sin fallback en todos los lectores/API/React. La compatibilidad legacy de esta entrega se limita a pruebas de servicio/routing; no se declara regresión integral PostgreSQL legacy.

Sin cutover, campañas reales, entrenamiento clínico, cambios al dataset congelado ni acceso al PostgreSQL operativo. TEST no participó en selección o calibración.

## Reproducción

Arrancar exclusivamente el container_id del descriptor E.1 aislado; cada probe valida aislamiento antes del acceso runtime. No ejecutar setup ni reutilizar configuración operativa. Evidencia nueva en E.2; credenciales sólo referenciadas por rutas privadas.

```sh
PYTHONPATH=malaria_dl_local_project malaria_dl_local_project/.venv/bin/python -m pytest -q malaria_dl_local_project/tests/test_e02_projection_routing.py malaria_dl_local_project/tests/test_result_service.py
malaria_dl_local_project/.venv/bin/python scripts/db/probe_v2_e2_projection.py
malaria_dl_local_project/.venv/bin/python scripts/db/capture_v2_e2_state.py
```

El probe termina en 0 cuando sus aserciones, incluido el rechazo E-03, se cumplen. Ese código no significa integración E completa. El contenedor se detiene al finalizar, conservando su volumen y evidencia.
