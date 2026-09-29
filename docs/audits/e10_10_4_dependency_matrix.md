# E10.10.4 — Matriz de dependencias y compatibilidad
> Actualización E10.10.5A: A-01 fue aprobada por el usuario. La sección final documenta la enmienda; el cuerpo original conserva su contexto histórico. Implementación y límites actuales: [e10_10_5_implementation.md](e10_10_5_implementation.md).

**Lectura estática; cambios futuros.** Las rutas ML abreviadas se resuelven en `malaria_dl_local_project/src/malaria_dl/`. [CSV](e10_10_4_schema_matrix.csv) inventaría las 97 tablas con PK/FK/CHECK/índices/triggers/funciones, cardinalidad capturada y localizadores completos de código y migraciones. No hay acceso SQL desde React.

## 1. Matriz de consumidores y cambios

| Componente real | Escritura / lectura actual | Cambio requerido v2 | Contrato/prueba futura |
| --- | --- | --- | --- |
| backend_api/app/models/cell_detection.py | Modelos de dominio; el directorio models no representa todo el catálogo SQLAlchemy | Mantener clínica; no usar autogenerate sobre metadata incompleta como baseline | Comparar SQL real, DTO y schema; todos los objetos de catálogo inventariados |
| backend_api/app/db y configuración de datasource | SQLAlchemy engine y transacciones read-only | Una conexión canónica; no fallback a archivos/base antigua | Rutas desconocidas rechazadas; tests de configuración sin conectar producción |
| persistence/run_repository.py | start/update/finish_run, métricas EAV, history, confusion_matrices/classification_reports, predicciones/artefactos | Escritores de matrices/reportes cambian a evaluación+medición; extensión EAV reservada; mismo scope transaccional | Evitar safe_track para resultado canónico; contratos de callbacks/legacy resueltos |
| persistence/tracking.py | args_to_parameters, start_tracking_run, log_training_results, wrappers y JSON serializado | Resolver columnas desde effective config; no duplicar stable metrics en 3 tablas | Casos de overrides/aliases y JSON desconocido; round-trip |
| persistence/model_configuration.py | UPDATE runs.execution_parameters.model_configuration_e2 y lectura fresca | Insertar configuración tipada congelada en transacción autorizada; conservar snapshot para guards | Hash/columnas/JSON consistentes antes del fit |
| models/configuration.py, registry.py, optimizers.py, adapters.py | Precedencia, registry, optimizer y preprocessing por arquitectura | Sin cambiar ciencia; adaptar sólo DTO persistido | Custom/VGG/DenseNet, Adam/AdamW/SGD/Adadelta y fine tuning |
| training/cli.py, training/trainer.py | Configuración, selección, artefactos, curvas, resultado final; Docker/Python | Emitir misma evidencia, usar proyección tipada; no introducir consulta directa del local a otra DB | Unit contracts con runtime fake, sin ejecutar TRAIN |
| execution/contracts/context.py, events.py, reporter.py y execution/emitter.py | ExecutionContext/RunEvent/RunEventEmitter/RunReporter | Mantener identidad, payload y canonicalización | event_id y sequence estables, schema_version vigente |
| results/service.py, results/training.py | Valida v1 zero_division=0, materializa training_results | Mapper binary_nullable_v2 conserva v1; no modificar evento ya recibido | Métrica indefinida→NULL sólo en proyección; tasas definidas coinciden |
| persistence/result_repository.py | acceptance_scope con gate/session locks; append + UPDATE JSON | Misma conexión: append + evaluations + clinical_metrics/history | Atomicidad ante error a mitad, commit fallido y ACK perdido |
| results/identity.py | Canonical event/hash, compatibilidad | Sin reserializar ledger ni cambiar digest | Fixtures legacy y actuales |
| execution/reporters/docker.py | Reporter directo vía composición | Mantener ResultService; v2 como adapter persistencia | Tests Docker reporter sin entrenamiento real |
| execution/reporters/http.py | Retry, comunicación y estado remoto | Mismo event envelope, ACK sólo después del commit | Replay, timeout, owner inválido y evento conflictivo |
| backend_api/app/routes/local_execution.py | /events, /event-state, dispatch /{operation} | Seleccionar backend compatible por capacidad v2 | Auth System Admin y fencing intactos |
| local_execution/backend.py, event_backend.py, event_context.py | Reserva/heartbeat/record/exit y resolución identity | Conservar jobs/gate/retención hasta salida; proyección cambia internamente | calculation_reported no libera; recovery después de caída |
| execution/repository.py, completion.py y lectores del ledger | Claim, legacy records, verificación del resultado y checkpoint | Leer evaluación por origen, serializar vista v1 sólo para comparar evidencia; no JSON fallback heterogéneo | completed exige exactamente la misma evidencia técnica |
| execution/global_gate.py | Singleton owner/PID/process_evidence + eventos | Sin consolidación ni retiro | Exclusión global TRAIN/assessment/local; owner perdido y OOM |
| execution/controlled.py | Revision y reserve controlled idempotentes | Conservar request/revision/bindings diferidos | Reintento autorizado único sobre paused |
| campaigns/repository.py y execution/campaign.py | Campaña/member/attempt/config snapshot | Tipado por run no sustituye hash contrato de campaña | Trazabilidad y exclusión sin mezclar seeds/reintentos |
| assessment/contracts.py, service.py, repository.py, runtime.py | Identidad evaluate/explain, final locks, results/artifacts | Preservar payload; proyección E/M/predictions/XAI en misma transacción de resultado aceptado | TEST final, val desarrollo, SHAP background TRAIN; no selección por TEST |
| evaluation/* lineage services | EVALUATE asociado a TRAIN/model/checkpoint | evaluation_id explícito para lectura científica; preservar run EVALUATE de publicación | Linaje y publicación sin nuevo gate |
| governance/repository.py, services/training_model_version_finalizer.py | Model/version/artifact/snapshots | Misma finalización; evaluar model_version nullable hasta existir realmente | No crear versión prematura para satisfacer FK |
| governance/services/stage2_publication_service.py | Publish/status/reactivate/deactivate | Incorporar FK compuesta; conservar _eligibility | TRAIN completed + EVALUATE completed, sin recall ni XAI requerido |
| backend_api/app/services/training_summaries.py:309 | JSON científico precede fallbacks heterogéneos | Leer evaluación final/M por run, métricas nullable y phase explícita | Misma precedencia conceptual del checkpoint final, no epoch mezclada |
| backend_api/app/services/run_lineage.py | Vistas lineage / métricas | Joins por evaluación/version, sin multiplicar por artefactos | Hijos TRAIN/EVALUATE/EXPLAIN completos |
| backend_api/app/routes/runs.py | /runs, /training-summaries, clinical-summary, history, matrices/reportes | DTO v2, métricas desde proyección, adaptar escrituras ausentes | Rutas compatibles en lectura; cambio de nullability versionado |
| backend_api/app/routes/metrics.py | /metrics/{run_id}, /confusion-matrix/{run_id}, /classification-report/{run_id} leen las tres tablas directamente | Métricas desde vista v2; matrices/reportes derivados y evaluación/split explícitos | frontend/src/services/api.ts:1363; orden e identidad por clase, aliases legacy y NULL |
| backend_api/app/routes/dashboard.py, catalog.py | vw_run_dashboard/model_run_summary | Redirigir agregados legacy a proyección canónica y aliases conocidos | No contar de nuevo EAV+medición ni reintentos |
| backend_api/app/services/dataset_browser.py | Summary sobre dos raíces e inventario global | Separar scientific_summary y physical_roots; root explícita | Dos raíces/orden permutado/suma clases estable |
| backend_api/app/services/governed_datasets.py y dataset_versions routes | Version/materialización/assignments | Mantener autoridad científica; sin refreeze ni hashes nuevos | UUID y 22.180/2.693/2.685 conservados |
| inference/predictor.py / inference/traceable.py | Predicción e imágenes XAI, SHAP zero+input | Preservar ruta y provenance; extender numeric artifacts futuro | Registrar salida explicada real; no asumir background TRAIN |
| explainability/pipeline.py + gradcam.py/shap_explainer.py/lime_explainer.py | Algoritmos/exports, figuras y arrays en memoria | Instrumentación de evidencia/versiones/artefactos numéricos, sin alterar algoritmos | Comparar números antes/después en etapa futura sintética |
| backend_api/app/services/case_gradcam.py | Modelo/checkpoint acreditado, PNG artifacts, explainability_results | Enlace a xai_evidence y manifesto; conservar resultados existentes | No generar por GET; reproducibilidad incompleta visible |
| backend_api/app/services/cell_classification.py, repositories/cell_classification.py | Inputs, predicciones, summary/reviews y Grad-CAM celular | Mantener cadena clínica; extensión XAI específica, sin habilitar SHAP/LIME celular implícitamente | Distinguir resultado automático, reviewed y explicación |
| backend_api/app/services/cell_explanation_storage.py | Stage/promote PNG, hashes y cleanup | Conservar claves existentes; anexar NPY sólo en implementación autorizada | Fallo filesystem/DB, disponibilidad missing y no sobrescritura |
| backend_api/app/routes/explainability.py | Casos/galerías/FP/FN, POST Grad-CAM | Lecturas v2 por evidencia/imagen/método, links autenticados | Paginación por evidencia, filtros y método disponible |
| backend_api/app/routes/cell_classification.py | Predicciones/reviews/explanations/content | Añadir metadatos reproducibles sin confundir scope clínico | ACL existentes; URI externa no expone rutas privadas |
| backend_api/app/services/microscopy_analysis.py / cell_analysis.py | QC/detección/crops/estado | KEEP; lectura de XAI por cadena existente | Caso→imagen→QC→crop→prediction→review |
| frontend/src/services/api.ts | Contratos HTTP centrales | Tipos Evaluation/Configuration/XaiEvidence y nullable metrics | Parser y errores versionados; sin payloads JSON heterogéneos |
| frontend/src/pages/ModelComparison.tsx | Comparaciones/modelos | Filtros arquitectura/optimizer/seed/protocolo/split, NULL y denominadores | Evitar pooling entre splits/cohortes, n de seeds correcto |
| frontend/src/pages/Runs.tsx y RunDetail.tsx | Resumen y detalle/training history | Mostrar config efectiva, etapas, threshold, checkpoint y métricas finales | Epoch no reemplaza final; TEST sólo informativo |
| frontend/src/components/reports/TrainingRunGroupCard.tsx, RunSummaryRow.tsx, RunLineageChildCard.tsx | Resúmenes y linaje | Adaptar métricas nullable, IDs evaluación y origen | Render sin ??0 y sin pérdida de estados |
| frontend/src/pages/Explainability.tsx | Galería y casos | Comparador Grad-CAM/SHAP/LIME con método/version/target/background y disponibilidad | No declarar validación clínica de heatmap |
| frontend/src/components/explainability/CaseExplainabilityView.tsx, explainabilityCaseAdapters.ts | Caso XAI bajo demanda | Distinguir numeric/visual, generated/quantitative/interpreted/reviewed | Sin botón de método no implementado en esa ruta |
| frontend/src/pages/SmearWorkflow.tsx, SmearAnalysisHistory.tsx; hooks useSmearAnalysis* | Proceso/historial clínico | Reusar APIs; enlaces XAI por predicción, interpretación/revisión separadas | Historia no mezcla experimentos con pacientes |
| frontend/src/components/cell-review/SmearAnalysisResultsView.tsx, SmearAnalysisImmersiveView.tsx | Resultados/revisión celular | Etiquetas de resultado asistido y evidencia XAI | No promover predicción a diagnóstico confirmado |
| frontend/src/pages/ModelVersions.tsx y components/deployments/ActiveStage2Model.tsx | Publicación y disponibilidad | Campos de linaje legibles; misma elegibilidad | Publicación válida aun sin XAI/recall meta |
| frontend/src/pages/DatasetBrowser.tsx, UploadedPredictions.tsx, Deployments.tsx | Versión oficial vs inventario para inferencia | Mostrar raíz/versión, usar summary nuevo donde corresponda | 55.116 nunca presentado como universo científico oficial |
| execution/schema.py | Head exacto + capabilities E10 | Guard v2 con allowlist y nuevas capacidades | Desconocido/dañado rechazado antes de claim |
| alembic/env.py, scripts/db/*, Makefile | Bootstrap/upgrade/preflight mixto | Entorno v2 integral, dos rutas separadas y manifest | No SQL histórico en Ruta A; checksums legacy en B |

Los nombres de archivos son localizadores, no garantías de que cada ruta ya tenga la interfaz v2. El lector debe consultar la lista de URLs reales en routers: la propuesta no crea ni renombra endpoints en esta etapa.

## 2. Incompatibilidades API explícitas

| Contrato | Cambio | Compatibilidad propuesta |
| --- | --- | --- |
| Métricas v1 obligatorias | recall/specificity/precision/F1/F2/BA pueden ser NULL v2 | DTO v2 con metric_definition/undefined_reason; mantener evento v1 intacto. No emitir silenciosamente NULL bajo schema v1 estricto. |
| /training-summaries | Fuente JSON → evaluación final relacional | Conservar nombres de respuesta vigentes mediante adapter donde puedan expresarse; versión nueva para nullability. |
| confusion_matrices | Tabla escribible → vista derivada | Lectura forma compatible, escritura sólo nuevo ResultService; clientes INSERT antiguos deben actualizarse antes del corte. |
| classification_reports | UUID por fila → clave evaluación/clase, macro/weighted derivados | Versionar endpoints/DTO que dependan de ID único. Nunca reutilizar id de medición como si fuera único por clase. |
| dataset physical summary | Objeto agregado ambiguo → scientific_summary + physical_roots[] | Nuevo contrato/version; no reemplazar field total=55116 por 27558 sin indicar distinto alcance. |
| XAI | output_path aislado → evidencia y colección de artefactos | Mantener URLs content autorizadas; anexar detalles versionados, no exponer storage_uri cruda sin autorización. |
| Run detail parameters | Resultados/config ya no se leen de parameters | Entregar configuration/result como recursos explícitos; fallback legacy limitado a evidencia identificada, no COALESCE indiscriminado. |
| Métricas EAV | Métricas estables dejan de insertarse en run_metrics | Vistas/servicio de lectura derivan aliases; consultas directas al EAV se migran. |

## 3. Consolidaciones y cobertura de contratos

| Objeto actual | Destino | Escritores a trasladar | Lectores a adaptar | Riesgo / prueba |
| --- | --- | --- | --- | --- |
| confusion_matrices | M.tn/fp/fn/tp + vista | run_repository.log_confusion_matrix y callers tracking/training/evaluation | training_summaries, runs detail y tests de matrices | Misma orientación TN/FP/FN/TP, n y split; no aceptar matriz de checkpoint distinto |
| classification_reports | Vista por clase/DTO macro-weighted | run_repository.log_classification_report y callers | runs detail/report API/frontend | Diferencia ID/NULL; cobertura clase positiva/negativa y promedios |
| runs.parameters.training_results | E + M | PostgresResultRepository.project_training_result | summaries + completion/recovery | Evento/proyección atómicos, hashes v1 intactos |
| runs JSON configuración estable | run_configurations + snapshot evidencia | reserva/model_configuration/tracking | summaries/preflight/recovery | No contradicción entre seed/optimizer y contrato congelado |

No se retira ninguna de las seis tablas técnicas ACTIVE ni predictions/cell_predictions: tienen scope y contratos distintos. `legacy_cell_predictions` e `inference_runs` son vistas de uso externo no acreditado y se conservan; no se clasifican como tablas retiradas. Las vistas legacy que agregan run_metrics requieren adaptación de aliases y selección de evaluación final; no usar sólo UNION y luego MAX para mezclar final y calibración. Se propone redirigir endpoints a servicios de lectura v2 y dejar las vistas antiguas como compatibilidad revisada.

## 4. Criterios de aceptación de integración

- Mismo evento por Docker/HTTP produce la misma fila E/M y ACK, sin depender de modo de ejecución.
- Resumen final jamás se mezcla con epoch, otra raíz, otro split o intento abandonado.
- El fallo de métrica/FK/proyección revierte también el evento; pérdida de ACK no duplica.
- Curvas y recursos no medidos se muestran ausentes, nunca como cero.
- Comparación XAI filtra misma entrada/crop y salida/clase; método/version/background visibles.
- Historial clínico mantiene predicción automática y revisión humana separadas.
- Publicación conserva regla funcional y añade sólo coherencia declarativa de TRAIN de la versión.
- No usar tests PostgreSQL existentes sin aislar su target y asegurar que no disparen workflows científicos.

## Enmienda A-01 aprobada — 2026-09-29

**A-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5A PUEDE REANUDARSE.** Autorización explícita del usuario, limitada a diseño, baseline y validación estática; no autoriza B ni cutover. El texto anterior conserva la decisión original. Sus hashes y la definición original de evaluations están en [e10_10_5a_design_before_a01.json](e10_10_5a_design_before_a01.json); el bloqueo original se conserva en [e10_10_5a_initial_block.md](e10_10_5a_initial_block.md).

- `evaluations.split` admite `external` además de los tres splits oficiales. `external_validation` permanece intacto en el dataset protegido; no se crea un alias ni mapping automático.
- Ámbito (`split`), población (`population_hash` y manifiesto), origen (`dataset_origin_id`, `dataset_origin_role` y evidencia de procedencia), protocolo (`protocol_hash/version/snapshot`) y finalidad (`purpose`) son conceptos independientes.
- External exige `purpose=complementary`, `evaluation_role=external_complementary`, manifiestos de población/procedencia recuperables con SHA-256 y FK a la PK existente `(dataset_version_id,dataset_id,role)` del origen registrado en `dataset_version_sources`, sin añadir UNIQUE al dominio protegido. La versión evaluada puede diferir de la versión de entrenamiento; se conserva íntegro el linaje TRAIN/checkpoint/modelo. No se crean versiones ni fuentes ficticias para completar esa FK.
- `source_kind=external_record` identifica nuevas entradas externas; `legacy` permite adopción con evidencia suficiente. No se hace pasar una entrada externa por evento E10 ni por assessment cuyo contrato actual sólo admite splits oficiales.
- Se prohíbe usar external como calibración, selección de checkpoint/modelo, VALIDATION sustitutiva o agregado TEST oficial. Los roles y la finalidad lo impiden en evaluations, el par de calibración exige val, y `vw_v2_model_comparison` sólo contiene train/val/test. `vw_v2_external_evidence` expone evidencia complementaria sin agregación, con población, protocolo y procedencia. El catálogo pasa de 32 a **33 vistas**; mantiene **103 tablas**.
- `run_clinical_metrics.split_name` sigue representando `external`; su trigger lo deriva de la evaluación externa trazada. Se conservan el lector/escritor legacy en la aplicación operativa. Adaptar esos escritores al contrato transaccional v2 corresponde a E10.10.5E: esta enmienda no afirma compatibilidad binaria de INSERT antiguos que carezcan de evaluation_id.
- La existencia de un URI/hash no certifica disponibilidad o validez científica del manifiesto. La adopción abortará sin mapping si falta evidencia; los servicios deben verificar procedencia y políticas de selección. No se modifican imágenes, asignaciones ni hashes históricos.
