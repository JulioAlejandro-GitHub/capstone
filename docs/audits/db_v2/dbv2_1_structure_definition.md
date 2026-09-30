# DBV2.1 — Propuesta estructural completa

Estado: propuesta pendiente de **GATE DBV2.1**. Diseño para PostgreSQL 17.9 vacío. No constituye una baseline congelada ni certificada. No se ejecutó SQL, no se accedió al PostgreSQL operativo y no se modificaron Alembic, adoption_v2, dataset, usuarios o consumidores.

## Contrato documental

La definición completa está formada por este documento, el [SQL autónomo de diseño](dbv2_1_target_schema.sql), las [104 fichas por tabla](dbv2_1_table_details.md), el [catálogo de columnas](dbv2_1_columns.csv), las [relaciones](dbv2_1_relationships.csv), la [matriz de decisiones](dbv2_1_table_matrix.csv), los [índices](dbv2_1_indexes.md), las [funciones y triggers](dbv2_1_functions_triggers.md), las [vistas](dbv2_1_views.md) y el [ER completo](dbv2_1_er_diagram.md). Las fichas incluyen tipos, nulabilidad efectiva, defaults/generación, PK, UNIQUE, CHECK, FK y acciones de borrado, auditoría y provenance. Los triggers definen garantías entre filas que no caben en CHECK.

El SQL contiene las formas finales de las tablas, no una secuencia de conversión desde legacy. No importa archivos históricos, no requiere sus datos ni ejecuta adoption_v2. DBV2.2 podrá convertir esta especificación, tras aprobación, en una única revisión `pg_v2_baseline`, `down_revision = None`.

## Fuentes inspeccionadas y criterio

- `alembic_v2/baseline/01_prerequisites.sql` a `11_technical_state.sql`, manifiesto, `e04_contract.sql` y README: catálogo candidato, funciones reales, constraints y privilegios.
- `adoption_v2/README.md`, contratos y herramientas existentes: contexto de adopción; no son dependencia del objetivo nuevo ni procedimiento propuesto para datos experimentales.
- `docs/audits/e10_10_4_postgresql_v2_architecture.md`, matriz, SQL y ER: entidades, responsabilidades y diferenciación de poblaciones oficiales y raíces físicas.
- `docs/audits/e10_10_5e4_resolution.md` y `e10_10_5e5_decision.md`: E-04 resuelta y origen del conflicto E-05. La nueva instrucción aprobada sustituye la alternativa histórica que fijaba 0,98.
- `backend_api/app/routes/auth.py`, `security.py`, funciones de dataset y definiciones candidatas: usuario funcional, roles, password_hash y dependencias de transferencia.
- Repositorios de persistencia de runs/calibración y contrato de configuración de campañas: columnas efectivas frente a snapshots y linaje.

[Checksums de fuentes](dbv2_1_source_evidence.json) sirven únicamente para comprobar que estos archivos permanecen intactos. No promueven ni sustituyen hashes de baseline.

Se conserva una entidad cuando representa un concepto distinto con relaciones útiles; el número de tablas no se reduce eliminando trazabilidad o mezclando procesos. `assessment_*` representa identidad/intento técnico, `evaluations` representa contexto científico y `run_clinical_metrics` su medición clínica. No son tres copias del mismo resultado. `cell_explanations` y `explainability_results` conservan solicitudes/estado de generación y resultados de sus rutas; `xai_evidence` identifica la evidencia reproducible que puede enlazarlas. No se crea `xai_explanations`.

## Resumen de catálogo

104 tablas de aplicación propuestas: **78 KEEP, 22 MODIFY, 4 NEW**. Se retiran **2** tablas candidatas; **2 VIEW** registran la conservación como vistas de conceptos que eran tablas legacy. La matriz tiene 108 filas y no suma VIEW o REMOVE como tablas físicas nuevas.

251 FK; 518 CHECK; 77 constraints UNIQUE más 41 índices UNIQUE explícitos; 104 PK. 232 índices explícitos y 181 implícitos de PK/UNIQUE: **413 índices**. 79 funciones propias, 105 triggers y 33 vistas normales. No se cuentan funciones de extensión ni índices internos TOAST.

Alembic administrará aparte `alembic_version(version_num varchar(32) NOT NULL, PRIMARY KEY(version_num))`: una tabla técnica adicional, total físico esperado **105** una vez instalada la futura baseline. No se declara manualmente en el SQL para no colisionar con Alembic. Tampoco se incluye en el denominador de aplicación de las métricas anteriores.

