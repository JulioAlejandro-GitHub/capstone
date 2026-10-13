# CAPSTONE-DB-02A — Observabilidad

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Bloque 1 implementado en rama aislada; no desplegado.

`CampaignRepository.transaction` conserva rollback y emite un evento JSON sin formatear la excepción SQLAlchemy. Campos: event, exception_class (driver), sqlstate, table, constraint, message y correlation_id. Solo mensajes científicos exactos, sin valores y con SQLSTATE P0001 se propagan; los demás se omiten. No es una whitelist de esquema ni una comprobación de versión.

`create_campaign` reutiliza el correlation_id del middleware, mantiene el código público en error.details.code y traduce CAMPAIGN_DATABASE_OPERATION_FAILED a HTTP 500; rechazos científicos siguen en 422. `services/api.ts` lee el envelope y expone correlationId. `CampaignConfiguration.tsx` distingue red, timeout, cancelación, 422, 500 y otros estados sin imprimir el mensaje bruto.

Validación: `make -f docs/audits/capstone_db_02a/Makefile test-observability`: **16 PASS**, contra capstone_db02a_test_20261012. Incluye trigger campaign_guard real, error SQL 42703, mensaje potencialmente sensible omitido, correlación HTTP/log, rollback y cero campañas/configuraciones/miembros. El productor científico se sustituye en el test HTTP para no ejecutar verificación de datasets ni pipelines.

`make -f docs/audits/capstone_db_02a/Makefile test-errors-ui build-ui`: **PASS**. `make test-frontend`: 1 fallo preexistente en executions-dataset-version.test.mjs (espera «No registrado», código base tiene «No registrado 2»); no se modifica. La compilación separada pasa.

Preparación de pruebas: primera ejecución omitió configs y falló por INCOMPLETE_MODEL_DESCRIPTOR; segunda detectó catálogo models vacío. Se copiaron configs y se cargaron tres modelos sintéticos en la base aislada. Las ejecuciones finales pasan. No se instalaron dependencias.

No se ha repetido una creación desde la interfaz operativa. Su atribución concreta sigue pendiente del usuario después de desplegar este código.
