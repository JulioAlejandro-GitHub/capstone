# E10.10.2 — Candidatos de obsolescencia

**E10.10.2 — GOBERNANZA DOCUMENTADA**

## Dictamen

**Las seis tablas investigadas son ACTIVE. Ninguna es OBSOLETE_CONFIRMED. No se recomienda eliminar ninguna.** El baseline E10.10.1 refuta la hipótesis de “seis tablas sin referencias” de `revision-bd-malaria.md`: conserva cinco vacías y una fila técnica en el gate después de la reconstrucción. Esta auditoría identifica productores, lectores y dependencias SQL actuales; no afirma que se haya ejecutado una campaña nueva ni que exista tráfico reciente.

Referencia operativa: [baseline Markdown](e10_10_1_baseline.md), [JSON completo](e10_10_1_baseline.json), captura UTC 2026-09-29T02:34:49.403485+00:00. La [matriz de ownership](e10_10_2_schema_ownership.md) contiene todos los objetos y la gobernanza de migraciones. Conteos y definiciones proceden del baseline; E10.10.2 no se conectó a PostgreSQL.

## Criterios y alcance de búsqueda

ACTIVE exige un contrato vigente y consumidor concreto, incluida una ruta opt-in o una dependencia SQL invocada por otra tabla. LEGACY_REQUIRED conserva procedencia/compatibilidad demostrada. UNDETERMINED conserva la incertidumbre. OBSOLETE_CONFIRMED requeriría retiro funcional explícito y revisión de consumidores directos, SQL dinámico, dependencias y clientes externos; no basta que una tabla esté vacía, que no aparezca en el frontend o que tenga contadores cero.

Se buscaron nombres literales y rutas de ejecución en `backend_api/app`, `frontend/src`, `malaria_dl_local_project/src`, `malaria_dataset_split_project/src`, ambos proyectos de tests, tests backend, `alembic/versions`, SQL histórico, scripts de proyecto y raíz, y `docs/engineering/e10_execution_refactor`. Se leyeron las definiciones de vistas, funciones, triggers, índices y constraints del JSON completo para encontrar dependencias sin SQL directo en Python. Se revisaron constantes/interpolación de vistas, tablas declaradas en inventarios de mantenimiento y dispatch HTTP dinámico. Referencias de tests, documentación, resets o fixtures se separan de consumidores runtime. No se usaron dumps antiguos ni snapshots de reset como estado actual.

No se encontraron referencias directas a los seis nombres SQL en el frontend revisado. Esto no acredita desuso: Local accede por HTTP y Docker por CLI/worker; la UI no es el único entrypoint. No se inspeccionaron clientes externos ni telemetría nueva, y E10.10.1 no tiene pg_stat_statements. Por eso las ausencias se reportan como límites y no como pruebas negativas.

## Clasificación de las seis tablas

| Tabla | Filas E10.10.1 | Responsable funcional | Clasificación | Papel para E10 | Recomendación |
| --- | ---: | --- | --- | --- | --- |
| `campaign_controlled_requests` | 0 | MLOps / coordinación de ejecución | **ACTIVE** | Petición idempotente para un único reintento autorizado sobre campaña paused; enlaza intento anterior, nuevo intento, run, miembro y revisión técnica. | Conservar; no iniciar retiro |
| `campaign_technical_revisions` | 0 | MLOps / coordinación de ejecución | **ACTIVE** | Evidencia técnica explícita de cambio de entorno sin cambiar el contrato científico congelado: payload, canonical_payload, hash, razón, archivos, pruebas y autorización. | Conservar; no iniciar retiro |
| `experiment_execution_events` | 0 | MLOps / coordinación de ejecución | **ACTIVE** | Historial append-only de coordinación global (owner/event/payload), distinto del stream científico RunEvent. | Conservar; no iniciar retiro |
| `experiment_execution_gate` | 1 | MLOps / coordinación de ejecución | **ACTIVE** | Singleton de exclusión experimental y fencing: owner, PID DB y evidencia de procesos. El owner coordina TRAIN/assessment y se comparte con ejecución Local. | Conservar; no iniciar retiro |
| `local_execution_jobs` | 0 | MLOps / coordinación de ejecución | **ACTIVE** | Reserva remota persistente, identidad principal/agente/owner, heartbeat, resultado, prueba de salida y retención de recursos hasta demostrar ausencia del proceso. | Conservar; no iniciar retiro |
| `train_execution_revisions` | 0 | MLOps / coordinación de ejecución | **ACTIVE** | Binding inmutable intento–campaña–revisión para ejecución secuencial con entorno técnico autorizado. No duplica la petición controlled: cubre otra ruta. | Conservar; no iniciar retiro |

