# CAPSTONE-DB-01 — Dependencias de código

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Inspección estática y lecturas acotadas.

## Alcance

[code_search_inventory.csv](code_search_inventory.csv) conserva cada coincidencia con archivo, línea, función/clase cuando es Python, capa, términos, categoría preliminar, impacto y recomendación. [search_coverage.json](search_coverage.json) identifica expresión, recuentos y exclusiones. Se buscaron todos los términos solicitados, sin distinguir mayúsculas, incluyendo subcadenas frozen/legacy/migration. Las coincidencias de documentación, pruebas, historial y scripts no se presentan como dependencias runtime confirmadas.

Se recorrieron 443 archivos runtime, 262 de tests, 523 de documentación, 65 de historial y 1.008 de scripts/configuración versionados. La búsqueda es un índice de investigación, **no una certificación semántica de todas las coincidencias**. Artefactos, datasets binarios, outputs y datos operativos quedaron fuera. La solicitud explícita de recorrer todos los proyectos prevaleció sobre la exclusión habitual del skill: se incluyó el código de `malaria_dataset_split_project`, sus interfaces y configuración, sin leer imágenes ni ejecutar su pipeline. No se ejecutaron scripts administrativos encontrados.

## Dependencias activas y hallazgos priorizados

Rutas ML relativas a `malaria_dl_local_project/src/malaria_dl/`, salvo indicación distinta.