## Cobertura de dominios

| Dominio | Representación propuesta |
|---|---|
| A Usuarios / seguridad | users, roles, user_roles; auditoría mediante audit_events |
| B Dataset | datasets, clinical_identities, identity_evidence y todas las dataset_* |
| C Imágenes / pacientes / splits | research_subjects → scientific_cases → blood_samples → smear_slides → microscopy_images; ingestión, análisis, detección, clasificación, predicciones y validación científica existentes |
| D Modelos | models |
| E Model versions / checkpoints | model_versions, artifacts, run_checkpoint_policy; no nueva tabla checkpoint |
| F Experimentos | experiments |
| G Runs | runs, run_lineage |
| H Run configurations | run_configurations, 1:1 por run_id; requerida para TRAIN por trigger diferido |
| I Campañas | experimental_campaigns, campaign_configurations, campaign_members, campaign_attempts y revisiones/eventos/solicitudes existentes |
| J TRAIN / execution ledger | train_execution_sessions, train_execution_records, train_execution_revisions, training_history, experiment_execution_gate/events, local_execution_jobs |
| K Evaluaciones | evaluations; assessment_* registra identidad, intentos, resultados y artefactos técnicos |
| L Métricas clínicas | run_clinical_metrics; run_metrics para medidas extensibles; confusion_matrices y classification_reports son vistas |
| M Calibración | run_threshold_calibration y su pareja de evaluations E-04 |
| N Ensembles | evaluation_ensemble_members, N:M con model_versions; pesos y checkpoint explícitos |
| O XAI | nueve tablas xai_*; contextos de generación existentes enlazables |
| P Publicación / deployment | stage2_model_publications/events, deployed_model_versions, run_model_deployments |
| Q Auditoría y trazabilidad técnica | audit_events, execution_logs, errors, environment_packages, run_io_records; registros técnicos anteriores sin duplicación |

## Cambios respecto de la candidata

1. `run_configurations.clinical_target_recall numeric NOT NULL`, sin default, con `0 < valor <= 1`. Se modifica también el CHECK de calibración que fijaba `target_recall=0.98`; conserva `calibration_split='val'` y `default_threshold=0.5`. El valor 0,98 queda en configuración SW, sin política numérica fija en DB.
2. La configuración inmutable debe concordar con `canonical_configuration.execution.target_recall`; la calibración debe concordar con `run_configurations.clinical_target_recall`. E-04 ya verifica concordancia de evento y calibración. Cambiar el objetivo exige otra configuración/run, nunca reescribir historia.
3. Se normaliza identidad XAI en cuatro entidades nuevas. Se sustituyen configuración embebida y comparación binaria rígida por FK de configuración, protocolos y membresía N:M. El detalle está en el [modelo XAI](dbv2_1_xai_model.md).
4. Se elimina `schema_migrations`: los checksums de migraciones SQL históricas no participan en una instalación nueva. Se elimina `model_governance_backfill_audit` y su función/trigger: representa remediación legacy; su evidencia permanece en el archivo histórico, no se migra ni se borra del origen.
5. Se cambia CASCADE/SET NULL a RESTRICT donde borrar padres destruiría evidencia, metadatos de ejecución, predicciones o procedencia. Sólo permanecen cascadas de `user_roles`, una asociación de seguridad sin significado propio. No se cambia el contenido científico del dataset.
6. Se conservan las 33 vistas; `vw_v2_xai_comparison` consulta la nueva configuración por FK. Dos índices XAI existentes se adaptan y cuatro se agregan. Se eliminan los tres índices del backfill retirado.

## Invariantes E-04 y límites científicos

Se preservan **exactamente** las definiciones del overlay `e04_contract.sql`: admisión legacy por migrador autenticado, pareja default/selected, roles, evento, población, dataset, modelo/checkpoint, protocolo/snapshot, input contract, umbrales, métricas, índices de unicidad NULL-safe y validación diferida al COMMIT. Se conserva la inserción en cualquiera de los órdenes válidos. No se reabre E-04; ampliar el dominio del objetivo no cambia esas invariantes.

VALIDATION sigue siendo la población de calibración. TEST no es selección de modelo ni checkpoint. Evaluación externa exige procedencia/población y conserva sus restricciones de uso complementario. Las publicaciones siguen el contrato TRAIN completed + EVALUATE completed; no se agrega gate de recall, XAI ni acuerdo entre métodos.

