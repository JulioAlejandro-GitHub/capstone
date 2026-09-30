# E10.10.5E — integración funcional: avance y bloqueo contractual

**E10.10.5E — INTEGRACIÓN INCOMPLETA. BLOQUEADA EN PREFLIGHT RUNTIME. GATE E NO SOLICITADO.**

Gate D fue aprobado explícitamente por el usuario al iniciar E. Esa aprobación no autoriza despliegue, cutover ni cambios al PostgreSQL operativo. Este informe no acredita validación clínica.

## 1. Objetivo y resultado

Se inició exclusivamente E y se instaló la baseline D.4 en una instancia PostgreSQL 17.9 nueva, sin copiar datos científicos. El preflight real con `capstone_v2_runtime` falla: la baseline certificada revoca explícitamente todo permiso sobre `public.alembic_version`. La verificación fail closed de revisiones no puede leer su head. No se eludió el fallo, no se concedieron privilegios y no se usó el migrador como runtime.

**E-01:** `alembic_v2/baseline/10_privileges.sql` termina con `REVOKE ALL ON TABLE public.alembic_version FROM PUBLIC, capstone_v2_runtime;`. La evidencia muestra `runtime_revision_select=false`, `runtime_is_superuser=false`, `E10_SCHEMA_NOT_READY: schema_inspection_failed` e `integration_ready=false`. El diagnóstico SELECT con migrador sí reconoce `pg_v2_baseline` y las capacidades certificadas. Esa lectura diagnóstica no acredita funcionamiento del runtime.

No es correcto declarar el estado de integración completada solicitado hasta resolver E-01 y ejecutar la matriz pendiente.

## 2. Archivos y trabajo preparado

Inventario exacto: [changed_files.txt](e10_10_5e_evidence/changed_files.txt).

- Guarda E10 con lista explícita de revisiones legacy/v2; rechazo de revisión desconocida, ausente o múltiple. V2 coteja funciones y triggers contra un contrato derivado del catálogo certificado D.4. El runtime no importa ni ejecuta Alembic.
- ResultRepository aplica esa guarda antes del ledger. Proyección preparada de `evaluations` y `run_clinical_metrics` en la misma conexión/transacción que el evento y el JSONB histórico; no cambia `canonical_event` ni sus hashes.
- Inserción preparada de `run_configurations` al crear TRAIN. No consulta defaults para completar información ausente.
- La proyección necesita `execution_parameters.e10_v2_evaluation_context_v1`, con checkpoint, hashes y snapshot del protocolo, población y contrato de entrada; falta de procedencia provoca rechazo. **Su producción y sellado desde TRAIN aún no están conectados ni acreditados.**
- Endpoint de lectura `/runs/{run_id}/scientific-results` con distinción legacy/v2 y consulta de las diez entidades solicitadas. Las métricas tipadas incluyen valor nullable, motivo de indefinición y orientación de matriz. Panel React en el detalle de ejecución con métricas, checkpoint/modelo, publicación, evidencia XAI e interpretaciones/revisiones.
- Preparación de instancia E admite una autorización explícita de Gate D en la guarda aislada existente, sin relajar identidad, volumen, puerto, usuario ni prohibición de stamp. No se modificó la baseline certificada.

Estos cambios son trabajo preparatorio sin validación integral y **no están listos para despliegue**.

## 3. Comandos ejecutados

[Registro de comandos y resultados](e10_10_5e_evidence/command_results.json), [orquestación aislada](e10_10_5e_evidence/instance/orchestration.jsonl), [Alembic](e10_10_5e_evidence/instance/commands.jsonl).

Comandos principales:

```sh
/private/tmp/e10e-venv/bin/python scripts/db/provision_v2_e_integration.py setup
/private/tmp/e10e-venv/bin/python scripts/db/provision_v2_e_integration.py preflight
/private/tmp/e10e-venv/bin/python scripts/db/provision_v2_e_integration.py upgrade
/private/tmp/e10e-venv/bin/python scripts/db/probe_v2_e_runtime.py
```

El último retorna **2**, deliberadamente indicando integración no lista. No debe interpretarse como prueba integral aprobada. Las dependencias auxiliares se instalaron en `/private/tmp/e10e-venv`; las suites usaron además el virtualenv existente del proyecto. La primera instalación sin acceso de red falló; la instalación autorizada posterior terminó correctamente. Credenciales aisladas permanecen en archivos privados, fuera de los informes.

## 4. Pruebas, cobertura y omisiones

**265 pruebas Python únicas aprobadas:** 142 de servicio, arquitectura, resultados científicos y emisor; 121 de baseline/adopción, reconocimiento de revisión y API de resúmenes; 2 nuevas del DTO nullable. **201 pruebas frontend aprobadas**, incluidas 2 nuevas que renderizan realmente el componente React con `react-dom/server`. Build TypeScript/Vite correcto; `git diff --check` correcto. No se midió cobertura porcentual de líneas.