| Archivo:línea / símbolo | Control / dependencias | Impacto y clasificación | Recomendación |
|---|---|---|---|
| execution/schema.py:78 require_e10_schema | pg_class, alembic_version, CAPABILITIES; revisions líneas 7–9 | C: bloqueo demostrado del head vigente | Retirar decisión por head; usar esquema actual. |
| execution/schema.py:19–74 CAPABILITIES | Expresión CHECK, índices y hash de train_event_guard | B en semántica; D en pinning exacto | Preservar integridad; no reemplazar por nuevas whitelists históricas. |
| persistence/schema_contract.py:16,33 load_contract/require_v2_capabilities | v2_runtime_contract.json, hashes/listas exactas pg_proc/trigger/constraint/index | D: coincide hoy, acoplamiento al baseline | Revisar si es verificación de despliegue y no requisito runtime permanente. |
| execution/repository.py:83,89 preflight_e10_schema/authorize | require_e10_schema; sesión y propietario | C para versión, B para autorización | Separar eliminación de etiqueta y conservación del fencing. |
| execution/repository.py:178,256 _create_run | Proyecta run_configurations solo en V2_REVISION | C: nueva etiqueta podría omitir configuración requerida por trigger diferido | Usar siempre proyección vigente. |
| execution/repository.py:284 bind_evaluation_context | Retorna None cuando revision != V2_REVISION | C: riesgo de perder contexto de checkpoint/evaluación | Usar contexto relacional vigente sin selector histórico. |
| persistence/result_repository.py:72,92,127 | Guard y ramas V2_REVISION para resultados/calibración; alternativa runs.parameters | C: escritura determinada por historia Alembic | Adoptar v2_projection directamente; conservar transacción evento→resultado. |
| backend_api/app/services/scientific_results.py:23 | Guard y rama legacy_e10_v1 | C: 503 con head vigente; lectura histórica si se parchea solo whitelist | Consultar tablas actuales; conservar run_id. |
| backend_api/app/routes/runs.py:21–34 | Traduce E10SchemaNotReady a 503 SCIENTIFIC_SCHEMA_NOT_READY | Dependiente de C; manejo HTTP válido | Actualizar al contrato directo, no ocultar fallos SQL. |
| backend_api/app/routes/health.py:24–34 ready | require_e10_schema y comprobación de destino | C para revisión: puede declarar database/migrations not_ready con conexión válida | Eliminar dependencia histórica; conservar conexión/destino/storage. |
| execution/campaign.py:216,379,442 | Preflight antes de ejecución/reserva | C heredada; B para datos/configuración | Corregir consumidor conjunto con repositorio. |
| local_execution/backend.py:95; execution/controlled.py:100 | Reutilizan guard E10 | C heredada en planos local/controlado | Cubrir ambos caminos en aceptación futura. |
| campaigns/plan.py:100 | Convierte fallo del preflight en check e10_schema | C heredada | Plan no debe marcar esquema vigente inválido por su etiqueta. |
| campaigns/service.py:139 + data/governed_dataset.py:64 | Solicita train/val y produce verified_requested_splits | B: evita exposición innecesaria de TEST | Conservar política por splits; alinear consumidor SQL. |
| campaigns/repository.py:50,281,325 | Sanitización, creación atómica y materialización; triggers campaign_* | B/D mixto; oculta código SQL específico bajo error genérico | Mantener atomicidad; mejorar diagnóstico seguro sin filtrar parámetros. |
| backend_api/app/services/campaign_configuration.py:154 | Dataset FROZEN/trainable; configure; traducción CampaignError | B para dataset; dependencia de DB-01 | Mantener trazabilidad y corregir presentación de fallo. |
| frontend/src/pages/CampaignConfiguration.tsx:50,55 | Convierte cualquier error en texto de contrato | D de presentación: envuelve el error genérico del repositorio; no identifica su causa | Distinguir network/timeout/http y códigos científicos. |
| backend_api/app/repositories/assessment_lineage.py:24 | visible_assessments solo evaluate | C: omite evidencia EXPLAIN vigente | Extender proyección a kind explain. |
| backend_api/app/services/training_summaries.py:58–74 | Contadores EXPLAIN solo desde run_lineage | C: cero pese a dos intentos verificados | Alinear contadores con identidades/intentos E6. |
| backend_api/app/services/lineage_children.py:25,174,423 | Hijos por run, explicación en explainability_results; todo assessment_e6 va a evaluations | C: SQL/serializador incompletos para EXPLAIN E6 | Corregir proyección y discriminación explícita. |
| backend_api/app/schemas/lineage_children.py:63,87; frontend/src/types/api.ts:355,414 | EXPLAIN exige run_id de ejecución separada | C: contrato de lectura insuficiente | Representar attempt_id/identity_id/training_run_id sin inventar runs. |
| frontend/src/pages/Runs.tsx:133,151 | Límite 100, cache por datasource/TRAIN y contadores de respuesta | B para identidad de respuesta; no causa del caso actual | Conservar verificaciones; ampliar representación E6 y pruebas de paginación. |
| explainability/pipeline.py:1217; assessment/cli.py:42 | src.explain delega a assessment, no a legacy run_lineage | B: productor vigente con identidad explícita | Consumir persistencia vigente en UI; no duplicar resultados. |
| assessment/repository.py:74,117,198,209 | Identidades, intentos, resultados, artefactos y consumidores de campaña | B | Conservar contratos/FK/propiedad; ausencia en runs no es pérdida de resultados. |
| persistence/execution_record_readers.py:8,17 | to_jsonb(record)->>event_id para tolerar columna ausente pre-E10 | C en tolerancia de esquema antiguo; B en ledger e identidad | Usar columnas existentes directamente; conservar acceso a evidencia histórica que siga presente. |
| backend_api/app/services/training_summaries.py:187,213; services/run_lineage.py | Fallbacks entre métricas, vistas y sesiones | D: conviven fuentes presentes, no columnas inexistentes demostradas | Medir uso y precedencia antes de retirar. La consulta de summaries funcionó. |
| backend_api/app/services/cell_classification.py:1544 _resolved_input_contract | Reconstruye input_contract para legacy_publication_v1 desde snapshot | D: compatibilidad de artefacto, no head SQL | Verificar publicaciones vivas antes de retirar; no cambiar identidad de modelo. |
| assessment/lineage.py:100–141 | legacy_registered_artifact y comprobación de checksum/propiedad | B para identidad; D para rama histórica | No eliminar por nombre legacy; comprobar uso vigente. |
| backend_api/app/database_safety.py:60–89 | Destino, prohibición de DROP y aislamiento de pruebas | A | Conservar. |
| smear_segmentation_project/src/smear_segmentation/dataset.py:35 read_records | dataset_split_assignments→dataset_source_records→clinical_identities | B; tablas/columnas consultadas existen | Conservar linaje; no ejecutar segmentación. |
| backend_api/app/services/cell_detection.py:53 y cell_classification.py | Snapshot de imagen/crop, estado, modelo publicado y revisión | B | Mantener relaciones con imagen/frotis y revisión humana. |