## campaign_controlled_requests — ACTIVE

Petición idempotente para un único reintento autorizado sobre campaña paused; enlaza intento anterior, nuevo intento, run, miembro y revisión técnica.

- Creación: [Alembic 20260914_01 — alembic/versions/20260914_01_controlled_train.py:19](../../alembic/versions/20260914_01_controlled_train.py#L19).
- Consumidor: [ControlledRepository.reserve — malaria_dl_local_project/src/malaria_dl/execution/controlled.py:90](../../malaria_dl_local_project/src/malaria_dl/execution/controlled.py#L90).
- Evidencia SQL en ese módulo: `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:94`, `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:106`, `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:118`, `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:147`.
- Dependencias declarativas salientes: `campaign_controlled_requests_attempt_id_fkey`: FOREIGN KEY (attempt_id) REFERENCES campaign_attempts(id) DEFERRABLE INITIALLY DEFERRED; `campaign_controlled_requests_campaign_id_fkey`: FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id); `campaign_controlled_requests_campaign_id_revision_id_fkey`: FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions(campaign_id, id); `campaign_controlled_requests_member_id_fkey`: FOREIGN KEY (member_id) REFERENCES campaign_members(id); `campaign_controlled_requests_previous_attempt_id_fkey`: FOREIGN KEY (previous_attempt_id) REFERENCES campaign_attempts(id); `campaign_controlled_requests_run_id_fkey`: FOREIGN KEY (run_id) REFERENCES runs(id) DEFERRABLE INITIALLY DEFERRED.
- Dependencias entrantes por FK: ninguna en el catálogo; esto no excluye consumidores procedimentales.
- Triggers propios sobre la tabla: `controlled_binding_guard`, `controlled_request_guard`.
- Lectores/escritores procedimentales SQL vigentes: `campaign_attempt_guard`, `controlled_pause_guard`, `controlled_run_guard`.
- Pruebas existentes, **leídas y no ejecutadas**: [test_paused_atomic_idempotent_identity — malaria_dl_local_project/tests/test_controlled_train_postgres.py:37](../../malaria_dl_local_project/tests/test_controlled_train_postgres.py#L37); [test_concurrent_idempotence — malaria_dl_local_project/tests/test_controlled_train_postgres.py:82](../../malaria_dl_local_project/tests/test_controlled_train_postgres.py#L82); [test_controlled_existing_request_and_recover_do_not_reserve_on_old_schema — malaria_dl_local_project/tests/test_e10_preclaim_schema_postgres.py:183](../../malaria_dl_local_project/tests/test_e10_preclaim_schema_postgres.py#L183).

**Impacto de retiro:** Eliminarla rompe reserva controlada, recuperación por request y los guards de campaña/run; la petición se inserta antes del intento/run gracias a FK diferibles.

## campaign_technical_revisions — ACTIVE

Evidencia técnica explícita de cambio de entorno sin cambiar el contrato científico congelado: payload, canonical_payload, hash, razón, archivos, pruebas y autorización.

- Creación: [Alembic 20260914_01 — alembic/versions/20260914_01_controlled_train.py:10](../../alembic/versions/20260914_01_controlled_train.py#L10).
- Consumidor: [ControlledRepository.register_revision / revision — malaria_dl_local_project/src/malaria_dl/execution/controlled.py:44](../../malaria_dl_local_project/src/malaria_dl/execution/controlled.py#L44).
- Evidencia SQL en ese módulo: `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:42`, `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:50`, `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:54`, `malaria_dl_local_project/src/malaria_dl/execution/controlled.py:57`.
- Dependencias declarativas salientes: `campaign_technical_revisions_campaign_id_fkey`: FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id).
- Dependencias entrantes por FK: `campaign_controlled_requests.campaign_controlled_requests_campaign_id_revision_id_fkey`, `train_execution_revisions.train_execution_revisions_campaign_id_revision_id_fkey`.
- Triggers propios sobre la tabla: `technical_revision_guard`.
- Lectores/escritores procedimentales SQL vigentes: `campaign_attempt_guard`, `controlled_binding_guard`, `train_revision_binding_guard`.
- Pruebas existentes, **leídas y no ejecutadas**: [test_invalid_revision_rejected — malaria_dl_local_project/tests/test_controlled_train_postgres.py:55](../../malaria_dl_local_project/tests/test_controlled_train_postgres.py#L55); [test_resume_and_revision_mutation_blocked — malaria_dl_local_project/tests/test_controlled_train_postgres.py:126](../../malaria_dl_local_project/tests/test_controlled_train_postgres.py#L126); [test_sequential_revision_and_verified_before_next — malaria_dl_local_project/tests/test_global_execution_postgres.py:103](../../malaria_dl_local_project/tests/test_global_execution_postgres.py#L103).

**Impacto de retiro:** Eliminarla impide resolver el entorno autorizado tanto en controlled como en sequential con revisión y rompe referencias compuestas de ambos bindings.

## experiment_execution_events — ACTIVE

Historial append-only de coordinación global (owner/event/payload), distinto del stream científico RunEvent.

- Creación: [Alembic 20260914_02 — alembic/versions/20260914_02_global_execution.py:15](../../alembic/versions/20260914_02_global_execution.py#L15).
- Consumidor: [GlobalGate.event — malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:147](../../malaria_dl_local_project/src/malaria_dl/execution/global_gate.py#L147).
- Evidencia SQL en ese módulo: `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:148`.
- Dependencias declarativas salientes: sin FK salientes; dependencia de coordinación por función/trigger.
- Dependencias entrantes por FK: ninguna en el catálogo; esto no excluye consumidores procedimentales.
- Triggers propios sobre la tabla: `global_execution_event_immutable`.
- Lectores/escritores procedimentales SQL vigentes: no encontrados en funciones propias; productor Python identificado arriba.
- Pruebas existentes, **leídas y no ejecutadas**: [test_two_coordinators_global_lock — malaria_dl_local_project/tests/test_global_execution_postgres.py:48](../../malaria_dl_local_project/tests/test_global_execution_postgres.py#L48); [test_new_oom_and_consecutive_failure_circuit — malaria_dl_local_project/tests/test_global_execution_postgres.py:79](../../malaria_dl_local_project/tests/test_global_execution_postgres.py#L79).

**Impacto de retiro:** Eliminarla hace fallar las escrituras de GlobalGate y elimina evidencia de coordinación. No puede sustituirse por train_execution_records, que tiene otra identidad y semántica.

## experiment_execution_gate — ACTIVE

Singleton de exclusión experimental y fencing: owner, PID DB y evidencia de procesos. El owner coordina TRAIN/assessment y se comparte con ejecución Local.

- Creación: [Alembic 20260914_02 — alembic/versions/20260914_02_global_execution.py:9](../../alembic/versions/20260914_02_global_execution.py#L9).
- Consumidor: [GlobalGate.__enter__ / close / status — malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:153](../../malaria_dl_local_project/src/malaria_dl/execution/global_gate.py#L153).
- Evidencia SQL en ese módulo: `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:159`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:164`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:183`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:205`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:211`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:219`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:249`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:253`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:261`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:280`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:282`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:314`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:325`, `malaria_dl_local_project/src/malaria_dl/execution/global_gate.py:328`.
- Dependencias declarativas salientes: sin FK salientes; dependencia de coordinación por función/trigger.
- Dependencias entrantes por FK: ninguna en el catálogo; esto no excluye consumidores procedimentales.
- Triggers propios sobre la tabla: ninguno; la protección depende de los contratos y guards invocados desde las rutas consumidoras.
- Lectores/escritores procedimentales SQL vigentes: `experiment_require_owner`.
- Pruebas existentes, **leídas y no ejecutadas**: [test_lost_db_lock_fences_owner — malaria_dl_local_project/tests/test_global_execution_postgres.py:190](../../malaria_dl_local_project/tests/test_global_execution_postgres.py#L190); [test_train_assessment_cross_exclusion — malaria_dl_local_project/tests/test_global_execution_postgres.py:252](../../malaria_dl_local_project/tests/test_global_execution_postgres.py#L252); [test_local_job_blocks_docker_gate_while_held — malaria_dl_local_project/tests/test_local_execution_postgres.py:227](../../malaria_dl_local_project/tests/test_local_execution_postgres.py#L227).

**Impacto de retiro:** Eliminarla rompe experiment_require_owner, reservas y aceptación de eventos E10. La fila libre es un requisito técnico; no es un residuo experimental.

## local_execution_jobs — ACTIVE

Reserva remota persistente, identidad principal/agente/owner, heartbeat, resultado, prueba de salida y retención de recursos hasta demostrar ausencia del proceso.

- Creación: [Alembic 20260915_01 — alembic/versions/20260915_01_local_execution.py:9](../../alembic/versions/20260915_01_local_execution.py#L9).
- Consumidor: [LocalBackend.claim / operation — malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:71](../../malaria_dl_local_project/src/malaria_dl/local_execution/backend.py#L71).
- Evidencia SQL en ese módulo: `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:45`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:75`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:91`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:105`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:122`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:144`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:156`, `malaria_dl_local_project/src/malaria_dl/local_execution/backend.py:168`.
- Dependencias declarativas salientes: `local_execution_jobs_campaign_id_fkey`: FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id); `local_execution_jobs_run_id_fkey`: FOREIGN KEY (run_id) REFERENCES runs(id).
- Dependencias entrantes por FK: ninguna en el catálogo; esto no excluye consumidores procedimentales.
- Triggers propios sobre la tabla: ninguno; la protección depende de los contratos y guards invocados desde las rutas consumidoras.
- Lectores/escritores procedimentales SQL vigentes: `experiment_require_owner`.
- Pruebas existentes, **leídas y no ejecutadas**: [test_claim_is_idempotent_by_request_id — malaria_dl_local_project/tests/test_local_execution_postgres.py:190](../../malaria_dl_local_project/tests/test_local_execution_postgres.py#L190); [test_owner_and_agent_fencing — malaria_dl_local_project/tests/test_local_execution_postgres.py:210](../../malaria_dl_local_project/tests/test_local_execution_postgres.py#L210); [test_gate_owner_persists_until_exit — malaria_dl_local_project/tests/test_local_execution_postgres.py:545](../../malaria_dl_local_project/tests/test_local_execution_postgres.py#L545).

**Impacto de retiro:** Eliminarla rompe la API Local y su resolución de identidad E10. calculation_reported no equivale a released: local_one_active mantiene exclusión hasta salida confirmada.

## train_execution_revisions — ACTIVE

Binding inmutable intento–campaña–revisión para ejecución secuencial con entorno técnico autorizado. No duplica la petición controlled: cubre otra ruta.

- Creación: [Alembic 20260914_02 — alembic/versions/20260914_02_global_execution.py:46](../../alembic/versions/20260914_02_global_execution.py#L46).
- Consumidor: [ExecutionRepository.claim(revision_id) — malaria_dl_local_project/src/malaria_dl/execution/repository.py:85](../../malaria_dl_local_project/src/malaria_dl/execution/repository.py#L85).
- Evidencia SQL en ese módulo: `malaria_dl_local_project/src/malaria_dl/execution/repository.py:118`.
- Dependencias declarativas salientes: `train_execution_revisions_attempt_id_fkey`: FOREIGN KEY (attempt_id) REFERENCES campaign_attempts(id) DEFERRABLE INITIALLY DEFERRED; `train_execution_revisions_campaign_id_fkey`: FOREIGN KEY (campaign_id) REFERENCES experimental_campaigns(id); `train_execution_revisions_campaign_id_revision_id_fkey`: FOREIGN KEY (campaign_id, revision_id) REFERENCES campaign_technical_revisions(campaign_id, id).
- Dependencias entrantes por FK: ninguna en el catálogo; esto no excluye consumidores procedimentales.
- Triggers propios sobre la tabla: `train_execution_revision_immutable`, `train_revision_binding_guard`.
- Lectores/escritores procedimentales SQL vigentes: `campaign_attempt_guard`.
- Pruebas existentes, **leídas y no ejecutadas**: [test_sequential_revision_and_verified_before_next — malaria_dl_local_project/tests/test_global_execution_postgres.py:103](../../malaria_dl_local_project/tests/test_global_execution_postgres.py#L103); [@pytest.mark.parametrize('entry' — malaria_dl_local_project/tests/test_e10_preclaim_schema_postgres.py:50](../../malaria_dl_local_project/tests/test_e10_preclaim_schema_postgres.py#L50).

**Impacto de retiro:** Eliminarla rompe claim con revisión, validación de campaign_attempt_guard y effective_row para workers/recuperación. No tener filas hoy no suprime la opción revision_id.

## Dependencias indirectas y contratos E10

| Ruta | Evidencia verificable | Dependencia que una búsqueda sólo en backend perdería |
| --- | --- | --- |
| Docker campaña | `malaria_dl_local_project/src/malaria_dl/execution/campaign.py:321` entra en GlobalGate; `execute_campaign:174` coordina claims. | Gate/eventos y binding secuencial aunque las tablas no se nombren en el router FastAPI. |
| Docker controlled | `execution/controlled.py:199` (`execute_one`), `:270` (`GlobalGate`), `:90` (`reserve`). | Revisiones, petición idempotente, intento y run en una transacción. |
| Worker Docker | `execution/worker.py:56` (`attach_worker`); `:102` (`build_docker_run_reporter`). | Token global y resultados E10; la composición conduce a ResultService/PostgresResultRepository. |
| API Local | `backend_api/app/main.py:49` registra router; `backend_api/app/routes/local_execution.py:80` (`local_operation`) despacha claim/heartbeat/record/exit/status. | `LocalBackend` crea/consulta jobs y mantiene el gate; opt-in por CAPSTONE_LOCAL_EXECUTION_ENABLED. |
| E10 HTTP | `backend_api/app/routes/local_execution.py:21` (`local_event`), `local_execution/event_backend.py:36` (`accept`), `event_context.py:40`. | La identidad se resuelve leyendo local_execution_jobs antes de autorizar persistencia; no basta un token remoto declarado por el cliente. |
| Persistencia de eventos | `persistence/result_repository.py:98` (`acceptance_scope`), `:138` (`_authorize`). | `experiment_require_owner()` lee el gate; su versión de 20260915 admite owner Local sólo con job retenido. Después verifica sesión/run/linaje. |
| Guard previo a reserva | `execution/schema.py:76` (`require_e10_schema`); `execution/repository.py:85`, `execution/controlled.py:99`, `local_execution/backend.py:71`. | El head exacto y capacidades E10 se verifican antes de nuevas reservas. No migra ni repara automáticamente. |
| Recuperación y entorno | `execution/controlled.py:140` (`effective_row`) busca petición controlled y, en su ausencia, train_execution_revisions. | Quitar el binding secuencial rompe selección del entorno legítimo aunque no existan requests controlled. |
| Mantenimiento | `scripts/maintenance/database.py:39` verifica jobs activos, `:43` gate libre; `protected_resources.py:11` clasifica tablas técnicas. | Operaciones administrativas también dependen de esos nombres; no se ejecutaron aquí. |

Las rutas ML abreviadas de la tabla son relativas a `malaria_dl_local_project/src/malaria_dl/`. Los contratos [E10.3](../engineering/e10_execution_refactor/e10_3_postgres_result_repository.md), [E10.OP1](../engineering/e10_execution_refactor/e10_op1_preclaim_schema_guard.md), [E10.9](../engineering/e10_execution_refactor/e10_9_training_results.md) y [E10.10](../engineering/e10_execution_refactor/e10_10_completion_verification.md) explican persistencia, autorización y completion. Sus estados operativos históricos no reemplazan el baseline vigente: la revisión E10 ya está aplicada en la captura E10.10.1.

Ninguna de las seis tablas se sustituye por el nuevo stream E10. `experiment_execution_events` registra coordinación; `train_execution_records` registra evidencia TRAIN y eventos de resultados; `train_execution_revisions` registra el entorno técnico del intento. Son responsabilidades complementarias.

## Otros objetos heredados o potencialmente retirables

| Objeto | Clasificación | Evidencia actual | Decisión pendiente |
| --- | --- | --- | --- |
| `schema_migrations` | LEGACY_REQUIRED | Ledger histórico conservado, leído por preflight de adopción; 22 checksums coinciden con archivos locales. main de init_db está retirado, no sus funciones de reconstrucción. | Mantener trazabilidad y documentar bootstrap autorizado; no eliminar ni unificar. |
| `model_governance_backfill_audit` | LEGACY_REQUIRED | SQL 023 crea auditoría append-only; 027 endurece vínculos y constraints; la función prevent_model_governance_audit_mutation prohíbe modificar historial. Sin productor runtime periódico acreditado. | Preservar contrato de backfill/revert; no confundir ausencia de filas con permiso de retiro. |
| Filas legacy de `train_execution_records` | LEGACY_REQUIRED dentro de tabla ACTIVE | `execution_record_readers.py:8`, `ExecutionRepository.records/legacy_records` y completion mantienen hashes/lectura anteriores. | Mantener discriminación por event_id y compatibilidad de records_hash. |
| `synthetic_data_runs` | UNDETERMINED | SQL `001_schema.sql:243`, FK a datasets/runs; referencias administrativas, sin consumidor runtime localizado. | Identificar responsable y contratos de generación sintética/clientes externos antes de considerar retiro. |
| `legacy_cell_predictions` | UNDETERMINED | Vista renombrada, filtrada sobre predictions; sin consumidor runtime ni vista dependiente localizada. | Verificar compatibilidad externa; el nombre legacy no demuestra obsolescencia. |
| `inference_runs` | UNDETERMINED | Vista sobre runs y run_model_deployments; sin consumidor runtime localizado. | Validar API/consultas externas antes de retirar alias. |
| Ocho vistas auxiliares indicadas abajo | UNDETERMINED | Sin consumidor runtime ni dependencia desde una vista ACTIVE localizada. | Revisar consultas manuales/BI/notebooks, compatibilidad y responsable funcional. |

Las ocho vistas son `vw_dataset_split_images_summary`, `vw_explainability_gallery`, `vw_false_negative_cases`, `vw_false_positive_cases`, `vw_low_confidence_cases`, `vw_run_dataset_usage_summary`, `vw_run_image_predictions_summary` y `vw_run_io_summary`. Las pantallas de falsos positivos/negativos y galería acceden actualmente a `vw_visual_explainability_audit` mediante `VISUAL_AUDIT_VIEW`; no asumir consumo de la vista antigua por el nombre del endpoint.

Las 17 vistas restantes tienen consumidor runtime directo o cadena hacia una vista activa, incluida `vw_case_level_explainability` a través de `vw_case_type_summary` y `vw_uploaded_predictions` a través de `vw_clinical_inference_predictions`. Sus dependencias completas se listan en ownership. Esto acredita contratos de código, no frecuencia de consultas ni rendimiento.

`identity_evidence` y `dataset_materialization_activations` **no se proponen para retiro**: el proyecto `malaria_dataset_split_project/src/malaria_split/persistence/bootstrap.py:485` escribe evidencia y `:608` consulta activaciones; pertenecen al dataset protegido. Son ACTIVE aun si una tabla está vacía o no aparece en el backend clínico.

## Condiciones para cualquier decisión futura

Antes de clasificar un objeto como OBSOLETE_CONFIRMED haría falta una decisión funcional de retiro, un inventario de clientes externos/consultas dinámicas y el análisis de dependencias entrantes, funciones y conservación de evidencia. Cualquier migración futura deberá ser nueva en Alembic, considerar el guard de revisión E10 y respetar backups/política de recuperación. Este informe no autoriza esa migración ni propone ejecutar un DROP.

El dictamen cierra la investigación de las seis tablas con evidencia positiva. Las incertidumbres sobre vistas auxiliares, generación sintética y ownership administrativo son decisiones documentadas, no impedimentos para cerrar este diagnóstico. No se realizaron escrituras SQL, pruebas clínicas, cambios al dataset ni E10.10.3.
