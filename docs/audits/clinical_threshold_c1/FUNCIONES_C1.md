# C1 — Inventario de funciones y pruebas

Estado documental: `HISTORICAL_AUDIT`. 2026-10-04.

**Metodología: auditoría estática, sin ejecución de código, pruebas ni consultas PostgreSQL.**

Las rutas abreviadas `M/` corresponden a `malaria_dl_local_project/src/malaria_dl/`; `T/` a `malaria_dl_local_project/tests/`. Los números indican líneas del archivo leído. «Activa» significa ruta de invocación localizada (**CONECTADO**), no ejecución nueva acreditada. Persistencia describe operaciones **PERSISTIDO** en código. Ninguna prueba se ejecutó.

## Inventario del flujo canónico

| Archivo:línea | Función/clase | Responsabilidad | Entradas → salidas | Consumidor y estado | Persistencia |
| --- | --- | --- | --- | --- | --- |
| M/evaluation/threshold_calibration.py:54 | validate_calibration_split | Normaliza val/validation; rechaza test y otros | split → 'val' o ValueError | calibration_cli.main; activa | Ninguna |
| M/evaluation/threshold_calibration.py:63 | build_threshold_candidates | Finitez y clip sólo de candidatos; únicos más extremos/default | scores, include_default → list[float] ordenada | find_threshold_for_target_recall; activa | Ninguna |
| M/evaluation/threshold_calibration.py:113 | evaluate_threshold | Métricas a un umbral; beta sólo metadato | y_true, y_scores, threshold, beta → dict | buscador; activa | Ninguna |
| M/evaluation/threshold_calibration.py:126 | _selection_key | Ranking lexicográfico especificidad/precision/F2/BA/t | record → tuple | max de factibles; activa | Ninguna |
| M/evaluation/threshold_calibration.py:137 | _fallback_key | Anteponer recall al ranking anterior | record → tuple | max sin factibles; activa | Ninguna |
| M/evaluation/threshold_calibration.py:154 | find_threshold_for_target_recall | Calibración principal TRAIN | arrays, target_recall=.98, min_specificity=None, beta=2 → dict con umbral, métricas, flags y warning | execution.train.train; trainer.main legacy; calibration_cli.main; activa | No escribe por sí misma |
| M/evaluation/threshold_calibration.py:275 | write_threshold_calibration | Serializa resultado | ruta, dict → Path | trainer.main legacy; conectado allí | JSON local, no ruta normal de campaña |
| M/evaluation/threshold_calibration.py:285 | default_threshold_calibration_path | Ubicación de sidecar | output_dir → Path | trainer/calibration_cli | Ninguna |
| M/evaluation/clinical_metrics.py:32 | _safe_divide | Cociente, cero ante denominador cero | números → float | métricas y distribución | Ninguna |
| M/evaluation/clinical_metrics.py:39,50 | _safe_roc_auc / _safe_pr_auc | ROC-AUC / average precision; None sin dos clases o ValueError | etiquetas, scores → float/None | compute_clinical_metrics | Ninguna |
| M/evaluation/clinical_metrics.py:67 | clinical_probabilities_from_raw_scores | Interpretar mapping clínico/legacy | scores, clases, versión → raw, P(1), P(0) | predicción/evaluación | Ninguna |
| M/evaluation/clinical_metrics.py:93 | clinical_predictions_from_probabilities | Regla >= en float32 | P(parasitized), clases, threshold → array de etiquetas | métricas/callback | Ninguna |
| M/evaluation/clinical_metrics.py:109 | clinical_predictions_from_raw_scores | Conversión de score y decisión | scores, clases, threshold, versión → etiquetas | collect_predictions | Ninguna |
| M/evaluation/clinical_metrics.py:127 | clinical_confusion_counts | Conteos por etiquetas clínicas | y_true, y_pred, clases → dict TP/FN/FP/TN | evaluación clínica | Ninguna |
| M/evaluation/clinical_metrics.py:146 | compute_prediction_distribution | Cuenta etiquetas y fracciones | y_pred, clases → dict | métricas/detector colapso | Ninguna |
| M/evaluation/clinical_metrics.py:171 | detect_prediction_collapse | Vacío, una clase o fracción < mínimo | y_pred, clases, min_class_fraction=.05 → dict | callback y métricas; activa | Ninguna |
| M/evaluation/clinical_metrics.py:234 | compute_clinical_metrics | Matriz, recall, specificity, F1/F2, AUC/AP, colapso | y_true, y_scores, threshold=.5 → dict | calibrador, callback, evaluación final | Ninguna directa |
| M/evaluation/clinical_metrics.py:430 | collect_predictions | model.predict por batch; scores y etiquetas | modelo, dataset, clases, threshold, mapping → (y_true,y_pred,y_score) | train, callback, trainer | Ninguna directa; el llamador persiste samples |
| M/evaluation/validation.py:8 | evaluate_validation_predictions | Valida arrays y evalúa con threshold explícito | etiquetas, probabilities, ThresholdResult → ValidationEvaluationV1 | execution.train.train, rama con emitter | Evento posterior |
| M/training/checkpoint_policy.py:40 | CheckpointPolicyConfig | Configuración política/colapso/F2 | política, min_recall, beta, threshold, rechazo, fracción → dataclass | train y callbacks; activa | Resumen del llamador |
| M/training/checkpoint_policy.py:64 | get_monitor_for_policy | Monitor lógico por política | config → (monitor,mode) | trainer/selección | Ninguna |
| M/training/checkpoint_policy.py:72 | checkpoint_policy_score | 2+AUC si recall cumple; recall como fallback | logs, config → float/None | callback clínico | logs por época |
| M/training/checkpoint_policy.py:100 | early_stopping_score | Dirección, tanh acotada y penalización de colapso | logs, monitor, mode, config → float/None | callback clínico | val_early_stopping_score en logs |
| M/training/checkpoint_policy.py:225 | _selection_result | Forma resultado y conserva selected_record | selección/config/flags → dict | selectores | Llamador guarda selection |
| M/training/checkpoint_policy.py:271 | _records_after_collapse_filter | Excluye colapsados si hay alternativa; conserva todos con warning si no | history, config → candidatos y flags | selectores | Ninguna |
| M/training/checkpoint_policy.py:319 | select_best_epoch_from_history | Política F2/AUC/BA/AUC con recall | history, config → selección | train si no monitor explícito; callback legacy | Registro selection del llamador |
| M/training/checkpoint_policy.py:422 | select_best_epoch_by_monitor | Min/max explícito, sin filtro min_recall | history, config, monitor, mode → selección | train si selection.explicit | Igual |
| M/training/checkpoint_policy.py:458,487 | checkpoint_policy_summary / write_checkpoint_policy_summary | Compone/escribe resumen legacy | config, selection, path / output_dir, summary → dict/Path | ClinicalCheckpointCallback | checkpoint_policy_summary.json |
| M/training/checkpoint_policy.py:498,520 | ClinicalValidationMetricsCallback / on_epoch_end | Predicción VAL, métricas a .5, scores de selección/ES | dataset/config; epoch/logs → muta logs | execution.train por fase; activa | PersistEpoch guarda logs |
| M/training/checkpoint_policy.py:605,656,666 | ClinicalCheckpointCallback / _select_best / on_epoch_end | Selección y guardado legacy del mejor modelo | output/config/monitor; logs → estado y archivo | trainer.main; no callback usado por execution.train | best_model.keras y resumen |
| M/models/configuration.py:13,37 | merge_strict / resolve_config | Defaults, batch, JSON y override; validar | nombre/JSON/overrides/batch → requested/resolved/provenance | CLI, contratos campaña | Snapshot posterior |
| M/models/configuration.py:197 | selection_semantics | Monitor explícito y ES; threshold .5 | execution → dict | resolve_config | resolved.selection |
| M/training/cli.py:245–322,377 | parse_args / main | Sólo flags explícitos sobre JSON; llama standalone | argv → Namespace; main → resultado ejecución | src.train como módulo; activa | Mediante ejecutor |
| M/campaigns/configuration.py:181,276,433,454 | catalog / normalize / build_protocol / resolve | Exposición pública, validación y matriz | configuración operadora → catálogo/normalizado/protocolo/matriz | backend campaign_configuration; activa | Servicio de campaña |
| M/campaigns/contracts.py:235 | expand_matrix | Resolver combinaciones; imponer protocolo congelado | request, protocol, frozen, dataset → matriz | resolve/campaign_plan | campaign_configurations posterior |
| M/science/protocol.py:148 | campaign_plan | Derivar protocolo E7 con calibration none | protocolo científico → request/protocol | protocol_template/campañas | No escribe directamente |
| M/execution/campaign.py:189,309,406 | execute_campaign / parse_args / main | Ejecutar miembros persistidos, sin overrides científicos | repositorio/campaña/argv → ejecución | run_train_all_models.main; activa | Sesiones e intentos |
| M/execution/worker.py:38 | run_scientific_train | Conecta ejecutor y emitter | repo, session, descriptor, emitter → None | worker; activa | Eventos mediante reporter |
| M/execution/train.py:36 | train | Fases, selección global, calibración/final VAL | repo, session, descriptor, emitter opcional → None | worker/standalone; activa | Registros/eventos/artifacts |
| M/execution/train.py:108 | train.put | Registro legacy y evento canónico; omite evento de calibración desactivada | kind, phase, key, payload → None | train/PersistEpoch | train_execution_records y reporter |
| M/execution/train.py:141–205 | PersistEpoch.on_epoch_end | Selección, checkpoint por época y scores VAL | epoch/logs → None | callbacks de model.fit | epoch/artifact/selection/predictions |
| M/execution/train.py:331,337 | standalone / _standalone | TRAIN individual gobernado sin TEST/sidecar | args → ejecución | training.cli.main | Repositorio; train llamado sin emitter |
| M/execution/repository.py:179 | ExecutionRepository._create_run | Identidad y snapshot efectivo | conexión, RUN, config, dataset, entorno → None | claim/standalone | runs y run_configurations v2 |
| M/execution/repository.py:283 | bind_evaluation_context | Asocia checkpoint/población/protocolo | run, owner, selected_epoch → contexto | train con emitter | artifacts y contexto RUN |
| M/execution/repository.py:355,409 | put / finish | Idempotencia por clave y cierre | run/owner/tipo/payload o estado/evidencia → None | train | registros y completion de sesión |
| M/execution/reporters/docker.py:11 | DockerRunReporter.report | Entrega a ResultService | RunEvent → None | emitter | Repositorio del servicio |
| M/execution/reporters/http.py:11 | HttpRunReporter.report | Entrega por transporte cliente | RunEvent → None | emitter/agente local | Backend; no SQL directo en reporter |
| M/results/service.py:19 | ResultService.accept_event | Identidad, secuencia, idempotencia, proyección atómica | context, event → EventAcceptance | reporter/API | Ledger y proyección |
| M/persistence/result_repository.py:92 | project_calibration_result | Selecciona proyección v2 | estado/evento transaccional → None | ResultService | project_calibration |
| M/persistence/v2_projection.py:29 | project_configuration | Snapshot científico tipado | connection, run_id, config → None | _create_run | run_configurations |
| M/persistence/v2_projection.py:60 | training_evaluation_context | Hashes y linaje VAL exacto | checkpoint, protocolo, dataset, población, contrato → dict | binding del repositorio | Contexto en execution_parameters |
| M/persistence/v2_projection.py:116 | project_evaluation | Evaluación final y conteos; enlaza calibración si corresponde | connection,event,TrainingResultsV1 → None | result_repository | evaluations + run_clinical_metrics |
| M/persistence/v2_projection.py:144 | project_calibration | Pareja default/selected, umbral/target y conteos | connection,event → None | ResultService | evaluations + run_threshold_calibration + métricas |
| M/science/statistics.py:27,125 | validate_rows / threshold_selection | Selector E7 estricto, no calibrador TRAIN | filas con sample_id/label/raw_score/predicted, split → propuesta | comparison.py:173, ensemble.py:250; conectado | Consumidores científicos; no modifica predicciones aquí |
| M/assessment/contracts.py:28 | threshold | Resuelve número permitido o clinical con evidencia VAL; no calibra | requested,protocol,calibration → decision con effective/source/comparison | assessment.service.prepare; activa | Identidad posterior |
| M/assessment/lineage.py:21 | resolve | Comprueba RUN/modelo y calibration de época seleccionada | repo,training_run_id,model_version_id → binding,dataset,calibration | assessment.service.prepare; activa | Sólo lectura |
| M/assessment/service.py:53 | prepare | Resuelve decisión antes de evaluación separada TRAIN/VAL/TEST | repo,identidades,split,purpose,protocol,requested_threshold,... → identity | assessment CLI; activa | Reserva posterior |
| M/assessment/contracts.py:67,140 | identity / prediction | TEST exige purpose final; decisión >= sin búsqueda | contrato/decisión/samples → identity; muestra/score/decision → fila | assessment.service/runtime; activa | assessment_identities/assessment_results vía repositorio |