| Requisito E | Evidencia actual | Estado |
|---|---|---|
| Legacy reconocido | Prueba de decisión con conexión simulada; regresión offline | Parcial; falta integración PostgreSQL legacy |
| V2 reconocido | Catálogo real reconocido por lectura del migrador; runtime rechazado por ACL | Bloqueado E-01 |
| Revisión desconocida | Rechazo unitario de head desconocido, vacío y múltiple | Aprobado unitario; falta prueba SQL E |
| Duplicación global/eventos | Regresión existente de servicio/emisor | Falta repetición integral v2 |
| Fallo SQL intermedio | No ejecutado en flujo v2 | Pendiente |
| Reinicio/recuperación | Regresión del emisor; no reinicio integral de runtime/servidor | Pendiente |
| Historial E10 sintético poblado | No se generó un historial para simular éxito tras rechazo | Pendiente |
| Publicación | Lectura preparada; pruebas previas no equivalen a certificación E | Pendiente |
| Linaje EVALUATE/EXPLAIN y XAI | Lectores preparados; no escrituras ni ciclo completo acreditados | Pendiente |
| API y React | DTO, SSR, regresión API y build; sin API contra runtime v2 | Parcial |
| TRAIN local y Docker | Sin entrenamiento real ni sintético completo en esta ejecución | Pendiente |

Las diez tablas tienen lectores preparados. Sólo configuración, evaluación TRAIN y métricas tienen nuevas proyecciones de escritura preparadas; `training_history`, ensembles y cinco entidades XAI requieren integración de sus productores y pruebas. Ninguna colección vacía acredita esas relaciones.

## 5. Evidencia reproducible

- [Preflight runtime](e10_10_5e_evidence/runtime_preflight.json).
- [Identidad del entorno nuevo](e10_10_5e_evidence/instance/target.json), [preflight Alembic](e10_10_5e_evidence/instance/preflight_before_alembic.json).
- [Preservación de recursos y 54 archivos históricos](e10_10_5e_evidence/preservation.json).
- [Comandos y conteos](e10_10_5e_evidence/command_results.json).
- Informes D.4 anteriores conservados íntegramente en `e10_10_5e_evidence/previous_reports/`.

Manifest conservado: `f276f819aa8512492ed89a52f12d192c1ace6cde24eee967287d17cd5f05dd57`. La referencia de catálogo sigue siendo la certificada D.4: `6df01a4d0e8fbcfd3e65a23e1394902097e565adad6b1b99de56a90f342cfa68`. No se expidió un certificado nuevo ni se modificaron D-01 a D-06.

## 6. Diferencias e incidencias

E-01 demuestra una incompatibilidad funcional entre la ACL certificada y el requisito de inspección runtime de revisión. El diagnóstico SQL independiente confirmó `permission denied for table alembic_version`. Un simple cambio de head permitido en código no resuelve el problema.

No se alteró el manifiesto para ocultar esta incompatibilidad. Tampoco se añadió fallback a otra base, otra fuente de métricas o credenciales de migrador. La guarda falla antes de aceptar eventos.

Los tests PostgreSQL históricos de preclaim se actualizaron para el nuevo código `unsupported_alembic_revision`, pero no se ejecutaron en esta etapa. Warnings no bloqueantes observados: deprecación Starlette/httpx y bundle frontend >500 kB.

## 7. Riesgos y trabajo pendiente

Además de E-01, queda conectar y sellar procedencia del checkpoint/protocolo/población sin inventar información, cubrir calibración exclusivamente VALIDATION, integrar productores de historial/ensembles/XAI, completar DTOs y migrar los lectores existentes de resumen/detalle que todavía pueden priorizar JSONB legacy. El nuevo panel no corrige por sí solo esos lectores. Debe evitarse que sus fallbacks conviertan una métrica v2 indefinida en un cero legacy.

Faltan fixtures pobladas, concurrencia/fencing en PostgreSQL v2, rechazo SQL intermedio con rollback de ledger y proyección, pérdida de ACK, reinicio, publicación, linaje, evaluación VALIDATION y recorrido HTTP/Docker/API/React. Los INSERT preparados están sujetos a constraints y triggers reales todavía no ejercitados por el runtime.

## 8. Estado operativo

Sin conexiones a PostgreSQL operativo, stamp operativo, cutover, campañas reales ni entrenamiento clínico. No se regeneró dataset, no se modificaron checkpoints, eventos ni hashes históricos. La instancia nueva sólo contiene instalación técnica de la baseline; no contiene resultados científicos ficticios derivados de datos reales. TEST continúa reservado para evaluación final.

La instancia aislada se conserva con su volumen y credenciales privadas; su estado final se registra en `isolated_shutdown.json`. No se utilizó el PostgreSQL operativo ni las copias certificadas D.4 para estas pruebas.

## 9. Decisión requerida

**Gate E no está listo para revisión de aprobación.** Se solicitó al usuario decidir entre conservar D.4 intacta y mantener E bloqueada, o autorizar una corrección acotada que permita leer la revisión desde runtime y recertificar el contrato afectado en aislamiento. Una opción concreta es conceder exclusivamente `SELECT` sobre la tabla de versión, manteniendo prohibidos INSERT/UPDATE/DELETE, DDL y stamp para runtime. Esa opción no fue aplicada ni aprobada implícitamente.

Incluso autorizada la corrección, no bastaría para aprobar E: deberá completarse toda la matriz pendiente y reemplazar este estado por evidencia integral verificable. No se inicia ninguna etapa posterior.