`clinical_target_recall`: válidos 0.95, 0.98, 0.99, 1.00; inválidos 0, -0.1, 1.01, NULL. El CHECK combinado con NOT NULL representa exactamente el dominio aprobado. No se escribe un resolver ni productor SW.

## Tipos, relaciones, JSONB y auditoría

Se conservan UUID y timestamps del contrato existente. Las claves de identidad no se actualizan; todas las FK omiten ON UPDATE o declaran NO ACTION (mismo efecto). El CSV de relaciones enumera cada FK, opcionalidad, cardinalidad máxima y diferibilidad. Una relación 1:1 permite cero hijos salvo regla de completitud explícita; PK compuestas materializan N:M.

Columnas que identifican, participan en FK, comparaciones o reglas científicas son relacionales. JSONB queda para parámetros extensibles, snapshots de entorno/configuración/eventos y metadatos auxiliares. Los snapshots canónicos preservan procedencia y bytes hash; no se consideran otra autoridad editable sobre las columnas tipadas. E-04 requiere snapshots históricos concretos; eliminarlos rompería la trazabilidad ya resuelta.

Los campos `created_at`, `generated_at`, `evaluated_at`, actores y equivalentes están inventariados por tabla. No se presupone auto-update de `updated_at` por su nombre. Las asociaciones sin reloj propio heredan auditoría del padre. Evidencia XAI, membresía, protocolos y configuraciones son append-only; la disponibilidad física de un artefacto admite cambio sin cambiar su identidad.

## Borrado y seguridad

RESTRICT conserva linaje. Para retirar usuarios se utiliza status/disabled_at; un usuario autor de evidencia o auditoría no se borra porque existan FK restrictivas. Si se borra una cuenta sin evidencia, `user_roles` puede desaparecer con ella. Padres científicos se archivan mediante estados; no existe autorización implícita para borrar campañas, runs o archivos.

DBV2.2 mantendrá los roles `capstone_v2_migrator` y `capstone_v2_runtime`, sin privilegios elevados ni memberships, propietario migrador y runtime sin DDL, TEMP, TRUNCATE o escritura de alembic_version. PUBLIC no accede al esquema ni ejecuta funciones propias. Runtime tiene SELECT/INSERT en nuevas entidades XAI y ejecución de guardas; UPDATE/DELETE de evidencia sigue prohibido por triggers. Se conservará la ACL E-01 de objetos retenidos; las funciones retiradas no reciben grants. Provisionar roles es responsabilidad del entorno futuro, nunca del esquema científico ni del runtime.

El singleton vacío de `experiment_execution_gate` debe inicializarse en DBV2.2 con `(true,NULL,NULL,'{}',NULL)` para singleton/owner/db_pid/process_evidence/blocked_reason. Es estado técnico, no dataset ni evidencia experimental. No se ejecuta ni se agrega DML de instalación en DBV2.1.

## Validación y gate

[Resultado estático](dbv2_1_static_validation.json). Ejecución reproducible con pglast 8.4 instalado:

```sh
python3 scripts/db/validate_dbv2_1.py
```

Revalidación del 30 de septiembre de 2026: `PASS_STATIC_ONLY`, con coincidencia de todos los catálogos derivados y checksums de fuentes. El Python del sistema no tiene `pglast`; en esta estación se utilizó la instalación local existente, sin instalar dependencias ni conectar a PostgreSQL:

```sh
PYTHONPATH=/tmp/e10_10_4_sql_parser python3 scripts/db/validate_dbv2_1.py
```

La ruta temporal es específica de esta estación; en otro entorno debe estar disponible `pglast==8.4` para ejecutar el primer comando.

`--write` sólo regenera catálogos documentales derivados del SQL. Nunca instala ni ejecuta SQL. El parser usa gramática PostgreSQL 18.4; parseo SQL/PLpgSQL y revisión de relaciones no certifican runtime, concurrencia o instalación en PostgreSQL 17.9. Las pruebas de servidor corresponden a DBV2.2 después del gate.

Fuera de alcance: campañas, resolución .env, TRAIN/EVALUATE/EXPLAIN, Grad-CAM/SHAP/LIME, cálculo de métricas XAI, API/DTO/React, integración E2E, consumidores y cutover. No se inicia DBV2.2. Solicitud final: **GATE DBV2.1**.