Los helpers `_as_float`, `_json_safe`, `_metric_subset`, `_warnings` del calibrador (líneas 30,36,83,149) convierten/copían datos para el resultado; no añaden validación de factibilidad ni persistencia. Helpers de checkpoint `_metric`, `_is_collapsed`, `_epoch` (173,192,187) leen logs; `_max_by_metric` y `_min_by_metric` (297,308) desempatan a favor de la época más reciente.

## Compatibilidad, consumidores secundarios y backend

| Archivo:línea | Función | Contrato / consumidor | Estado y persistencia |
| --- | --- | --- | --- |
| M/training/trainer.py:67,88 | ValidationEarlyStopping / build_phase_callbacks | Clase ES con valor lógico; callbacks legacy | Importado por módulos callbacks/early_stopping; no es el motor principal de campañas |
| M/training/trainer.py:926,1424–1495 | main | Carga best_model, calibra VAL y construye threshold_info | Legacy/importable por src.train; CLI normal redirige a execution.train; JSON/metadata/tracking legacy |
| M/training/trainer.py:874,920 | evaluate_selected_checkpoint_once / evaluate_selected_checkpoint_if_enabled | Evaluación TEST opcional legacy, con umbral previamente elegido | Implementado; prohibido y no invocado en C1; no inferir uso B1 |
| M/evaluation/calibration_cli.py:30,93,406,484 | parse_args / collect_validation_probabilities / main | CLI de calibración separada; carga checkpoint y predice VAL | Conectado al buscador; no sirve tal cual para C2 sin inferencia; payload y tracking |
| M/evaluation/calibration_cli.py:168,202,212 | build_threshold_calibration_payload / save_calibration / track_calibration_run | Resultado con contexto → JSON y registro | Consumidos por main; compatibilidad, ejecución B1 no acreditada |
| malaria_dl_local_project/src/model_metadata.py:100,136 | clinical_threshold_metadata_from_calibration / update_model_metadata_with_clinical_threshold | resultado → metadata clínica / actualización | Trainer/calibration CLI; JSON sidecar |
| malaria_dl_local_project/src/model_metadata.py:169,202 | load_clinical_threshold_for_checkpoint / resolve_threshold_for_checkpoint | checkpoint y número/'clinical' → threshold_info; error si metadata ausente | Inference/evaluation legacy; no fuente de umbral del TRAIN de campaña |
| M/persistence/tracking.py:354,364 | clinical_metrics_for_tracking / threshold_calibration_for_tracking | dict → campos de tracking | Pipeline legacy; no escritura directa |
| M/persistence/tracking.py:1230,1271 | record_clinical_metrics / record_threshold_calibration | contexto/resultados → delegación a tracker | Legacy; guardas por contexto/método disponible |
| M/persistence/run_repository.py:1119,1323 | log_clinical_metrics / log_threshold_calibration | SQL legacy con métricas/resumen | Implementado; no atribuir compatibilidad v2: INSERT no aporta evaluación obligatoria como la proyección v2 |
| backend_api/app/routes/runs.py:541 | get_run_clinical_summary | run_id/datasource → resumen compuesto | Conectado; lee latest metrics, prioriza TEST/external, vista de calibración; no filtra rol final VAL |
| backend_api/app/routes/runs.py:705 | get_run_clinical_metrics | run_id → items de run_clinical_metrics | GET /[api/]runs/{run_id}/clinical-metrics; lectura |
| backend_api/app/routes/runs.py:724 | get_run_checkpoint_policy | run_id → vista de política | GET /[api/]runs/{run_id}/checkpoint-policy; B1 reporta tabla vacía |
| backend_api/app/routes/runs.py:743 | get_run_threshold_calibration | run_id → vw_threshold_calibration_summary | GET /[api/]runs/{run_id}/threshold-calibration; limitación proyección H04 |
| backend_api/app/services/training_summaries.py:365 | list_training_summaries | datasource,limit → resumen | routes/runs.py:447–458; consulta configuración y final VAL; archivo tenía cambios locales al iniciar C1 |
| backend_api/app/services/campaign_configuration.py:28,80,154 | campaign_catalog / preview / create_campaign | petición → catálogo/previsualización/campaña | Usa resolver público; la creación no se ejecutó |

