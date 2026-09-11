# E5 — Implementación local del ejecutor

**Dictamen: NO APROBADA.** Integración PostgreSQL y migración operativa pendientes por acceso denegado a Docker. No se inició E6 ni se ejecutaron campañas científicas.

## Base y alcance

HEAD `cd5c64d703358797570f5183dd598d93314dc0eb`, main. Árbol inicial de código limpio; se preservaron los documentos sin seguimiento de línea base E5 y cierre E4 creados en la conversación. Los 25 hashes del manifiesto final E4 coincidían al inicio. E4 está aprobada mediante 49 pruebas sintéticas y una comprobación pública aportadas por el usuario; sus resultados no se atribuyen a E5.

Se revisaron contrato 0B v1.1, políticas PostgreSQL/Alembic, cierres E1–E4, migraciones 01/02, registro/adaptadores E2, contratos de entrada E3, servicios/guardas E4 y camino TRAIN/tracking/checkpoints. No se encontraron AGENTS aplicables. El nuevo head de código es `20260912_01`; las migraciones E4 permanecen byte a byte intactas.

## Cambios

- CLI del lote por campaign-id con inspect/result/resume y dataset como aserción; elimina el bucle ejecutable basado en registro actual.
- Dominio `execution`: repositorio propietario, coordinador de procesos, hijo que valida el contrato congelado, motor TRAIN sin CSV y verificador de artefactos/resultados.
- Sesiones y resultados estructurados aditivos, registros idempotentes/inmutables, guardas de propiedad/estado y ampliación de verified con aceptación first_verified_attempt.
- CLI TRAIN individual usa el motor persistido, conserva dataset explícito y no exige campaña. Rechaza TEST/salida lateral de calibración.
- Recuperación conservadora por ausencia comprobada de PID locales, sin leases, sin asumir que una conexión caída implica muerte del proceso. Propietario indeterminado pausa con diagnóstico.
- Resumen desde BD distingue miembros, intentos, aceptación, completitud, terminalidad y cumplimiento clínico; sin ranking/publicación.

Guía y comandos completos: `docs/engineering/etapa_5_ejecutor_2026-09-11.md`.

## Evidencia real

Conjunto local consolidado: **96 aprobadas, 14 PostgreSQL omitidas**, cuatro avisos existentes (protobuf/Alembic). Una invocación inicial desde la raíz, sin el cwd ML, falló en colección por ModuleNotFoundError src; se corrigió el cwd y no se interpreta ese intento como fallo de implementación.

Comando consolidado, desde malaria_dl_local_project:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_campaign_executor_e5.py tests/test_campaign_executor_postgres.py \
 tests/test_campaigns_e4.py tests/test_migration_root_e4.py tests/test_governed_dataset_contract.py \
 tests/test_model_registry_e2.py::test_lazy_cli \
 tests/test_model_registry_e2.py::test_matrix_and_identical_child_resolution \
 tests/test_model_registry_e2.py::test_invalid_config_before_adapter \
 tests/test_model_registry_e2.py::test_precedence_requested_resolved_and_tracking
```

El control de TRAIN se ejecutó con modelo/adaptador y callbacks sintéticos: se importa TensorFlow pero no se construye ni entrena una red. Espías comprobaron carga sólo train/val e inferencias sólo VAL, guardado binario sintético y ausencia de CSV/JSON laterales. Los casos locales comprueban rechazo de overrides, evidencia parcial, checkpoint alterado/no cargable y preparación del SQL sin parámetros accidentales.

Historial Alembic: **24 revisiones, head único 20260912_01**. DDL E5 renderizado en memoria: **9.844 bytes**, SHA-256 `58c13c23e17e7d9d579c906faa1a2bb3b28e3beb78c80cbcdab82529ba069cab`. Es renderizado, no ejecución/validación PL/pgSQL. Ruff pasó en archivos E5.

Intento de integración E5 por Compose: `permission denied while trying to connect to the docker API` (ruta del socket omitida). No hubo acceso a PostgreSQL. No se aplicó la migración ni se eludió el wrapper de respaldo/preflight.

## Escenarios y límites de evidencia

Las 14 pruebas PostgreSQL preparadas incluyen matriz de doce, reanudación sin repetir verified, fallo individual con presupuesto agotado, idempotencia/propietario revocado, pausa sistémica, exit0 incompleto, reclamación concurrente de un único miembro, interrupción, seis puntos de fallo (antes de TRAIN, métricas, después de checkpoint/artefacto, antes/después de aceptación) y una lectura de instalación pública. Las trece sintéticas quedan **NO VERIFICADAS** hasta ejecución real; la pública requiere instalación posterior. El fixture conserva rollback/cleanup desde otra conexión y las restricciones de la instancia autorizada.

EXEC-01/02/03 TRAIN, TRACE-01/02/04 y guarda TEST tienen implementación y casos preparados, pero no evidencia crítica completa para aprobar. S10–S12, S20–S24, S26 y S30–S31 deben cerrarse con integración, regresiones E1–E4 aplicables y comprobación operacional. No se atribuye la concurrencia aprobada de E4 a las nuevas reclamaciones E5.

La prueba de interrupción del coordinador en integración usa KeyboardInterrupt controlado; no acredita una caída real del host. No se ha probado durabilidad ante reinicio, pérdida de confirmación de commit ni muerte por fallo de alimentación. Un active en host distinto o con PID vivo/reutilizado requiere diagnóstico; no se recupera automáticamente ni se declara completado.

Los checkpoints guardan versión exacta en la evidencia de artefacto E5; no se ha acreditado su consumo por los resolvers legacy model_versions de EVALUATE/EXPLAIN. E6 debe cerrar esos consumidores sin usar latest/fechas. Los helpers históricos de trainer y escritores EVALUATE/EXPLAIN permanecen; los nuevos entrypoints TRAIN se desvían al motor E5 y no dependen de esos CSV/JSON. No se afirma eliminación global de escritores del repositorio.

La identidad clínica de muestra se conserva como ruta relativa a la materialización sellada y snapshot E1, con labels/scores en lotes JSONB. No se ha realizado entrenamiento real ni validación de resultados clínicos. Dataset, split, históricos y publicación manual permanecen intactos.

## Cierre pendiente

Ejecutar primero los 13 casos sintéticos; corregir cualquier fallo antes de instalar. Después, wrapper make db-migrate autorizado por la solicitud, comprobación pública, suite completa y /ready. Hasta obtener esas evidencias, **E5 NO APROBADA**, sin observaciones que sustituyan integridad, persistencia o concurrencia pendientes.