## Scripts, pruebas e historia

`scripts/maintenance/database.py:50–54`, `snapshot`, exige tabla exacta y revisión `20260922_01`, además del guard E10: C respecto de revisión histórica; inventario fijo D hasta revisar política. No es una ruta normal del backend y no se ejecutó. Su corrección necesita revisar operaciones destructivas que protege, no solo suprimir el chequeo.

`scripts/reset/reset3/verify_operational.py:20` y otros reset/probe/certify contienen heads históricos. Son procedimientos fechados o pruebas, no instrucciones a ejecutar contra la base actual. `scripts/db/apply_cell_activation.py`, herramientas de adopción y scripts Alembic se inspeccionan estáticamente; no constituyen evidencia del esquema instalado.

`malaria_dl_local_project/tests/test_schema_revision_contract.py`, `test_v2_runtime_contract_guard.py` y `test_e10_preclaim_schema_postgres.py` codifican expectativas de rechazo por revisión. En Fase 2 deben actualizarse junto con el contrato, preservando pruebas negativas de integridad y aislamiento. No se ejecutaron pruebas que escriban.

`alembic/`, `alembic.ini`, `alembic_v2/`, `alembic_v2.ini` permanecen intactos. La política del usuario permite retirarlos en fases posteriores; no se propone conservarlos como dependencia runtime. Cualquier eliminación debe revisar Makefile, Docker mounts y documentación, además de imports.

## Incompatibilidades y límites

Demostradas: DB-01 literal de evidencia; DB-02 selección por head; DB-03 omisión de assessments EXPLAIN. `to_jsonb(record)` demuestra tolerancia explícita de esquema antiguo, aunque hoy la consulta siga funcionando. Vistas con nombres históricos están **instaladas**: no asumir que son tablas ausentes ni eliminarlas antes de sustituir lectores.

Los logs contienen firmas de columnas inexistentes (`type_kind`, entre otras), pero no se identificó una consulta activa correspondiente en los caminos inspeccionados; pueden ser consultas manuales o pruebas. Se registran como pendientes y no se atribuyen al frontend. No se declara compatibilidad total de cada SQL dinámico, script o módulo del repositorio.

## Subsistema de particionado de datasets

- `malaria_dataset_split_project/src/malaria_split/persistence/database.py:8`, create_postgresql_engine: recibe la URL del llamador, normaliza driver y exige PostgreSQL; no fija head Alembic. A, conservar destino PostgreSQL y verificar configuración del llamador.
- `discovery/system_contract_auditor.py:102–109`: lee alembic_version como migration_state y contempla schema_migrations como alternativa. No exige revisión concreta. D para fallback histórico; mantener valor como información y simplificar alternativa si no tiene consumidor vigente. No usar esa lectura como criterio de validez.
- `persistence/models.py:3`: docstring declara Alembic como esquema canónico; contradice la política aprobada. C documental; corregir posteriormente a catálogo vigente, sin inferir estructura desde migraciones.
- `governance/trainability.py:95,107`: validaciones lógicas PASS, versión FROZEN y materialización READY/reconciliada; B, conservar coherencia científica.
- `governance/freeze.py:103`, _preflight: exige VALIDATED/FROZEN, checks formales y materialización; B. El conteo fijo 27.558 es D: verificar alcance específico del dataset antes de generalizar o retirar; no prueba una restricción de esquema.
- Persistencia usa dataset_versions, dataset_version_sources, clinical_identities, dataset_source_records, identity_evidence, dataset_split_assignments y materializaciones existentes. Inspección estática sin generar splits, congelar versiones ni ejecutar validaciones que escriban.