No se localizó `calibrate_clinical_threshold`; no se propone crear un alias ni sistema nuevo por esa ausencia nominal. `src/train.py:1–8` distingue explícitamente ejecución como módulo (CLI nueva) de importación (trainer legacy). Los helpers batch de `run_train_all_models.py:46,103,137` no gobiernan su `main:161`, que delega a campaña persistida.

## Matriz de pruebas inspeccionadas

**IMPLEMENTADO** significa intención expresada por cuerpo/aserciones; resultado actual **NO VERIFICADO** en todos los casos. Los nombres siguientes son exactos. Las pruebas legacy de tracking usan mocks: no acreditan INSERT válido contra el esquema v2.

| Archivo:línea / test | Entradas y comportamiento | Aserciones y límites cubiertos | Cobertura faltante relevante |
| --- | --- | --- | --- |
| T/test_threshold_calibration.py:20 `test_find_threshold_for_target_recall_satisfies_target_when_possible` | y=[1,1,1,0,0,0], s=[.9,.8,.2,.7,.1,.05], target=.98 | threshold≈.2; recall>=.98; satisfied true; fuente validación | Frontera exacta .98, especificidad incompatible |
| mismo:38 `test_find_threshold_uses_secondary_specificity_then_highest_threshold` | Mismos arrays, target=2/3 | threshold≈.8; specificity=1 | No aísla todos los desempates lexicográficos |
| mismo:52 `test_find_threshold_fallback_when_target_not_reached` | Sólo negativos, [.2,.4,.8] | satisfied false; warning | Ausencia de negativos; rechazo obligatorio de ambos soportes |
| mismo:65 `test_threshold_applied_to_probability_parasitized` | y=[1,0], s=[.4,.6], t=.5 | FN=FP=1; TP=TN=0 | Igualdad score==threshold |
| mismo:77 `test_build_threshold_candidates_includes_default_threshold` | [.2,.8] | Incluye 0,.5,1 | NaN, infinitos, rango y precisión |
| mismo:84 `test_test_set_cannot_be_used_for_calibration` | split='test' | ValueError y mensaje | Buscador numérico no recibe split |
| T/test_clinical_metrics.py:15 `test_label_mapping_is_clinical` | Constantes | Convención clínica | Mapping legacy en retorno de collect_predictions |
| mismo:21 `test_confusion_matrix_values_clinical_order` | y=[0,0,1,1], scores de dos clases | Matriz y conteos en orden clínico | Etiquetas inválidas |
| mismo:35 `test_f2_score_prioritizes_recall_for_parasitized` | y=[0,0,1,1,1], s=[.1,.8,.2,.9,.3] | F2 igual a sklearn.fbeta_score(beta=2), clase positiva 1 | Pese al nombre, no compara escenarios de FN frente a FP; tampoco prueba otro beta |
| mismo:74,81 `test_prediction_collapse_all_parasitized` / `test_prediction_collapse_all_uninfected` | Todos 1 / todos 0 | Colapso y tipo | Gate de calibración no existe |
| T/test_clinical_validation_callback.py:22 `test_callback_adds_clinical_validation_metrics_to_logs` | Modelo Keras sigmoid mínimo, x=[−4,4,−3,3], y=[0,1,0,1] | recall,specificity,F2,BA=1; colapso=0 | Flujo completo de campaña |
| mismo:40 `test_callback_detects_validation_prediction_collapse` | Cuatro predicciones positivas | recall=1; specificity=0; colapso=1; n positivos=4 | No demuestra rechazo posterior |
| T/test_checkpoint_policy.py:22 `test_auc_with_min_recall_score_prioritizes_constraint_then_auc` | Logs factibles/fallback | Orden por factibilidad y AUC | Monitor explícito con el mismo nombre de política |
| mismo:44 `test_early_stopping_score_rejects_collapsed_epochs` | Log colapsado | Score finito y <−1e6 | ES vs desempate exacto de checkpoint |
| mismo:64 `test_collapsed_scores_remain_ordered_when_all_epochs_collapse` | Dos scores colapsados | Finitud y orden | Factibilidad clínica conjunta |
| mismo:92 `test_early_stopping_score_inverts_min_monitors` | Monitor min .25 | Score≈−.25 | Variación min_delta |
| mismo:102 `test_f2_policy_selects_highest_val_f2` | Historia con máximos F2 distintos | Época 2 y flag de política true | Flag no implica recall objetivo |
| mismo:118 `test_auc_with_min_recall_selects_best_auc_among_valid_epochs` | Historia, min_recall=.98 | Época 2, val_auc, sin colapso | min_specificity no pertenece a config checkpoint |
| mismo:163 `test_auc_with_min_recall_fallback_when_no_epoch_reaches_min_recall` | Ninguna época factible | Época 2; policy false; warning | Cierre recalibrado |
| mismo:178 `test_policy_rejects_collapsed_epoch_when_enabled` | Candidato colapsado y alternativa | Época 1; un rechazado | Colapso del threshold final |
| mismo:206 `test_policy_all_epochs_collapsed_returns_warning` | Todos colapsados | Época 2, all_epochs_collapsed true, warning | Aceptación clínica no debe inferirse |
| T/test_threshold_calibration_tracking.py:27 `test_record_threshold_calibration_passes_model_name_from_context` | Contexto/tracker simulado | run_uuid y model_name propagados | Integridad v2 |
| mismo:44 `test_log_threshold_calibration_extracts_selected_metrics` | Resultado prefabricado, t=.42, min_spec=.7 | INSERT contiene tabla; recall .96/spec .88/candidatos 101 | No prueba optimizador ni factibilidad; no ejecuta SQL real |
| mismo:92 `test_log_threshold_calibration_skips_missing_selected_threshold` | Resultado sin umbral | None, execute no llamado | No detecta omisiones de project_calibration |
| T/test_training_results.py:29 `test_manual_scientific_golden` | [0,0,1,1], [.1,.8,.6,.9], t=.5 | TN=1 FP=1 FN=0 TP=2; F2=10/11, AUC=.75, AP=5/6 | Proyección SQL de flags |
| mismo:43 `test_zero_division_and_single_class` | Tres casos, clases ausentes/cero positivos predichos | Conteos; métricas Python; AUC/AP None en una clase | Equivalencia cero Python/null SQL |
| mismo:58 `test_threshold_policy_preserved` | enabled false/true con mismo fixture | Threshold idéntico; métricas y matriz coinciden con calibrador | No ejecuta train ni protocolo público |
| mismo:77,85 `test_invalid_science_rejected` / `test_invalid_predictions_rejected` | Payload/arrays inválidos, NaN, 1.1, clase 2, vacío | ValueError en contrato/evaluación final | Validar antes del calibrador y su persistencia |
| mismo:101 `test_projection_retry_and_immutable_final` | Servicio/repositorio falso, mismo evento repetido | duplicate_accepted; un evento y proyección estable | Integración real no ejecutada |
| T/test_science_e7.py:138 `test_strict_threshold_098_not_success_and_stable_ties` | 50 positivos (49 altos), dos negativos | t=.1, sensibilidad=1, specificity=.5; orden invertido igual; TEST rechazado; sin positivos t=None | Pertenece a E7, no al calibrador TRAIN |
| mismo:515 `test_invalid_prediction_mapping_duplicate_and_nonfinite` | label 2/True, score NaN, predicted −1, duplicados | ScienceError | Sus guardas no se heredan automáticamente a TRAIN |
| T/test_assessment_e6.py:227 `test_threshold_no_implicit_clinical_fallback` | clinical sin evidencia, .5 sin permiso; fixture VAL t=.63 | Rechaza ausencias; effective=.63 con evidencia | Fixture no exige flags de recall/especificidad |
| mismo:245 `test_test_forbidden_development` | split test, purpose development | AssessmentError TEST | Intención de protección; no ejecutado |

Tests adicionales localizados: `test_train_checkpoint_policy_args.py:14–50` (defaults/CLI), `test_model_metadata_threshold.py:50–89`, `test_evaluate_threshold_modes.py:39–65`, `test_threshold_clinical_mode.py:72–145` (fijo/clinical, metadata ausente, TTA/ensemble), `test_training_results_postgres.py:36–122` (atomicidad y reintentos), `tests/db_v2/test_static_baseline.py:137,289,467` (estructura y VAL de calibración), `backend_api/tests/test_clinical_summary_api.py`. Su presencia no equivale a cobertura integral ni resultados aprobados en C1.

No se encontró prueba directa del calibrador TRAIN para `min_specificity_satisfied=false`, factibilidad conjunta, recall exactamente .98, ambos soportes obligatorios, NaN/Inf/rango, labels fraccionarios, beta distinto de 2, scores float64 muy próximos ni propagación de flags/warning de calibración v2 hasta API. No se requiere test de maximización Youden: no es el criterio implementado ni el solicitado para C2. Los casos faltantes se proponen en [PLAN_C2.md](PLAN_C2.md).
