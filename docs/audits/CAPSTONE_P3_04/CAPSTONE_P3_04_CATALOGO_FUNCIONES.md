# CAPSTONE-P3-04 — Catálogo de funciones

Inventario estático reproducible, con cierre transitivo de imports frontend y módulos backend/ML asociados. Los archivos incluyen un superconjunto de helpers; no se afirma que cada función del archivo sea invocada por esta ruta. Las fichas matemáticas y contratos ejecutados están en el documento 05; este catálogo conserva entradas, llamadas, retornos, controles, consumidores textuales y tests encontrados. Las coincidencias textuales no acreditan cobertura dinámica ni que una función haya sido invocada.

Todos los campos solicitados se entregan por fila en [functions.csv](csv/functions.csv). Índice de fuentes con SHA-256: [sources.csv](csv/sources.csv). Las líneas corresponden al workspace auditado, incluidas modificaciones previas.


## backend_api/app/db.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| normalize_sqlalchemy_url | [17](../../../backend_api/app/db.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_postgres_transaction_isolation.py; backend_api/tests/test_auth_postgres_docker.py; … (7 referencias nominales; ver CSV) |
| _datasources | [21](../../../backend_api/app/db.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| list_datasources | [31](../../../backend_api/app/db.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| resolve_datasource | [37](../../../backend_api/app/db.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scc_xai_original.py |
| get_engine | [45](../../../backend_api/app/db.py#L45) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_stage2_publication_api_e2e.py; backend_api/tests/test_training_summaries_api.py; backend_api/tests/test_model_availability_e2e_postgres.py; … (26 referencias nominales; ver CSV) |
| get_primary_engine | [54](../../../backend_api/app/db.py#L54) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_docker_postgres_tooling.py; … (12 referencias nominales; ver CSV) |
| fetch_all | [58](../../../backend_api/app/db.py#L58) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explainability_api.py; backend_api/tests/test_run_detail_api.py; backend_api/tests/test_grouped_run_lineage_api.py; … (8 referencias nominales; ver CSV) |
| fetch_one | [63](../../../backend_api/app/db.py#L63) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explainability_api.py; backend_api/tests/test_run_detail_api.py; backend_api/tests/test_governance_api.py; … (7 referencias nominales; ver CSV) |
| read_only_transaction | [69](../../../backend_api/app/db.py#L69) | Yield one bounded PostgreSQL transaction that cannot write. | backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_lineage_children_api.py; … (12 referencias nominales; ver CSV) |
| check_connection | [96](../../../backend_api/app/db.py#L96) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_backend_endpoints.py |

## backend_api/app/repositories/activation_traces.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ActivationTraceRepository.evaluation | [11](../../../backend_api/app/repositories/activation_traces.py#L11) | VAL first, as EXPLAIN: TEST stays reserved for the final evaluation. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_lineage_children_api.py; … (68 referencias nominales; ver CSV) |
| ActivationTraceRepository.candidates | [22](../../../backend_api/app/repositories/activation_traces.py#L22) | Cells of one outcome, most confident first; «explained» marks cells with a verified EXPLAIN of the same TRAIN. | backend_api/tests/test_stage2_publication_api_e2e.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_activation_traces.py; … (10 referencias nominales; ver CSV) |
| ActivationTraceRepository.result | [47](../../../backend_api/app/repositories/activation_traces.py#L47) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; … (123 referencias nominales; ver CSV) |

## backend_api/app/repositories/artifacts.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ArtifactReadRepository.get | [9](../../../backend_api/app/repositories/artifacts.py#L9) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_cell_classification_postgres.py; … (62 referencias nominales; ver CSV) |

## backend_api/app/repositories/assessments.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AssessmentReadRepository.list | [11](../../../backend_api/app/repositories/assessments.py#L11) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (72 referencias nominales; ver CSV) |
| AssessmentReadRepository.detail | [32](../../../backend_api/app/repositories/assessments.py#L32) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_microscopy_quality_services.py; … (33 referencias nominales; ver CSV) |
| AssessmentReadRepository.payloads | [42](../../../backend_api/app/repositories/assessments.py#L42) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_assessment_artifacts_sample_filter.py; malaria_dl_local_project/tests/test_campaign_executor_postgres.py; malaria_dl_local_project/tests/test_campaign_executor_e5.py; … (5 referencias nominales; ver CSV) |
| AssessmentReadRepository.preflight_detail | [54](../../../backend_api/app/repositories/assessments.py#L54) | Exact attempt, without materializing samples or filesystem locators. | backend_api/tests/test_scientific_preflight.py |
| AssessmentReadRepository.preflight_candidates | [64](../../../backend_api/app/repositories/assessments.py#L64) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py |
| AssessmentReadRepository.preflight_population | [72](../../../backend_api/app/repositories/assessments.py#L72) | Full SQL aggregates over exact attempts, never a page or diagnostic recalculation.  Declared and observed IDs are compared in both directions. Membership is proved against governed assignments, not by assuming UUID names | backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_assessment_population_query.py |
| AssessmentReadRepository.comparison_results | [134](../../../backend_api/app/repositories/assessments.py#L134) | Full exact-attempt population for server-side analysis, never sent as a browser array. | Sin referencia nominal localizada |
| AssessmentReadRepository.eligibility_training | [140](../../../backend_api/app/repositories/assessments.py#L140) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_comparison_eligibility.py |
| AssessmentReadRepository.eligibility_attempts | [149](../../../backend_api/app/repositories/assessments.py#L149) | Counts belong to one attempt; identities without attempts remain visible. | Sin referencia nominal localizada |

## backend_api/app/repositories/catalog.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| CatalogRepository.models | [24](../../../backend_api/app/repositories/catalog.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (59 referencias nominales; ver CSV) |

## backend_api/app/repositories/dataset_samples.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| DatasetSampleReadRepository.explanation_context | [12](../../../backend_api/app/repositories/dataset_samples.py#L12) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scc_xai_original.py |
| DatasetSampleReadRepository.training_dataset | [25](../../../backend_api/app/repositories/dataset_samples.py#L25) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scc_xai_original.py |
| DatasetSampleReadRepository.sample_reference | [36](../../../backend_api/app/repositories/dataset_samples.py#L36) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scc_xai_original.py |

## backend_api/app/repositories/explain_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| assessment_scope | [11](../../../backend_api/app/repositories/explain_generation.py#L11) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ExplainRepository.__init__ | [19](../../../backend_api/app/repositories/explain_generation.py#L19) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |

## backend_api/app/repositories/model_architecture.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ModelArchitectureRepository.read | [10](../../../backend_api/app/repositories/model_architecture.py#L10) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/repositories/representation_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| RepresentRepository.__init__ | [7](../../../backend_api/app/repositories/representation_generation.py#L7) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |

## backend_api/app/repositories/representation_queries.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| RepresentQueries.represent_candidates | [10](../../../backend_api/app/repositories/representation_queries.py#L10) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_representation_generation.py |
| RepresentQueries.represent_requests | [18](../../../backend_api/app/repositories/representation_queries.py#L18) | Host GPU queue rows for one EVALUATE source, most recent first. | backend_api/tests/test_representation_generation.py |

## backend_api/app/repositories/scientific.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ScientificRepository.__init__ | [20](../../../backend_api/app/repositories/scientific.py#L20) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificRepository._config | [24](../../../backend_api/app/repositories/scientific.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_evaluation_training_lineage_migration_postgres.py |
| ScientificRepository._parameters | [31](../../../backend_api/app/repositories/scientific.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificRepository._value_expression | [38](../../../backend_api/app/repositories/scientific.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificRepository.create | [41](../../../backend_api/app/repositories/scientific.py#L41) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_event_journal.py; … (19 referencias nominales; ver CSV) |
| ScientificRepository.get | [56](../../../backend_api/app/repositories/scientific.py#L56) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_cell_classification_postgres.py; … (62 referencias nominales; ver CSV) |
| ScientificRepository.update | [65](../../../backend_api/app/repositories/scientific.py#L65) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_lineage_children_api.py; … (54 referencias nominales; ver CSV) |
| ScientificRepository.archive | [80](../../../backend_api/app/repositories/scientific.py#L80) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_data_api_postgres.py |
| ScientificRepository.list | [92](../../../backend_api/app/repositories/scientific.py#L92) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (72 referencias nominales; ver CSV) |
| ScientificRepository.active_child_count | [130](../../../backend_api/app/repositories/scientific.py#L130) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificRepository.traceability | [146](../../../backend_api/app/repositories/scientific.py#L146) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_data_api_postgres.py; backend_api/tests/test_assessment_artifacts_sample_filter.py; backend_api/tests/test_scc_core.py; … (7 referencias nominales; ver CSV) |

## backend_api/app/repositories/scientific_results.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| metric_dto | [10](../../../backend_api/app/repositories/scientific_results.py#L10) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_results_v2.py |
| read_run_configurations | [26](../../../backend_api/app/repositories/scientific_results.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| read_scientific_results | [32](../../../backend_api/app/repositories/scientific_results.py#L32) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| rows | [37](../../../backend_api/app/repositories/scientific_results.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_smear_reset_tool.py; … (65 referencias nominales; ver CSV) |
| ScientificReadRepository.read | [59](../../../backend_api/app/repositories/scientific_results.py#L59) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |
| ScientificReadRepository.preflight_training | [97](../../../backend_api/app/repositories/scientific_results.py#L97) | Small projection; no history series, predictions or XAI contents. | backend_api/tests/test_scientific_preflight.py |
| ScientificReadRepository.preflight_configuration | [108](../../../backend_api/app/repositories/scientific_results.py#L108) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; frontend/tests/scc-preflight.test.mjs |
| ScientificReadRepository.preflight_history | [124](../../../backend_api/app/repositories/scientific_results.py#L124) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py |
| ScientificReadRepository.evaluation | [131](../../../backend_api/app/repositories/scientific_results.py#L131) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_lineage_children_api.py; … (68 referencias nominales; ver CSV) |
| ScientificReadRepository.comparison_catalog | [137](../../../backend_api/app/repositories/scientific_results.py#L137) | Historical evaluations and independent attempts, without inventing attempts. | Sin referencia nominal localizada |
| ScientificReadRepository.comparison_governance | [157](../../../backend_api/app/repositories/scientific_results.py#L157) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificReadRepository.comparison_epochs | [188](../../../backend_api/app/repositories/scientific_results.py#L188) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificReadRepository.comparison_checkpoint | [194](../../../backend_api/app/repositories/scientific_results.py#L194) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py |
| ScientificReadRepository.comparison_metrics | [208](../../../backend_api/app/repositories/scientific_results.py#L208) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py |
| ScientificReadRepository.comparison_predictions | [213](../../../backend_api/app/repositories/scientific_results.py#L213) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py |
| ScientificReadRepository.comparison_representation | [220](../../../backend_api/app/repositories/scientific_results.py#L220) | Latest verified REPRESENT of exactly this EVALUATE model, population and decision; never computes one. | Sin referencia nominal localizada |
| ScientificReadRepository.comparison_representation_rows | [239](../../../backend_api/app/repositories/scientific_results.py#L239) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificReadRepository.comparison_representation_artifacts | [244](../../../backend_api/app/repositories/scientific_results.py#L244) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/repositories/scientific_validation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ScientificValidationRepository.__init__ | [11](../../../backend_api/app/repositories/scientific_validation.py#L11) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificValidationRepository.source_rows | [14](../../../backend_api/app/repositories/scientific_validation.py#L14) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.image_run_membership | [30](../../../backend_api/app/repositories/scientific_validation.py#L30) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.create | [51](../../../backend_api/app/repositories/scientific_validation.py#L51) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_event_journal.py; … (19 referencias nominales; ver CSV) |
| ScientificValidationRepository.get | [87](../../../backend_api/app/repositories/scientific_validation.py#L87) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_cell_classification_postgres.py; … (62 referencias nominales; ver CSV) |
| ScientificValidationRepository.list | [109](../../../backend_api/app/repositories/scientific_validation.py#L109) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (72 referencias nominales; ver CSV) |
| ScientificValidationRepository.update | [125](../../../backend_api/app/repositories/scientific_validation.py#L125) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_lineage_children_api.py; … (54 referencias nominales; ver CSV) |
| ScientificValidationRepository.archive | [135](../../../backend_api/app/repositories/scientific_validation.py#L135) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_data_api_postgres.py |
| ScientificValidationRepository.target_belongs_to_session | [144](../../../backend_api/app/repositories/scientific_validation.py#L144) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.target_exists | [215](../../../backend_api/app/repositories/scientific_validation.py#L215) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository._annotation_state | [229](../../../backend_api/app/repositories/scientific_validation.py#L229) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository._append_annotation_event | [248](../../../backend_api/app/repositories/scientific_validation.py#L248) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.create_annotation | [273](../../../backend_api/app/repositories/scientific_validation.py#L273) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.get_annotation | [296](../../../backend_api/app/repositories/scientific_validation.py#L296) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.list_annotations | [312](../../../backend_api/app/repositories/scientific_validation.py#L312) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.update_annotation | [353](../../../backend_api/app/repositories/scientific_validation.py#L353) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationRepository.annotation_history | [391](../../../backend_api/app/repositories/scientific_validation.py#L391) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/repositories/training_trajectories.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| TrainingTrajectoryRepository.read | [9](../../../backend_api/app/repositories/training_trajectories.py#L9) | One snapshot: the TRAIN, its per-epoch VAL predictions and the identity of its latest verified VAL EVALUATE. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/routes/activation_traces.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| catalog | [16](../../../backend_api/app/routes/activation_traces.py#L16) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_activation_traces.py; … (20 referencias nominales; ver CSV) |
| candidates | [21](../../../backend_api/app/routes/activation_traces.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_stage2_publication_api_e2e.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_activation_traces.py; … (10 referencias nominales; ver CSV) |
| read | [27](../../../backend_api/app/routes/activation_traces.py#L27) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |
| create | [32](../../../backend_api/app/routes/activation_traces.py#L32) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_event_journal.py; … (19 referencias nominales; ver CSV) |
| delete | [37](../../../backend_api/app/routes/activation_traces.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_clean_training_outputs.py; frontend/tests/scc-xai.test.mjs; … (4 referencias nominales; ver CSV) |

## backend_api/app/routes/artifacts.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| artifact_file | [15](../../../backend_api/app/routes/artifacts.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_artifacts_api.py; malaria_dl_local_project/tests/test_backend_endpoints.py |

## backend_api/app/routes/assessments.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_service | [21](../../../backend_api/app/routes/assessments.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py |
| list_assessments | [29](../../../backend_api/app/routes/assessments.py#L29) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| assessment | [36](../../../backend_api/app/routes/assessments.py#L36) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_representation_generation.py; backend_api/tests/test_e6_lineage_read_only.py; backend_api/tests/test_scientific_preflight.py; … (30 referencias nominales; ver CSV) |
| results | [44](../../../backend_api/app/routes/assessments.py#L44) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_detection_crop_equivalence.py; backend_api/tests/test_assessment_artifacts_sample_filter.py; backend_api/tests/test_comparison_eligibility.py; … (44 referencias nominales; ver CSV) |
| artifacts | [51](../../../backend_api/app/routes/assessments.py#L51) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_stage2_status_read_only.py; … (58 referencias nominales; ver CSV) |

## backend_api/app/routes/catalog.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| models | [15](../../../backend_api/app/routes/catalog.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (59 referencias nominales; ver CSV) |
| model_comparison | [26](../../../backend_api/app/routes/catalog.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_model_comparison_api.py |
| datasets | [44](../../../backend_api/app/routes/catalog.py#L44) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_governed_dataset_versions_api.py; backend_api/tests/test_e6_lineage_read_only.py; backend_api/tests/test_dataset_browser_api.py; … (11 referencias nominales; ver CSV) |

## backend_api/app/routes/explain_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_service | [21](../../../backend_api/app/routes/explain_generation.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py |
| docker_cpu | [28](../../../backend_api/app/routes/explain_generation.py#L28) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_launcher | [33](../../../backend_api/app/routes/explain_generation.py#L33) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| executor | [40](../../../backend_api/app/routes/explain_generation.py#L40) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_local_train_launcher.py; malaria_dl_local_project/tests/test_campaign_configuration_postgres_swv22.py; malaria_dl_local_project/tests/test_campaign_cli_plan_swv22.py; … (5 referencias nominales; ver CSV) |
| state | [47](../../../backend_api/app/routes/explain_generation.py#L47) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_scientific_report.py; … (79 referencias nominales; ver CSV) |
| prepare | [59](../../../backend_api/app/routes/explain_generation.py#L59) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (12 referencias nominales; ver CSV) |
| generate | [67](../../../backend_api/app/routes/explain_generation.py#L67) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_case_gradcam_service.py; malaria_dl_local_project/tests/test_run_event_emitter.py; frontend/tests/cell-classification-workflow.test.mjs; … (4 referencias nominales; ver CSV) |

## backend_api/app/routes/model_architecture.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| model_architecture | [13](../../../backend_api/app/routes/model_architecture.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; backend_api/tests/test_model_architecture.py |

## backend_api/app/routes/representation_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_service | [21](../../../backend_api/app/routes/representation_generation.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py |
| get_launcher | [28](../../../backend_api/app/routes/representation_generation.py#L28) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| state | [37](../../../backend_api/app/routes/representation_generation.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_scientific_report.py; … (79 referencias nominales; ver CSV) |
| generate | [46](../../../backend_api/app/routes/representation_generation.py#L46) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_case_gradcam_service.py; malaria_dl_local_project/tests/test_run_event_emitter.py; frontend/tests/cell-classification-workflow.test.mjs; … (4 referencias nominales; ver CSV) |

## backend_api/app/routes/runs.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| scientific_results | [27](../../../backend_api/app/routes/runs.py#L27) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_scc_core.py |
| latest_item | [208](../../../backend_api/app/routes/runs.py#L208) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| clinical_summary_payload | [213](../../../backend_api/app/routes/runs.py#L213) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| list_runs | [306](../../../backend_api/app/routes/runs.py#L306) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_run_detail_api.py |
| get_training_summaries | [455](../../../backend_api/app/routes/runs.py#L455) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_lineage_children | [478](../../../backend_api/app/routes/runs.py#L478) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| list_grouped_run_lineage | [502](../../../backend_api/app/routes/runs.py#L502) | Group recent training runs with linked children and separate orphans. | backend_api/tests/test_grouped_run_lineage_api.py |
| list_clinical_run_summary | [512](../../../backend_api/app/routes/runs.py#L512) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_backend_endpoints.py |
| get_run_clinical_summary | [544](../../../backend_api/app/routes/runs.py#L544) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_clinical_summary_api.py |
| get_run | [656](../../../backend_api/app/routes/runs.py#L656) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_services.py; backend_api/tests/test_cell_detection_postgres.py; malaria_dl_local_project/tests/test_checkpoint_lineage_resolution.py |
| get_run_clinical_metrics | [708](../../../backend_api/app/routes/runs.py#L708) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_run_checkpoint_policy | [727](../../../backend_api/app/routes/runs.py#L727) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_run_detail_api.py |
| get_run_threshold_calibration | [746](../../../backend_api/app/routes/runs.py#L746) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_run_detail_api.py |
| get_run_artifacts_summary | [767](../../../backend_api/app/routes/runs.py#L767) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_run_detail_api.py |
| get_run_image_predictions | [786](../../../backend_api/app/routes/runs.py#L786) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_run_detail_api.py; malaria_dl_local_project/tests/test_backend_endpoints.py |
| get_run_io_records | [841](../../../backend_api/app/routes/runs.py#L841) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_run_explainability | [860](../../../backend_api/app/routes/runs.py#L860) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_run_detail_api.py |

## backend_api/app/routes/training_trajectories.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| read | [14](../../../backend_api/app/routes/training_trajectories.py#L14) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/schemas/explain_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ExplainRequest.integer_class | [20](../../../backend_api/app/schemas/explain_generation.py#L20) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/schemas/scientific.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _assert_no_pii | [18](../../../backend_api/app/schemas/scientific.py#L18) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| MetadataSchema.metadata_has_no_pii | [47](../../../backend_api/app/schemas/scientific.py#L47) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationCreate.identifiers_are_unique | [184](../../../backend_api/app/schemas/scientific.py#L184) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationAnnotationCreate.annotation_text_is_not_blank | [206](../../../backend_api/app/schemas/scientific.py#L206) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationAnnotationCreate.validate_target | [212](../../../backend_api/app/schemas/scientific.py#L212) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationAnnotationUpdate.updated_annotation_text_is_not_blank | [238](../../../backend_api/app/schemas/scientific.py#L238) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationAnnotationUpdate.contains_change | [244](../../../backend_api/app/schemas/scientific.py#L244) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/schemas/scientific_preflight.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| PreflightRequest.validate_selection | [69](../../../backend_api/app/schemas/scientific_preflight.py#L69) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| Verdict.validate_state | [113](../../../backend_api/app/schemas/scientific_preflight.py#L113) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/services/activation_trace_compute.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| block_of | [23](../../../backend_api/app/services/activation_trace_compute.py#L23) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| traced_layers | [28](../../../backend_api/app/services/activation_trace_compute.py#L28) | Block poolings, then the head as this TRAIN built it: each run may use GAP, Flatten or other Dense sizes. | backend_api/tests/test_activation_traces.py |
| custom_cnn_blocks | [40](../../../backend_api/app/services/activation_trace_compute.py#L40) | Block of each layer with the rule of the architecture service: every Conv2D opens a block that also holds its BatchNormalization, Activation and pooling; the rest is the head, and the sigmoid Dense is the output. | Sin referencia nominal localizada |
| traced_custom_cnn | [56](../../../backend_api/app/services/activation_trace_compute.py#L56) | Output of each convolutional block (its last layer: pooling, or the activation of a block without pooling), then the head layers that change the tensor and the output. | Sin referencia nominal localizada |
| densenet_block | [68](../../../backend_api/app/services/activation_trace_compute.py#L68) | Block of a DenseNet121 layer, with the rule of the architecture service (``_keras_block``). | backend_api/tests/test_activation_traces.py |
| flattened | [84](../../../backend_api/app/services/activation_trace_compute.py#L84) | Layers in flow order, with the nested backbone expanded in place (as the architecture service flattens it). | backend_api/tests/test_activation_traces.py |
| traced_densenet | [95](../../../backend_api/app/services/activation_trace_compute.py#L95) | Output of each architecture block (its last layer), then the final activated features, the head and the output. | backend_api/tests/test_activation_traces.py |
| nested_outputs | [111](../../../backend_api/app/services/activation_trace_compute.py#L111) | Outputs of ``names`` for a linear chain whose backbone is a nested model: Keras cannot expose the backbone's inner layers as outputs of the outer graph, so the backbone runs once as its own sub-model and the outer layers | Sin referencia nominal localizada |
| traced | [141](../../../backend_api/app/services/activation_trace_compute.py#L141) | (layers to read, block of each read layer). VGG16 keeps its own naming; custom_cnn uses the block rule. | backend_api/tests/test_activation_traces.py |
| histogram | [153](../../../backend_api/app/services/activation_trace_compute.py#L153) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| statistics | [158](../../../backend_api/app/services/activation_trace_compute.py#L158) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_ensemble_e8.py; malaria_dl_local_project/tests/test_science_e7.py |
| channel_png | [163](../../../backend_api/app/services/activation_trace_compute.py#L163) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| trace_steps | [173](../../../backend_api/app/services/activation_trace_compute.py#L173) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| compute | [194](../../../backend_api/app/services/activation_trace_compute.py#L194) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| write_atomic | [218](../../../backend_api/app/services/activation_trace_compute.py#L218) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| main | [225](../../../backend_api/app/services/activation_trace_compute.py#L225) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |

## backend_api/app/services/activation_traces.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_activation_trace_service | [120](../../../backend_api/app/services/activation_traces.py#L120) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ActivationTraceService.__init__ | [32](../../../backend_api/app/services/activation_traces.py#L32) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ActivationTraceService._supported | [37](../../../backend_api/app/services/activation_traces.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ActivationTraceService._directory | [51](../../../backend_api/app/services/activation_traces.py#L51) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ActivationTraceService.used_bytes | [54](../../../backend_api/app/services/activation_traces.py#L54) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| ActivationTraceService._read | [57](../../../backend_api/app/services/activation_traces.py#L57) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ActivationTraceService.catalog | [60](../../../backend_api/app/services/activation_traces.py#L60) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_activation_traces.py; … (20 referencias nominales; ver CSV) |
| ActivationTraceService.candidates | [67](../../../backend_api/app/services/activation_traces.py#L67) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_stage2_publication_api_e2e.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_activation_traces.py; … (10 referencias nominales; ver CSV) |
| ActivationTraceService.read | [76](../../../backend_api/app/services/activation_traces.py#L76) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |
| ActivationTraceService.delete | [82](../../../backend_api/app/services/activation_traces.py#L82) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_clean_training_outputs.py; frontend/tests/scc-xai.test.mjs; … (4 referencias nominales; ver CSV) |
| ActivationTraceService.create | [88](../../../backend_api/app/services/activation_traces.py#L88) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_event_journal.py; … (19 referencias nominales; ver CSV) |

## backend_api/app/services/artifacts.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| resolve_artifact_path | [59](../../../backend_api/app/services/artifacts.py#L59) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| artifact_error | [113](../../../backend_api/app/services/artifacts.py#L113) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| scientific_artifact | [117](../../../backend_api/app/services/artifacts.py#L117) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| resolve_artifact_reference | [190](../../../backend_api/app/services/artifacts.py#L190) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_artifacts_api.py; backend_api/tests/test_explainability_api.py; backend_api/tests/test_run_detail_api.py |
| validate_served_artifact | [205](../../../backend_api/app/services/artifacts.py#L205) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| detect_image_mime | [220](../../../backend_api/app/services/artifacts.py#L220) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/services/assessments.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AssessmentReadService.__init__ | [10](../../../backend_api/app/services/assessments.py#L10) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| AssessmentReadService.list | [13](../../../backend_api/app/services/assessments.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (72 referencias nominales; ver CSV) |
| AssessmentReadService.detail | [18](../../../backend_api/app/services/assessments.py#L18) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_microscopy_quality_services.py; … (33 referencias nominales; ver CSV) |
| AssessmentReadService.payloads | [22](../../../backend_api/app/services/assessments.py#L22) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_assessment_artifacts_sample_filter.py; malaria_dl_local_project/tests/test_campaign_executor_postgres.py; malaria_dl_local_project/tests/test_campaign_executor_e5.py; … (5 referencias nominales; ver CSV) |

## backend_api/app/services/catalog.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_catalog_service | [35](../../../backend_api/app/services/catalog.py#L35) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| CatalogService.__init__ | [9](../../../backend_api/app/services/catalog.py#L9) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| CatalogService.models | [13](../../../backend_api/app/services/catalog.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (59 referencias nominales; ver CSV) |

## backend_api/app/services/comparison_eligibility.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| checkpoint_binding | [16](../../../backend_api/app/services/comparison_eligibility.py#L16) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| decision | [45](../../../backend_api/app/services/comparison_eligibility.py#L45) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_representation_generation.py; backend_api/tests/test_cell_detection_services.py; … (32 referencias nominales; ver CSV) |
| query_error | [92](../../../backend_api/app/services/comparison_eligibility.py#L92) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_comparison_eligibility.py; frontend/tests/scc-preflight.test.mjs |
| reason | [49](../../../backend_api/app/services/comparison_eligibility.py#L49) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_check_alembic_linearity.py; backend_api/tests/test_scientific_data_api_postgres.py; … (48 referencias nominales; ver CSV) |
| ComparisonEligibilityService.__init__ | [99](../../../backend_api/app/services/comparison_eligibility.py#L99) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ComparisonEligibilityService.read | [104](../../../backend_api/app/services/comparison_eligibility.py#L104) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |
| ComparisonEligibilityService.require | [121](../../../backend_api/app/services/comparison_eligibility.py#L121) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_database_url_contract.py; backend_api/tests/test_comparison_eligibility.py; … (22 referencias nominales; ver CSV) |

## backend_api/app/services/dataset_samples.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| original_sample_image | [14](../../../backend_api/app/services/dataset_samples.py#L14) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/services/explain_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| owner_absent | [15](../../../backend_api/app/services/explain_generation.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py |
| scientific_context | [22](../../../backend_api/app/services/explain_generation.py#L22) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ExplainService.__init__ | [34](../../../backend_api/app/services/explain_generation.py#L34) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ExplainService.submit | [37](../../../backend_api/app/services/explain_generation.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_training_completion_postgres.py; malaria_dl_local_project/tests/test_result_service.py; … (11 referencias nominales; ver CSV) |
| ExplainService.preview | [53](../../../backend_api/app/services/explain_generation.py#L53) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_stage2_status_read_only.py; malaria_dl_local_project/tests/test_stage2_simplified_eligibility.py; … (5 referencias nominales; ver CSV) |
| ExplainService.context | [63](../../../backend_api/app/services/explain_generation.py#L63) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_stage2_status_read_only.py; … (52 referencias nominales; ver CSV) |
| ExplainService.specification | [77](../../../backend_api/app/services/explain_generation.py#L77) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_storage_docker_contract.py; backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_campaigns_e4.py; … (4 referencias nominales; ver CSV) |
| ExplainService.compatible | [88](../../../backend_api/app/services/explain_generation.py#L88) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_training_release_status_migration.py; backend_api/tests/test_explain_generation.py; … (5 referencias nominales; ver CSV) |
| ExplainService.matching | [105](../../../backend_api/app/services/explain_generation.py#L105) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_training_release_status_migration.py; backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_local_execution_postgres.py |
| ExplainService.reusable | [110](../../../backend_api/app/services/explain_generation.py#L110) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_assessment_e6.py |
| ExplainService.prepare | [122](../../../backend_api/app/services/explain_generation.py#L122) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (12 referencias nominales; ver CSV) |
| ExplainService.state | [133](../../../backend_api/app/services/explain_generation.py#L133) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_scientific_report.py; … (79 referencias nominales; ver CSV) |

## backend_api/app/services/model_architecture.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| family_of | [17](../../../backend_api/app/services/model_architecture.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_model_architecture.py |
| _tensors | [24](../../../backend_api/app/services/model_architecture.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _output_shape | [36](../../../backend_api/app/services/model_architecture.py#L36) | Keras shape rule, used where the record keeps no consumer tensor (Sequential). | Sin referencia nominal localizada |
| _weights | [57](../../../backend_api/app/services/model_architecture.py#L57) | (total, trainable) weights implied by the recorded layer configuration. | Sin referencia nominal localizada |
| _flatten | [74](../../../backend_api/app/services/model_architecture.py#L74) | Flatten a Keras config into `target` (execution order). Returns the name of the model's output. | Sin referencia nominal localizada |
| _last_shape | [118](../../../backend_api/app/services/model_architecture.py#L118) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _keras_block | [123](../../../backend_api/app/services/model_architecture.py#L123) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| _summarize | [144](../../../backend_api/app/services/model_architecture.py#L144) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| normalize_keras | [163](../../../backend_api/app/services/model_architecture.py#L163) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_model_architecture.py; frontend/tests/custom-cnn-training.test.mjs |
| _vit_trained | [185](../../../backend_api/app/services/model_architecture.py#L185) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _fine_tune_layers | [192](../../../backend_api/app/services/model_architecture.py#L192) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| learning_rates | [201](../../../backend_api/app/services/model_architecture.py#L201) | Initial learning rate of each optimizer group in a phase, as recorded at the phase start. | backend_api/tests/test_model_architecture.py; frontend/tests/vit-architecture.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| normalize_biomedclip | [211](../../../backend_api/app/services/model_architecture.py#L211) | The TRAIN records tensor counts, not layers. Block shapes and parameters come from the registered base (``structure``, derived once per base SHA-256); without it the ViT blocks stay a reference structure. | backend_api/tests/test_model_architecture.py |
| logical_base | [278](../../../backend_api/app/services/model_architecture.py#L278) | A zero-shot TRAIN is its own base: its registered version, checkpoint and dependency bytes. | backend_api/tests/test_model_architecture.py |
| normalize_zero_shot | [286](../../../backend_api/app/services/model_architecture.py#L286) | Logical TRAIN: nothing was trained. The image path is the base's ViT (derived once per base); the output compares the L2 image embedding with the embeddings of the registered prompts and applies softmax over the classes. | Sin referencia nominal localizada |
| recorded_base | [329](../../../backend_api/app/services/model_architecture.py#L329) | The registered base of the recipe, only if every phase of the TRAIN recorded that same checkpoint. | Sin referencia nominal localizada |
| get_model_architecture_service | [391](../../../backend_api/app/services/model_architecture.py#L391) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| block | [225](../../../backend_api/app/services/model_architecture.py#L225) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; backend_api/tests/test_model_architecture.py; backend_api/tests/test_backend_runtime_role_contract.py; … (8 referencias nominales; ver CSV) |
| block | [294](../../../backend_api/app/services/model_architecture.py#L294) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; backend_api/tests/test_model_architecture.py; backend_api/tests/test_backend_runtime_role_contract.py; … (8 referencias nominales; ver CSV) |
| ModelArchitectureService.__init__ | [342](../../../backend_api/app/services/model_architecture.py#L342) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ModelArchitectureService.vit_structure | [346](../../../backend_api/app/services/model_architecture.py#L346) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_model_architecture.py |
| ModelArchitectureService.read | [355](../../../backend_api/app/services/model_architecture.py#L355) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/services/representation_generation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| run_represent | [92](../../../backend_api/app/services/representation_generation.py#L92) | Reserve durably, acknowledge, then compute; same gate and fencing as EXPLAIN batches. | Sin referencia nominal localizada |
| request_key | [130](../../../backend_api/app/services/representation_generation.py#L130) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_representation_generation.py; backend_api/tests/test_explain_host_executor.py |
| RepresentService.__init__ | [18](../../../backend_api/app/services/representation_generation.py#L18) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| RepresentService.context | [21](../../../backend_api/app/services/representation_generation.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_stage2_status_read_only.py; … (52 referencias nominales; ver CSV) |
| RepresentService.compatible | [29](../../../backend_api/app/services/representation_generation.py#L29) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_training_release_status_migration.py; backend_api/tests/test_explain_generation.py; … (5 referencias nominales; ver CSV) |
| RepresentService.matching | [34](../../../backend_api/app/services/representation_generation.py#L34) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_training_release_status_migration.py; backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_local_execution_postgres.py |
| RepresentService.reusable | [38](../../../backend_api/app/services/representation_generation.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_assessment_e6.py |
| RepresentService.prepare | [50](../../../backend_api/app/services/representation_generation.py#L50) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (12 referencias nominales; ver CSV) |
| RepresentService.submit | [60](../../../backend_api/app/services/representation_generation.py#L60) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_training_completion_postgres.py; malaria_dl_local_project/tests/test_result_service.py; … (11 referencias nominales; ver CSV) |
| RepresentService.state | [66](../../../backend_api/app/services/representation_generation.py#L66) | Cheap status for polling: never hashes the checkpoint (reuse and the report read verify). | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_scientific_report.py; … (79 referencias nominales; ver CSV) |
| RepresentHostLauncher.__init__ | [137](../../../backend_api/app/services/representation_generation.py#L137) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| RepresentHostLauncher.launch | [140](../../../backend_api/app/services/representation_generation.py#L140) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_explain_host_executor.py; backend_api/tests/test_explain_generation.py; … (10 referencias nominales; ver CSV) |

## backend_api/app/services/scientific.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _actor_id | [43](../../../backend_api/app/services/scientific.py#L43) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _audit_state | [49](../../../backend_api/app/services/scientific.py#L49) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificError.__init__ | [13](../../../backend_api/app/services/scientific.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificService.create | [62](../../../backend_api/app/services/scientific.py#L62) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_event_journal.py; … (19 referencias nominales; ver CSV) |
| ScientificService.get | [98](../../../backend_api/app/services/scientific.py#L98) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_cell_classification_postgres.py; … (62 referencias nominales; ver CSV) |
| ScientificService.list | [105](../../../backend_api/app/services/scientific.py#L105) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (72 referencias nominales; ver CSV) |
| ScientificService.update | [109](../../../backend_api/app/services/scientific.py#L109) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_lineage_children_api.py; … (54 referencias nominales; ver CSV) |
| ScientificService.archive | [140](../../../backend_api/app/services/scientific.py#L140) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_data_api_postgres.py |
| ScientificService.traceability | [164](../../../backend_api/app/services/scientific.py#L164) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_data_api_postgres.py; backend_api/tests/test_assessment_artifacts_sample_filter.py; backend_api/tests/test_scc_core.py; … (7 referencias nominales; ver CSV) |

## backend_api/app/services/scientific_preflight.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| known | [35](../../../backend_api/app/services/scientific_preflight.py#L35) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_catalog_postgres.py; frontend/tests/scc-preflight.test.mjs |
| unknown | [39](../../../backend_api/app/services/scientific_preflight.py#L39) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_lineage_children_api.py; backend_api/tests/test_detection_crop_equivalence.py; … (29 referencias nominales; ver CSV) |
| verdict | [43](../../../backend_api/app/services/scientific_preflight.py#L43) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_comparison_eligibility.py; … (4 referencias nominales; ver CSV) |
| safe_configuration | [49](../../../backend_api/app/services/scientific_preflight.py#L49) | Allowlisted effective fields; free-form snapshots never become public payloads. | Sin referencia nominal localizada |
| ScientificPreflightService.__init__ | [71](../../../backend_api/app/services/scientific_preflight.py#L71) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificPreflightService.read | [77](../../../backend_api/app/services/scientific_preflight.py#L77) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |
| ScientificPreflightService._individual | [514](../../../backend_api/app/services/scientific_preflight.py#L514) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificPreflightService._differences | [534](../../../backend_api/app/services/scientific_preflight.py#L534) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificPreflightService._population | [565](../../../backend_api/app/services/scientific_preflight.py#L565) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| finding | [88](../../../backend_api/app/services/scientific_preflight.py#L88) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | frontend/tests/frotis-v3.test.mjs; frontend/tests/scc-preflight.test.mjs |
| query | [95](../../../backend_api/app/services/scientific_preflight.py#L95) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_assessment_population_query.py; backend_api/tests/test_db_purge_tool.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (17 referencias nominales; ver CSV) |
| scope | [440](../../../backend_api/app/services/scientific_preflight.py#L440) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_microscopy_quality_services.py; backend_api/tests/test_run_detail_api.py; … (34 referencias nominales; ver CSV) |
| parts | [445](../../../backend_api/app/services/scientific_preflight.py#L445) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_storage_docker_contract.py; backend_api/tests/test_yolo_detector_adapter.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (5 referencias nominales; ver CSV) |
| compare | [535](../../../backend_api/app/services/scientific_preflight.py#L535) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_ensemble_e8.py; malaria_dl_local_project/tests/test_science_e7.py |
| resolve_e5_checkpoint | [300](../../../backend_api/app/services/scientific_preflight.py#L300) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/services/scientific_public.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| public_evidence | [12](../../../backend_api/app/services/scientific_public.py#L12) | Remove storage locators recursively, including extension metadata. | backend_api/tests/test_scc_core.py |
| assessment_projection | [25](../../../backend_api/app/services/scientific_public.py#L25) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/services/scientific_report.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| number | [19](../../../backend_api/app/services/scientific_report.py#L19) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_services.py; backend_api/tests/test_cell_activation.py; malaria_dl_local_project/tests/test_cli01.py; … (8 referencias nominales; ver CSV) |
| checkpoint_evidence | [29](../../../backend_api/app/services/scientific_report.py#L29) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py |
| validate_samples | [44](../../../backend_api/app/services/scientific_report.py#L44) | Never deduplicate or repair a scientific population silently. | backend_api/tests/test_scientific_report.py |
| population_coverage | [72](../../../backend_api/app/services/scientific_report.py#L72) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py |
| consensus | [82](../../../backend_api/app/services/scientific_report.py#L82) | All ratios use the explicitly identified common population. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_scientific_validation_contract.py; … (5 referencias nominales; ver CSV) |
| superiority_answer | [151](../../../backend_api/app/services/scientific_report.py#L151) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py |
| ScientificReportService.__init__ | [162](../../../backend_api/app/services/scientific_report.py#L162) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificReportService.historical | [166](../../../backend_api/app/services/scientific_report.py#L166) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; … (14 referencias nominales; ver CSV) |
| ScientificReportService.metrics | [179](../../../backend_api/app/services/scientific_report.py#L179) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_read_only.py; … (51 referencias nominales; ver CSV) |
| ScientificReportService.assessment_metrics | [201](../../../backend_api/app/services/scientific_report.py#L201) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificReportService.prediction_population | [230](../../../backend_api/app/services/scientific_report.py#L230) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py |
| ScientificReportService.read | [273](../../../backend_api/app/services/scientific_report.py#L273) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/services/scientific_representations.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _round | [19](../../../backend_api/app/services/scientific_representations.py#L19) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _load | [23](../../../backend_api/app/services/scientific_representations.py#L23) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| representation_evidence | [34](../../../backend_api/app/services/scientific_representations.py#L34) | One RUN: its REPRESENT for the selected EVALUATE, or why there is none. Returns (dto, embeddings). | backend_api/tests/test_representation_generation.py |
| cka_matrix | [71](../../../backend_api/app/services/scientific_representations.py#L71) | Pairwise linear CKA over the samples each pair has in common (ordered by sample id). | backend_api/tests/test_representation_generation.py |
| representations | [91](../../../backend_api/app/services/scientific_representations.py#L91) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | frontend/tests/scc-selection.test.mjs |

## backend_api/app/services/scientific_results.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_scientific_read_service | [47](../../../backend_api/app/services/scientific_results.py#L47) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificReadService.__init__ | [13](../../../backend_api/app/services/scientific_results.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificReadService.read | [17](../../../backend_api/app/services/scientific_results.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/services/scientific_validation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _actor | [24](../../../backend_api/app/services/scientific_validation.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _state | [30](../../../backend_api/app/services/scientific_validation.py#L30) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService.__init__ | [38](../../../backend_api/app/services/scientific_validation.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ScientificValidationService._engine | [42](../../../backend_api/app/services/scientific_validation.py#L42) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_case_gradcam_service.py |
| ScientificValidationService.create | [45](../../../backend_api/app/services/scientific_validation.py#L45) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_event_journal.py; … (19 referencias nominales; ver CSV) |
| ScientificValidationService.get | [126](../../../backend_api/app/services/scientific_validation.py#L126) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_cell_classification_postgres.py; … (62 referencias nominales; ver CSV) |
| ScientificValidationService.list | [133](../../../backend_api/app/services/scientific_validation.py#L133) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (72 referencias nominales; ver CSV) |
| ScientificValidationService.update | [137](../../../backend_api/app/services/scientific_validation.py#L137) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_lineage_children_api.py; … (54 referencias nominales; ver CSV) |
| ScientificValidationService.archive | [162](../../../backend_api/app/services/scientific_validation.py#L162) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_data_api_postgres.py |
| ScientificValidationService._annotation_audit_state | [182](../../../backend_api/app/services/scientific_validation.py#L182) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService._ensure_annotation_session | [186](../../../backend_api/app/services/scientific_validation.py#L186) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService.create_annotation | [192](../../../backend_api/app/services/scientific_validation.py#L192) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService.list_annotations | [229](../../../backend_api/app/services/scientific_validation.py#L229) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService.get_annotation | [236](../../../backend_api/app/services/scientific_validation.py#L236) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService.update_annotation | [246](../../../backend_api/app/services/scientific_validation.py#L246) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ScientificValidationService.annotation_history | [283](../../../backend_api/app/services/scientific_validation.py#L283) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## backend_api/app/services/training_summaries.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _summary_row | [351](../../../backend_api/app/services/training_summaries.py#L351) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_training_summaries_api.py |
| list_training_summaries | [368](../../../backend_api/app/services/training_summaries.py#L368) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_e6_lineage_read_only.py; backend_api/tests/test_training_summaries_api.py |

## backend_api/app/services/training_trajectories.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| score | [18](../../../backend_api/app/services/training_trajectories.py#L18) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_training_trajectories.py; backend_api/tests/test_activation_traces.py; … (19 referencias nominales; ver CSV) |
| governed_ids | [25](../../../backend_api/app/services/training_trajectories.py#L25) | relative_path → sample_id, only for paths that occur exactly once. | Sin referencia nominal localizada |
| get_training_trajectory_service | [99](../../../backend_api/app/services/training_trajectories.py#L99) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| TrainingTrajectoryService.__init__ | [35](../../../backend_api/app/services/training_trajectories.py#L35) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| TrainingTrajectoryService.read | [38](../../../backend_api/app/services/training_trajectories.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/services/vit_structure.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| VitStructureService.__init__ | [21](../../../backend_api/app/services/vit_structure.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| VitStructureService.path | [24](../../../backend_api/app/services/vit_structure.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_cell_classification_postgres.py; … (188 referencias nominales; ver CSV) |
| VitStructureService._saved | [29](../../../backend_api/app/services/vit_structure.py#L29) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| VitStructureService.read | [35](../../../backend_api/app/services/vit_structure.py#L35) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_smear_reset_tool.py; … (56 referencias nominales; ver CSV) |

## backend_api/app/services/vit_structure_compute.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| group_of | [22](../../../backend_api/app/services/vit_structure_compute.py#L22) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_model_architecture.py |
| registered_size | [34](../../../backend_api/app/services/vit_structure_compute.py#L34) | Image side of the base's own registered configuration (preprocess_cfg.size or vision_cfg.image_size). | Sin referencia nominal localizada |
| text_tower | [48](../../../backend_api/app/services/vit_structure_compute.py#L48) | Parameters of the text tower and the logit scale, read from the base checkpoint's tensors (no model built). A zero-shot classifier compares the image embedding with the prompts' embeddings through them. | Sin referencia nominal localizada |
| compute | [70](../../../backend_api/app/services/vit_structure_compute.py#L70) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| write_atomic | [116](../../../backend_api/app/services/vit_structure_compute.py#L116) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py |
| main | [123](../../../backend_api/app/services/vit_structure_compute.py#L123) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |

## frontend/src/auth.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AuthProvider | [24](../../../frontend/src/auth.tsx#L24) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@29 | [29](../../../frontend/src/auth.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@29.callback@30 | [30](../../../frontend/src/auth.tsx#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@29.callback@34 | [34](../../../frontend/src/auth.tsx#L34) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@37 | [37](../../../frontend/src/auth.tsx#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@37.callback@44 | [44](../../../frontend/src/auth.tsx#L44) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@37.callback@47 | [47](../../../frontend/src/auth.tsx#L47) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@37.callback@52 | [52](../../../frontend/src/auth.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@37.callback@59 | [59](../../../frontend/src/auth.tsx#L59) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@62 | [62](../../../frontend/src/auth.tsx#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@62.retrySession | [66](../../../frontend/src/auth.tsx#L66) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@62.retrySession.callback@66 | [66](../../../frontend/src/auth.tsx#L66) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@62.login | [67](../../../frontend/src/auth.tsx#L67) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthProvider.callback@62.logout | [80](../../../frontend/src/auth.tsx#L80) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAuth | [90](../../../frontend/src/auth.tsx#L90) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/scc-selection.test.mjs; … (5 referencias nominales; ver CSV) |
| ProtectedRoute | [96](../../../frontend/src/auth.tsx#L96) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |
| SessionStatus | [105](../../../frontend/src/auth.tsx#L105) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |

## frontend/src/components/ScientificResults.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ScientificResultsView | [15](../../../frontend/src/components/ScientificResults.tsx#L15) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@20 | [20](../../../frontend/src/components/ScientificResults.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@20.callback@23 | [23](../../../frontend/src/components/ScientificResults.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@20.callback@23 | [23](../../../frontend/src/components/ScientificResults.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@20.callback@23.callback@24 | [24](../../../frontend/src/components/ScientificResults.tsx#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@34 | [34](../../../frontend/src/components/ScientificResults.tsx#L34) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@35 | [35](../../../frontend/src/components/ScientificResults.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@35.callback@36 | [36](../../../frontend/src/components/ScientificResults.tsx#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResultsView.callback@35.callback@36 | [36](../../../frontend/src/components/ScientificResults.tsx#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResults | [41](../../../frontend/src/components/ScientificResults.tsx#L41) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResults.callback@43 | [43](../../../frontend/src/components/ScientificResults.tsx#L43) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResults.callback@43.callback@46 | [46](../../../frontend/src/components/ScientificResults.tsx#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResults.callback@43.callback@47 | [47](../../../frontend/src/components/ScientificResults.tsx#L47) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificResults.callback@43.callback@48 | [48](../../../frontend/src/components/ScientificResults.tsx#L48) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |

## frontend/src/components/StatusBadge.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| StatusBadge | [5](../../../frontend/src/components/StatusBadge.tsx#L5) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/cell-review/AuthenticatedCellImage.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AuthenticatedImageCacheProvider | [30](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L30) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| AuthenticatedImageCacheProvider.callback@36 | [36](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| AuthenticatedImageCacheProvider.callback@36.callback@38 | [38](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L38) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| AuthenticatedImageCacheProvider.callback@36.callback@38.callback@39 | [39](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L39) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| rememberCropBlob | [52](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L52) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| readCachedCropBlob | [63](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L63) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createCropBlobRequest | [73](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L73) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createCropBlobRequest.callback@81 | [81](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L81) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createCropBlobRequest.callback@85 | [85](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L85) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob | [96](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L96) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111 | [111](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L111) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.release | [114](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L114) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.finish | [121](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L121) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.onAbort | [128](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L128) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.onAbort.callback@129 | [129](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.callback@133 | [133](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L133) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.callback@133.callback@133 | [133](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L133) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.callback@134 | [134](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| loadCachedCropBlob.callback@111.callback@134.callback@134 | [134](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAuthenticatedObjectUrl | [151](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L151) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/scc-xai.test.mjs |
| useAuthenticatedObjectUrl.callback@163 | [163](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L163) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/scc-xai.test.mjs |
| useAuthenticatedObjectUrl.callback@163.callback@173 | [173](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/scc-xai.test.mjs |
| useAuthenticatedObjectUrl.callback@163.callback@182 | [182](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L182) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/scc-xai.test.mjs |
| useAuthenticatedObjectUrl.callback@163.callback@185 | [185](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L185) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/scc-xai.test.mjs |
| AuthenticatedCropImage | [204](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L204) | FunctionExpression; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthenticatedCropImage.callback@213 | [213](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L213) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthenticatedCropImage.callback@213.callback@225 | [225](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L225) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthenticatedCropImage.callback@213.callback@225.callback@226 | [226](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L226) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthenticatedCropImage.callback@213.callback@234 | [234](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L234) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AuthenticatedCropImage.callback@238 | [238](../../../frontend/src/components/cell-review/AuthenticatedCellImage.tsx#L238) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/model-architecture/ActivationTracePanel.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| png | [22](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_microscopy_quality_services.py; … (67 referencias nominales; ver CSV) |
| message | [23](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_stage2_status_read_only.py; … (32 referencias nominales; ver CSV) |
| shortId | [24](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stat | [26](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_lineage_children_postgres.py; … (184 referencias nominales; ver CSV) |
| shapeOf | [27](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| drawnBlock | [29](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| drawnBlock.callback@30 | [30](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| outcomeKey | [33](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| outcomeLabel | [35](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Outcome | [38](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L38) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| Modal | [44](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L44) | Native modal: focus trap, Escape and backdrop come from the browser. | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/run-detail-explainability.test.mjs; frontend/tests/model-ai-navigation.test.mjs; … (8 referencias nominales; ver CSV) |
| Modal.callback@46 | [46](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/run-detail-explainability.test.mjs; frontend/tests/model-ai-navigation.test.mjs; … (8 referencias nominales; ver CSV) |
| Modal.callback@52 | [52](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/run-detail-explainability.test.mjs; frontend/tests/model-ai-navigation.test.mjs; … (8 referencias nominales; ver CSV) |
| MapCanvas | [58](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L58) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MapCanvas.callback@60 | [60](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MapCanvas.callback@60.callback@60 | [60](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps | [64](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L64) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@68 | [68](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L68) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@70 | [70](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@70.callback@70 | [70](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@70.callback@70 | [70](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@82 | [82](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L82) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@83 | [83](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L83) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@88 | [88](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L88) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SpatialMaps.callback@88.callback@90 | [90](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L90) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| explainHint | [100](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L100) | Where to compare this trace with the explanations: Grad-CAM weighs the last convolutional block; a ViT has none. | Sin referencia nominal localizada |
| explainHint.callback@102 | [102](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L102) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellImage | [107](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L107) | The cell image as the access to «Vista ampliada» (rule: every cell image opens it, unless its EVALUATE context is missing). | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/cell-review-workspace.test.mjs; frontend/tests/scc-art.test.mjs; … (6 referencias nominales; ver CSV) |
| StepBody | [113](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L113) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepBody.callback@129 | [129](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ActivationTracePanel | [134](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L134) | Saved forward passes of one TRAIN. Opening it reads files only; the model runs when «Calcular» is pressed. | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@161 | [161](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L161) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@167 | [167](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L167) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@173 | [173](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@173.callback@177 | [177](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L177) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@173.callback@178 | [178](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L178) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@173.callback@179 | [179](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L179) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@182 | [182](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L182) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@185 | [185](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L185) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@185.callback@190 | [190](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L190) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@185.callback@191 | [191](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L191) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@196 | [196](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L196) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@197 | [197](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L197) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@197.callback@200 | [200](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L200) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@197.callback@200.callback@200 | [200](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L200) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@197.callback@201 | [201](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L201) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@204 | [204](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L204) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@204.callback@206 | [206](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L206) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@210 | [210](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L210) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@210.callback@210 | [210](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L210) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@213 | [213](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L213) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@213.callback@216 | [216](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L216) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@213.callback@216 | [216](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L216) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@213.callback@219 | [219](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L219) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@221 | [221](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L221) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@221.callback@221 | [221](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L221) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.go | [223](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L223) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.onKeys | [224](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L224) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.calculate | [230](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L230) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.remove | [239](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L239) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.compareWith | [249](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L249) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.loadCurve | [254](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L254) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.loadCurve.callback@258 | [258](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L258) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.loadCurve.callback@258 | [258](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L258) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.selectRun | [261](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L261) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@264 | [264](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L264) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@265 | [265](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L265) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.actives | [266](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L266) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.actives.callback@266 | [266](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L266) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@268 | [268](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L268) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@272 | [272](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L272) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@274 | [274](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L274) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@275 | [275](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L275) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@275 | [275](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L275) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@282 | [282](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L282) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@283 | [283](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L283) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@295 | [295](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L295) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@299 | [299](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L299) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@300 | [300](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L300) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@301 | [301](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L301) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@313 | [313](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L313) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@313 | [313](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L313) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@346 | [346](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L346) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@355 | [355](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L355) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@359 | [359](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L359) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@361 | [361](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L361) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@361 | [361](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L361) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@380 | [380](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L380) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@381 | [381](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L381) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@381.callback@382 | [382](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L382) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@383 | [383](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L383) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@385 | [385](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L385) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@385.callback@392 | [392](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L392) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@398 | [398](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L398) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@401 | [401](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L401) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@401.callback@405 | [405](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L405) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@401.callback@406 | [406](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L406) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |
| ActivationTracePanel.callback@401.callback@407 | [407](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L407) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |

## frontend/src/components/model-architecture/ArchitectureChart.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| blockTitle | [12](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L12) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Frame | [14](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L14) | FunctionDeclaration; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_runtime_environment_contract.py |
| Arrow | [21](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| blockWidth | [24](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| wrapLabel | [29](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L29) | Words of a block name in lines of at most `max` characters; a single long word keeps its own line. | frontend/tests/cell-expanded-view.test.mjs |
| Labels | [39](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L39) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs; frontend/tests/campaign-configuration.test.mjs |
| Labels.callback@48 | [48](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L48) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs; frontend/tests/campaign-configuration.test.mjs |
| layout | [59](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L59) | Lays blocks left to right: each one reports its own width. | backend_api/tests/test_image_ingestion_services.py; frontend/tests/clean-routing.test.mjs; frontend/tests/smear-ui-refresh.test.mjs; … (6 referencias nominales; ver CSV) |
| layout.callback@61 | [61](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_image_ingestion_services.py; frontend/tests/clean-routing.test.mjs; frontend/tests/smear-ui-refresh.test.mjs; … (6 referencias nominales; ver CSV) |
| StackedMaps | [65](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L65) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StackedMaps.callback@66 | [66](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L66) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StackedMaps.callback@72 | [72](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StackedMaps.callback@72.callback@77 | [77](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Blocks3D | [85](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L85) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Blocks3D.callback@86 | [86](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L86) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Blocks3D.callback@91 | [91](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L91) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| BlockBars | [104](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L104) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| BlockBars.callback@105 | [105](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L105) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| BlockBars.callback@108 | [108](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L108) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseGraph | [120](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L120) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseGraph.callback@121 | [121](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L121) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseGraph.callback@126 | [126](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L126) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseGraph.callback@129 | [129](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseGraph.callback@129.callback@133 | [133](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L133) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| denseUnits | [143](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L143) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| denseUnits.callback@145 | [145](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L145) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| DenseConnections | [148](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L148) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@149 | [149](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L149) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@151 | [151](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L151) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@154 | [154](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L154) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.unitX | [156](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L156) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@159 | [159](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@159.callback@160 | [160](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L160) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@164 | [164](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L164) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@168 | [168](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L168) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@168.callback@169 | [169](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L169) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| DenseConnections.callback@168.callback@169 | [169](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L169) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow | [179](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L179) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@180 | [180](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L180) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@180 | [180](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L180) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@181 | [181](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L181) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@182 | [182](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L182) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@182 | [182](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L182) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@183 | [183](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L183) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@186 | [186](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L186) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@186 | [186](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L186) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@198 | [198](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L198) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitFlow.callback@198.callback@201 | [201](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L201) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitBlocks | [207](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L207) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitBlocks.callback@208 | [208](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L208) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VitBlocks.callback@211 | [211](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L211) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| LayerTable | [223](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L223) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| LayerTable.callback@225 | [225](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L225) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| LayerTable.callback@228 | [228](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L228) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| LayerTable.callback@231 | [231](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L231) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| LayerTable.callback@233 | [233](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L233) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| LayerTable.callback@237 | [237](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L237) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ArchitectureChart | [242](../../../frontend/src/components/model-architecture/ArchitectureChart.tsx#L242) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/cell-expanded-view.test.mjs |

## frontend/src/components/model-architecture/ArchitectureDetail.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ArchitectureDetail | [14](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L14) | One model's architecture; Arquitectura del modelo and Análisis de Modelos differ only in who owns the view and the phase. | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@17 | [17](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L17) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@23 | [23](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@23 | [23](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.pickBlock | [25](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.pickBlock.callback@27 | [27](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@29 | [29](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@30 | [30](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@45 | [45](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@54 | [54](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L54) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@54.callback@55 | [55](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L55) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@59 | [59](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L59) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitectureDetail.callback@59.callback@60 | [60](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/model-architecture/ArchitecturePanel.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| runLabel | [10](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ArchitecturePanel | [13](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L13) | Sección Arquitectura de Análisis de Modelos: one selected RUN at a time, read only while the section is open. | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@20 | [20](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@22 | [22](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@25 | [25](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@27 | [27](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@27.callback@28 | [28](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@31 | [31](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L31) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| ArchitecturePanel.callback@31.callback@31 | [31](../../../frontend/src/components/model-architecture/ArchitecturePanel.tsx#L31) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/model-architecture/MathFunctionPanel.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| MathFunctionPanel | [4](../../../frontend/src/components/model-architecture/MathFunctionPanel.tsx#L4) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MathFunctionPanel.callback@8 | [8](../../../frontend/src/components/model-architecture/MathFunctionPanel.tsx#L8) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MathFunctionPanel.callback@9 | [9](../../../frontend/src/components/model-architecture/MathFunctionPanel.tsx#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MathFunctionPanel.callback@11 | [11](../../../frontend/src/components/model-architecture/MathFunctionPanel.tsx#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MathFunctionPanel.callback@12 | [12](../../../frontend/src/components/model-architecture/MathFunctionPanel.tsx#L12) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/model-architecture/TraceCharts.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ScoreBar | [5](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L5) | Probability on a 0–1 track with the decision threshold: how far a cell fell from the other side. | Sin referencia nominal localizada |
| ScoreBar.clamp | [6](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L6) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile | [18](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L18) | Share of active values at every step, for one or two cells: where the signal of a cell fades or survives. | Sin referencia nominal localizada |
| StepProfile.x | [20](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.y | [21](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@24 | [24](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@27 | [27](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@28 | [28](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@28.callback@29 | [29](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@28.callback@31 | [31](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L31) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@33 | [33](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@33.callback@33 | [33](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| StepProfile.callback@36 | [36](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VectorHistogram | [41](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L41) | Distribution of a dense vector: a ReLU layer piles values at zero and spreads the few active ones. | Sin referencia nominal localizada |
| VectorHistogram.callback@45 | [45](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves | [57](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L57) | Loss of the TRAIN by epoch, with the epoch whose checkpoint processed the cell. | Sin referencia nominal localizada |
| MiniCurves.callback@60 | [60](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.callback@60.callback@60 | [60](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.callback@60.callback@60 | [60](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.x | [63](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L63) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.y | [64](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L64) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.callback@70 | [70](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.callback@70.callback@70 | [70](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniCurves.callback@70.callback@70 | [70](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/model-architecture/architectureViews.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| viewsFor | [17](../../../frontend/src/components/model-architecture/architectureViews.ts#L17) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| isTraceable | [21](../../../frontend/src/components/model-architecture/architectureViews.ts#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| resolveView | [22](../../../frontend/src/components/model-architecture/architectureViews.ts#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| resolveView.callback@24 | [24](../../../frontend/src/components/model-architecture/architectureViews.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| isTrained | [28](../../../frontend/src/components/model-architecture/architectureViews.ts#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| shapeText | [29](../../../frontend/src/components/model-architecture/architectureViews.ts#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| countText | [30](../../../frontend/src/components/model-architecture/architectureViews.ts#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| outputText | [36](../../../frontend/src/components/model-architecture/architectureViews.ts#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-scientific-parameters.test.mjs; frontend/tests/training-history.test.mjs; frontend/tests/scc-art.test.mjs; … (17 referencias nominales; ver CSV) |
| lossText | [41](../../../frontend/src/components/model-architecture/architectureViews.ts#L41) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| isSpatial | [46](../../../frontend/src/components/model-architecture/architectureViews.ts#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| spatialSize | [49](../../../frontend/src/components/model-architecture/architectureViews.ts#L49) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| depthSize | [50](../../../frontend/src/components/model-architecture/architectureViews.ts#L50) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| GlobalAveragePooling2D | [53](../../../frontend/src/components/model-architecture/architectureViews.ts#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_activation_traces.py; backend_api/tests/test_cell_classification_services.py; backend_api/tests/test_model_architecture.py; … (11 referencias nominales; ver CSV) |
| GlobalMaxPooling2D | [53](../../../frontend/src/components/model-architecture/architectureViews.ts#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Flatten | [53](../../../frontend/src/components/model-architecture/architectureViews.ts#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_assessment_e6.py; … (4 referencias nominales; ver CSV) |
| Dense | [54](../../../frontend/src/components/model-architecture/architectureViews.ts#L54) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_activation_traces.py; backend_api/tests/test_cell_classification_services.py; backend_api/tests/test_model_architecture.py; … (19 referencias nominales; ver CSV) |
| splitHead | [61](../../../frontend/src/components/model-architecture/architectureViews.ts#L61) | The head drawn as the layers that transform the tensor (pooling or flatten, each Dense), one block each, so the drawing has one element per step of a cell's trace. Dropout is the identity in inference and joins the layer | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@62 | [62](../../../frontend/src/components/model-architecture/architectureViews.ts#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@63 | [63](../../../frontend/src/components/model-architecture/architectureViews.ts#L63) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@67 | [67](../../../frontend/src/components/model-architecture/architectureViews.ts#L67) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@68 | [68](../../../frontend/src/components/model-architecture/architectureViews.ts#L68) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@68.callback@69 | [69](../../../frontend/src/components/model-architecture/architectureViews.ts#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@68.callback@70 | [70](../../../frontend/src/components/model-architecture/architectureViews.ts#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@68.callback@72 | [72](../../../frontend/src/components/model-architecture/architectureViews.ts#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@74 | [74](../../../frontend/src/components/model-architecture/architectureViews.ts#L74) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| splitHead.callback@77 | [77](../../../frontend/src/components/model-architecture/architectureViews.ts#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/model-architecture/mathOperations.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| node | [9](../../../frontend/src/components/model-architecture/mathOperations.tsx#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_case_gradcam_service.py; backend_api/tests/test_docker_postgres_contract_guard.py; … (57 referencias nominales; ver CSV) |
| v | [10](../../../frontend/src/components/model-architecture/mathOperations.tsx#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_cell_activation_read_only.py; … (282 referencias nominales; ver CSV) |
| num | [11](../../../frontend/src/components/model-architecture/mathOperations.tsx#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (78 referencias nominales; ver CSV) |
| op | [12](../../../frontend/src/components/model-architecture/mathOperations.tsx#L12) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_lineage_children_postgres.py; … (213 referencias nominales; ver CSV) |
| word | [13](../../../frontend/src/components/model-architecture/mathOperations.tsx#L13) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (22 referencias nominales; ver CSV) |
| row | [14](../../../frontend/src/components/model-architecture/mathOperations.tsx#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_cell_classification_postgres.py; … (131 referencias nominales; ver CSV) |
| sub | [15](../../../frontend/src/components/model-architecture/mathOperations.tsx#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (58 referencias nominales; ver CSV) |
| sup | [16](../../../frontend/src/components/model-architecture/mathOperations.tsx#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_detection_crop_equivalence.py; … (35 referencias nominales; ver CSV) |
| under | [17](../../../frontend/src/components/model-architecture/mathOperations.tsx#L17) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_dataset_split_isolation.py; malaria_dl_local_project/tests/test_scc_evidence_fase0.py; malaria_dl_local_project/tests/test_science_extensibility.py |
| frac | [18](../../../frontend/src/components/model-architecture/mathOperations.tsx#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_cell_classification_services.py; malaria_dl_local_project/tests/test_train_checkpoint_policy_args.py; … (8 referencias nominales; ver CSV) |
| root | [19](../../../frontend/src/components/model-architecture/mathOperations.tsx#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (87 referencias nominales; ver CSV) |
| paren | [20](../../../frontend/src/components/model-architecture/mathOperations.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_lineage_children_api.py; … (151 referencias nominales; ver CSV) |
| indices | [21](../../../frontend/src/components/model-architecture/mathOperations.tsx#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_minimal_keras_inference.py |
| indices.callback@21 | [21](../../../frontend/src/components/model-architecture/mathOperations.tsx#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_minimal_keras_inference.py |
| tensor | [22](../../../frontend/src/components/model-architecture/mathOperations.tsx#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; … (47 referencias nominales; ver CSV) |
| shifted | [23](../../../frontend/src/components/model-architecture/mathOperations.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| math | [24](../../../frontend/src/components/model-architecture/mathOperations.tsx#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_report.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_minimal_keras_inference.py; … (9 referencias nominales; ver CSV) |
| pair | [26](../../../frontend/src/components/model-architecture/mathOperations.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_db_purge_tool.py; backend_api/tests/test_backend_runtime_role_contract.py; malaria_dl_local_project/tests/test_result_service.py; … (8 referencias nominales; ver CSV) |
| activationOf | [27](../../../frontend/src/components/model-architecture/mathOperations.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| convolution | [30](../../../frontend/src/components/model-architecture/mathOperations.tsx#L30) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_cli01.py; frontend/tests/vit-architecture.test.mjs; … (7 referencias nominales; ver CSV) |
| normalization | [38](../../../frontend/src/components/model-architecture/mathOperations.tsx#L38) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_execution_record_readers.py; … (13 referencias nominales; ver CSV) |
| pooling | [44](../../../frontend/src/components/model-architecture/mathOperations.tsx#L44) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_ensemble_e8.py; frontend/tests/custom-cnn-training.test.mjs |
| sizeText | [49](../../../frontend/src/components/model-architecture/mathOperations.tsx#L49) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| list | [50](../../../frontend/src/components/model-architecture/mathOperations.tsx#L50) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (108 referencias nominales; ver CSV) |
| describe | [52](../../../frontend/src/components/model-architecture/mathOperations.tsx#L52) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-ui-refresh.test.mjs; frontend/tests/vit-architecture.test.mjs; frontend/tests/frotis-v3.test.mjs; … (4 referencias nominales; ver CSV) |
| describe.callback@61 | [61](../../../frontend/src/components/model-architecture/mathOperations.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/smear-ui-refresh.test.mjs; frontend/tests/vit-architecture.test.mjs; frontend/tests/frotis-v3.test.mjs; … (4 referencias nominales; ver CSV) |
| lossOperation | [77](../../../frontend/src/components/model-architecture/mathOperations.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| referenceOperations | [83](../../../frontend/src/components/model-architecture/mathOperations.tsx#L83) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| blockOperations | [103](../../../frontend/src/components/model-architecture/mathOperations.tsx#L103) | The operations of one block, built only from what its layers recorded; repeated layers collapse into one line. | frontend/tests/model-explorer.test.mjs |
| blockOperations.callback@106 | [106](../../../frontend/src/components/model-architecture/mathOperations.tsx#L106) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| layerOperations | [111](../../../frontend/src/components/model-architecture/mathOperations.tsx#L111) | Operations of an explicit set of layers (one step of a cell's trace); repeated layers collapse into one line. | Sin referencia nominal localizada |
| layerOperations.callback@113 | [113](../../../frontend/src/components/model-architecture/mathOperations.tsx#L113) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| tensorPath | [124](../../../frontend/src/components/model-architecture/mathOperations.tsx#L124) | Real tensor path. Per-sample values are absent on purpose: this view describes the model, not one prediction. | frontend/tests/model-explorer.test.mjs |
| tensorPath.callback@127 | [127](../../../frontend/src/components/model-architecture/mathOperations.tsx#L127) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| tensorPath.callback@130 | [130](../../../frontend/src/components/model-architecture/mathOperations.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/model-architecture/traceCode.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| pair | [4](../../../frontend/src/components/model-architecture/traceCode.ts#L4) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_db_purge_tool.py; backend_api/tests/test_backend_runtime_role_contract.py; malaria_dl_local_project/tests/test_result_service.py; … (8 referencias nominales; ver CSV) |
| quoted | [5](../../../frontend/src/components/model-architecture/traceCode.ts#L5) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_postgres_transaction_isolation.py |
| args | [6](../../../frontend/src/components/model-architecture/traceCode.ts#L6) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; … (107 referencias nominales; ver CSV) |
| args.callback@6 | [6](../../../frontend/src/components/model-architecture/traceCode.ts#L6) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; … (107 referencias nominales; ver CSV) |
| layerCode | [9](../../../frontend/src/components/model-architecture/traceCode.ts#L9) | Keras call that rebuilds one recorded layer; only settings the TRAIN registered appear, nothing is assumed. | Sin referencia nominal localizada |
| isBackboneBlock | [33](../../../frontend/src/components/model-architecture/traceCode.ts#L33) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| isBackboneBlock.callback@34 | [34](../../../frontend/src/components/model-architecture/traceCode.ts#L34) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stepLayers | [39](../../../frontend/src/components/model-architecture/traceCode.ts#L39) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stepLayers.callback@41 | [41](../../../frontend/src/components/model-architecture/traceCode.ts#L41) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stepLayers.callback@42 | [42](../../../frontend/src/components/model-architecture/traceCode.ts#L42) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| vitCode | [47](../../../frontend/src/components/model-architecture/traceCode.ts#L47) | ViT step (timm VisionTransformer inside OpenCLIP): what the block computes, with the registered base's sizes. | Sin referencia nominal localizada |
| stepCode | [60](../../../frontend/src/components/model-architecture/traceCode.ts#L60) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| stepCode.callback@63 | [63](../../../frontend/src/components/model-architecture/traceCode.ts#L63) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| stepCode.callback@70 | [70](../../../frontend/src/components/model-architecture/traceCode.ts#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| stepTitle | [78](../../../frontend/src/components/model-architecture/traceCode.ts#L78) | Readable title of a step: the architecture names blocks; head layers are named by what they do. | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| stepTitle.callback@80 | [80](../../../frontend/src/components/model-architecture/traceCode.ts#L80) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| stepTitle.callback@82 | [82](../../../frontend/src/components/model-architecture/traceCode.ts#L82) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |
| stepTitle.callback@85 | [85](../../../frontend/src/components/model-architecture/traceCode.ts#L85) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/vit-architecture.test.mjs; frontend/tests/model-explorer.test.mjs; frontend/tests/custom-cnn-training.test.mjs |

## frontend/src/components/model-architecture/traceColor.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| callback@3 | [3](../../../frontend/src/components/model-architecture/traceColor.ts#L3) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| callback@3.callback@3 | [3](../../../frontend/src/components/model-architecture/traceColor.ts#L3) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| callback@5 | [5](../../../frontend/src/components/model-architecture/traceColor.ts#L5) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| cividis | [7](../../../frontend/src/components/model-architecture/traceColor.ts#L7) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| cividis.callback@10 | [10](../../../frontend/src/components/model-architecture/traceColor.ts#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| load | [16](../../../frontend/src/components/model-architecture/traceColor.ts#L16) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_lineage_children_postgres.py; … (159 referencias nominales; ver CSV) |
| load.callback@19 | [19](../../../frontend/src/components/model-architecture/traceColor.ts#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_lineage_children_postgres.py; … (159 referencias nominales; ver CSV) |
| load.callback@19.callback@21 | [21](../../../frontend/src/components/model-architecture/traceColor.ts#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_lineage_children_postgres.py; … (159 referencias nominales; ver CSV) |
| paintMap | [35](../../../frontend/src/components/model-architecture/traceColor.ts#L35) | Paints one stored channel. The PNG keeps 0–255 inside the channel's own [min, max]; with that range the raw value is rebuilt and redrawn either on its own scale or on the layer's, so channels can be compared honestly. | Sin referencia nominal localizada |

## frontend/src/components/model-architecture/traceSteps.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| outcomeOf | [7](../../../frontend/src/components/model-architecture/traceSteps.ts#L7) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| number | [11](../../../frontend/src/components/model-architecture/traceSteps.ts#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_stage2_status_read_only.py; backend_api/tests/test_microscopy_quality_services.py; … (25 referencias nominales; ver CSV) |
| percent | [12](../../../frontend/src/components/model-architecture/traceSteps.ts#L12) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_microscopy_quality_services.py; malaria_dl_local_project/tests/test_prediction_collapse.py; frontend/tests/frotis-v2.test.mjs |
| points | [13](../../../frontend/src/components/model-architecture/traceSteps.ts#L13) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_governed_dataset_versions_api.py; … (18 referencias nominales; ver CSV) |
| megabytes | [14](../../../frontend/src/components/model-architecture/traceSteps.ts#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stepChange | [17](../../../frontend/src/components/model-architecture/traceSteps.ts#L17) | Change against the previous step that shares its kind of tensor; 1D and 2D means are not comparable. | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/navigation/NavigationIcon.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| NavigationIcon | [25](../../../frontend/src/components/navigation/NavigationIcon.tsx#L25) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| NavigationIcon.callback@28 | [28](../../../frontend/src/components/navigation/NavigationIcon.tsx#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |

## frontend/src/components/navigation/navigationConfig.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| callback@77 | [77](../../../frontend/src/components/navigation/navigationConfig.ts#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| callback@77.callback@78 | [78](../../../frontend/src/components/navigation/navigationConfig.ts#L78) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| pathMatches | [80](../../../frontend/src/components/navigation/navigationConfig.ts#L80) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| moduleForPath | [83](../../../frontend/src/components/navigation/navigationConfig.ts#L83) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| moduleForPath.callback@84 | [84](../../../frontend/src/components/navigation/navigationConfig.ts#L84) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sectionForPath | [86](../../../frontend/src/components/navigation/navigationConfig.ts#L86) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| sectionForPath.callback@87 | [87](../../../frontend/src/components/navigation/navigationConfig.ts#L87) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| sectionForPath.callback@88 | [88](../../../frontend/src/components/navigation/navigationConfig.ts#L88) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| sectionForPath.callback@90 | [90](../../../frontend/src/components/navigation/navigationConfig.ts#L90) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |

## frontend/src/components/reports/AnalysisWorkspace.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| isAnalysisSection | [16](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| isAnalysisSection.callback@17 | [17](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L17) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| tabId | [19](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| panelId | [20](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AnalysisSectionNav | [22](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L22) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| AnalysisSectionNav.move | [25](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| AnalysisSectionNav.move.callback@26 | [26](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| AnalysisSectionNav.callback@35 | [35](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| AnalysisSectionNav.callback@35.callback@37 | [37](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| useVisitedSections | [44](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L44) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useVisitedSections.callback@46 | [46](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useVisitedSections.callback@46.callback@46 | [46](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AnalysisPanel | [50](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L50) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| AnalysisPanel.callback@52 | [52](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TraceabilityProvider | [62](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L62) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityProvider.callback@66 | [66](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L66) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityProvider.open | [67](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L67) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityProvider.callback@70 | [70](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityProvider.callback@72 | [72](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidenceButton | [79](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L79) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceButton.callback@83 | [83](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L83) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SectionAnswer | [87](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L87) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Kpi | [90](../../../frontend/src/components/reports/AnalysisWorkspace.tsx#L90) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/AssessmentEvaluationCard.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AssessmentEvaluationSummary | [10](../../../frontend/src/components/reports/AssessmentEvaluationCard.tsx#L10) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| AssessmentEvaluationCard | [44](../../../frontend/src/components/reports/AssessmentEvaluationCard.tsx#L44) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |

## frontend/src/components/reports/AssessmentExplanationCard.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AssessmentExplanationCard | [6](../../../frontend/src/components/reports/AssessmentExplanationCard.tsx#L6) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |

## frontend/src/components/reports/AssessmentXAI.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| cellComparison | [10](../../../frontend/src/components/reports/AssessmentXAI.tsx#L10) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| cellComparison.callback@11 | [11](../../../frontend/src/components/reports/AssessmentXAI.tsx#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| AssessmentSampleXAI | [29](../../../frontend/src/components/reports/AssessmentXAI.tsx#L29) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| AssessmentSampleXAI.callback@32 | [32](../../../frontend/src/components/reports/AssessmentXAI.tsx#L32) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| AssessmentSampleXAI.callback@33 | [33](../../../frontend/src/components/reports/AssessmentXAI.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| AssessmentSampleXAI.callback@35 | [35](../../../frontend/src/components/reports/AssessmentXAI.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| AssessmentSampleXAI.callback@36 | [36](../../../frontend/src/components/reports/AssessmentXAI.tsx#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| TrainingAssessmentXAI | [42](../../../frontend/src/components/reports/AssessmentXAI.tsx#L42) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| TrainingAssessmentXAI.callback@45 | [45](../../../frontend/src/components/reports/AssessmentXAI.tsx#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| TrainingAssessmentXAIContent | [51](../../../frontend/src/components/reports/AssessmentXAI.tsx#L51) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.callback@57 | [57](../../../frontend/src/components/reports/AssessmentXAI.tsx#L57) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.callback@57.callback@62 | [62](../../../frontend/src/components/reports/AssessmentXAI.tsx#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.callback@67 | [67](../../../frontend/src/components/reports/AssessmentXAI.tsx#L67) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.refresh | [72](../../../frontend/src/components/reports/AssessmentXAI.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.refresh.callback@72 | [72](../../../frontend/src/components/reports/AssessmentXAI.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.callback@77 | [77](../../../frontend/src/components/reports/AssessmentXAI.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingAssessmentXAIContent.callback@79 | [79](../../../frontend/src/components/reports/AssessmentXAI.tsx#L79) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/AutoAnalysisBadge.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AutoAnalysisBadge | [9](../../../frontend/src/components/reports/AutoAnalysisBadge.tsx#L9) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/CommandChips.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| CommandChips | [15](../../../frontend/src/components/reports/CommandChips.tsx#L15) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CommandChips.callback@16 | [16](../../../frontend/src/components/reports/CommandChips.tsx#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CommandChips.callback@25 | [25](../../../frontend/src/components/reports/CommandChips.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/ComparisonEligibilityStatus.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ComparisonEligibilityStatus | [4](../../../frontend/src/components/reports/ComparisonEligibilityStatus.tsx#L4) | Compact eligibility mark under the selection checkbox; stages and reasons are in its tooltip. | Sin referencia nominal localizada |
| ComparisonEligibilityStatus.callback@9 | [9](../../../frontend/src/components/reports/ComparisonEligibilityStatus.tsx#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEligibilityStatus.callback@11 | [11](../../../frontend/src/components/reports/ComparisonEligibilityStatus.tsx#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEligibilityStatus.callback@14 | [14](../../../frontend/src/components/reports/ComparisonEligibilityStatus.tsx#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/ComparisonPython.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| configurationEvidence | [16](../../../frontend/src/components/reports/ComparisonPython.tsx#L16) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| configurationEvidence.callback@17 | [17](../../../frontend/src/components/reports/ComparisonPython.tsx#L17) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| pythonLiteral | [19](../../../frontend/src/components/reports/ComparisonPython.tsx#L19) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| pythonLiteral.callback@23 | [23](../../../frontend/src/components/reports/ComparisonPython.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| configurationCode | [26](../../../frontend/src/components/reports/ComparisonPython.tsx#L26) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| configurationCode.callback@27 | [27](../../../frontend/src/components/reports/ComparisonPython.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| configurationCode.callback@27.callback@29 | [29](../../../frontend/src/components/reports/ComparisonPython.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| configurationCode.callback@27.callback@30 | [30](../../../frontend/src/components/reports/ComparisonPython.tsx#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| CopyText | [36](../../../frontend/src/components/reports/ComparisonPython.tsx#L36) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| CopyText.callback@38 | [38](../../../frontend/src/components/reports/ComparisonPython.tsx#L38) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython | [42](../../../frontend/src/components/reports/ComparisonPython.tsx#L42) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@45 | [45](../../../frontend/src/components/reports/ComparisonPython.tsx#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@49 | [49](../../../frontend/src/components/reports/ComparisonPython.tsx#L49) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@55 | [55](../../../frontend/src/components/reports/ComparisonPython.tsx#L55) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@55.callback@55 | [55](../../../frontend/src/components/reports/ComparisonPython.tsx#L55) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@56 | [56](../../../frontend/src/components/reports/ComparisonPython.tsx#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@59 | [59](../../../frontend/src/components/reports/ComparisonPython.tsx#L59) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ComparisonPython.callback@60 | [60](../../../frontend/src/components/reports/ComparisonPython.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/components/reports/ComparisonRunCard.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| evidence | [10](../../../frontend/src/components/reports/ComparisonRunCard.tsx#L10) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; … (67 referencias nominales; ver CSV) |
| evidence.callback@11 | [11](../../../frontend/src/components/reports/ComparisonRunCard.tsx#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; … (67 referencias nominales; ver CSV) |
| ComparisonRunCard | [16](../../../frontend/src/components/reports/ComparisonRunCard.tsx#L16) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonRunCard.callback@44 | [44](../../../frontend/src/components/reports/ComparisonRunCard.tsx#L44) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonRunCard.callback@45 | [45](../../../frontend/src/components/reports/ComparisonRunCard.tsx#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |

## frontend/src/components/reports/ConsensusSamplesTable.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| runLabel | [10](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| shortSample | [11](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| score | [14](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_lineage_children_api.py; … (63 referencias nominales; ver CSV) |
| SampleThumbnail | [20](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L20) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SampleThumbnail.callback@26 | [26](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable | [37](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L37) | Server-side page of consensus samples: the column filters (sample, real class, category, score range per RUN) are sent to the backend, which filters and sorts the whole population before paging; the table adds column hid | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46 | [46](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.Cell | [48](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L48) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.accessorFn | [50](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L50) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.accessorFn | [52](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.callback@53 | [53](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.callback@53 | [53](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.callback@54 | [54](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L54) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.callback@54.accessorFn | [55](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L55) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.callback@54.Cell | [56](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@46.Cell | [64](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L64) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.callback@69 | [69](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.onPaginationChange | [80](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L80) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.onSortingChange | [81](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L81) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.onColumnFiltersChange | [82](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L82) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.getRowId | [87](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L87) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusSamplesTable.renderTopToolbarCustomActions | [91](../../../frontend/src/components/reports/ConsensusSamplesTable.tsx#L91) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/DatasetIntegrity.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| record | [6](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L6) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; … (90 referencias nominales; ver CSV) |
| checkState | [9](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L9) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CheckValue | [16](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L16) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Checks | [28](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L28) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_local_storage_contract.py; backend_api/tests/test_clinical_content_storage_contract.py; malaria_dl_local_project/tests/test_model_governance_migration.py; … (7 referencias nominales; ver CSV) |
| Checks.callback@52 | [52](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_local_storage_contract.py; backend_api/tests/test_clinical_content_storage_contract.py; malaria_dl_local_project/tests/test_model_governance_migration.py; … (7 referencias nominales; ver CSV) |
| Checks.callback@52.callback@57 | [57](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L57) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_local_storage_contract.py; backend_api/tests/test_clinical_content_storage_contract.py; malaria_dl_local_project/tests/test_model_governance_migration.py; … (7 referencias nominales; ver CSV) |
| DatasetIntegrity | [67](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L67) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| DatasetIntegrity.callback@69 | [69](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| DatasetIntegrity.callback@79 | [79](../../../frontend/src/components/reports/DatasetIntegrity.tsx#L79) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/components/reports/GeneratedXAIComparison.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| listText | [7](../../../frontend/src/components/reports/GeneratedXAIComparison.tsx#L7) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| GeneratedXAIComparison | [9](../../../frontend/src/components/reports/GeneratedXAIComparison.tsx#L9) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| GeneratedXAIComparison.callback@25 | [25](../../../frontend/src/components/reports/GeneratedXAIComparison.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| GeneratedXAIComparison.callback@26 | [26](../../../frontend/src/components/reports/GeneratedXAIComparison.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| GeneratedXAIComparison.callback@26 | [26](../../../frontend/src/components/reports/GeneratedXAIComparison.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |

## frontend/src/components/reports/LineageBadge.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| LineageBadge | [21](../../../frontend/src/components/reports/LineageBadge.tsx#L21) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/MetricChip.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| MetricChip | [8](../../../frontend/src/components/reports/MetricChip.tsx#L8) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/MiniConfusionMatrix.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| MatrixValue | [12](../../../frontend/src/components/reports/MiniConfusionMatrix.tsx#L12) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniConfusionMatrix | [22](../../../frontend/src/components/reports/MiniConfusionMatrix.tsx#L22) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MiniConfusionMatrix.callback@26 | [26](../../../frontend/src/components/reports/MiniConfusionMatrix.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/ReportBadge.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ReportBadge | [12](../../../frontend/src/components/reports/ReportBadge.tsx#L12) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/RunLineageChildCard.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| visibleRunId | [29](../../../frontend/src/components/reports/RunLineageChildCard.tsx#L29) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| countLabel | [33](../../../frontend/src/components/reports/RunLineageChildCard.tsx#L33) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunLineageChildCard | [38](../../../frontend/src/components/reports/RunLineageChildCard.tsx#L38) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/stage2-availability.test.mjs |
| RunLineageChildCard.callback@130 | [130](../../../frontend/src/components/reports/RunLineageChildCard.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/stage2-availability.test.mjs |

## frontend/src/components/reports/RunProcessBadge.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| RunProcessBadge | [13](../../../frontend/src/components/reports/RunProcessBadge.tsx#L13) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/RunSelectorDialog.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| RunSelectorDialog | [8](../../../frontend/src/components/reports/RunSelectorDialog.tsx#L8) | Native dialog that picks TRAIN from the Ejecuciones report rows; the caller owns what the selection means. | frontend/tests/model-explorer.test.mjs |
| RunSelectorDialog.callback@21 | [21](../../../frontend/src/components/reports/RunSelectorDialog.tsx#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| RunSelectorDialog.callback@21.callback@23 | [23](../../../frontend/src/components/reports/RunSelectorDialog.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| RunSelectorDialog.callback@30 | [30](../../../frontend/src/components/reports/RunSelectorDialog.tsx#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/reports/RunSummaryRow.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| CopyableId | [30](../../../frontend/src/components/reports/RunSummaryRow.tsx#L30) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-dataset-version.test.mjs |
| CopyableId.callback@37 | [37](../../../frontend/src/components/reports/RunSummaryRow.tsx#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-dataset-version.test.mjs |
| CopyableId.callback@37.callback@37 | [37](../../../frontend/src/components/reports/RunSummaryRow.tsx#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-dataset-version.test.mjs |
| CopyableId.callback@37.callback@37 | [37](../../../frontend/src/components/reports/RunSummaryRow.tsx#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-dataset-version.test.mjs |
| ModelExplorerLink | [45](../../../frontend/src/components/reports/RunSummaryRow.tsx#L45) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunIdentityCell | [55](../../../frontend/src/components/reports/RunSummaryRow.tsx#L55) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunModelCell | [78](../../../frontend/src/components/reports/RunSummaryRow.tsx#L78) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunResultsCell | [91](../../../frontend/src/components/reports/RunSummaryRow.tsx#L91) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunAnalysisCell | [106](../../../frontend/src/components/reports/RunSummaryRow.tsx#L106) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunAnalysisCell.callback@116 | [116](../../../frontend/src/components/reports/RunSummaryRow.tsx#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RunSummaryRow | [131](../../../frontend/src/components/reports/RunSummaryRow.tsx#L131) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; … (6 referencias nominales; ver CSV) |

## frontend/src/components/reports/ScientificParameters.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ScientificParameters | [15](../../../frontend/src/components/reports/ScientificParameters.tsx#L15) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_training_scientific_parameters.py; frontend/tests/executions-scientific-parameters.test.mjs |
| ScientificParameters.callback@19 | [19](../../../frontend/src/components/reports/ScientificParameters.tsx#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_training_scientific_parameters.py; frontend/tests/executions-scientific-parameters.test.mjs |

## frontend/src/components/reports/ScientificPreflight.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| observationText | [18](../../../frontend/src/components/reports/ScientificPreflight.tsx#L18) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| jsonText | [23](../../../frontend/src/components/reports/ScientificPreflight.tsx#L23) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| jsonText.callback@28 | [28](../../../frontend/src/components/reports/ScientificPreflight.tsx#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| verdictText | [30](../../../frontend/src/components/reports/ScientificPreflight.tsx#L30) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VerdictBadge | [32](../../../frontend/src/components/reports/ScientificPreflight.tsx#L32) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| groupWarnings | [33](../../../frontend/src/components/reports/ScientificPreflight.tsx#L33) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| findingLabel | [41](../../../frontend/src/components/reports/ScientificPreflight.tsx#L41) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| architecture | [48](../../../frontend/src/components/reports/ScientificPreflight.tsx#L48) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_stage2_status_read_only.py; backend_api/tests/test_representation_generation.py; … (42 referencias nominales; ver CSV) |
| ErrorMessage | [56](../../../frontend/src/components/reports/ScientificPreflight.tsx#L56) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/db02a-errors.test.mjs |
| EvidenceCell | [62](../../../frontend/src/components/reports/ScientificPreflight.tsx#L62) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@63 | [63](../../../frontend/src/components/reports/ScientificPreflight.tsx#L63) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@67 | [67](../../../frontend/src/components/reports/ScientificPreflight.tsx#L67) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@69 | [69](../../../frontend/src/components/reports/ScientificPreflight.tsx#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@70 | [70](../../../frontend/src/components/reports/ScientificPreflight.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@70.callback@72 | [72](../../../frontend/src/components/reports/ScientificPreflight.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@70.callback@72 | [72](../../../frontend/src/components/reports/ScientificPreflight.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@70.callback@72.callback@73 | [73](../../../frontend/src/components/reports/ScientificPreflight.tsx#L73) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@77 | [77](../../../frontend/src/components/reports/ScientificPreflight.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceCell.callback@77 | [77](../../../frontend/src/components/reports/ScientificPreflight.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| parameterRows | [86](../../../frontend/src/components/reports/ScientificPreflight.tsx#L86) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.selected | [87](../../../frontend/src/components/reports/ScientificPreflight.tsx#L87) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.selected.callback@87 | [87](../../../frontend/src/components/reports/ScientificPreflight.tsx#L87) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.projected | [88](../../../frontend/src/components/reports/ScientificPreflight.tsx#L88) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.projected.callback@88 | [88](../../../frontend/src/components/reports/ScientificPreflight.tsx#L88) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@89 | [89](../../../frontend/src/components/reports/ScientificPreflight.tsx#L89) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@90 | [90](../../../frontend/src/components/reports/ScientificPreflight.tsx#L90) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@94 | [94](../../../frontend/src/components/reports/ScientificPreflight.tsx#L94) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@94.callback@95 | [95](../../../frontend/src/components/reports/ScientificPreflight.tsx#L95) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@94.callback@96 | [96](../../../frontend/src/components/reports/ScientificPreflight.tsx#L96) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@94.callback@98 | [98](../../../frontend/src/components/reports/ScientificPreflight.tsx#L98) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@100 | [100](../../../frontend/src/components/reports/ScientificPreflight.tsx#L100) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@101 | [101](../../../frontend/src/components/reports/ScientificPreflight.tsx#L101) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@101.callback@101 | [101](../../../frontend/src/components/reports/ScientificPreflight.tsx#L101) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@103 | [103](../../../frontend/src/components/reports/ScientificPreflight.tsx#L103) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@103 | [103](../../../frontend/src/components/reports/ScientificPreflight.tsx#L103) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@103.callback@103 | [103](../../../frontend/src/components/reports/ScientificPreflight.tsx#L103) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@103.callback@103.callback@103 | [103](../../../frontend/src/components/reports/ScientificPreflight.tsx#L103) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@104 | [104](../../../frontend/src/components/reports/ScientificPreflight.tsx#L104) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@104.callback@104 | [104](../../../frontend/src/components/reports/ScientificPreflight.tsx#L104) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@104.callback@104.callback@104 | [104](../../../frontend/src/components/reports/ScientificPreflight.tsx#L104) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| parameterRows.callback@104.callback@104.callback@104.callback@104 | [104](../../../frontend/src/components/reports/ScientificPreflight.tsx#L104) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CompactValue | [108](../../../frontend/src/components/reports/ScientificPreflight.tsx#L108) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| CompactValue.list | [125](../../../frontend/src/components/reports/ScientificPreflight.tsx#L125) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| CompactValue.list.callback@125 | [125](../../../frontend/src/components/reports/ScientificPreflight.tsx#L125) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ParameterValue | [135](../../../frontend/src/components/reports/ScientificPreflight.tsx#L135) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings | [138](../../../frontend/src/components/reports/ScientificPreflight.tsx#L138) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@139 | [139](../../../frontend/src/components/reports/ScientificPreflight.tsx#L139) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@139 | [139](../../../frontend/src/components/reports/ScientificPreflight.tsx#L139) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@140 | [140](../../../frontend/src/components/reports/ScientificPreflight.tsx#L140) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@140 | [140](../../../frontend/src/components/reports/ScientificPreflight.tsx#L140) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.affected | [141](../../../frontend/src/components/reports/ScientificPreflight.tsx#L141) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.affected.callback@141 | [141](../../../frontend/src/components/reports/ScientificPreflight.tsx#L141) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.affected.callback@141.callback@141 | [141](../../../frontend/src/components/reports/ScientificPreflight.tsx#L141) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@143 | [143](../../../frontend/src/components/reports/ScientificPreflight.tsx#L143) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@143.callback@143 | [143](../../../frontend/src/components/reports/ScientificPreflight.tsx#L143) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@143.callback@143 | [143](../../../frontend/src/components/reports/ScientificPreflight.tsx#L143) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@143.callback@143 | [143](../../../frontend/src/components/reports/ScientificPreflight.tsx#L143) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedFindings.callback@143.callback@143 | [143](../../../frontend/src/components/reports/ScientificPreflight.tsx#L143) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| evidenceTarget | [147](../../../frontend/src/components/reports/ScientificPreflight.tsx#L147) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail | [150](../../../frontend/src/components/reports/ScientificPreflight.tsx#L150) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@153 | [153](../../../frontend/src/components/reports/ScientificPreflight.tsx#L153) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@154 | [154](../../../frontend/src/components/reports/ScientificPreflight.tsx#L154) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@154.callback@154 | [154](../../../frontend/src/components/reports/ScientificPreflight.tsx#L154) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@155 | [155](../../../frontend/src/components/reports/ScientificPreflight.tsx#L155) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@157 | [157](../../../frontend/src/components/reports/ScientificPreflight.tsx#L157) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@158 | [158](../../../frontend/src/components/reports/ScientificPreflight.tsx#L158) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@158 | [158](../../../frontend/src/components/reports/ScientificPreflight.tsx#L158) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@158.callback@158 | [158](../../../frontend/src/components/reports/ScientificPreflight.tsx#L158) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@159 | [159](../../../frontend/src/components/reports/ScientificPreflight.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@159 | [159](../../../frontend/src/components/reports/ScientificPreflight.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@159.callback@159 | [159](../../../frontend/src/components/reports/ScientificPreflight.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@159 | [159](../../../frontend/src/components/reports/ScientificPreflight.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@159.callback@159 | [159](../../../frontend/src/components/reports/ScientificPreflight.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsolidatedDetail.callback@159 | [159](../../../frontend/src/components/reports/ScientificPreflight.tsx#L159) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PartitionCards | [162](../../../frontend/src/components/reports/ScientificPreflight.tsx#L162) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.field | [163](../../../frontend/src/components/reports/ScientificPreflight.tsx#L163) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.field.callback@163 | [163](../../../frontend/src/components/reports/ScientificPreflight.tsx#L163) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.callback@170 | [170](../../../frontend/src/components/reports/ScientificPreflight.tsx#L170) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.callback@173 | [173](../../../frontend/src/components/reports/ScientificPreflight.tsx#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.callback@173.callback@173 | [173](../../../frontend/src/components/reports/ScientificPreflight.tsx#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.callback@173.callback@173 | [173](../../../frontend/src/components/reports/ScientificPreflight.tsx#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.callback@173.callback@173 | [173](../../../frontend/src/components/reports/ScientificPreflight.tsx#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PartitionCards.callback@175 | [175](../../../frontend/src/components/reports/ScientificPreflight.tsx#L175) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings | [182](../../../frontend/src/components/reports/ScientificPreflight.tsx#L182) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings.callback@183 | [183](../../../frontend/src/components/reports/ScientificPreflight.tsx#L183) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings.callback@185 | [185](../../../frontend/src/components/reports/ScientificPreflight.tsx#L185) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings.callback@186 | [186](../../../frontend/src/components/reports/ScientificPreflight.tsx#L186) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings.callback@186.callback@189 | [189](../../../frontend/src/components/reports/ScientificPreflight.tsx#L189) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings.callback@192 | [192](../../../frontend/src/components/reports/ScientificPreflight.tsx#L192) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalWarnings.callback@192 | [192](../../../frontend/src/components/reports/ScientificPreflight.tsx#L192) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| AvailabilityMatrix | [196](../../../frontend/src/components/reports/ScientificPreflight.tsx#L196) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@197 | [197](../../../frontend/src/components/reports/ScientificPreflight.tsx#L197) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@198 | [198](../../../frontend/src/components/reports/ScientificPreflight.tsx#L198) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@199 | [199](../../../frontend/src/components/reports/ScientificPreflight.tsx#L199) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@199.callback@200 | [200](../../../frontend/src/components/reports/ScientificPreflight.tsx#L200) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@199.callback@200 | [200](../../../frontend/src/components/reports/ScientificPreflight.tsx#L200) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@199.callback@201 | [201](../../../frontend/src/components/reports/ScientificPreflight.tsx#L201) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AvailabilityMatrix.callback@199.callback@201.callback@202 | [202](../../../frontend/src/components/reports/ScientificPreflight.tsx#L202) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MethodologicalSynthesis | [208](../../../frontend/src/components/reports/ScientificPreflight.tsx#L208) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@209 | [209](../../../frontend/src/components/reports/ScientificPreflight.tsx#L209) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@209.callback@210 | [210](../../../frontend/src/components/reports/ScientificPreflight.tsx#L210) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@209.callback@211 | [211](../../../frontend/src/components/reports/ScientificPreflight.tsx#L211) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@213 | [213](../../../frontend/src/components/reports/ScientificPreflight.tsx#L213) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@213.callback@213 | [213](../../../frontend/src/components/reports/ScientificPreflight.tsx#L213) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@216 | [216](../../../frontend/src/components/reports/ScientificPreflight.tsx#L216) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@217 | [217](../../../frontend/src/components/reports/ScientificPreflight.tsx#L217) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| MethodologicalSynthesis.callback@218 | [218](../../../frontend/src/components/reports/ScientificPreflight.tsx#L218) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceLinks | [222](../../../frontend/src/components/reports/ScientificPreflight.tsx#L222) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidenceLinks.callback@223 | [223](../../../frontend/src/components/reports/ScientificPreflight.tsx#L223) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidenceLinks.callback@223.callback@224 | [224](../../../frontend/src/components/reports/ScientificPreflight.tsx#L224) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidenceLinks.callback@223.callback@225 | [225](../../../frontend/src/components/reports/ScientificPreflight.tsx#L225) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidenceLinks.callback@223.callback@225.callback@225 | [225](../../../frontend/src/components/reports/ScientificPreflight.tsx#L225) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidenceLinks.callback@223.callback@226 | [226](../../../frontend/src/components/reports/ScientificPreflight.tsx#L226) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| pendingEvidence | [231](../../../frontend/src/components/reports/ScientificPreflight.tsx#L231) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| pendingCategory | [254](../../../frontend/src/components/reports/ScientificPreflight.tsx#L254) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| pendingCategory.callback@259 | [259](../../../frontend/src/components/reports/ScientificPreflight.tsx#L259) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| pendingCount | [263](../../../frontend/src/components/reports/ScientificPreflight.tsx#L263) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| pendingCount.callback@263 | [263](../../../frontend/src/components/reports/ScientificPreflight.tsx#L263) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory | [265](../../../frontend/src/components/reports/ScientificPreflight.tsx#L265) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.run | [267](../../../frontend/src/components/reports/ScientificPreflight.tsx#L267) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.run.callback@267 | [267](../../../frontend/src/components/reports/ScientificPreflight.tsx#L267) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.impact | [268](../../../frontend/src/components/reports/ScientificPreflight.tsx#L268) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.impact.callback@268 | [268](../../../frontend/src/components/reports/ScientificPreflight.tsx#L268) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.impact.callback@268.callback@268 | [268](../../../frontend/src/components/reports/ScientificPreflight.tsx#L268) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.weight | [270](../../../frontend/src/components/reports/ScientificPreflight.tsx#L270) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@271 | [271](../../../frontend/src/components/reports/ScientificPreflight.tsx#L271) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@271.callback@271 | [271](../../../frontend/src/components/reports/ScientificPreflight.tsx#L271) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@271 | [271](../../../frontend/src/components/reports/ScientificPreflight.tsx#L271) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@272 | [272](../../../frontend/src/components/reports/ScientificPreflight.tsx#L272) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@272.callback@272 | [272](../../../frontend/src/components/reports/ScientificPreflight.tsx#L272) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@277 | [277](../../../frontend/src/components/reports/ScientificPreflight.tsx#L277) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@277.callback@277 | [277](../../../frontend/src/components/reports/ScientificPreflight.tsx#L277) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@278 | [278](../../../frontend/src/components/reports/ScientificPreflight.tsx#L278) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@278.callback@278 | [278](../../../frontend/src/components/reports/ScientificPreflight.tsx#L278) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@280 | [280](../../../frontend/src/components/reports/ScientificPreflight.tsx#L280) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@280.callback@280 | [280](../../../frontend/src/components/reports/ScientificPreflight.tsx#L280) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@280.callback@280 | [280](../../../frontend/src/components/reports/ScientificPreflight.tsx#L280) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@282 | [282](../../../frontend/src/components/reports/ScientificPreflight.tsx#L282) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@282.callback@285 | [285](../../../frontend/src/components/reports/ScientificPreflight.tsx#L285) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@293 | [293](../../../frontend/src/components/reports/ScientificPreflight.tsx#L293) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvidenceInventory.callback@294 | [294](../../../frontend/src/components/reports/ScientificPreflight.tsx#L294) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| runLabel | [301](../../../frontend/src/components/reports/ScientificPreflight.tsx#L301) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| dimensionFields | [303](../../../frontend/src/components/reports/ScientificPreflight.tsx#L303) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| dimensionFields.callback@304 | [304](../../../frontend/src/components/reports/ScientificPreflight.tsx#L304) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| dimensionFields.callback@304.callback@304 | [304](../../../frontend/src/components/reports/ScientificPreflight.tsx#L304) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| disabledOptions | [310](../../../frontend/src/components/reports/ScientificPreflight.tsx#L310) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| disabledOptions.callback@312 | [312](../../../frontend/src/components/reports/ScientificPreflight.tsx#L312) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| accredited | [314](../../../frontend/src/components/reports/ScientificPreflight.tsx#L314) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_campaigns_e4.py; malaria_dl_local_project/tests/test_assessment_e6.py; malaria_dl_local_project/tests/test_input_contract_e3.py; … (4 referencias nominales; ver CSV) |
| lineageCoverage | [316](../../../frontend/src/components/reports/ScientificPreflight.tsx#L316) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| lineageCoverage.callback@317 | [317](../../../frontend/src/components/reports/ScientificPreflight.tsx#L317) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| lineageCoverage.callback@317.callback@320 | [320](../../../frontend/src/components/reports/ScientificPreflight.tsx#L320) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| lineageCoverage.callback@317.callback@320.callback@320 | [320](../../../frontend/src/components/reports/ScientificPreflight.tsx#L320) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| lineageCoverage.callback@317.callback@320.callback@320 | [320](../../../frontend/src/components/reports/ScientificPreflight.tsx#L320) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| lineageCoverage.callback@317.callback@320.callback@320 | [320](../../../frontend/src/components/reports/ScientificPreflight.tsx#L320) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| coverageTone | [323](../../../frontend/src/components/reports/ScientificPreflight.tsx#L323) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| plainObject | [329](../../../frontend/src/components/reports/ScientificPreflight.tsx#L329) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| objectFields | [333](../../../frontend/src/components/reports/ScientificPreflight.tsx#L333) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| objectFields.callback@335 | [335](../../../frontend/src/components/reports/ScientificPreflight.tsx#L335) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| objectFields.callback@336 | [336](../../../frontend/src/components/reports/ScientificPreflight.tsx#L336) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| objectFields.callback@336.callback@336 | [336](../../../frontend/src/components/reports/ScientificPreflight.tsx#L336) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| dimensionTab | [339](../../../frontend/src/components/reports/ScientificPreflight.tsx#L339) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart | [340](../../../frontend/src/components/reports/ScientificPreflight.tsx#L340) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@344 | [344](../../../frontend/src/components/reports/ScientificPreflight.tsx#L344) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@345 | [345](../../../frontend/src/components/reports/ScientificPreflight.tsx#L345) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@345.callback@347 | [347](../../../frontend/src/components/reports/ScientificPreflight.tsx#L347) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@345.callback@347.callback@350 | [350](../../../frontend/src/components/reports/ScientificPreflight.tsx#L350) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@356 | [356](../../../frontend/src/components/reports/ScientificPreflight.tsx#L356) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@356.callback@356 | [356](../../../frontend/src/components/reports/ScientificPreflight.tsx#L356) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CoverageChart.callback@356.callback@356 | [356](../../../frontend/src/components/reports/ScientificPreflight.tsx#L356) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview | [361](../../../frontend/src/components/reports/ScientificPreflight.tsx#L361) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@366 | [366](../../../frontend/src/components/reports/ScientificPreflight.tsx#L366) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@367 | [367](../../../frontend/src/components/reports/ScientificPreflight.tsx#L367) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@368 | [368](../../../frontend/src/components/reports/ScientificPreflight.tsx#L368) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@369 | [369](../../../frontend/src/components/reports/ScientificPreflight.tsx#L369) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@370 | [370](../../../frontend/src/components/reports/ScientificPreflight.tsx#L370) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@371 | [371](../../../frontend/src/components/reports/ScientificPreflight.tsx#L371) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@373 | [373](../../../frontend/src/components/reports/ScientificPreflight.tsx#L373) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@374 | [374](../../../frontend/src/components/reports/ScientificPreflight.tsx#L374) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@375 | [375](../../../frontend/src/components/reports/ScientificPreflight.tsx#L375) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TraceabilityOverview.callback@387 | [387](../../../frontend/src/components/reports/ScientificPreflight.tsx#L387) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SingleRunParameters | [395](../../../frontend/src/components/reports/ScientificPreflight.tsx#L395) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396 | [396](../../../frontend/src/components/reports/ScientificPreflight.tsx#L396) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@397 | [397](../../../frontend/src/components/reports/ScientificPreflight.tsx#L397) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@399 | [399](../../../frontend/src/components/reports/ScientificPreflight.tsx#L399) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@400 | [400](../../../frontend/src/components/reports/ScientificPreflight.tsx#L400) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@401 | [401](../../../frontend/src/components/reports/ScientificPreflight.tsx#L401) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@402 | [402](../../../frontend/src/components/reports/ScientificPreflight.tsx#L402) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@403 | [403](../../../frontend/src/components/reports/ScientificPreflight.tsx#L403) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@404 | [404](../../../frontend/src/components/reports/ScientificPreflight.tsx#L404) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SingleRunParameters.callback@396.callback@405 | [405](../../../frontend/src/components/reports/ScientificPreflight.tsx#L405) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence | [413](../../../frontend/src/components/reports/ScientificPreflight.tsx#L413) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@419 | [419](../../../frontend/src/components/reports/ScientificPreflight.tsx#L419) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@419.callback@420 | [420](../../../frontend/src/components/reports/ScientificPreflight.tsx#L420) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@419.callback@420 | [420](../../../frontend/src/components/reports/ScientificPreflight.tsx#L420) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@421 | [421](../../../frontend/src/components/reports/ScientificPreflight.tsx#L421) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@421.callback@421 | [421](../../../frontend/src/components/reports/ScientificPreflight.tsx#L421) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@421 | [421](../../../frontend/src/components/reports/ScientificPreflight.tsx#L421) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@421.callback@421 | [421](../../../frontend/src/components/reports/ScientificPreflight.tsx#L421) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@421.callback@421 | [421](../../../frontend/src/components/reports/ScientificPreflight.tsx#L421) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@421.callback@421 | [421](../../../frontend/src/components/reports/ScientificPreflight.tsx#L421) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@423 | [423](../../../frontend/src/components/reports/ScientificPreflight.tsx#L423) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.open | [424](../../../frontend/src/components/reports/ScientificPreflight.tsx#L424) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.open.callback@424 | [424](../../../frontend/src/components/reports/ScientificPreflight.tsx#L424) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.move | [426](../../../frontend/src/components/reports/ScientificPreflight.tsx#L426) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.move.callback@427 | [427](../../../frontend/src/components/reports/ScientificPreflight.tsx#L427) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.panel | [434](../../../frontend/src/components/reports/ScientificPreflight.tsx#L434) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@436 | [436](../../../frontend/src/components/reports/ScientificPreflight.tsx#L436) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@436 | [436](../../../frontend/src/components/reports/ScientificPreflight.tsx#L436) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@438 | [438](../../../frontend/src/components/reports/ScientificPreflight.tsx#L438) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@438.callback@439 | [439](../../../frontend/src/components/reports/ScientificPreflight.tsx#L439) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444 | [444](../../../frontend/src/components/reports/ScientificPreflight.tsx#L444) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@447 | [447](../../../frontend/src/components/reports/ScientificPreflight.tsx#L447) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@450 | [450](../../../frontend/src/components/reports/ScientificPreflight.tsx#L450) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@450.callback@450 | [450](../../../frontend/src/components/reports/ScientificPreflight.tsx#L450) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@450.callback@450.callback@450 | [450](../../../frontend/src/components/reports/ScientificPreflight.tsx#L450) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@454 | [454](../../../frontend/src/components/reports/ScientificPreflight.tsx#L454) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455 | [455](../../../frontend/src/components/reports/ScientificPreflight.tsx#L455) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@456 | [456](../../../frontend/src/components/reports/ScientificPreflight.tsx#L456) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457 | [457](../../../frontend/src/components/reports/ScientificPreflight.tsx#L457) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@458 | [458](../../../frontend/src/components/reports/ScientificPreflight.tsx#L458) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@459 | [459](../../../frontend/src/components/reports/ScientificPreflight.tsx#L459) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@459.callback@459 | [459](../../../frontend/src/components/reports/ScientificPreflight.tsx#L459) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@459.callback@459.callback@459 | [459](../../../frontend/src/components/reports/ScientificPreflight.tsx#L459) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@460 | [460](../../../frontend/src/components/reports/ScientificPreflight.tsx#L460) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@461 | [461](../../../frontend/src/components/reports/ScientificPreflight.tsx#L461) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@463 | [463](../../../frontend/src/components/reports/ScientificPreflight.tsx#L463) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@444.callback@455.callback@457.callback@465 | [465](../../../frontend/src/components/reports/ScientificPreflight.tsx#L465) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@482 | [482](../../../frontend/src/components/reports/ScientificPreflight.tsx#L482) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@483 | [483](../../../frontend/src/components/reports/ScientificPreflight.tsx#L483) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@483.callback@483 | [483](../../../frontend/src/components/reports/ScientificPreflight.tsx#L483) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@483.callback@483.callback@483 | [483](../../../frontend/src/components/reports/ScientificPreflight.tsx#L483) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@483.callback@483.callback@483 | [483](../../../frontend/src/components/reports/ScientificPreflight.tsx#L483) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@483.callback@483 | [483](../../../frontend/src/components/reports/ScientificPreflight.tsx#L483) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| PreflightEvidence.callback@483.callback@483 | [483](../../../frontend/src/components/reports/ScientificPreflight.tsx#L483) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| CellSearch | [493](../../../frontend/src/components/reports/ScientificPreflight.tsx#L493) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellSearch.callback@496 | [496](../../../frontend/src/components/reports/ScientificPreflight.tsx#L496) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellSearch.callback@497 | [497](../../../frontend/src/components/reports/ScientificPreflight.tsx#L497) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonModules | [503](../../../frontend/src/components/reports/ScientificPreflight.tsx#L503) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonModules.callback@509 | [509](../../../frontend/src/components/reports/ScientificPreflight.tsx#L509) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonModules.callback@511 | [511](../../../frontend/src/components/reports/ScientificPreflight.tsx#L511) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonModules.callback@511.callback@511 | [511](../../../frontend/src/components/reports/ScientificPreflight.tsx#L511) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonModules.callback@511.callback@511 | [511](../../../frontend/src/components/reports/ScientificPreflight.tsx#L511) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sectionStates | [518](../../../frontend/src/components/reports/ScientificPreflight.tsx#L518) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sectionStates.callback@520 | [520](../../../frontend/src/components/reports/ScientificPreflight.tsx#L520) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sectionStates.callback@520.callback@521 | [521](../../../frontend/src/components/reports/ScientificPreflight.tsx#L521) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sectionStates.callback@520.callback@521 | [521](../../../frontend/src/components/reports/ScientificPreflight.tsx#L521) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sectionStates.callback@520.callback@522 | [522](../../../frontend/src/components/reports/ScientificPreflight.tsx#L522) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AnalysisContextBar | [527](../../../frontend/src/components/reports/ScientificPreflight.tsx#L527) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AnalysisContextBar.callback@529 | [529](../../../frontend/src/components/reports/ScientificPreflight.tsx#L529) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| AnalysisContextBar.callback@534 | [534](../../../frontend/src/components/reports/ScientificPreflight.tsx#L534) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SectionMap | [538](../../../frontend/src/components/reports/ScientificPreflight.tsx#L538) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SectionMap.callback@539 | [539](../../../frontend/src/components/reports/ScientificPreflight.tsx#L539) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SectionMap.callback@539 | [539](../../../frontend/src/components/reports/ScientificPreflight.tsx#L539) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SectionMap.callback@539.callback@539 | [539](../../../frontend/src/components/reports/ScientificPreflight.tsx#L539) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession | [547](../../../frontend/src/components/reports/ScientificPreflight.tsx#L547) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.select | [553](../../../frontend/src/components/reports/ScientificPreflight.tsx#L553) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.focus | [558](../../../frontend/src/components/reports/ScientificPreflight.tsx#L558) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@565 | [565](../../../frontend/src/components/reports/ScientificPreflight.tsx#L565) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.refresh | [566](../../../frontend/src/components/reports/ScientificPreflight.tsx#L566) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.refresh.callback@566 | [566](../../../frontend/src/components/reports/ScientificPreflight.tsx#L566) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.refresh.callback@566 | [566](../../../frontend/src/components/reports/ScientificPreflight.tsx#L566) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@567 | [567](../../../frontend/src/components/reports/ScientificPreflight.tsx#L567) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@567 | [567](../../../frontend/src/components/reports/ScientificPreflight.tsx#L567) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@567 | [567](../../../frontend/src/components/reports/ScientificPreflight.tsx#L567) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@585 | [585](../../../frontend/src/components/reports/ScientificPreflight.tsx#L585) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@587 | [587](../../../frontend/src/components/reports/ScientificPreflight.tsx#L587) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@595 | [595](../../../frontend/src/components/reports/ScientificPreflight.tsx#L595) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@596 | [596](../../../frontend/src/components/reports/ScientificPreflight.tsx#L596) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@597 | [597](../../../frontend/src/components/reports/ScientificPreflight.tsx#L597) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@598 | [598](../../../frontend/src/components/reports/ScientificPreflight.tsx#L598) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonEvidenceSession.callback@599 | [599](../../../frontend/src/components/reports/ScientificPreflight.tsx#L599) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ScientificPreflight | [604](../../../frontend/src/components/reports/ScientificPreflight.tsx#L604) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_comparison_eligibility.py; … (6 referencias nominales; ver CSV) |

## frontend/src/components/reports/ScientificReport.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| runLabel | [20](../../../frontend/src/components/reports/ScientificReport.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| value | [21](../../../frontend/src/components/reports/ScientificReport.tsx#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (176 referencias nominales; ver CSV) |
| percent | [23](../../../frontend/src/components/reports/ScientificReport.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_microscopy_quality_services.py; malaria_dl_local_project/tests/test_prediction_collapse.py; frontend/tests/frotis-v2.test.mjs |
| listText | [24](../../../frontend/src/components/reports/ScientificReport.tsx#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| short | [25](../../../frontend/src/components/reports/ScientificReport.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_users_postgres_docker.py; backend_api/tests/test_yolo_detector_adapter.py; frontend/tests/stage2-status.test.mjs |
| evaluationSelection | [26](../../../frontend/src/components/reports/ScientificReport.tsx#L26) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| when | [32](../../../frontend/src/components/reports/ScientificReport.tsx#L32) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_activation_traces.py; … (28 referencias nominales; ver CSV) |
| choiceText | [33](../../../frontend/src/components/reports/ScientificReport.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| explanationText | [35](../../../frontend/src/components/reports/ScientificReport.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| SlotChoice | [36](../../../frontend/src/components/reports/ScientificReport.tsx#L36) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SlotChoice.callback@39 | [39](../../../frontend/src/components/reports/ScientificReport.tsx#L39) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| SlotChoice.callback@40 | [40](../../../frontend/src/components/reports/ScientificReport.tsx#L40) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation | [43](../../../frontend/src/components/reports/ScientificReport.tsx#L43) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@49 | [49](../../../frontend/src/components/reports/ScientificReport.tsx#L49) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@50 | [50](../../../frontend/src/components/reports/ScientificReport.tsx#L50) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@52 | [52](../../../frontend/src/components/reports/ScientificReport.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@54 | [54](../../../frontend/src/components/reports/ScientificReport.tsx#L54) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.currentOf | [56](../../../frontend/src/components/reports/ScientificReport.tsx#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.currentOf.callback@56 | [56](../../../frontend/src/components/reports/ScientificReport.tsx#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@58 | [58](../../../frontend/src/components/reports/ScientificReport.tsx#L58) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@59 | [59](../../../frontend/src/components/reports/ScientificReport.tsx#L59) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.explainParts | [60](../../../frontend/src/components/reports/ScientificReport.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.explainOf | [61](../../../frontend/src/components/reports/ScientificReport.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.explainOf.callback@61 | [61](../../../frontend/src/components/reports/ScientificReport.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@62 | [62](../../../frontend/src/components/reports/ScientificReport.tsx#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@62.callback@62 | [62](../../../frontend/src/components/reports/ScientificReport.tsx#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@63 | [63](../../../frontend/src/components/reports/ScientificReport.tsx#L63) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@66 | [66](../../../frontend/src/components/reports/ScientificReport.tsx#L66) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@66.callback@66 | [66](../../../frontend/src/components/reports/ScientificReport.tsx#L66) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@70 | [70](../../../frontend/src/components/reports/ScientificReport.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@70.callback@71 | [71](../../../frontend/src/components/reports/ScientificReport.tsx#L71) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@70.callback@72 | [72](../../../frontend/src/components/reports/ScientificReport.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@70.callback@72.callback@72 | [72](../../../frontend/src/components/reports/ScientificReport.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@76 | [76](../../../frontend/src/components/reports/ScientificReport.tsx#L76) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@76.callback@76 | [76](../../../frontend/src/components/reports/ScientificReport.tsx#L76) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@77 | [77](../../../frontend/src/components/reports/ScientificReport.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@77.callback@79 | [79](../../../frontend/src/components/reports/ScientificReport.tsx#L79) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@77.callback@79 | [79](../../../frontend/src/components/reports/ScientificReport.tsx#L79) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@77.callback@79.callback@79 | [79](../../../frontend/src/components/reports/ScientificReport.tsx#L79) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@84 | [84](../../../frontend/src/components/reports/ScientificReport.tsx#L84) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@84 | [84](../../../frontend/src/components/reports/ScientificReport.tsx#L84) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@89 | [89](../../../frontend/src/components/reports/ScientificReport.tsx#L89) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| EvaluationNavigation.callback@90 | [90](../../../frontend/src/components/reports/ScientificReport.tsx#L90) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-preflight.test.mjs |
| LazyScientificModule | [104](../../../frontend/src/components/reports/ScientificReport.tsx#L104) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| LazyScientificModule.callback@109 | [109](../../../frontend/src/components/reports/ScientificReport.tsx#L109) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| LazyScientificModule.callback@115 | [115](../../../frontend/src/components/reports/ScientificReport.tsx#L115) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| LazyScientificModule.callback@115.callback@115 | [115](../../../frontend/src/components/reports/ScientificReport.tsx#L115) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| LazyScientificModule.callback@116 | [116](../../../frontend/src/components/reports/ScientificReport.tsx#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| LazyScientificModule.callback@119 | [119](../../../frontend/src/components/reports/ScientificReport.tsx#L119) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| epochsText | [125](../../../frontend/src/components/reports/ScientificReport.tsx#L125) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingCurves | [126](../../../frontend/src/components/reports/ScientificReport.tsx#L126) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.toggle | [130](../../../frontend/src/components/reports/ScientificReport.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.toggle.callback@130 | [130](../../../frontend/src/components/reports/ScientificReport.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.toggle.callback@130.callback@130 | [130](../../../frontend/src/components/reports/ScientificReport.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@131 | [131](../../../frontend/src/components/reports/ScientificReport.tsx#L131) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@131.callback@131 | [131](../../../frontend/src/components/reports/ScientificReport.tsx#L131) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@131.callback@131.callback@131 | [131](../../../frontend/src/components/reports/ScientificReport.tsx#L131) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@132 | [132](../../../frontend/src/components/reports/ScientificReport.tsx#L132) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@132.callback@132 | [132](../../../frontend/src/components/reports/ScientificReport.tsx#L132) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@132.callback@132.callback@132 | [132](../../../frontend/src/components/reports/ScientificReport.tsx#L132) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@134 | [134](../../../frontend/src/components/reports/ScientificReport.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@134.callback@134 | [134](../../../frontend/src/components/reports/ScientificReport.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@134 | [134](../../../frontend/src/components/reports/ScientificReport.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@136 | [136](../../../frontend/src/components/reports/ScientificReport.tsx#L136) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@137 | [137](../../../frontend/src/components/reports/ScientificReport.tsx#L137) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@137.callback@137 | [137](../../../frontend/src/components/reports/ScientificReport.tsx#L137) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@137.callback@137.callback@137 | [137](../../../frontend/src/components/reports/ScientificReport.tsx#L137) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@137.callback@137.callback@137 | [137](../../../frontend/src/components/reports/ScientificReport.tsx#L137) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@138 | [138](../../../frontend/src/components/reports/ScientificReport.tsx#L138) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@140 | [140](../../../frontend/src/components/reports/ScientificReport.tsx#L140) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@140.callback@140 | [140](../../../frontend/src/components/reports/ScientificReport.tsx#L140) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@140.callback@140.callback@140 | [140](../../../frontend/src/components/reports/ScientificReport.tsx#L140) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@141 | [141](../../../frontend/src/components/reports/ScientificReport.tsx#L141) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@141.callback@141 | [141](../../../frontend/src/components/reports/ScientificReport.tsx#L141) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@141 | [141](../../../frontend/src/components/reports/ScientificReport.tsx#L141) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@143 | [143](../../../frontend/src/components/reports/ScientificReport.tsx#L143) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@146 | [146](../../../frontend/src/components/reports/ScientificReport.tsx#L146) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@147 | [147](../../../frontend/src/components/reports/ScientificReport.tsx#L147) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@147 | [147](../../../frontend/src/components/reports/ScientificReport.tsx#L147) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@150 | [150](../../../frontend/src/components/reports/ScientificReport.tsx#L150) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@152 | [152](../../../frontend/src/components/reports/ScientificReport.tsx#L152) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@152.callback@152 | [152](../../../frontend/src/components/reports/ScientificReport.tsx#L152) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@153 | [153](../../../frontend/src/components/reports/ScientificReport.tsx#L153) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@153 | [153](../../../frontend/src/components/reports/ScientificReport.tsx#L153) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@156 | [156](../../../frontend/src/components/reports/ScientificReport.tsx#L156) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@156.callback@156 | [156](../../../frontend/src/components/reports/ScientificReport.tsx#L156) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@158 | [158](../../../frontend/src/components/reports/ScientificReport.tsx#L158) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@158 | [158](../../../frontend/src/components/reports/ScientificReport.tsx#L158) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@164 | [164](../../../frontend/src/components/reports/ScientificReport.tsx#L164) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| TrainingCurves.callback@164.callback@164 | [164](../../../frontend/src/components/reports/ScientificReport.tsx#L164) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConfusionHeatmap | [168](../../../frontend/src/components/reports/ScientificReport.tsx#L168) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConfusionHeatmap.cell | [170](../../../frontend/src/components/reports/ScientificReport.tsx#L170) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ClinicalMetrics | [176](../../../frontend/src/components/reports/ScientificReport.tsx#L176) | FunctionDeclaration; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@177 | [177](../../../frontend/src/components/reports/ScientificReport.tsx#L177) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@179 | [179](../../../frontend/src/components/reports/ScientificReport.tsx#L179) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@180 | [180](../../../frontend/src/components/reports/ScientificReport.tsx#L180) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@180 | [180](../../../frontend/src/components/reports/ScientificReport.tsx#L180) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@182 | [182](../../../frontend/src/components/reports/ScientificReport.tsx#L182) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@187 | [187](../../../frontend/src/components/reports/ScientificReport.tsx#L187) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@190 | [190](../../../frontend/src/components/reports/ScientificReport.tsx#L190) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@190 | [190](../../../frontend/src/components/reports/ScientificReport.tsx#L190) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@190 | [190](../../../frontend/src/components/reports/ScientificReport.tsx#L190) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@191 | [191](../../../frontend/src/components/reports/ScientificReport.tsx#L191) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@195 | [195](../../../frontend/src/components/reports/ScientificReport.tsx#L195) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@195.callback@195 | [195](../../../frontend/src/components/reports/ScientificReport.tsx#L195) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@195 | [195](../../../frontend/src/components/reports/ScientificReport.tsx#L195) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@197 | [197](../../../frontend/src/components/reports/ScientificReport.tsx#L197) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@199 | [199](../../../frontend/src/components/reports/ScientificReport.tsx#L199) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@200 | [200](../../../frontend/src/components/reports/ScientificReport.tsx#L200) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@200.callback@200 | [200](../../../frontend/src/components/reports/ScientificReport.tsx#L200) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@201 | [201](../../../frontend/src/components/reports/ScientificReport.tsx#L201) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| ClinicalMetrics.callback@201.callback@201 | [201](../../../frontend/src/components/reports/ScientificReport.tsx#L201) | ArrowFunction; operación exacta en llamadas y cuerpo | malaria_dl_local_project/tests/test_clinical_metrics_tracking.py; malaria_dl_local_project/tests/test_metrics.py; frontend/tests/scc-preflight.test.mjs |
| PairHeatmap | [210](../../../frontend/src/components/reports/ScientificReport.tsx#L210) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PairHeatmap.callback@211 | [211](../../../frontend/src/components/reports/ScientificReport.tsx#L211) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PairHeatmap.callback@211 | [211](../../../frontend/src/components/reports/ScientificReport.tsx#L211) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PairHeatmap.callback@211.callback@211 | [211](../../../frontend/src/components/reports/ScientificReport.tsx#L211) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PairHeatmap.callback@211.callback@211.callback@211 | [211](../../../frontend/src/components/reports/ScientificReport.tsx#L211) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusResults | [214](../../../frontend/src/components/reports/ScientificReport.tsx#L214) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@221 | [221](../../../frontend/src/components/reports/ScientificReport.tsx#L221) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@240 | [240](../../../frontend/src/components/reports/ScientificReport.tsx#L240) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@242 | [242](../../../frontend/src/components/reports/ScientificReport.tsx#L242) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@249 | [249](../../../frontend/src/components/reports/ScientificReport.tsx#L249) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@250 | [250](../../../frontend/src/components/reports/ScientificReport.tsx#L250) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@253 | [253](../../../frontend/src/components/reports/ScientificReport.tsx#L253) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@253 | [253](../../../frontend/src/components/reports/ScientificReport.tsx#L253) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| ConsensusResults.callback@254 | [254](../../../frontend/src/components/reports/ScientificReport.tsx#L254) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| CurvesModule | [257](../../../frontend/src/components/reports/ScientificReport.tsx#L257) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CurvesModule.callback@258 | [258](../../../frontend/src/components/reports/ScientificReport.tsx#L258) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CurvesModule.callback@258 | [258](../../../frontend/src/components/reports/ScientificReport.tsx#L258) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MetricsModule | [260](../../../frontend/src/components/reports/ScientificReport.tsx#L260) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| MetricsModule.callback@261 | [261](../../../frontend/src/components/reports/ScientificReport.tsx#L261) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| filterNumber | [263](../../../frontend/src/components/reports/ScientificReport.tsx#L263) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusFilterParams | [265](../../../frontend/src/components/reports/ScientificReport.tsx#L265) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusFilterParams.value | [266](../../../frontend/src/components/reports/ScientificReport.tsx#L266) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusFilterParams.value.callback@266 | [266](../../../frontend/src/components/reports/ScientificReport.tsx#L266) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusFilterParams.callback@268 | [268](../../../frontend/src/components/reports/ScientificReport.tsx#L268) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusFilterParams.callback@269 | [269](../../../frontend/src/components/reports/ScientificReport.tsx#L269) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusFilterParams.callback@270 | [270](../../../frontend/src/components/reports/ScientificReport.tsx#L270) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| shortId | [274](../../../frontend/src/components/reports/ScientificReport.tsx#L274) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusCellModal | [277](../../../frontend/src/components/reports/ScientificReport.tsx#L277) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusCellModal.callback@282 | [282](../../../frontend/src/components/reports/ScientificReport.tsx#L282) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusCellModal.callback@290 | [290](../../../frontend/src/components/reports/ScientificReport.tsx#L290) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusCellModal.callback@290.callback@291 | [291](../../../frontend/src/components/reports/ScientificReport.tsx#L291) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusCellModal.callback@293 | [293](../../../frontend/src/components/reports/ScientificReport.tsx#L293) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule | [299](../../../frontend/src/components/reports/ScientificReport.tsx#L299) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule.sorted | [303](../../../frontend/src/components/reports/ScientificReport.tsx#L303) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule.sorted.callback@303 | [303](../../../frontend/src/components/reports/ScientificReport.tsx#L303) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule.filtered | [306](../../../frontend/src/components/reports/ScientificReport.tsx#L306) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule.filtered.callback@306 | [306](../../../frontend/src/components/reports/ScientificReport.tsx#L306) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule.callback@310 | [310](../../../frontend/src/components/reports/ScientificReport.tsx#L310) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ConsensusModule.callback@314 | [314](../../../frontend/src/components/reports/ScientificReport.tsx#L314) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ScientificResults | [317](../../../frontend/src/components/reports/ScientificReport.tsx#L317) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scientific-results-v2.test.mjs |
| ScientificQuestions | [320](../../../frontend/src/components/reports/ScientificReport.tsx#L320) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ScientificQuestions.callback@321 | [321](../../../frontend/src/components/reports/ScientificReport.tsx#L321) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ScientificQuestions.callback@321.callback@321 | [321](../../../frontend/src/components/reports/ScientificReport.tsx#L321) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI | [328](../../../frontend/src/components/reports/ScientificReport.tsx#L328) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@336 | [336](../../../frontend/src/components/reports/ScientificReport.tsx#L336) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@336.callback@341 | [341](../../../frontend/src/components/reports/ScientificReport.tsx#L341) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@336.callback@342 | [342](../../../frontend/src/components/reports/ScientificReport.tsx#L342) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@349 | [349](../../../frontend/src/components/reports/ScientificReport.tsx#L349) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351 | [351](../../../frontend/src/components/reports/ScientificReport.tsx#L351) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351 | [351](../../../frontend/src/components/reports/ScientificReport.tsx#L351) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.callback@352 | [352](../../../frontend/src/components/reports/ScientificReport.tsx#L352) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.size | [357](../../../frontend/src/components/reports/ScientificReport.tsx#L357) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.callback@359 | [359](../../../frontend/src/components/reports/ScientificReport.tsx#L359) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.contains | [360](../../../frontend/src/components/reports/ScientificReport.tsx#L360) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.contains.callback@360 | [360](../../../frontend/src/components/reports/ScientificReport.tsx#L360) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.callback@370 | [370](../../../frontend/src/components/reports/ScientificReport.tsx#L370) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.callback@372 | [372](../../../frontend/src/components/reports/ScientificReport.tsx#L372) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@351.callback@377 | [377](../../../frontend/src/components/reports/ScientificReport.tsx#L377) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@383 | [383](../../../frontend/src/components/reports/ScientificReport.tsx#L383) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@383.callback@387 | [387](../../../frontend/src/components/reports/ScientificReport.tsx#L387) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@383.callback@392 | [392](../../../frontend/src/components/reports/ScientificReport.tsx#L392) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@383.callback@392 | [392](../../../frontend/src/components/reports/ScientificReport.tsx#L392) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@398 | [398](../../../frontend/src/components/reports/ScientificReport.tsx#L398) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@398.callback@402 | [402](../../../frontend/src/components/reports/ScientificReport.tsx#L402) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.evaluateFor | [407](../../../frontend/src/components/reports/ScientificReport.tsx#L407) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.evaluateFor.callback@410 | [410](../../../frontend/src/components/reports/ScientificReport.tsx#L410) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.evaluateFor.callback@410 | [410](../../../frontend/src/components/reports/ScientificReport.tsx#L410) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@412 | [412](../../../frontend/src/components/reports/ScientificReport.tsx#L412) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@413 | [413](../../../frontend/src/components/reports/ScientificReport.tsx#L413) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.withOutcome | [428](../../../frontend/src/components/reports/ScientificReport.tsx#L428) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.withOutcome.callback@428 | [428](../../../frontend/src/components/reports/ScientificReport.tsx#L428) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@433 | [433](../../../frontend/src/components/reports/ScientificReport.tsx#L433) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@433 | [433](../../../frontend/src/components/reports/ScientificReport.tsx#L433) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@436 | [436](../../../frontend/src/components/reports/ScientificReport.tsx#L436) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@436.callback@436 | [436](../../../frontend/src/components/reports/ScientificReport.tsx#L436) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@439 | [439](../../../frontend/src/components/reports/ScientificReport.tsx#L439) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@440 | [440](../../../frontend/src/components/reports/ScientificReport.tsx#L440) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@441 | [441](../../../frontend/src/components/reports/ScientificReport.tsx#L441) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@441 | [441](../../../frontend/src/components/reports/ScientificReport.tsx#L441) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@442 | [442](../../../frontend/src/components/reports/ScientificReport.tsx#L442) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@442.callback@442 | [442](../../../frontend/src/components/reports/ScientificReport.tsx#L442) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@442.callback@442.callback@442 | [442](../../../frontend/src/components/reports/ScientificReport.tsx#L442) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@443 | [443](../../../frontend/src/components/reports/ScientificReport.tsx#L443) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@443.callback@443 | [443](../../../frontend/src/components/reports/ScientificReport.tsx#L443) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@443 | [443](../../../frontend/src/components/reports/ScientificReport.tsx#L443) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@443.callback@443 | [443](../../../frontend/src/components/reports/ScientificReport.tsx#L443) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@444 | [444](../../../frontend/src/components/reports/ScientificReport.tsx#L444) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@444.callback@444 | [444](../../../frontend/src/components/reports/ScientificReport.tsx#L444) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@444 | [444](../../../frontend/src/components/reports/ScientificReport.tsx#L444) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PersistedXAI.callback@444.callback@444 | [444](../../../frontend/src/components/reports/ScientificReport.tsx#L444) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/components/reports/ScientificRepresentations.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| runLabel | [12](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L12) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| percent | [14](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_microscopy_quality_services.py; malaria_dl_local_project/tests/test_prediction_collapse.py; frontend/tests/frotis-v2.test.mjs |
| decimal | [15](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_training_summaries_api.py; backend_api/tests/test_cell_classification_services.py; backend_api/tests/test_grouped_run_lineage_api.py; … (8 referencias nominales; ver CSV) |
| shortSample | [18](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| outcome | [29](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_cell_classification_services.py; malaria_dl_local_project/tests/test_training_completion_postgres.py; … (15 referencias nominales; ver CSV) |
| componentsFor | [32](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L32) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| componentsFor.callback@33 | [33](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration | [38](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L38) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.callback@43 | [43](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L43) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.callback@43.read | [47](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L47) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.callback@43.read.callback@52 | [52](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.callback@43.callback@56 | [56](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.generate | [60](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.generate.callback@61 | [61](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentGeneration.callback@67 | [67](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L67) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PointDetails | [76](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L76) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| PointDetails.callback@107 | [107](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L107) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart | [113](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L113) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@114 | [114](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L114) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@114.callback@116 | [116](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@114.callback@117 | [117](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L117) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@114.callback@117.callback@120 | [120](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L120) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@127 | [127](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L127) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@128 | [128](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L128) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@128.release | [130](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@128.escape | [131](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L131) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@128.callback@134 | [134](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.pin | [136](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L136) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@140 | [140](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L140) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@145 | [145](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L145) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@150 | [150](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L150) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@150.callback@151 | [151](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L151) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ProjectionChart.callback@154 | [154](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L154) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart | [160](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L160) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@161 | [161](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L161) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@162 | [162](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L162) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@162.callback@162 | [162](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L162) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@165 | [165](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L165) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@166 | [166](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L166) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@166 | [166](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L166) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| VarianceChart.callback@167 | [167](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L167) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CkaHeatmap | [171](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L171) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CkaHeatmap.callback@175 | [175](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L175) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CkaHeatmap.callback@176 | [176](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L176) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CkaHeatmap.callback@176.callback@176 | [176](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L176) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| RepresentationResults | [180](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L180) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@183 | [183](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L183) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@183 | [183](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L183) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@184 | [184](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L184) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@184 | [184](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L184) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@185 | [185](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L185) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@185.callback@185 | [185](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L185) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@186 | [186](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L186) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@189 | [189](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L189) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@189.callback@190 | [190](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L190) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@198 | [198](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L198) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@202 | [202](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L202) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@202.callback@202 | [202](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L202) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@203 | [203](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L203) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@203.callback@203 | [203](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L203) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@205 | [205](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L205) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| RepresentationResults.callback@213 | [213](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L213) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations | [222](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L222) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@226 | [226](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L226) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@226.callback@226 | [226](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L226) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@226.callback@226.callback@226 | [226](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L226) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@228 | [228](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L228) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@228.callback@229 | [229](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L229) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@228.callback@230 | [230](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L230) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ScientificRepresentations.callback@233 | [233](../../../frontend/src/components/reports/ScientificRepresentations.tsx#L233) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |

## frontend/src/components/reports/Stage2PublicationPanel.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| value | [14](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (176 referencias nominales; ver CSV) |
| date | [15](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; … (140 referencias nominales; ver CSV) |
| completionLabel | [19](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L19) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| Stage2PublicationPanel | [32](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L32) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |
| Stage2PublicationPanel.execute | [41](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L41) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |
| Stage2PublicationPanel.callback@73 | [73](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L73) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |
| Stage2PublicationPanel.callback@92 | [92](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L92) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |
| Stage2PublicationPanel.callback@114 | [114](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L114) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |
| Stage2PublicationPanel.callback@115 | [115](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L115) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |
| Stage2PublicationPanel.callback@119 | [119](../../../frontend/src/components/reports/Stage2PublicationPanel.tsx#L119) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; frontend/tests/stage2-availability.test.mjs; … (4 referencias nominales; ver CSV) |

## frontend/src/components/reports/TrainingRunGroupCard.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| isStage2Active | [22](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L22) | Canonical availability wins over the persisted summary; a status error never shows a stale productive summary. | Sin referencia nominal localizada |
| TrainingRunDetailPanel | [51](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L51) | Derived pipeline (EVALUATE / EXPLAIN) and the release panel of one TRAIN; expansion state is owned by the caller. | Sin referencia nominal localizada |
| TrainingRunDetailPanel.callback@118 | [118](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L118) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingRunDetailPanel.callback@119 | [119](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L119) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingRunDetailPanel.callback@126 | [126](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L126) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingRunDetailPanel.callback@138 | [138](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L138) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingRunGroupCard | [172](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L172) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; … (6 referencias nominales; ver CSV) |
| TrainingRunGroupCard.toggleChildren | [179](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L179) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; … (6 referencias nominales; ver CSV) |
| TrainingRunGroupCard.toggleStage2 | [186](../../../frontend/src/components/reports/TrainingRunGroupCard.tsx#L186) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/e6-lineage.test.mjs; … (6 referencias nominales; ver CSV) |

## frontend/src/components/reports/TrainingRunsTable.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| label | [26](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (97 referencias nominales; ver CSV) |
| modelFilterValue | [28](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L28) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sortedOptions | [33](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sortedOptions.callback@33 | [33](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| sortedOptions.callback@34 | [34](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L34) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| openDialog | [45](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| TrainingRunsTable | [86](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L86) | Client-side TRAIN report (the summaries endpoint returns the whole bounded collection): global search, faceted filters per column, sorting and 7-row pages. Selection is keyed by run_id, so it survives paging and filterin | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@91 | [91](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L91) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@97 | [97](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L97) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.updateFilters | [99](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L99) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.updateFilters.callback@102 | [102](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L102) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.updateFilters.callback@103 | [103](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L103) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.toggleActiveModel | [107](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L107) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.toggleActiveModel.callback@107 | [107](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L107) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.toggleActiveModel.callback@107.callback@108 | [108](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L108) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.toggleActiveModel.callback@107.callback@109 | [109](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L109) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@111 | [111](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L111) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@111.callback@116 | [116](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@111.callback@126 | [126](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L126) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130 | [130](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L130) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.accessorFn | [134](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.sortingFn | [135](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L135) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.filterFn | [137](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L137) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.Cell | [139](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L139) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.accessorFn | [145](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L145) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.filterFn | [147](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L147) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.Cell | [150](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L150) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.accessorFn | [156](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L156) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.Cell | [158](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L158) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.callback@162 | [162](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L162) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.callback@162.accessorFn | [163](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L163) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.callback@162.Cell | [165](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L165) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.accessorFn | [169](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L169) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@130.Cell | [171](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L171) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@180 | [180](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L180) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@180.callback@180 | [180](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L180) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@183 | [183](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L183) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@183.callback@183 | [183](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L183) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.getRowId | [189](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L189) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.onGlobalFilterChange | [192](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L192) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.onGlobalFilterChange.callback@192 | [192](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L192) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@210 | [210](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L210) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.Cell | [217](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L217) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.onRowSelectionChange | [223](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L223) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.onRowSelectionChange.callback@226 | [226](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L226) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.callback@231 | [231](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L231) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.getRowCanExpand | [233](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L233) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.muiDetailPanelProps | [235](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L235) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.muiTableBodyRowProps | [236](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L236) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.renderTopToolbarCustomActions | [241](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L241) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.renderTopToolbarCustomActions.callback@250 | [250](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L250) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.renderTopToolbarCustomActions.callback@250.callback@250 | [250](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L250) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| TrainingRunsTable.renderTopToolbarCustomActions.callback@250.callback@250 | [250](../../../frontend/src/components/reports/TrainingRunsTable.tsx#L250) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |

## frontend/src/components/reports/XAIComparisonViewer.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| record | [14](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L14) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_smear_reset_tool.py; … (90 referencias nominales; ver CSV) |
| classLabel | [15](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| identityOf | [16](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| compactMetadata | [18](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L18) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| downloadJson | [23](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L23) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| downloadJson.callback@27 | [27](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| methodSettings | [30](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L30) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace | [48](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L48) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@49 | [49](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L49) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.samplesOf | [51](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L51) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@52 | [52](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@52.callback@52 | [52](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@54 | [54](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L54) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@68 | [68](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L68) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@68.callback@70 | [70](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@68.callback@71 | [71](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L71) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| CellTrace.callback@77 | [77](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidencePanel | [86](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L86) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidencePanel.callback@101 | [101](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L101) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidencePanel.callback@107 | [107](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L107) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| EvidencePanel.callback@117 | [117](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L117) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| outcomeCategory | [129](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| decimal | [131](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L131) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_training_summaries_api.py; backend_api/tests/test_cell_classification_services.py; backend_api/tests/test_grouped_run_lineage_api.py; … (8 referencias nominales; ver CSV) |
| CellOutcome | [133](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L133) | Real class, the model's category for this cell and its score against the decision threshold. | frontend/tests/scc-xai.test.mjs |
| XAIComparisonContent | [146](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L146) | Pure shared presentation: neither modal nor inline starts a second image request. | frontend/tests/scc-xai.test.mjs |
| XAIComparisonContent.callback@152 | [152](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L152) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIComparisonContent.callback@156 | [156](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L156) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIExpandedView | [166](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L166) | Expanded view body (Comparación / Superposición); the viewer's own modal and hosts with their own modal share it. | Sin referencia nominal localizada |
| XAIExpandedView.callback@172 | [172](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L172) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| XAIExpandedView.callback@176 | [176](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L176) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| XAIExpandedView.callback@176.callback@177 | [177](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L177) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| XAIComparisonViewer | [192](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L192) | variant="expanded" renders only the expanded view, for a host that already is a modal (Errores y consenso). variant="toolbar" renders the cell's image as the link to «Vista ampliada» and its outcome; the XAI images load  | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@203 | [203](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L203) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@203.callback@206 | [206](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L206) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@203.callback@206.callback@207 | [207](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L207) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@203.callback@210 | [210](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L210) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@220 | [220](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L220) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@223 | [223](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L223) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.expand | [231](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L231) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@238 | [238](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L238) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@240 | [240](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L240) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |
| XAIComparisonViewer.callback@246 | [246](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L246) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs; frontend/tests/scc-xai.test.mjs |

## frontend/src/components/reports/XAIOverlayView.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useAttributionLayer | [17](../../../frontend/src/components/reports/XAIOverlayView.tsx#L17) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAttributionLayer.callback@20 | [20](../../../frontend/src/components/reports/XAIOverlayView.tsx#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAttributionLayer.callback@20.callback@23 | [23](../../../frontend/src/components/reports/XAIOverlayView.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAttributionLayer.callback@20.callback@23 | [23](../../../frontend/src/components/reports/XAIOverlayView.tsx#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAttributionLayer.callback@20.callback@29 | [29](../../../frontend/src/components/reports/XAIOverlayView.tsx#L29) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useAttributionLayer.callback@20.callback@32 | [32](../../../frontend/src/components/reports/XAIOverlayView.tsx#L32) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useLoadedImage | [38](../../../frontend/src/components/reports/XAIOverlayView.tsx#L38) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useLoadedImage.callback@40 | [40](../../../frontend/src/components/reports/XAIOverlayView.tsx#L40) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useLoadedImage.callback@40.callback@44 | [44](../../../frontend/src/components/reports/XAIOverlayView.tsx#L44) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| XAIOverlayView | [51](../../../frontend/src/components/reports/XAIOverlayView.tsx#L51) | Original cell as base; each attribution map drawn on top with its own opacity (0–100 %). | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@52 | [52](../../../frontend/src/components/reports/XAIOverlayView.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@52.callback@52 | [52](../../../frontend/src/components/reports/XAIOverlayView.tsx#L52) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@62 | [62](../../../frontend/src/components/reports/XAIOverlayView.tsx#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@63 | [63](../../../frontend/src/components/reports/XAIOverlayView.tsx#L63) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.update | [76](../../../frontend/src/components/reports/XAIOverlayView.tsx#L76) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.update.callback@77 | [77](../../../frontend/src/components/reports/XAIOverlayView.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@81 | [81](../../../frontend/src/components/reports/XAIOverlayView.tsx#L81) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@82 | [82](../../../frontend/src/components/reports/XAIOverlayView.tsx#L82) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@82.callback@83 | [83](../../../frontend/src/components/reports/XAIOverlayView.tsx#L83) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@82.callback@85 | [85](../../../frontend/src/components/reports/XAIOverlayView.tsx#L85) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@82.callback@85.callback@85 | [85](../../../frontend/src/components/reports/XAIOverlayView.tsx#L85) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@82.callback@86 | [86](../../../frontend/src/components/reports/XAIOverlayView.tsx#L86) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@82.callback@86.callback@86 | [86](../../../frontend/src/components/reports/XAIOverlayView.tsx#L86) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.generate | [88](../../../frontend/src/components/reports/XAIOverlayView.tsx#L88) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.generate.callback@91 | [91](../../../frontend/src/components/reports/XAIOverlayView.tsx#L91) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.generate.callback@92 | [92](../../../frontend/src/components/reports/XAIOverlayView.tsx#L92) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.generate.callback@95 | [95](../../../frontend/src/components/reports/XAIOverlayView.tsx#L95) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.generate.callback@95.callback@95 | [95](../../../frontend/src/components/reports/XAIOverlayView.tsx#L95) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.generate.callback@96 | [96](../../../frontend/src/components/reports/XAIOverlayView.tsx#L96) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@103 | [103](../../../frontend/src/components/reports/XAIOverlayView.tsx#L103) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@105 | [105](../../../frontend/src/components/reports/XAIOverlayView.tsx#L105) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@114 | [114](../../../frontend/src/components/reports/XAIOverlayView.tsx#L114) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@114.callback@125 | [125](../../../frontend/src/components/reports/XAIOverlayView.tsx#L125) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@114.callback@128 | [128](../../../frontend/src/components/reports/XAIOverlayView.tsx#L128) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| XAIOverlayView.callback@114.callback@134 | [134](../../../frontend/src/components/reports/XAIOverlayView.tsx#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |

## frontend/src/components/reports/useCellComparison.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useCellComparison | [18](../../../frontend/src/components/reports/useCellComparison.ts#L18) | «Vista ampliada» of a cell: the same comparison as Explicabilidad, read from the EVALUATE that produced the cell (GET /assessments/{attempt_id}) and completed with its outcome (real class, prediction, score and threshold | Sin referencia nominal localizada |
| useCellComparison.callback@23 | [23](../../../frontend/src/components/reports/useCellComparison.ts#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useCellComparison.callback@23.callback@27 | [27](../../../frontend/src/components/reports/useCellComparison.ts#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useCellComparison.callback@23.callback@31 | [31](../../../frontend/src/components/reports/useCellComparison.ts#L31) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useCellComparison.callback@23.callback@32 | [32](../../../frontend/src/components/reports/useCellComparison.ts#L32) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useCellComparison.callback@35 | [35](../../../frontend/src/components/reports/useCellComparison.ts#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useExpandRequest | [50](../../../frontend/src/components/reports/useCellComparison.ts#L50) | Click on a cell image → «Vista ampliada». A click that arrives before the comparison is ready is kept and opens the view as soon as it is; each new value of `signal` opens it (XAIComparisonViewer `expandSignal`). | frontend/tests/cell-expanded-view.test.mjs |
| useExpandRequest.callback@53 | [53](../../../frontend/src/components/reports/useCellComparison.ts#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs |
| useExpandRequest.callback@53.callback@54 | [54](../../../frontend/src/components/reports/useCellComparison.ts#L54) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs |
| useExpandRequest.callback@56 | [56](../../../frontend/src/components/reports/useCellComparison.ts#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs |
| useExpandRequest.callback@56.callback@56 | [56](../../../frontend/src/components/reports/useCellComparison.ts#L56) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-expanded-view.test.mjs |

## frontend/src/components/reports/xai/comparison.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| execution | [59](../../../frontend/src/components/reports/xai/comparison.ts#L59) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (106 referencias nominales; ver CSV) |
| canonicalContext | [66](../../../frontend/src/components/reports/xai/comparison.ts#L66) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| canonicalContext.callback@68 | [68](../../../frontend/src/components/reports/xai/comparison.ts#L68) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| canonicalContext.callback@69 | [69](../../../frontend/src/components/reports/xai/comparison.ts#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| groupXAIComparisons | [74](../../../frontend/src/components/reports/xai/comparison.ts#L74) | Only explicit identities establish equivalence. No filenames, ordering or SHAP background. | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@83 | [83](../../../frontend/src/components/reports/xai/comparison.ts#L83) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@91 | [91](../../../frontend/src/components/reports/xai/comparison.ts#L91) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@99 | [99](../../../frontend/src/components/reports/xai/comparison.ts#L99) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@101 | [101](../../../frontend/src/components/reports/xai/comparison.ts#L101) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@102 | [102](../../../frontend/src/components/reports/xai/comparison.ts#L102) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@119 | [119](../../../frontend/src/components/reports/xai/comparison.ts#L119) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| groupXAIComparisons.callback@131 | [131](../../../frontend/src/components/reports/xai/comparison.ts#L131) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |

## frontend/src/components/ui/StatusPill.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| StatusPill | [33](../../../frontend/src/components/ui/StatusPill.tsx#L33) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/hooks/useComparisonCatalog.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useComparisonCatalog | [5](../../../frontend/src/hooks/useComparisonCatalog.ts#L5) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonCatalog.callback@9 | [9](../../../frontend/src/hooks/useComparisonCatalog.ts#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonCatalog.callback@9.callback@13 | [13](../../../frontend/src/hooks/useComparisonCatalog.ts#L13) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonCatalog.callback@9.callback@15 | [15](../../../frontend/src/hooks/useComparisonCatalog.ts#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonCatalog.callback@9.callback@16 | [16](../../../frontend/src/hooks/useComparisonCatalog.ts#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonCatalog.retry | [18](../../../frontend/src/hooks/useComparisonCatalog.ts#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonCatalog.retry.callback@18 | [18](../../../frontend/src/hooks/useComparisonCatalog.ts#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |

## frontend/src/hooks/useComparisonEvidence.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useComparisonEvidence | [4](../../../frontend/src/hooks/useComparisonEvidence.ts#L4) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| useComparisonEvidence.callback@6 | [6](../../../frontend/src/hooks/useComparisonEvidence.ts#L6) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| useComparisonEvidence.callback@6.callback@9 | [9](../../../frontend/src/hooks/useComparisonEvidence.ts#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| useComparisonEvidence.callback@6.callback@10 | [10](../../../frontend/src/hooks/useComparisonEvidence.ts#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| useComparisonEvidence.callback@6.callback@11 | [11](../../../frontend/src/hooks/useComparisonEvidence.ts#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/hooks/useComparisonRun.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useComparisonRun | [5](../../../frontend/src/hooks/useComparisonRun.ts#L5) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonRun.callback@9 | [9](../../../frontend/src/hooks/useComparisonRun.ts#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonRun.callback@9.callback@13 | [13](../../../frontend/src/hooks/useComparisonRun.ts#L13) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonRun.callback@9.callback@18 | [18](../../../frontend/src/hooks/useComparisonRun.ts#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonRun.callback@9.callback@22 | [22](../../../frontend/src/hooks/useComparisonRun.ts#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonRun.retry | [24](../../../frontend/src/hooks/useComparisonRun.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonRun.retry.callback@24 | [24](../../../frontend/src/hooks/useComparisonRun.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |

## frontend/src/hooks/useComparisonSelection.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| addComparisonRun | [10](../../../frontend/src/hooks/useComparisonSelection.tsx#L10) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonSelectionProvider | [15](../../../frontend/src/hooks/useComparisonSelection.tsx#L15) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonSelectionProvider.add | [18](../../../frontend/src/hooks/useComparisonSelection.tsx#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonSelectionProvider.add.callback@18 | [18](../../../frontend/src/hooks/useComparisonSelection.tsx#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonSelectionProvider.remove | [19](../../../frontend/src/hooks/useComparisonSelection.tsx#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonSelectionProvider.remove.callback@19 | [19](../../../frontend/src/hooks/useComparisonSelection.tsx#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| ComparisonSelectionProvider.remove.callback@19.callback@19 | [19](../../../frontend/src/hooks/useComparisonSelection.tsx#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonSelection | [23](../../../frontend/src/hooks/useComparisonSelection.tsx#L23) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs; frontend/tests/scc-selection.test.mjs |

## frontend/src/hooks/useComparisonTrainingSummaries.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useComparisonTrainingSummaries | [6](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L6) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.callback@10 | [10](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.callback@10.callback@15 | [15](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.callback@10.callback@15.callback@17 | [17](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L17) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.callback@10.callback@15.callback@18 | [18](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L18) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.callback@10.callback@22 | [22](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.retry | [24](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |
| useComparisonTrainingSummaries.retry.callback@24 | [24](../../../frontend/src/hooks/useComparisonTrainingSummaries.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs |

## frontend/src/hooks/useExplainExecutor.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| useExplainExecutor | [9](../../../frontend/src/hooks/useExplainExecutor.ts#L9) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainExecutor.callback@12 | [12](../../../frontend/src/hooks/useExplainExecutor.ts#L12) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainExecutor.callback@12.read | [16](../../../frontend/src/hooks/useExplainExecutor.ts#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainExecutor.callback@12.read.callback@19 | [19](../../../frontend/src/hooks/useExplainExecutor.ts#L19) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainExecutor.callback@12.callback@22 | [22](../../../frontend/src/hooks/useExplainExecutor.ts#L22) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-selection.test.mjs; frontend/tests/scc-xai.test.mjs |
| executorLabel | [28](../../../frontend/src/hooks/useExplainExecutor.ts#L28) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |

## frontend/src/hooks/useExplainGeneration.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| explainFailure | [8](../../../frontend/src/hooks/useExplainGeneration.ts#L8) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| useExplainGeneration | [23](../../../frontend/src/hooks/useExplainGeneration.ts#L23) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@44 | [44](../../../frontend/src/hooks/useExplainGeneration.ts#L44) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@44.callback@51 | [51](../../../frontend/src/hooks/useExplainGeneration.ts#L51) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@57 | [57](../../../frontend/src/hooks/useExplainGeneration.ts#L57) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@58 | [58](../../../frontend/src/hooks/useExplainGeneration.ts#L58) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@59 | [59](../../../frontend/src/hooks/useExplainGeneration.ts#L59) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@59.poll | [62](../../../frontend/src/hooks/useExplainGeneration.ts#L62) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@59.poll.callback@65 | [65](../../../frontend/src/hooks/useExplainGeneration.ts#L65) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@59.callback@68 | [68](../../../frontend/src/hooks/useExplainGeneration.ts#L68) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.execute | [72](../../../frontend/src/hooks/useExplainGeneration.ts#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.execute.callback@79 | [79](../../../frontend/src/hooks/useExplainGeneration.ts#L79) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.execute.callback@80 | [80](../../../frontend/src/hooks/useExplainGeneration.ts#L80) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@97 | [97](../../../frontend/src/hooks/useExplainGeneration.ts#L97) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@108 | [108](../../../frontend/src/hooks/useExplainGeneration.ts#L108) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@108.callback@109 | [109](../../../frontend/src/hooks/useExplainGeneration.ts#L109) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@108.callback@110 | [110](../../../frontend/src/hooks/useExplainGeneration.ts#L110) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@108.execute | [111](../../../frontend/src/hooks/useExplainGeneration.ts#L111) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@115 | [115](../../../frontend/src/hooks/useExplainGeneration.ts#L115) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@116 | [116](../../../frontend/src/hooks/useExplainGeneration.ts#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.callback@119 | [119](../../../frontend/src/hooks/useExplainGeneration.ts#L119) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| useExplainGeneration.generateAll | [120](../../../frontend/src/hooks/useExplainGeneration.ts#L120) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |

## frontend/src/hooks/useScientificArtifact.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| artifactFailure | [6](../../../frontend/src/hooks/useScientificArtifact.ts#L6) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| useScientificArtifact | [17](../../../frontend/src/hooks/useScientificArtifact.ts#L17) | SCC-ART.1 client and object URL lifecycle; one owner supplies inline and modal. | frontend/tests/scc-xai.test.mjs |
| useScientificArtifact.callback@27 | [27](../../../frontend/src/hooks/useScientificArtifact.ts#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |

## frontend/src/pages/ModelComparison.tsx

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| isEvaluationSlot | [9](../../../frontend/src/pages/ModelComparison.tsx#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| isEvaluationSlot.callback@9 | [9](../../../frontend/src/pages/ModelComparison.tsx#L9) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage | [21](../../../frontend/src/pages/ModelComparison.tsx#L21) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@25 | [25](../../../frontend/src/pages/ModelComparison.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@25.callback@25 | [25](../../../frontend/src/pages/ModelComparison.tsx#L25) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@27 | [27](../../../frontend/src/pages/ModelComparison.tsx#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@33 | [33](../../../frontend/src/pages/ModelComparison.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@33.callback@33 | [33](../../../frontend/src/pages/ModelComparison.tsx#L33) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@35 | [35](../../../frontend/src/pages/ModelComparison.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@35.callback@35 | [35](../../../frontend/src/pages/ModelComparison.tsx#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@41 | [41](../../../frontend/src/pages/ModelComparison.tsx#L41) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@41.callback@41 | [41](../../../frontend/src/pages/ModelComparison.tsx#L41) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@48 | [48](../../../frontend/src/pages/ModelComparison.tsx#L48) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@48.callback@48 | [48](../../../frontend/src/pages/ModelComparison.tsx#L48) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@55 | [55](../../../frontend/src/pages/ModelComparison.tsx#L55) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@55.callback@55 | [55](../../../frontend/src/pages/ModelComparison.tsx#L55) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@61 | [61](../../../frontend/src/pages/ModelComparison.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@61.callback@61 | [61](../../../frontend/src/pages/ModelComparison.tsx#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@69 | [69](../../../frontend/src/pages/ModelComparison.tsx#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@69.callback@69 | [69](../../../frontend/src/pages/ModelComparison.tsx#L69) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@70 | [70](../../../frontend/src/pages/ModelComparison.tsx#L70) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@70.callback@71 | [71](../../../frontend/src/pages/ModelComparison.tsx#L71) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@70.callback@71 | [71](../../../frontend/src/pages/ModelComparison.tsx#L71) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.runLabel | [72](../../../frontend/src/pages/ModelComparison.tsx#L72) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.runLabel.callback@73 | [73](../../../frontend/src/pages/ModelComparison.tsx#L73) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.runLabel.callback@74 | [74](../../../frontend/src/pages/ModelComparison.tsx#L74) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.openSelector | [77](../../../frontend/src/pages/ModelComparison.tsx#L77) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@93 | [93](../../../frontend/src/pages/ModelComparison.tsx#L93) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@93.callback@93 | [93](../../../frontend/src/pages/ModelComparison.tsx#L93) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@94 | [94](../../../frontend/src/pages/ModelComparison.tsx#L94) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@100 | [100](../../../frontend/src/pages/ModelComparison.tsx#L100) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@100.callback@100 | [100](../../../frontend/src/pages/ModelComparison.tsx#L100) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@104 | [104](../../../frontend/src/pages/ModelComparison.tsx#L104) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@104.callback@105 | [105](../../../frontend/src/pages/ModelComparison.tsx#L105) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@104.callback@107 | [107](../../../frontend/src/pages/ModelComparison.tsx#L107) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@109 | [109](../../../frontend/src/pages/ModelComparison.tsx#L109) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@109.callback@110 | [110](../../../frontend/src/pages/ModelComparison.tsx#L110) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@116 | [116](../../../frontend/src/pages/ModelComparison.tsx#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@116 | [116](../../../frontend/src/pages/ModelComparison.tsx#L116) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@117 | [117](../../../frontend/src/pages/ModelComparison.tsx#L117) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ComparisonPage.callback@118 | [118](../../../frontend/src/pages/ModelComparison.tsx#L118) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| ModelComparison | [122](../../../frontend/src/pages/ModelComparison.tsx#L122) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_model_comparison_api.py; frontend/tests/model-explorer.test.mjs; frontend/tests/scc-selection.test.mjs |

## frontend/src/router.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| encoded | [4](../../../frontend/src/router.ts#L4) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_explainability_api.py; backend_api/tests/test_foundation_config.py; backend_api/tests/test_cell_classification_services.py; … (4 referencias nominales; ver CSV) |
| runDetail | [10](../../../frontend/src/router.ts#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/run-detail-explainability.test.mjs; frontend/tests/model-ai-navigation.test.mjs |
| runReleaseDetail | [11](../../../frontend/src/router.ts#L11) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| assessmentDetail | [15](../../../frontend/src/router.ts#L15) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| modelVersionDetail | [21](../../../frontend/src/router.ts#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/clean-routing.test.mjs; frontend/tests/model-ai-navigation.test.mjs |
| deploymentDetail | [23](../../../frontend/src/router.ts#L23) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/clean-routing.test.mjs; frontend/tests/model-ai-navigation.test.mjs |
| smearMicroscopeAnalysis | [32](../../../frontend/src/router.ts#L32) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| smearHistoryDetail | [35](../../../frontend/src/router.ts#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/smear-ui-refresh.test.mjs; frontend/tests/frotis-v3.test.mjs |
| isValidPublicId | [41](../../../frontend/src/router.ts#L41) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/clean-routing.test.mjs; frontend/tests/frotis-v3.test.mjs; frontend/tests/model-explorer.test.mjs; … (6 referencias nominales; ver CSV) |
| withAllowedQuery | [44](../../../frontend/src/router.ts#L44) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| withAllowedQuery.callback@49 | [49](../../../frontend/src/router.ts#L49) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| buildShareableUrl | [58](../../../frontend/src/router.ts#L58) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/services/api.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| readStoredAccessToken | [218](../../../frontend/src/services/api.ts#L218) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |
| restoreAccessToken | [230](../../../frontend/src/services/api.ts#L230) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |
| setAccessToken | [235](../../../frontend/src/services/api.ts#L235) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/auth-foundation.test.mjs |
| onAuthenticationFailure | [252](../../../frontend/src/services/api.ts#L252) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| cancelPendingRequests | [256](../../../frontend/src/services/api.ts#L256) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |
| cancelPendingRequests.callback@257 | [257](../../../frontend/src/services/api.ts#L257) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |
| handleAuthenticationFailure | [261](../../../frontend/src/services/api.ts#L261) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/auth-foundation.test.mjs |
| request | [304](../../../frontend/src/services/api.ts#L304) | FunctionDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (81 referencias nominales; ver CSV) |
| request.callback@310 | [310](../../../frontend/src/services/api.ts#L310) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (81 referencias nominales; ver CSV) |
| request.callback@310.callback@311 | [311](../../../frontend/src/services/api.ts#L311) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (81 referencias nominales; ver CSV) |
| request.callback@337 | [337](../../../frontend/src/services/api.ts#L337) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (81 referencias nominales; ver CSV) |
| request.callback@338 | [338](../../../frontend/src/services/api.ts#L338) | ArrowFunction; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; … (81 referencias nominales; ver CSV) |
| performRequest | [344](../../../frontend/src/services/api.ts#L344) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| performRequest.abortFromCaller | [346](../../../frontend/src/services/api.ts#L346) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| performRequest.callback@351 | [351](../../../frontend/src/services/api.ts#L351) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| requestBlob | [417](../../../frontend/src/services/api.ts#L417) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| requestBlob.abortFromCaller | [419](../../../frontend/src/services/api.ts#L419) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| requestBlob.callback@423 | [423](../../../frontend/src/services/api.ts#L423) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| requestBlob.callback@435 | [435](../../../frontend/src/services/api.ts#L435) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| trustedCellContentPath | [469](../../../frontend/src/services/api.ts#L469) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| asObject | [488](../../../frontend/src/services/api.ts#L488) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizeClassificationRun | [494](../../../frontend/src/services/api.ts#L494) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizeExplanation | [519](../../../frontend/src/services/api.ts#L519) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizeClassificationReview | [552](../../../frontend/src/services/api.ts#L552) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizePrediction | [578](../../../frontend/src/services/api.ts#L578) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizePrediction.callback@601 | [601](../../../frontend/src/services/api.ts#L601) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizeClassificationSummary | [610](../../../frontend/src/services/api.ts#L610) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| login | [626](../../../frontend/src/services/api.ts#L626) | MethodDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_mutation_security_policy.py; backend_api/tests/test_backend_runtime_role_contract.py; … (4 referencias nominales; ver CSV) |
| me | [634](../../../frontend/src/services/api.ts#L634) | MethodDeclaration; operación exacta en llamadas y cuerpo | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_cell_activation_read_only.py; … (278 referencias nominales; ver CSV) |
| withDatasource | [639](../../../frontend/src/services/api.ts#L639) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getComparisonReport | [644](../../../frontend/src/services/api.ts#L644) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| getComparisonPreflight | [650](../../../frontend/src/services/api.ts#L650) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| getModelArchitecture | [655](../../../frontend/src/services/api.ts#L655) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getActivationTraces | [659](../../../frontend/src/services/api.ts#L659) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getActivationTraceCandidates | [662](../../../frontend/src/services/api.ts#L662) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getTrainingTrajectories | [665](../../../frontend/src/services/api.ts#L665) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getActivationTrace | [668](../../../frontend/src/services/api.ts#L668) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createActivationTrace | [671](../../../frontend/src/services/api.ts#L671) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-explorer.test.mjs |
| deleteActivationTrace | [675](../../../frontend/src/services/api.ts#L675) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getTrainingAssessments | [678](../../../frontend/src/services/api.ts#L678) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getExplainContext | [681](../../../frontend/src/services/api.ts#L681) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getExplainState | [684](../../../frontend/src/services/api.ts#L684) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs; frontend/tests/scc-xai.test.mjs |
| getExplainExecutor | [688](../../../frontend/src/services/api.ts#L688) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| prepareExplanation | [691](../../../frontend/src/services/api.ts#L691) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| generateExplanation | [694](../../../frontend/src/services/api.ts#L694) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/scc-art.test.mjs; frontend/tests/scc-xai.test.mjs |
| getRepresentationState | [697](../../../frontend/src/services/api.ts#L697) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| generateRepresentation | [700](../../../frontend/src/services/api.ts#L700) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| scientificTraceability | [704](../../../frontend/src/services/api.ts#L704) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| scientificResults | [709](../../../frontend/src/services/api.ts#L709) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| absoluteUrl | [712](../../../frontend/src/services/api.ts#L712) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getLegacyArtifactBlob | [722](../../../frontend/src/services/api.ts#L722) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs |
| getArtifactBlob | [730](../../../frontend/src/services/api.ts#L730) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/scc-xai.test.mjs |
| getDatasetSampleBlob | [741](../../../frontend/src/services/api.ts#L741) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/scc-xai.test.mjs |
| artifactUrl | [750](../../../frontend/src/services/api.ts#L750) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/e6-lineage.test.mjs |
| mediaUrl | [763](../../../frontend/src/services/api.ts#L763) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getDatasources | [770](../../../frontend/src/services/api.ts#L770) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| lookupScientificSubject | [774](../../../frontend/src/services/api.ts#L774) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-workflow.test.mjs |
| getScientificSamples | [780](../../../frontend/src/services/api.ts#L780) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-workflow.test.mjs |
| uploadMicroscopyImages | [784](../../../frontend/src/services/api.ts#L784) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-ui-refresh.test.mjs; frontend/tests/smear-workflow.test.mjs |
| createAnalysisRun | [796](../../../frontend/src/services/api.ts#L796) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-workflow.test.mjs |
| getAnalysisRun | [801](../../../frontend/src/services/api.ts#L801) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-workflow.test.mjs |
| getSmearWorkflow | [802](../../../frontend/src/services/api.ts#L802) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/smear-ui-refresh.test.mjs; frontend/tests/smear-workflow.test.mjs |
| getSmearAnalysisHistory | [807](../../../frontend/src/services/api.ts#L807) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs; frontend/tests/smear-analysis-history.test.mjs |
| getSmearAnalysisHistoryDetail | [813](../../../frontend/src/services/api.ts#L813) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs; frontend/tests/smear-analysis-history.test.mjs |
| getMicroscopyImageBlob | [818](../../../frontend/src/services/api.ts#L818) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs; frontend/tests/smear-analysis-history.test.mjs |
| getEligibleCellAnalysisRuns | [824](../../../frontend/src/services/api.ts#L824) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| createCellDetectionRun | [830](../../../frontend/src/services/api.ts#L830) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs; frontend/tests/smear-workflow.test.mjs |
| getCellDetectionRuns | [840](../../../frontend/src/services/api.ts#L840) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| getCellDetectionRun | [846](../../../frontend/src/services/api.ts#L846) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| getCellDetectionImages | [851](../../../frontend/src/services/api.ts#L851) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getCellDetections | [856](../../../frontend/src/services/api.ts#L856) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| getCellDetection | [866](../../../frontend/src/services/api.ts#L866) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs; frontend/tests/frotis-v3.test.mjs |
| getCellReviews | [871](../../../frontend/src/services/api.ts#L871) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createCellReview | [876](../../../frontend/src/services/api.ts#L876) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| getCellCropBlob | [893](../../../frontend/src/services/api.ts#L893) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs; frontend/tests/frotis-v3.test.mjs |
| getCellOriginalImageBlob | [897](../../../frontend/src/services/api.ts#L897) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-review-workspace.test.mjs |
| getEligibleCellClassificationRuns | [906](../../../frontend/src/services/api.ts#L906) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getEligibleCellClassificationRuns.callback@910 | [910](../../../frontend/src/services/api.ts#L910) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getEligibleCellClassificationRuns.callback@910.callback@912 | [912](../../../frontend/src/services/api.ts#L912) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| createCellClassificationRun | [920](../../../frontend/src/services/api.ts#L920) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellClassificationRuns | [934](../../../frontend/src/services/api.ts#L934) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellClassificationRuns.callback@938 | [938](../../../frontend/src/services/api.ts#L938) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellClassificationRun | [943](../../../frontend/src/services/api.ts#L943) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellClassificationPredictions | [948](../../../frontend/src/services/api.ts#L948) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| getCellClassificationPredictions.callback@955 | [955](../../../frontend/src/services/api.ts#L955) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/frotis-v3.test.mjs |
| getCellClassificationSummary | [960](../../../frontend/src/services/api.ts#L960) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellPrediction | [971](../../../frontend/src/services/api.ts#L971) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/frotis-v3.test.mjs |
| createCellExplanation | [976](../../../frontend/src/services/api.ts#L976) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs; frontend/tests/history-annotation-capabilities.test.mjs |
| getCellExplanation | [990](../../../frontend/src/services/api.ts#L990) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| generateCaseGradCam | [995](../../../frontend/src/services/api.ts#L995) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/run-detail-explainability.test.mjs |
| getCellExplanationHeatmapBlob | [1002](../../../frontend/src/services/api.ts#L1002) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellExplanationOverlayBlob | [1008](../../../frontend/src/services/api.ts#L1008) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| createCellClassificationReview | [1014](../../../frontend/src/services/api.ts#L1014) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getCellClassificationReviews | [1034](../../../frontend/src/services/api.ts#L1034) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getHumanCellClassification | [1039](../../../frontend/src/services/api.ts#L1039) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| saveHumanCellClassification | [1044](../../../frontend/src/services/api.ts#L1044) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/cell-classification-workflow.test.mjs |
| getHumanCellClassificationHistory | [1061](../../../frontend/src/services/api.ts#L1061) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| listScientificValidationSessions | [1066](../../../frontend/src/services/api.ts#L1066) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getScientificValidationSession | [1071](../../../frontend/src/services/api.ts#L1071) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveScientificValidationSession | [1076](../../../frontend/src/services/api.ts#L1076) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/history-annotation-capabilities.test.mjs |
| listScientificValidationAnnotations | [1090](../../../frontend/src/services/api.ts#L1090) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createScientificValidationAnnotation | [1107](../../../frontend/src/services/api.ts#L1107) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| updateScientificValidationAnnotation | [1126](../../../frontend/src/services/api.ts#L1126) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getScientificValidationAnnotationHistory | [1139](../../../frontend/src/services/api.ts#L1139) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| reviewQuality | [1146](../../../frontend/src/services/api.ts#L1146) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| enqueueQuality | [1151](../../../frontend/src/services/api.ts#L1151) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-workflow.test.mjs; frontend/tests/quality-queue.test.mjs |
| executeQueueItem | [1156](../../../frontend/src/services/api.ts#L1156) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/smear-workflow.test.mjs; frontend/tests/quality-queue.test.mjs |
| retryQueueItem | [1161](../../../frontend/src/services/api.ts#L1161) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/quality-queue.test.mjs |
| getDashboardSummary | [1167](../../../frontend/src/services/api.ts#L1167) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getClinicalDashboard | [1171](../../../frontend/src/services/api.ts#L1171) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRuns | [1175](../../../frontend/src/services/api.ts#L1175) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getGroupedRunLineage | [1179](../../../frontend/src/services/api.ts#L1179) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs |
| getTrainingSummaries | [1186](../../../frontend/src/services/api.ts#L1186) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/scc-selection.test.mjs |
| getAssessments | [1202](../../../frontend/src/services/api.ts#L1202) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getAssessmentResults | [1206](../../../frontend/src/services/api.ts#L1206) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getAssessmentArtifacts | [1209](../../../frontend/src/services/api.ts#L1209) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs |
| getAssessment | [1213](../../../frontend/src/services/api.ts#L1213) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-art.test.mjs; frontend/tests/e6-lineage.test.mjs |
| getTrainingLineageChildren | [1217](../../../frontend/src/services/api.ts#L1217) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/scc-art.test.mjs |
| getTrainingPromotionStatus | [1237](../../../frontend/src/services/api.ts#L1237) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| prepareTrainingRelease | [1244](../../../frontend/src/services/api.ts#L1244) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getStage2Availability | [1265](../../../frontend/src/services/api.ts#L1265) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/stage2-status.test.mjs |
| getStage2ReleaseStatus | [1271](../../../frontend/src/services/api.ts#L1271) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/stage2-status.test.mjs |
| getProductiveModelAvailability | [1278](../../../frontend/src/services/api.ts#L1278) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/stage2-availability.test.mjs; frontend/tests/stage2-status.test.mjs |
| activateCellModel | [1284](../../../frontend/src/services/api.ts#L1284) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/executions-promotion.test.mjs; frontend/tests/stage2-status.test.mjs |
| publishStage2Model | [1292](../../../frontend/src/services/api.ts#L1292) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| deactivateStage2Publication | [1302](../../../frontend/src/services/api.ts#L1302) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs |
| enableStage2 | [1313](../../../frontend/src/services/api.ts#L1313) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/stage2-availability.test.mjs |
| publishTrainingStage2 | [1325](../../../frontend/src/services/api.ts#L1325) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-promotion.test.mjs |
| getStage2Models | [1335](../../../frontend/src/services/api.ts#L1335) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getTechnicalProductionPreview | [1339](../../../frontend/src/services/api.ts#L1339) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| publishTechnicalProduction | [1346](../../../frontend/src/services/api.ts#L1346) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRun | [1359](../../../frontend/src/services/api.ts#L1359) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/run-detail-explainability.test.mjs |
| getRunClinicalSummary | [1363](../../../frontend/src/services/api.ts#L1363) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRunCheckpointPolicy | [1367](../../../frontend/src/services/api.ts#L1367) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRunThresholdCalibration | [1374](../../../frontend/src/services/api.ts#L1374) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRunArtifactsSummary | [1381](../../../frontend/src/services/api.ts#L1381) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRunImagePredictions | [1385](../../../frontend/src/services/api.ts#L1385) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRunExplainability | [1392](../../../frontend/src/services/api.ts#L1392) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/run-detail-explainability.test.mjs |
| getScientificModels | [1401](../../../frontend/src/services/api.ts#L1401) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getModels | [1404](../../../frontend/src/services/api.ts#L1404) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getModelVersions | [1408](../../../frontend/src/services/api.ts#L1408) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getModelVersion | [1412](../../../frontend/src/services/api.ts#L1412) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/executions-lazy-loading.test.mjs; frontend/tests/four-step-production-flow.test.mjs |
| getModelVersionLineage | [1416](../../../frontend/src/services/api.ts#L1416) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getModelVersionContractCandidates | [1420](../../../frontend/src/services/api.ts#L1420) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/four-step-production-flow.test.mjs |
| completeModelVersionContract | [1424](../../../frontend/src/services/api.ts#L1424) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/four-step-production-flow.test.mjs |
| publishModelVersionToProduction | [1430](../../../frontend/src/services/api.ts#L1430) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/deployments-inline-review.test.mjs; frontend/tests/four-step-production-flow.test.mjs |
| getModelProductionReadiness | [1436](../../../frontend/src/services/api.ts#L1436) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/four-step-production-flow.test.mjs |
| getDeployments | [1440](../../../frontend/src/services/api.ts#L1440) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| getDeploymentReadiness | [1444](../../../frontend/src/services/api.ts#L1444) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| getAvailableModels | [1448](../../../frontend/src/services/api.ts#L1448) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| validateModelVersion | [1452](../../../frontend/src/services/api.ts#L1452) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| approveModelVersion | [1458](../../../frontend/src/services/api.ts#L1458) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| createDeployment | [1464](../../../frontend/src/services/api.ts#L1464) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| smokeTestDeployment | [1470](../../../frontend/src/services/api.ts#L1470) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| activateDeployment | [1476](../../../frontend/src/services/api.ts#L1476) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| transitionDeployment | [1482](../../../frontend/src/services/api.ts#L1482) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| rollbackDeployment | [1488](../../../frontend/src/services/api.ts#L1488) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/model-ai-navigation.test.mjs |
| createImageAnalysisJob | [1494](../../../frontend/src/services/api.ts#L1494) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getClinicalModelComparison | [1500](../../../frontend/src/services/api.ts#L1500) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getDatasets | [1504](../../../frontend/src/services/api.ts#L1504) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getDatasetVersions | [1508](../../../frontend/src/services/api.ts#L1508) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/campaign-configuration.test.mjs; frontend/tests/governed-dataset-ui.test.mjs |
| getDatasetVersionDetail | [1512](../../../frontend/src/services/api.ts#L1512) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getCampaignCatalog | [1517](../../../frontend/src/services/api.ts#L1517) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/campaign-configuration.test.mjs |
| previewCampaign | [1521](../../../frontend/src/services/api.ts#L1521) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/campaign-configuration.test.mjs |
| createCampaign | [1528](../../../frontend/src/services/api.ts#L1528) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getCampaign | [1538](../../../frontend/src/services/api.ts#L1538) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/campaign-configuration.test.mjs; frontend/tests/campaigns-report.test.mjs |
| getCampaigns | [1542](../../../frontend/src/services/api.ts#L1542) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/campaigns-report.test.mjs |
| getDatasetImages | [1546](../../../frontend/src/services/api.ts#L1546) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/campaign-configuration.test.mjs; frontend/tests/campaigns-report.test.mjs |
| getMetrics | [1553](../../../frontend/src/services/api.ts#L1553) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getConfusionMatrix | [1557](../../../frontend/src/services/api.ts#L1557) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getClassificationReport | [1561](../../../frontend/src/services/api.ts#L1561) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getExplainability | [1565](../../../frontend/src/services/api.ts#L1565) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getExplainabilityCases | [1572](../../../frontend/src/services/api.ts#L1572) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getFalsePositiveCases | [1579](../../../frontend/src/services/api.ts#L1579) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getFalseNegativeCases | [1586](../../../frontend/src/services/api.ts#L1586) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getLowConfidenceCases | [1593](../../../frontend/src/services/api.ts#L1593) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getExplainabilityCaseSummary | [1600](../../../frontend/src/services/api.ts#L1600) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getExplainabilityGallery | [1607](../../../frontend/src/services/api.ts#L1607) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getUploadedPredictions | [1614](../../../frontend/src/services/api.ts#L1614) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getErrors | [1621](../../../frontend/src/services/api.ts#L1621) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getLogs | [1625](../../../frontend/src/services/api.ts#L1625) | MethodDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/utils/analysisSummaries.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| curveSummary | [6](../../../frontend/src/utils/analysisSummaries.ts#L6) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| curveSummary.callback@7 | [7](../../../frontend/src/utils/analysisSummaries.ts#L7) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| curveSummary.callback@10 | [10](../../../frontend/src/utils/analysisSummaries.ts#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| metricRange | [27](../../../frontend/src/utils/analysisSummaries.ts#L27) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| metricRange.callback@28 | [28](../../../frontend/src/utils/analysisSummaries.ts#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| pairwise | [35](../../../frontend/src/utils/analysisSummaries.ts#L35) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| pairwise.callback@37 | [37](../../../frontend/src/utils/analysisSummaries.ts#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| pairwise.callback@37.callback@37 | [37](../../../frontend/src/utils/analysisSummaries.ts#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| consensusSummary | [41](../../../frontend/src/utils/analysisSummaries.ts#L41) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| consensusSummary.callback@45 | [45](../../../frontend/src/utils/analysisSummaries.ts#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| consensusSummary.callback@46 | [46](../../../frontend/src/utils/analysisSummaries.ts#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| intensity | [51](../../../frontend/src/utils/analysisSummaries.ts#L51) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/utils/attributionMaps.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| parseNpy | [6](../../../frontend/src/utils/attributionMaps.ts#L6) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| parseNpy.callback@13 | [13](../../../frontend/src/utils/attributionMaps.ts#L13) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| parseNpy.callback@16 | [16](../../../frontend/src/utils/attributionMaps.ts#L16) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-xai.test.mjs |
| activationColor | [31](../../../frontend/src/utils/attributionMaps.ts#L31) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| activationColor.callback@35 | [35](../../../frontend/src/utils/attributionMaps.ts#L35) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| attributionPixels | [44](../../../frontend/src/utils/attributionMaps.ts#L44) | RGBA pixels for one layer. Alpha follows the attribution magnitude, so neutral regions stay transparent and the cell remains visible; the layer opacity slider scales it further. Grad-CAM: activation ramp, normalized by i | frontend/tests/scc-xai.test.mjs |

## frontend/src/utils/comparisonCache.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| createComparisonCache | [2](../../../frontend/src/utils/comparisonCache.ts#L2) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| createComparisonCache.read | [5](../../../frontend/src/utils/comparisonCache.ts#L5) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| createComparisonCache.read.callback@10 | [10](../../../frontend/src/utils/comparisonCache.ts#L10) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| createComparisonCache.clear | [13](../../../frontend/src/utils/comparisonCache.ts#L13) | MethodDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/utils/datasetChecks.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| datasetCheckLabel | [16](../../../frontend/src/utils/datasetChecks.ts#L16) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/utils/format.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| formatMetric | [3](../../../frontend/src/utils/format.ts#L3) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| formatDate | [8](../../../frontend/src/utils/format.ts#L8) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| formatDuration | [15](../../../frontend/src/utils/format.ts#L15) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| formatDuration.callback@26 | [26](../../../frontend/src/utils/format.ts#L26) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| getRunDuration | [32](../../../frontend/src/utils/format.ts#L32) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stringifyJson | [63](../../../frontend/src/utils/format.ts#L63) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/utils/lineageSlots.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| choiceKey | [24](../../../frontend/src/utils/lineageSlots.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| slotOf | [26](../../../frontend/src/utils/lineageSlots.ts#L26) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| groupEvaluations | [32](../../../frontend/src/utils/lineageSlots.ts#L32) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| effectiveSlot | [39](../../../frontend/src/utils/lineageSlots.ts#L39) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| effectiveSlot.callback@42 | [42](../../../frontend/src/utils/lineageSlots.ts#L42) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| isAssessmentExplanation | [45](../../../frontend/src/utils/lineageSlots.ts#L45) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| groupExplanations | [48](../../../frontend/src/utils/lineageSlots.ts#L48) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| groupExplanations.callback@50 | [50](../../../frontend/src/utils/lineageSlots.ts#L50) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| isCellExplanation | [59](../../../frontend/src/utils/lineageSlots.ts#L59) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| splitExplanations | [60](../../../frontend/src/utils/lineageSlots.ts#L60) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| splitExplanations.callback@61 | [61](../../../frontend/src/utils/lineageSlots.ts#L61) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/utils/preflightPresentation.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| stableValue | [4](../../../frontend/src/utils/preflightPresentation.ts#L4) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| stableValue.callback@6 | [6](../../../frontend/src/utils/preflightPresentation.ts#L6) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| completeValue | [9](../../../frontend/src/utils/preflightPresentation.ts#L9) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| equalityKey | [15](../../../frontend/src/utils/preflightPresentation.ts#L15) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| compareValues | [18](../../../frontend/src/utils/preflightPresentation.ts#L18) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| compareValues.callback@20 | [20](../../../frontend/src/utils/preflightPresentation.ts#L20) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| compareValues.callback@21 | [21](../../../frontend/src/utils/preflightPresentation.ts#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| compareValues.callback@21.callback@21 | [21](../../../frontend/src/utils/preflightPresentation.ts#L21) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| compareValues.callback@24 | [24](../../../frontend/src/utils/preflightPresentation.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| compareValues.callback@24.callback@24 | [24](../../../frontend/src/utils/preflightPresentation.ts#L24) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField | [26](../../../frontend/src/utils/preflightPresentation.ts#L26) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField.callback@27 | [27](../../../frontend/src/utils/preflightPresentation.ts#L27) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField.callback@28 | [28](../../../frontend/src/utils/preflightPresentation.ts#L28) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField.callback@28.callback@30 | [30](../../../frontend/src/utils/preflightPresentation.ts#L30) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField.callback@34 | [34](../../../frontend/src/utils/preflightPresentation.ts#L34) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField.callback@36 | [36](../../../frontend/src/utils/preflightPresentation.ts#L36) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| projectField.callback@37 | [37](../../../frontend/src/utils/preflightPresentation.ts#L37) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| evaluationComparison | [44](../../../frontend/src/utils/preflightPresentation.ts#L44) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| evaluationComparison.callback@46 | [46](../../../frontend/src/utils/preflightPresentation.ts#L46) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| classifyFields | [52](../../../frontend/src/utils/preflightPresentation.ts#L52) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| classifyFields.callback@53 | [53](../../../frontend/src/utils/preflightPresentation.ts#L53) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| evaluationDetails | [59](../../../frontend/src/utils/preflightPresentation.ts#L59) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| evaluationDetails.callback@60 | [60](../../../frontend/src/utils/preflightPresentation.ts#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| evaluationDetails.callback@60.callback@60 | [60](../../../frontend/src/utils/preflightPresentation.ts#L60) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| openEvidenceTarget | [63](../../../frontend/src/utils/preflightPresentation.ts#L63) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| openEvidenceTarget.reveal | [73](../../../frontend/src/utils/preflightPresentation.ts#L73) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| evaluationField | [81](../../../frontend/src/utils/preflightPresentation.ts#L81) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| evaluationField.callback@84 | [84](../../../frontend/src/utils/preflightPresentation.ts#L84) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| evaluationField.callback@94 | [94](../../../frontend/src/utils/preflightPresentation.ts#L94) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| evaluationField.callback@94 | [94](../../../frontend/src/utils/preflightPresentation.ts#L94) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| missingEvidence | [109](../../../frontend/src/utils/preflightPresentation.ts#L109) | FunctionDeclaration; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.add | [111](../../../frontend/src/utils/preflightPresentation.ts#L111) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122 | [122](../../../frontend/src/utils/preflightPresentation.ts#L122) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122.callback@127 | [127](../../../frontend/src/utils/preflightPresentation.ts#L127) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122.callback@127.callback@127 | [127](../../../frontend/src/utils/preflightPresentation.ts#L127) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122.callback@129 | [129](../../../frontend/src/utils/preflightPresentation.ts#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122.callback@129.callback@129 | [129](../../../frontend/src/utils/preflightPresentation.ts#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122.callback@129.callback@129 | [129](../../../frontend/src/utils/preflightPresentation.ts#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@122.callback@129 | [129](../../../frontend/src/utils/preflightPresentation.ts#L129) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@134 | [134](../../../frontend/src/utils/preflightPresentation.ts#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@134.callback@134 | [134](../../../frontend/src/utils/preflightPresentation.ts#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@134 | [134](../../../frontend/src/utils/preflightPresentation.ts#L134) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@136 | [136](../../../frontend/src/utils/preflightPresentation.ts#L136) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |
| missingEvidence.callback@136 | [136](../../../frontend/src/utils/preflightPresentation.ts#L136) | ArrowFunction; operación exacta en llamadas y cuerpo | frontend/tests/scc-preflight.test.mjs |

## frontend/src/utils/runDetail.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| parsedJson | [111](../../../frontend/src/utils/runDetail.ts#L111) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| recordValue | [122](../../../frontend/src/utils/runDetail.ts#L122) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| numberValue | [128](../../../frontend/src/utils/runDetail.ts#L128) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| textValue | [135](../../../frontend/src/utils/runDetail.ts#L135) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| booleanValue | [141](../../../frontend/src/utils/runDetail.ts#L141) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizeExecutionParameters | [149](../../../frontend/src/utils/runDetail.ts#L149) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| shellQuote | [158](../../../frontend/src/utils/runDetail.ts#L158) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| cliTokens | [163](../../../frontend/src/utils/runDetail.ts#L163) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| cliTokens.callback@172 | [172](../../../frontend/src/utils/runDetail.ts#L172) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| cliTokens.callback@173 | [173](../../../frontend/src/utils/runDetail.ts#L173) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| commandPrefix | [179](../../../frontend/src/utils/runDetail.ts#L179) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| commandFromCliArguments | [187](../../../frontend/src/utils/runDetail.ts#L187) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| commandFromCliArguments.callback@190 | [190](../../../frontend/src/utils/runDetail.ts#L190) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| commandFromCliArguments.callback@192 | [192](../../../frontend/src/utils/runDetail.ts#L192) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| commandFromCoreParameters | [198](../../../frontend/src/utils/runDetail.ts#L198) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| commandFromCoreParameters.callback@201 | [201](../../../frontend/src/utils/runDetail.ts#L201) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveCommand | [214](../../../frontend/src/utils/runDetail.ts#L214) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveDurationSeconds | [225](../../../frontend/src/utils/runDetail.ts#L225) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows | [237](../../../frontend/src/utils/runDetail.ts#L237) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows.callback@238 | [238](../../../frontend/src/utils/runDetail.ts#L238) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows.callback@240 | [240](../../../frontend/src/utils/runDetail.ts#L240) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows.callback@241 | [241](../../../frontend/src/utils/runDetail.ts#L241) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows.callback@242 | [242](../../../frontend/src/utils/runDetail.ts#L242) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows.callback@242.splitScore | [243](../../../frontend/src/utils/runDetail.ts#L243) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| metricFromRows.callback@242.classScore | [252](../../../frontend/src/utils/runDetail.ts#L252) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| firstNumber | [264](../../../frontend/src/utils/runDetail.ts#L264) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveClinicalMetrics | [272](../../../frontend/src/utils/runDetail.ts#L272) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| matrixValue | [324](../../../frontend/src/utils/runDetail.ts#L324) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| matrixValue.callback@327 | [327](../../../frontend/src/utils/runDetail.ts#L327) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| matrixValue.callback@327.callback@329 | [329](../../../frontend/src/utils/runDetail.ts#L329) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolvedMatrixCounts | [334](../../../frontend/src/utils/runDetail.ts#L334) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix | [344](../../../frontend/src/utils/runDetail.ts#L344) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@349 | [349](../../../frontend/src/utils/runDetail.ts#L349) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@353 | [353](../../../frontend/src/utils/runDetail.ts#L353) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@354 | [354](../../../frontend/src/utils/runDetail.ts#L354) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@354.splitPriority | [355](../../../frontend/src/utils/runDetail.ts#L355) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@363 | [363](../../../frontend/src/utils/runDetail.ts#L363) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@371 | [371](../../../frontend/src/utils/runDetail.ts#L371) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveConfusionMatrix.callback@372 | [372](../../../frontend/src/utils/runDetail.ts#L372) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| epochNumber | [388](../../../frontend/src/utils/runDetail.ts#L388) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| valueFromRow | [392](../../../frontend/src/utils/runDetail.ts#L392) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveTrainingSignals | [400](../../../frontend/src/utils/runDetail.ts#L400) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveTrainingSignals.callback@404 | [404](../../../frontend/src/utils/runDetail.ts#L404) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveTrainingSignals.callback@405 | [405](../../../frontend/src/utils/runDetail.ts#L405) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveTrainingSignals.callback@427 | [427](../../../frontend/src/utils/runDetail.ts#L427) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveTrainingSignals.callback@429 | [429](../../../frontend/src/utils/runDetail.ts#L429) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveTrainingSignals.callback@437 | [437](../../../frontend/src/utils/runDetail.ts#L437) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## frontend/src/utils/runReport.ts

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| tokenizeCommand | [41](../../../frontend/src/utils/runReport.ts#L41) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| tokenizeCommand.flush | [47](../../../frontend/src/utils/runReport.ts#L47) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| extractCommandParam | [83](../../../frontend/src/utils/runReport.ts#L83) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| extractCommandParam.callback@95 | [95](../../../frontend/src/utils/runReport.ts#L95) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| finiteNonNegative | [110](../../../frontend/src/utils/runReport.ts#L110) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| finiteMetric | [116](../../../frontend/src/utils/runReport.ts#L116) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| firstMetric | [122](../../../frontend/src/utils/runReport.ts#L122) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| recordValue | [130](../../../frontend/src/utils/runReport.ts#L130) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| firstCount | [136](../../../frontend/src/utils/runReport.ts#L136) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| normalizeConfusionMatrix | [144](../../../frontend/src/utils/runReport.ts#L144) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveRunConfusion | [184](../../../frontend/src/utils/runReport.ts#L184) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| resolveRunReportMetrics | [188](../../../frontend/src/utils/runReport.ts#L188) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| generateRunAutoAnalysis | [217](../../../frontend/src/utils/runReport.ts#L217) | FunctionDeclaration; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| generateRunAutoAnalysis.callback@221 | [221](../../../frontend/src/utils/runReport.ts#L221) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| generateRunAutoAnalysis.callback@222 | [222](../../../frontend/src/utils/runReport.ts#L222) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |
| generateRunAutoAnalysis.callback@224 | [224](../../../frontend/src/utils/runReport.ts#L224) | ArrowFunction; operación exacta en llamadas y cuerpo | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/assessment/cli.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| seed_arg | [13](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| positive_int | [17](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| image_limit | [24](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| internal_samples | [28](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L28) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| framework | [35](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L35) | Engine family of the item's model; None when no implementation describes it. | backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_stage2_status_read_only.py; … (28 referencias nominales; ver CSV) |
| not_convolutional | [45](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L45) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| parser | [49](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L49) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; malaria_dl_local_project/tests/test_exec1.py; … (4 referencias nominales; ver CSV) |
| main | [73](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L73) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |
| _execute | [96](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L96) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_model_execution_tracking.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (5 referencias nominales; ver CSV) |
| item_python | [118](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L118) | Interpreter of the item's framework environment when it is not this one (local only). | malaria_dl_local_project/tests/test_campaign_evaluation_only.py |
| _assess | [129](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L129) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_campaign_evaluation_only.py |
| _delegate | [160](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L160) | Same assessment in an owned process of the item's framework (.venv-metal / .venv-torch). | malaria_dl_local_project/tests/test_campaign_evaluation_only.py |
| delegated | [181](../../../malaria_dl_local_project/src/malaria_dl/assessment/cli.py#L181) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py |

## malaria_dl_local_project/src/malaria_dl/assessment/contracts.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| require | [15](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_database_url_contract.py; backend_api/tests/test_comparison_eligibility.py; … (22 referencias nominales; ver CSV) |
| probability | [20](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L20) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | frontend/tests/frotis-v3.test.mjs |
| threshold | [28](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L28) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_training_summaries_api.py; … (61 referencias nominales; ver CSV) |
| validate_split_protocol | [88](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L88) | The existing authorization rule, checked before selecting image files. | Sin referencia nominal localizada |
| identity | [108](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L108) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_stage2_status_read_only.py; backend_api/tests/test_representation_generation.py; … (51 referencias nominales; ver CSV) |
| prediction | [171](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L171) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_scientific_validation_annotations_postgres.py; … (26 referencias nominales; ver CSV) |
| metrics | [188](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L188) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_read_only.py; … (51 referencias nominales; ver CSV) |
| verify_rows | [210](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L210) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_assessment_e6.py; malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py; … (7 referencias nominales; ver CSV) |
| ratio | [194](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L194) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; frontend/tests/cell-review-workspace.test.mjs; … (4 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/assessment/lineage.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| resolve | [25](../../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L25) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (145 referencias nominales; ver CSV) |
| logical_train_binding | [158](../../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L158) | Zero-shot origin: frozen protocol from the version, dataset chosen explicitly (never inherited). | malaria_dl_local_project/tests/test_openclip_assessment.py |
| dataset_samples | [182](../../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L182) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scc_xai_original.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_science_postgres.py; … (8 referencias nominales; ver CSV) |
| campaign_inventory | [247](../../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L247) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_dataset_resolution.py; malaria_dl_local_project/tests/test_assessment_e6.py |
| connection | [97](../../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L97) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (76 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/assessment/openclip.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| is_openclip | [30](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L30) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| is_supervised | [34](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L34) | A head trained by an OpenCLIP TRAIN (linear probing or fine-tuning) over the registered base. | Sin referencia nominal localizada |
| supervised_input_contract | [39](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L39) | Frozen input/output identity of a trained BiomedCLIP head; the base is identified by bytes. | malaria_dl_local_project/tests/test_biomedclip_training.py |
| validate_supervised_contract | [55](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L55) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| input_contract | [82](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L82) | Location-independent identity of the frozen zero-shot protocol. | backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_availability.py; … (27 referencias nominales; ver CSV) |
| validate_input_contract | [97](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L97) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_representation_generation.py; malaria_dl_local_project/tests/test_biomedclip_training.py; malaria_dl_local_project/tests/test_input_contract_e3.py; … (4 referencias nominales; ver CSV) |
| decision | [121](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L121) | `auto` is the two-prompt argmax rule implied by the registered softmax output.  softmax(...)[parasitized] >= 0.5 selects the parasitized prompt (ties included). It is fixed by the version before any VAL/TEST, so TEST nee | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_representation_generation.py; backend_api/tests/test_cell_detection_services.py; … (32 referencias nominales; ver CSV) |
| calibration | [151](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L151) | Recompute the VAL threshold from the single verified argmax EVALUATE of this model and dataset.  The reference rows are re-verified against their attempt before use, so the threshold is reconstructible from persisted evi | backend_api/tests/test_campaigns_api_swv22.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_model_execution_tracking.py; … (32 referencias nominales; ver CSV) |
| registered_dependencies | [184](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L184) | Bind the frozen dependency bytes to this TRAIN's registered artifacts. | backend_api/tests/test_cell_classification_services.py |
| assessment_device | [348](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L348) | Local host: the Apple GPU (no silent CPU fallback); the Docker backend keeps CPU. | Sin referencia nominal localizada |
| _PositiveScore | [423](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L423) | Differentiable parasitized score; text features are constants of the frozen prompts. | malaria_dl_local_project/tests/test_openclip_assessment.py |
| OpenCLIPRuntime.__init__ | [210](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L210) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| OpenCLIPRuntime.images | [240](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L240) | Normalized NCHW float32, from verified bytes through the registered transform. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_microscopy_quality_services.py; … (23 referencias nominales; ver CSV) |
| OpenCLIPRuntime._scores | [255](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L255) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| OpenCLIPRuntime.predict | [260](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L260) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_activation.py; malaria_dl_local_project/tests/test_external_model_registration.py; … (9 referencias nominales; ver CSV) |
| OpenCLIPRuntime.represent | [263](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L263) | L2-normalized image embeddings and raw scores from one forward pass. | backend_api/tests/test_representation_generation.py |
| OpenCLIPRuntime.display | [278](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L278) | Undo only the normalization: the resized and cropped RGB image in [0, 1]. | malaria_dl_local_project/tests/test_input_contract_e3.py; frontend/tests/cell-review-workspace.test.mjs; frontend/tests/deployments-inline-review.test.mjs; … (4 referencias nominales; ver CSV) |
| OpenCLIPRuntime.from_display | [284](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L284) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| OpenCLIPRuntime.explain | [290](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L290) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_lineage_children_api.py; backend_api/tests/test_representation_generation.py; backend_api/tests/test_e6_lineage_read_only.py; … (33 referencias nominales; ver CSV) |
| OpenCLIPRuntime._positive_module | [344](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L344) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| SupervisedOpenCLIPRuntime.__init__ | [362](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L362) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| SupervisedOpenCLIPRuntime._scores | [385](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L385) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| SupervisedOpenCLIPRuntime.represent | [395](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L395) | L2-normalized embeddings that feed the head, and its raw scores, from one pass. | backend_api/tests/test_representation_generation.py |
| SupervisedOpenCLIPRuntime._positive_module | [408](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L408) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| PositiveScore.__init__ | [428](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L428) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| PositiveScore.forward | [434](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L434) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| PositiveScore.__init__ | [413](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L413) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| PositiveScore.forward | [417](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L417) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/assessment/repository.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| AssessmentRepository.authorize | [15](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_result_service.py; malaria_dl_local_project/tests/test_train_run_persistence.py; malaria_dl_local_project/tests/test_training_results.py; … (5 referencias nominales; ver CSV) |
| AssessmentRepository.reserve | [22](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L22) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; … (9 referencias nominales; ver CSV) |
| AssessmentRepository.attempt | [82](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L82) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_stage2_status_read_only.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_activation_traces.py; … (41 referencias nominales; ver CSV) |
| AssessmentRepository.identity | [95](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L95) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_activation_read_only.py; backend_api/tests/test_stage2_status_read_only.py; backend_api/tests/test_representation_generation.py; … (51 referencias nominales; ver CSV) |
| AssessmentRepository.verified_evaluations | [103](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L103) | Verified EVALUATE attempts of one TRAIN; callers match the full identity. | malaria_dl_local_project/tests/test_openclip_assessment.py |
| AssessmentRepository.results | [115](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L115) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_detection_crop_equivalence.py; backend_api/tests/test_assessment_artifacts_sample_filter.py; backend_api/tests/test_comparison_eligibility.py; … (44 referencias nominales; ver CSV) |
| AssessmentRepository.artifacts | [125](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L125) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_stage2_status_read_only.py; … (58 referencias nominales; ver CSV) |
| AssessmentRepository.write_batch | [135](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L135) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_assessment_e6.py; malaria_dl_local_project/tests/test_exec1_postgres.py; malaria_dl_local_project/tests/test_assessment_postgres.py |
| AssessmentRepository.artifact | [169](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L169) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_comparison_eligibility.py; … (36 referencias nominales; ver CSV) |
| AssessmentRepository.finish | [183](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L183) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_host_executor.py; malaria_dl_local_project/tests/test_training_completion_postgres.py; malaria_dl_local_project/tests/test_campaign_exit_diagnostics.py; … (24 referencias nominales; ver CSV) |
| AssessmentRepository.consume | [199](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L199) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_dataset_split_isolation.py; malaria_dl_local_project/tests/test_campaign_executor_postgres.py; malaria_dl_local_project/tests/test_dataset_resolution.py; … (6 referencias nominales; ver CSV) |
| AssessmentRepository.recover | [209](../../../malaria_dl_local_project/src/malaria_dl/assessment/repository.py#L209) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_host_executor.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; malaria_dl_local_project/tests/test_assessment_e6.py; … (6 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/assessment/representation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| representation_spec | [14](../../../malaria_dl_local_project/src/malaria_dl/assessment/representation.py#L14) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_representation_generation.py |
| pooling_layer | [24](../../../malaria_dl_local_project/src/malaria_dl/assessment/representation.py#L24) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| project | [32](../../../malaria_dl_local_project/src/malaria_dl/assessment/representation.py#L32) | PCA (variance curve + first two components) and UMAP 2D, deterministic for a seed. | malaria_dl_local_project/tests/test_e02_projection_routing.py; malaria_dl_local_project/tests/test_clean_training_outputs.py; malaria_dl_local_project/tests/test_dataset_evidence_postgres.py; … (6 referencias nominales; ver CSV) |
| linear_cka | [56](../../../malaria_dl_local_project/src/malaria_dl/assessment/representation.py#L56) | Linear CKA (Kornblith et al., 2019) between two representations of the same ordered samples. | backend_api/tests/test_representation_generation.py |

## malaria_dl_local_project/src/malaria_dl/assessment/runtime.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| verified_sample_bytes | [148](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L148) | Authorized sample of this identity, inside the governed root, with its recorded bytes. | Sin referencia nominal localizada |
| attribution_overlay | [168](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L168) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| runtime_for | [177](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L177) | Dispatch on the frozen input contract of the identity, never on the model name. | malaria_dl_local_project/tests/test_openclip_assessment.py |
| save_arrays | [192](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L192) | Population matrices of REPRESENT, with the same exclusive creation as EXPLAIN artifacts. | Sin referencia nominal localizada |
| save_artifacts | [215](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L215) | Exclusive binary creation; failures leave evidence, never overwrite a prior attempt. | Sin referencia nominal localizada |
| KerasRuntime.__init__ | [15](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| KerasRuntime.images | [31](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_microscopy_quality_services.py; … (23 referencias nominales; ver CSV) |
| KerasRuntime.predict | [46](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L46) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_activation.py; malaria_dl_local_project/tests/test_external_model_registration.py; … (9 referencias nominales; ver CSV) |
| KerasRuntime.represent | [53](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L53) | Pooled features and raw scores from one forward pass of the same graph. | backend_api/tests/test_representation_generation.py |
| KerasRuntime.explain | [70](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L70) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_lineage_children_api.py; backend_api/tests/test_representation_generation.py; backend_api/tests/test_e6_lineage_read_only.py; … (33 referencias nominales; ver CSV) |
| predict | [101](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L101) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_activation.py; malaria_dl_local_project/tests/test_external_model_registration.py; … (9 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/assessment/service.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| explanation_spec | [27](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L27) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; malaria_dl_local_project/tests/test_assessment_e6.py; … (6 referencias nominales; ver CSV) |
| inference_options | [62](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L62) | Use the persisted operation profile, then the TRAIN execution profile.  Current model configurations have no separate inference profile. Keeping the persisted execution batch is the minimal fallback; never impose a globa | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_openclip_assessment.py |
| select_explanation_samples | [91](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L91) | Select authorized targets in SQL before constructing the scientific identity. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_sample_repository.py |
| prepare | [114](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L114) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (12 referencias nominales; ver CSV) |
| verify | [234](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L234) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_postgres_transaction_isolation.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; … (12 referencias nominales; ver CSV) |
| verify_representation | [297](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L297) | Rows follow the ordered population; the four matrices exist, are intact and have its length. | Sin referencia nominal localizada |
| represent_reserved | [331](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L331) | One forward pass per batch, projections over the whole population, then rows that cite them. | Sin referencia nominal localizada |
| reserve_execution | [358](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L358) | Reserve in the executing process before HTTP acknowledges the attempt. | backend_api/tests/test_explain_generation.py |
| run | [366](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L366) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (112 referencias nominales; ver CSV) |
| execute_reserved | [375](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L375) | Same scientific execution for CLI and HTTP; no second algorithm pipeline. | backend_api/tests/test_explain_generation.py |
| inference_environment | [444](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L444) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; malaria_dl_local_project/tests/test_input_contract_e3.py; … (4 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/data/input_contract.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| make_input_contract | [19](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L19) | For new resolved configurations or explicitly authored synthetic fixtures only. | malaria_dl_local_project/tests/test_assessment_e6.py; malaria_dl_local_project/tests/test_input_contract_e3.py |
| validate_input_contract | [54](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L54) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_representation_generation.py; malaria_dl_local_project/tests/test_biomedclip_training.py; malaria_dl_local_project/tests/test_input_contract_e3.py; … (4 referencias nominales; ver CSV) |
| resolve_checkpoint_input | [142](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L142) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py |
| validate_model_input | [191](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L191) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_evaluation_finalization_integration.py; malaria_dl_local_project/tests/test_input_contract_e3.py |
| decode_rgb | [243](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L243) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| transform_rgb | [251](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L251) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_assessment_e6.py; malaria_dl_local_project/tests/test_input_contract_e3.py |
| transform_bytes | [267](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L267) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py |
| walk | [211](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py#L211) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_training_release_status_migration.py; … (15 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/data/preprocessing.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| resolve_preprocessing_mode | [25](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L25) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py; malaria_dl_local_project/tests/test_preprocessing.py |
| recommended_preprocessing_mode | [40](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L40) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_preprocessing.py |
| preprocessing_description | [47](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L47) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| resize_image_tensor | [52](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L52) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| apply_model_preprocessing | [57](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L57) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_dataset_resolution.py; malaria_dl_local_project/tests/test_preprocessing.py |
| preprocess_image_tensor | [69](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L69) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| preprocess_numpy_image | [74](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L74) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| preprocessing_metadata | [80](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L80) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_preprocessing.py |
| model_image_to_display | [88](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L88) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py; malaria_dl_local_project/tests/test_preprocessing.py |
| display_images_to_model_inputs | [103](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py#L103) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py; malaria_dl_local_project/tests/test_preprocessing.py |

## malaria_dl_local_project/src/malaria_dl/data/sample_repository.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| select_dataset_sample_ids | [9](../../../malaria_dl_local_project/src/malaria_dl/data/sample_repository.py#L9) | Keep EXPLAIN's exact predicates, deterministic order and LIMIT NULL semantics. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_sample_repository.py |
| select_dataset_sample_records | [26](../../../malaria_dl_local_project/src/malaria_dl/data/sample_repository.py#L26) | Shared source records for the governed materialization, including collisions. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/evaluation/binary_counts.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| metrics_from_counts | [4](../../../malaria_dl_local_project/src/malaria_dl/evaluation/binary_counts.py#L4) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_training_results.py |
| divide | [5](../../../malaria_dl_local_project/src/malaria_dl/evaluation/binary_counts.py#L5) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_governance_migration.py |

## malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| parse_args | [30](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L30) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_db_purge_tool.py; malaria_dl_local_project/tests/test_cli01.py; … (24 referencias nominales; ver CSV) |
| collect_validation_probabilities | [93](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L93) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| build_calibration_payload | [122](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L122) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| build_threshold_calibration_payload | [168](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L168) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| save_calibration | [202](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L202) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| track_calibration_run | [212](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L212) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| main | [406](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_cli.py#L406) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/evaluation/calibration_controller.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| CalibrationController.__init__ | [19](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_controller.py#L19) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| CalibrationController.from_request | [23](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_controller.py#L23) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_scientific_parameter_registry.py |
| CalibrationController.calibrate | [28](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_controller.py#L28) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_scientific_parameter_registry.py; malaria_dl_local_project/tests/test_train_integration.py |
| CalibrationController.threshold | [39](../../../malaria_dl_local_project/src/malaria_dl/evaluation/calibration_controller.py#L39) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_training_summaries_api.py; … (61 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _safe_divide | [32](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L32) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _safe_roc_auc | [39](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L39) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _safe_pr_auc | [50](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L50) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _label_index | [61](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L61) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| clinical_probabilities_from_raw_scores | [67](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L67) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| clinical_predictions_from_probabilities | [93](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L93) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| clinical_predictions_from_raw_scores | [109](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L109) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_threshold_integration.py; malaria_dl_local_project/tests/test_metrics.py; malaria_dl_local_project/tests/test_threshold_clinical_mode.py; … (4 referencias nominales; ver CSV) |
| clinical_confusion_counts | [127](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L127) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_metrics.py |
| compute_prediction_distribution | [146](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L146) | Resume la distribución de predicciones con la convención clínica oficial.  Convención:   0 = uninfected   1 = parasitized | Sin referencia nominal localizada |
| detect_prediction_collapse | [171](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L171) | Detecta predicciones concentradas en una sola clase o bajo el mínimo esperado.  Convención clínica:   0 = uninfected   1 = parasitized | malaria_dl_local_project/tests/test_prediction_collapse.py; malaria_dl_local_project/tests/test_clinical_metrics.py |
| compute_clinical_metrics | [234](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L234) | Calcula métricas clínicas para clasificación binaria de malaria.  Convención: 0 = uninfected 1 = parasitized  y_scores debe representar probability_parasitized. | malaria_dl_local_project/tests/test_metrics.py; malaria_dl_local_project/tests/test_model_registry_e2.py; malaria_dl_local_project/tests/test_clinical_metrics.py |
| clinical_metric_summary | [365](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L365) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| collect_predictions | [430](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L430) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_campaign_executor_e5.py; malaria_dl_local_project/tests/test_evaluation_finalization_integration.py; malaria_dl_local_project/tests/test_input_contract_e3.py |
| evaluate_binary_predictions | [467](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L467) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_metrics.py; malaria_dl_local_project/tests/test_evaluation_finalization_integration.py |
| evaluate_keras_model | [662](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L662) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |

## malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _uuid | [158](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L158) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _aware_datetime | [167](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L167) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _duration | [179](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L179) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _json_safe | [195](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L195) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _summary | [219](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L219) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _service_connection | [235](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L235) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _locked_run | [245](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L245) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _observed_status | [256](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L256) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _completed_result | [265](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L265) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| finalize_evaluation_run | [279](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L279) | Finalize one persisted EVALUATE with lock, CAS, and strict errors. | malaria_dl_local_project/tests/test_evaluation_terminal_service.py; malaria_dl_local_project/tests/test_evaluation_finalization_service.py; malaria_dl_local_project/tests/test_evaluation_finalization_postgres.py |
| fail_evaluation_run | [330](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L330) | Mark a started EVALUATE failed without rewriting terminal runs. | malaria_dl_local_project/tests/test_evaluation_finalization_service.py |
| EvaluationRunNotFoundError.__init__ | [25](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L25) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| NotEvaluationRunError.__init__ | [31](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| EvaluationFinalizationConflictError.__init__ | [37](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| InvalidEvaluationTransitionError.__init__ | [54](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py#L54) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_terminal_service.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _terminal_connection | [36](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_terminal_service.py#L36) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| finalize_evaluation_with_lineage | [46](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_terminal_service.py#L46) | Confirm lineage, complete EVALUATE, and reconcile its TRAIN atomically. | malaria_dl_local_project/tests/test_evaluation_terminal_service.py; malaria_dl_local_project/tests/test_evaluation_finalization_integration.py; malaria_dl_local_project/tests/test_evaluation_training_lineage_postgres.py; … (4 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _uuid | [195](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L195) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _json_safe | [204](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L204) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _metadata | [228](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L228) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _service_connection | [244](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L244) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _lock_evaluation | [254](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L254) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _lock_training | [264](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L264) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _validate_ownership | [274](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L274) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _result | [322](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L322) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_e8.py |
| _identity_mismatches | [348](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L348) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| create_or_confirm_evaluation_training_lineage | [374](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L374) | Create or confirm the exact scientific identity without any UPDATE. | malaria_dl_local_project/tests/test_backfill_run_lineage.py; malaria_dl_local_project/tests/test_evaluation_terminal_service.py; malaria_dl_local_project/tests/test_evaluation_training_lineage_postgres.py; … (6 referencias nominales; ver CSV) |
| TrainingRunNotFoundError.__init__ | [38](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| NotTrainingRunError.__init__ | [44](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L44) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| EvaluationTrainingLineageConflictError.__init__ | [50](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L50) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| EvaluationTrainingLineageCardinalityError.__init__ | [67](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_training_lineage_service.py#L67) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/evaluation/evaluator.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| parse_args | [26](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluator.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_db_purge_tool.py; malaria_dl_local_project/tests/test_cli01.py; … (24 referencias nominales; ver CSV) |
| track_source_training_lineage | [86](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluator.py#L86) | Resuelve y registra el entrenamiento origen de un run ya creado. | malaria_dl_local_project/tests/test_evaluation_finalization_integration.py; malaria_dl_local_project/tests/test_explain_lineage_tracking.py; malaria_dl_local_project/tests/test_evaluate_lineage_tracking.py |
| main | [199](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluator.py#L199) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |
| unresolved_or_raise | [125](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluator.py#L125) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _logit | [11](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L11) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _sigmoid | [16](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L16) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| logit_array | [20](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L20) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| sigmoid_array | [26](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| apply_temperature_scaling | [31](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_calibration.py |
| binary_nll | [38](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| brier_score | [50](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L50) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| expected_calibration_error | [58](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L58) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| calibration_metrics | [81](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L81) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| fit_temperature_scaling | [92](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L92) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_calibration.py |
| load_calibration_file | [147](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L147) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| calibration_params_from_file | [167](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L167) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_calibration.py |
| calibrate_probability | [179](../../../malaria_dl_local_project/src/malaria_dl/evaluation/probability_calibration.py#L179) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_calibration.py |

## malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _as_float | [30](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L30) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _json_safe | [36](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L36) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| validate_calibration_split | [54](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L54) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_threshold_calibration.py |
| build_threshold_candidates | [63](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L63) | Construye candidatos sobre probability_parasitized.  Convención:   0 = uninfected   1 = parasitized | malaria_dl_local_project/tests/test_threshold_calibration.py |
| _metric_subset | [83](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L83) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| evaluate_threshold | [113](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L113) | Evalúa un threshold usando compute_clinical_metrics.  y_scores debe ser probability_parasitized. El argumento beta se conserva para compatibilidad de API; las métricas clínicas actuales exponen F2. | malaria_dl_local_project/tests/test_threshold_calibration.py |
| _selection_key | [126](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L126) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _fallback_key | [137](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L137) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _warnings | [149](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L149) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| find_threshold_for_target_recall | [154](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L154) | Selecciona un threshold sobre probability_parasitized para alcanzar target_recall.  Convención:   0 = uninfected   1 = parasitized  La función no carga datos por sí misma: el llamador debe pasar aquí solo predicciones de | malaria_dl_local_project/tests/test_threshold_calibration.py; malaria_dl_local_project/tests/test_scientific_parameter_registry.py; malaria_dl_local_project/tests/test_training_results.py |
| write_threshold_calibration | [275](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L275) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| default_threshold_calibration_path | [285](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L285) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/evaluation/validation.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| evaluate_validation_predictions | [8](../../../malaria_dl_local_project/src/malaria_dl/evaluation/validation.py#L8) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_e02_projection_routing.py; malaria_dl_local_project/tests/test_training_results_docker.py; malaria_dl_local_project/tests/test_scientific_parameter_registry.py; … (6 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| get_pyplot | [65](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L65) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_model_output_tensor | [74](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L74) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| parse_args | [84](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L84) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_db_purge_tool.py; malaria_dl_local_project/tests/test_cli01.py; … (24 referencias nominales; ver CSV) |
| track_source_training_lineage | [166](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L166) | Resuelve y registra el entrenamiento origen de un run ya creado. | malaria_dl_local_project/tests/test_evaluation_finalization_integration.py; malaria_dl_local_project/tests/test_explain_lineage_tracking.py; malaria_dl_local_project/tests/test_evaluate_lineage_tracking.py |
| methods_to_run | [275](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L275) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| resolve_positive_label | [283](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L283) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| raw_model_predictions | [305](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L305) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| scores_from_predictions | [310](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L310) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| predict_positive_scores | [328](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L328) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py |
| binary_predict_proba | [344](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L344) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py |
| predicted_labels_from_scores | [364](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L364) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_explain_threshold_integration.py |
| get_case_type | [368](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L368) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_explain_threshold_integration.py |
| case_relevance | [378](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L378) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| push_candidate | [386](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L386) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| collect_prediction_candidates | [394](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L394) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_image_by_index | [483](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L483) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| sorted_indices_for_case | [491](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L491) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| select_cases | [521](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L521) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| select_explanation_cases | [623](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L623) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| collect_background_images | [653](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L653) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| sanitize_label | [663](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L663) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| build_output_path | [667](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L667) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| build_title | [680](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L680) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| predicted_class_index | [691](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L691) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_cell_classification_services.py |
| explain_with_lime | [697](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L697) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| extract_shap_array | [774](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L774) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| explain_with_shap | [797](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L797) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| layer_has_rank4_output | [861](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L861) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| iter_conv_layer_candidates | [882](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L882) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| build_gradcam_model | [893](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L893) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py |
| layer_is_connected_to_model | [938](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L938) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| find_last_conv_layer | [946](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L946) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py |
| compute_gradcam_artifacts | [963](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L963) | Return the shared Grad-CAM heatmap, derived overlay, and layer name.  This is the only mathematical implementation used by both the batch explainability pipeline and the on-demand cell explanation service. It performs no | backend_api/tests/test_cell_classification_services.py |
| explain_with_gradcam | [1050](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1050) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| make_summary_row | [1093](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1093) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_explain_threshold_integration.py |
| write_summary | [1124](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1124) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| run_lime | [1128](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1128) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| run_shap | [1148](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1148) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| should_invert_scalar_for_gradcam | [1170](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1170) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| run_gradcam | [1176](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1176) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| main | [1217](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L1217) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |
| unresolved_or_raise | [197](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L197) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| add_case | [547](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L547) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| predict_fn | [719](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L719) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/models/adapters.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| compile_phase | [92](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L92) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_campaign_executor_e5.py; malaria_dl_local_project/tests/test_model_registry_e2.py; … (4 referencias nominales; ver CSV) |
| AdapterResult.trainable_layers | [15](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L15) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_registry_e2.py |
| BaseAdapter.build | [23](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L23) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; … (10 referencias nominales; ver CSV) |
| BaseAdapter.set_phase | [26](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_registry_e2.py; malaria_dl_local_project/tests/test_early_stopping_policy.py |
| BaseAdapter.result | [38](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L38) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; … (123 referencias nominales; ver CSV) |
| CustomCNNAdapter.build | [51](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L51) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; … (10 referencias nominales; ver CSV) |
| VGG16Adapter.build | [65](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L65) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; … (10 referencias nominales; ver CSV) |
| DenseNet121Adapter.build | [79](../../../malaria_dl_local_project/src/malaria_dl/models/adapters.py#L79) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; … (10 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/models/architectures.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| compile_binary_model | [153](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L153) | Compila un modelo binario con métricas útiles para salud/diagnóstico. | malaria_dl_local_project/tests/test_model_registry_e2.py |
| conv_bn_relu | [179](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L179) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| build_custom_cnn | [193](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L193) | CNN propia inspirada en el paper: bloques convolucionales + batch normalization + global average pooling. Salida binaria sigmoid:     0 = uninfected     1 = parasitized La salida cerca de 1 representa probability_parasit | Sin referencia nominal localizada |
| build_vgg16_transfer | [240](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L240) | Transfer Learning con VGG16 preentrenada en ImageNet. Se reemplaza la cabeza de clasificación por:     GlobalAveragePooling2D -> Dense(1024) -> Dropout(0.5) -> Dense(1) | Sin referencia nominal localizada |
| build_densenet121_transfer | [286](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L286) | Build a binary DenseNet121 transfer-learning model.  The project data pipeline supplies RGB tensors in ``[0, 1]`` for the default/``auto`` preprocessing mode.  The persisted normalization layer applies the same channel-w | malaria_dl_local_project/tests/test_densenet_model.py |
| unfreeze_last_layers | [340](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L340) | Descongela las últimas capas del backbone para fine-tuning. | Sin referencia nominal localizada |
| ParasitizedRecall.__init__ | [21](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L21) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ParasitizedRecall.update_state | [27](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L27) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_training_selection.py |
| ParasitizedRecall.result | [51](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L51) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; … (123 referencias nominales; ver CSV) |
| ParasitizedRecall.reset_state | [57](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L57) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ParasitizedRecall.get_config | [61](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L61) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| Specificity.__init__ | [73](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L73) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| Specificity.update_state | [79](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L79) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_training_selection.py |
| Specificity.result | [104](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L104) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; … (123 referencias nominales; ver CSV) |
| Specificity.reset_state | [110](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L110) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| Specificity.get_config | [114](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L114) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| BalancedAccuracy.__init__ | [127](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L127) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| BalancedAccuracy.update_state | [133](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L133) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_training_selection.py |
| BalancedAccuracy.result | [137](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L137) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_lineage_children_postgres.py; … (123 referencias nominales; ver CSV) |
| BalancedAccuracy.reset_state | [140](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L140) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| BalancedAccuracy.get_config | [144](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L144) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| base_files | [26](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L26) | Verified local paths of the registered base: checkpoint plus its four dependencies. | malaria_dl_local_project/tests/test_biomedclip_training.py |
| device | [59](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L59) | Apple GPU only: local TRAIN uses the whole local accelerator, never a silent CPU fallback. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_explain_host_executor.py; backend_api/tests/test_yolo_detector_adapter.py; … (7 referencias nominales; ver CSV) |
| build | [71](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L71) | (classifier, eval transform) on CPU; the caller moves it to its device. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; … (10 referencias nominales; ver CSV) |
| trainable_names | [95](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L95) | Head always; the last ``fine_tune_layers`` ViT blocks (12 = total) with norm and projection. | malaria_dl_local_project/tests/test_biomedclip_training.py |
| set_trainable | [109](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L109) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_biomedclip_training.py |
| save_checkpoint | [116](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L116) | Exclusive creation and fsync, then an atomic link; never overwrites an epoch artifact. | malaria_dl_local_project/tests/test_biomedclip_training.py |
| load_classifier | [137](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L137) | Base plus the trained parameters of a checkpoint, in eval mode on CPU. | malaria_dl_local_project/tests/test_biomedclip_training.py |
| torch_loader | [161](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L161) | verify_session loader: the selected checkpoint reconstructs a (N, 1) parasitized score. | Sin referencia nominal localizada |
| BiomedCLIPClassifier.__init__ | [178](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L178) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| BiomedCLIPClassifier.predict | [185](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L185) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_activation.py; malaria_dl_local_project/tests/test_external_model_registration.py; … (9 referencias nominales; ver CSV) |
| BiomedCLIPBinary.__init__ | [81](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L81) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| BiomedCLIPBinary.embed | [86](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L86) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| BiomedCLIPBinary.forward | [89](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L89) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/models/configuration.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| merge_strict | [13](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L13) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _finite_tree | [26](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| resolve_config | [37](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L37) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_biomedclip_training.py; malaria_dl_local_project/tests/test_local_train_launcher.py; … (13 referencias nominales; ver CSV) |
| load_selected | [190](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L190) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| config_digest | [194](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L194) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| selection_semantics | [202](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L202) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| mode | [211](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py#L211) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_stage2_status_availability.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (60 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _dependencies | [17](../../../malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| image_transform | [34](../../../malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py#L34) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| transform_bytes | [41](../../../malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py#L41) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py |
| create_model | [47](../../../malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py#L47) | Original OpenCLIP model, transform and tokenizer from verified local files, CPU/fp32. | Sin referencia nominal localizada |
| OpenCLIPClassifier.__init__ | [79](../../../malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py#L79) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| OpenCLIPClassifier.predict | [91](../../../malaria_dl_local_project/src/malaria_dl/models/openclip_inference.py#L91) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_activation.py; malaria_dl_local_project/tests/test_external_model_registration.py; … (9 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/models/optimizers.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| optimizer_config | [46](../../../malaria_dl_local_project/src/malaria_dl/models/optimizers.py#L46) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_biomedclip_training.py; malaria_dl_local_project/tests/test_campaign_environment_e9.py; malaria_dl_local_project/tests/test_model_registry_e2.py |
| build_optimizer | [98](../../../malaria_dl_local_project/src/malaria_dl/models/optimizers.py#L98) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_campaign_environment_e9.py; malaria_dl_local_project/tests/test_model_registry_e2.py |

## malaria_dl_local_project/src/malaria_dl/models/registry.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| register | [41](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L41) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_catalog_postgres.py; malaria_dl_local_project/tests/test_campaigns_e4.py; malaria_dl_local_project/tests/test_model_registry_e2.py; … (6 referencias nominales; ver CSV) |
| model_catalog | [74](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L74) | Rows of public.models: the only source of which models exist and their catalog metadata. | malaria_dl_local_project/tests/test_local_train_launcher.py; malaria_dl_local_project/tests/test_model_catalog_postgres.py; malaria_dl_local_project/tests/test_campaigns_e4.py; … (9 referencias nominales; ver CSV) |
| registered_models | [91](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L91) | Model names from the catalog (public.models), not the Python implementations. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_biomedclip_training.py; malaria_dl_local_project/tests/test_model_catalog_postgres.py; … (9 referencias nominales; ver CSV) |
| resolve_descriptor | [96](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L96) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_docker_train_postgres.py; … (11 referencias nominales; ver CSV) |
| evaluation_only | [111](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L111) | Campaign role of a model without TRAIN: its versioned config, or None for trained models.  Such a model joins a campaign outside the TRAIN matrix: ``src.train`` never runs it and the campaign EVALUATE/TEST/EXPLAIN assess | malaria_dl_local_project/tests/test_campaign_evaluation_only.py; malaria_dl_local_project/tests/test_campaign_configuration_swv22.py |
| enabled_models | [130](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L130) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; malaria_dl_local_project/tests/test_model_catalog_postgres.py; malaria_dl_local_project/tests/test_campaigns_e4.py; … (5 referencias nominales; ver CSV) |
| model_arg | [135](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L135) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ModelDescriptor.create_adapter | [31](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_model_catalog_postgres.py; … (8 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _add | [47](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L47) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| flatten | [143](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L143) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_activation_traces.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_scientific_parameter_registry.py; … (4 referencias nominales; ver CSV) |
| defaults_by_model | [154](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L154) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_scientific_parameter_registry.py |
| effective_values | [190](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L190) | Read extension_configuration (or snapshot['resolved']); never fill defaults.  Unknown historical fields are preserved, and missing differs from JSON null. This is configuration evidence, not a claim that an inactive bran | malaria_dl_local_project/tests/test_scientific_parameter_registry.py |
| compare_runs | [202](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L202) | RUN id -> persisted resolved snapshot; include unchanged and missing values. | malaria_dl_local_project/tests/test_scientific_parameter_registry.py |
| consumer_map | [210](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L210) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| Parameter.persistence | [31](../../../malaria_dl_local_project/src/malaria_dl/models/scientific_parameters.py#L31) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_cell_activation.py; backend_api/tests/test_yolo_detector_adapter.py; malaria_dl_local_project/tests/test_external_model_registration.py; … (44 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/science/cli.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| provenance | [17](../../../malaria_dl_local_project/src/malaria_dl/science/cli.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_training_scientific_parameters.py; malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_docker_train_integration.py; … (7 referencias nominales; ver CSV) |
| main | [44](../../../malaria_dl_local_project/src/malaria_dl/science/cli.py#L44) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/science/comparison.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| read_evaluation | [25](../../../malaria_dl_local_project/src/malaria_dl/science/comparison.py#L25) | All DB transactions read-only, including E1 inspection; no audit-writing wrapper. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_ensemble_e8.py; malaria_dl_local_project/tests/test_science_e7.py |
| safe_reason | [125](../../../malaria_dl_local_project/src/malaria_dl/science/comparison.py#L125) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| classify | [135](../../../malaria_dl_local_project/src/malaria_dl/science/comparison.py#L135) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_e7.py; frontend/tests/scc-xai.test.mjs |
| select_candidate | [239](../../../malaria_dl_local_project/src/malaria_dl/science/comparison.py#L239) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_e7.py |
| compare | [303](../../../malaria_dl_local_project/src/malaria_dl/science/comparison.py#L303) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_ensemble_e8.py; malaria_dl_local_project/tests/test_science_e7.py |

## malaria_dl_local_project/src/malaria_dl/science/ensemble.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| architectures | [20](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L20) | One member per architecture of the parent E7 protocol (the experiment), in canonical order. Neither a fixed list nor the live catalog: historical evidence stays stable. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_model_registry_e2.py; malaria_dl_local_project/tests/test_canonical_architecture.py |
| experimental_matrix | [26](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L26) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py |
| weights_for | [56](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L56) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py |
| align | [76](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L76) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| combine | [146](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L146) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_ensemble_e8.py |
| prepare | [194](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L194) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_explain_generation.py; malaria_dl_local_project/tests/test_cli01.py; malaria_dl_local_project/tests/test_dataset_split_isolation.py; … (12 referencias nominales; ver CSV) |
| validate_configuration | [326](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L326) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_e8.py |
| evaluate | [465](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L465) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_lineage_children_api.py; backend_api/tests/test_stage2_status_read_only.py; backend_api/tests/test_representation_generation.py; … (31 referencias nominales; ver CSV) |
| validate_evaluation | [578](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L578) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_model_version_resolver.py; malaria_dl_local_project/tests/test_ensemble_e8.py |
| configuration_event_id | [641](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L641) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py |
| extension_contract | [648](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble.py#L648) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py |

## malaria_dl_local_project/src/malaria_dl/science/ensemble_cli.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| main | [19](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_cli.py#L19) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |
| compare_command | [98](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_cli.py#L98) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/science/ensemble_reporting.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| compare_results | [16](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_reporting.py#L16) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_ensemble_e8.py |
| validate_comparison | [137](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_reporting.py#L137) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| export | [161](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_reporting.py#L161) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_ensemble_e8.py; malaria_dl_local_project/tests/test_science_e7.py; … (10 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| validate_failure | [52](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py#L52) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| EvaluationRepository.read_verified | [16](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py#L16) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_e8.py |
| EvaluationRepository.persist_report | [34](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py#L34) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_persistence_e9_postgres.py; … (4 referencias nominales; ver CSV) |
| EvaluationRepository.read_report | [42](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py#L42) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_persistence_e9_postgres.py; … (5 referencias nominales; ver CSV) |
| ComparisonRepository.report_validator | [76](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py#L76) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ComparisonRepository.persist_report | [81](../../../malaria_dl_local_project/src/malaria_dl/science/ensemble_repository.py#L81) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_persistence_e9_postgres.py; … (4 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/science/protocol.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| require | [17](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L17) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_preflight.py; backend_api/tests/test_database_url_contract.py; backend_api/tests/test_comparison_eligibility.py; … (22 referencias nominales; ver CSV) |
| load_protocol | [22](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L22) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py; … (5 referencias nominales; ver CSV) |
| validate_architectures | [54](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L54) | The protocol declares its architectures; no fixed list. Catalog-free on purpose, so historical evidence never depends on the current public.models rows. | malaria_dl_local_project/tests/test_science_extensibility.py |
| matrix | [67](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L67) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_representation_generation.py; malaria_dl_local_project/tests/test_training_completion_postgres.py; … (13 referencias nominales; ver CSV) |
| configuration_key | [103](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L103) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_e7.py |
| e6_protocol | [107](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L107) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_ensemble_e8.py; … (4 referencias nominales; ver CSV) |
| protocol_document | [123](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L123) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_e7.py |
| campaign_plan | [148](../../../malaria_dl_local_project/src/malaria_dl/science/protocol.py#L148) | Explicit E4 request + protocol. Pure preparation, not campaign creation or execution.  Re-resolved E2 identity must exactly equal the frozen E7 snapshots before use. | malaria_dl_local_project/tests/test_science_extensibility.py; malaria_dl_local_project/tests/test_campaign_configuration_swv22.py; malaria_dl_local_project/tests/test_science_e7.py |

## malaria_dl_local_project/src/malaria_dl/science/reporting.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| markdown | [10](../../../malaria_dl_local_project/src/malaria_dl/science/reporting.py#L10) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_execution_outputs.py; malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py; malaria_dl_local_project/tests/test_science_e7.py |
| export_report | [99](../../../malaria_dl_local_project/src/malaria_dl/science/reporting.py#L99) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_science_e7.py |
| plot_curves | [119](../../../malaria_dl_local_project/src/malaria_dl/science/reporting.py#L119) | Standalone figures from persisted coordinates, never new inference or metrics. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/science/repository.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| validate_report | [14](../../../malaria_dl_local_project/src/malaria_dl/science/repository.py#L14) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_e7.py |
| ScienceRepository.campaign_inventory | [65](../../../malaria_dl_local_project/src/malaria_dl/science/repository.py#L65) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_dataset_resolution.py; malaria_dl_local_project/tests/test_assessment_e6.py |
| ScienceRepository.associated_explanations | [103](../../../malaria_dl_local_project/src/malaria_dl/science/repository.py#L103) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_science_postgres.py |
| ScienceRepository.persist_report | [117](../../../malaria_dl_local_project/src/malaria_dl/science/repository.py#L117) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_persistence_e9_postgres.py; … (4 referencias nominales; ver CSV) |
| ScienceRepository.read_report | [141](../../../malaria_dl_local_project/src/malaria_dl/science/repository.py#L141) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_postgres.py; malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_persistence_e9_postgres.py; … (5 referencias nominales; ver CSV) |
| ScienceRepository.freeze_final | [162](../../../malaria_dl_local_project/src/malaria_dl/science/repository.py#L162) | Persist an exact future TEST identity, after full read-only validation; no inference. | malaria_dl_local_project/tests/test_science_postgres.py; malaria_dl_local_project/tests/test_science_e7.py |

## malaria_dl_local_project/src/malaria_dl/science/statistics.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| validate_rows | [27](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L27) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| metrics | [45](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L45) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_results_v2.py; backend_api/tests/test_scientific_report.py; backend_api/tests/test_stage2_status_read_only.py; … (51 referencias nominales; ver CSV) |
| curves | [98](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L98) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; malaria_dl_local_project/tests/test_model_execution_outputs.py; … (6 referencias nominales; ver CSV) |
| threshold_selection | [125](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L125) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_ensemble_e8.py; malaria_dl_local_project/tests/test_science_e7.py |
| seed_summary | [173](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L173) | No pooling predictions. Require distinct seeds and expose missing repetitions. | malaria_dl_local_project/tests/test_science_e7.py |
| cluster_interval | [188](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L188) | Pointwise percentile CI, whole patients with multiplicity, never seed pooling. | malaria_dl_local_project/tests/test_science_e7.py |
| paired_contrasts | [251](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L251) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ratio | [56](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L56) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_scientific_preflight.py; frontend/tests/cell-review-workspace.test.mjs; … (4 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| checkpoint_policy_config_dict | [67](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L67) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| get_monitor_for_policy | [71](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L71) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_checkpoint_policy.py |
| checkpoint_policy_score | [79](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L79) | Return a scalar validation score whose ordering follows the policy. | malaria_dl_local_project/tests/test_checkpoint_policy.py |
| early_stopping_score | [107](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L107) | Normalize any validation objective to a collapse-aware max score. | malaria_dl_local_project/tests/test_checkpoint_policy.py |
| _json_safe | [135](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L135) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _to_float | [151](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L151) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _to_bool | [170](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L170) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _metric | [180](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L180) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _metric_name_present | [187](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L187) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _epoch | [194](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L194) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _is_collapsed | [199](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L199) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _selected_metrics | [212](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L212) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _selection_result | [232](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L232) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _records_after_collapse_filter | [284](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L284) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _max_by_metric | [310](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L310) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _min_by_metric | [321](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L321) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| select_best_epoch_from_history | [332](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L332) | Selecciona el mejor epoch según una política clínicamente segura.  Convención obligatoria del proyecto:   0 = uninfected   1 = parasitized   raw_model_score = probability_parasitized | malaria_dl_local_project/tests/test_checkpoint_policy.py |
| select_best_epoch_by_monitor | [431](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L431) | Select a validation checkpoint by an explicit metric and comparison mode. | malaria_dl_local_project/tests/test_early_stopping_policy.py |
| checkpoint_policy_summary | [487](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L487) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| write_checkpoint_policy_summary | [518](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L518) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| clinical_validation_logs | [529](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L529) | Clinical VAL metrics added to an epoch's logs; framework-independent. | Sin referencia nominal localizada |
| CheckpointPolicyConfig.__post_init__ | [55](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L55) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## malaria_dl_local_project/src/malaria_dl/training/cli.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| parse_args | [23](../../../malaria_dl_local_project/src/malaria_dl/training/cli.py#L23) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_smear_reset_tool.py; backend_api/tests/test_db_purge_tool.py; malaria_dl_local_project/tests/test_cli01.py; … (24 referencias nominales; ver CSV) |
| main | [380](../../../malaria_dl_local_project/src/malaria_dl/training/cli.py#L380) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |

## malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| ClinicalValidationMetricsCallback.__init__ | [19](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L19) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ClinicalValidationMetricsCallback.on_epoch_end | [40](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L40) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_clinical_validation_callback.py; malaria_dl_local_project/tests/test_campaign_executor_e5.py; … (4 referencias nominales; ver CSV) |
| ClinicalCheckpointCallback.__init__ | [68](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L68) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ClinicalCheckpointCallback.set_phase | [91](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L91) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_registry_e2.py; malaria_dl_local_project/tests/test_early_stopping_policy.py |
| ClinicalCheckpointCallback._record_from_logs | [95](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L95) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ClinicalCheckpointCallback._write_summary | [109](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L109) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ClinicalCheckpointCallback._select_best | [118](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L118) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ClinicalCheckpointCallback.on_epoch_end | [128](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L128) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_clinical_validation_callback.py; malaria_dl_local_project/tests/test_campaign_executor_e5.py; … (4 referencias nominales; ver CSV) |
| ClinicalCheckpointCallback.on_train_end | [147](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L147) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| ClinicalCheckpointCallback.selection_summary | [152](../../../malaria_dl_local_project/src/malaria_dl/training/keras_callbacks.py#L152) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_early_stopping_policy.py; malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |

## malaria_dl_local_project/src/malaria_dl/training/plots.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| _load_history | [23](../../../malaria_dl_local_project/src/malaria_dl/training/plots.py#L23) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _add_fine_tuning_marker | [52](../../../malaria_dl_local_project/src/malaria_dl/training/plots.py#L52) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _plot_metric | [64](../../../malaria_dl_local_project/src/malaria_dl/training/plots.py#L64) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _save_single_plot | [99](../../../malaria_dl_local_project/src/malaria_dl/training/plots.py#L99) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| plot_combined_training_curves | [132](../../../malaria_dl_local_project/src/malaria_dl/training/plots.py#L132) | Generate individual and two-panel plots from a combined history CSV. | malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_training_plots.py |

## malaria_dl_local_project/src/malaria_dl/training/trainer.py

| Función | Línea | Propósito / operación | Pruebas nominales |
|---|---:|---|---|
| resolve_monitor_mode | [54](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L54) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_config.py; malaria_dl_local_project/tests/test_training_selection.py |
| uses_explicit_metric_checkpoint | [60](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L60) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_config.py |
| build_phase_callbacks | [88](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L88) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_registry_e2.py; malaria_dl_local_project/tests/test_early_stopping_policy.py |
| clinical_objective_status | [138](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L138) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_registry_e2.py |
| callback_configuration | [147](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L147) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| find_early_stopping_callback | [154](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L154) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_early_stopping_policy.py |
| early_stopping_phase_summary | [165](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L165) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_early_stopping_policy.py |
| json_safe_float | [202](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L202) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| resolve_training_execution_type | [209](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L209) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_train_integration.py |
| _history_epoch_count | [213](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L213) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| _history_scalar | [223](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L223) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| write_combined_training_history | [238](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L238) | Write a continuous, phase-aware history CSV for one training run. | malaria_dl_local_project/tests/test_training_history_outputs.py; malaria_dl_local_project/tests/test_model_execution_outputs.py |
| _json_safe_value | [376](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L376) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| write_model_execution_summary | [391](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L391) | Persist the machine-readable and academic presentation summaries. | malaria_dl_local_project/tests/test_model_execution_outputs.py; malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| snapshot_execution_artifacts | [512](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L512) | Copy this run's files to an immutable per-execution directory. | malaria_dl_local_project/tests/test_model_execution_outputs.py |
| resolve_artifact_snapshot_id | [547](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L547) | Use the persisted training run UUID when PostgreSQL tracking is active. | malaria_dl_local_project/tests/test_model_execution_outputs.py |
| resolve_threshold_calibration_output_path | [577](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L577) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| snapshot_artifact_path | [600](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L600) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| rewrite_snapshot_json_paths | [607](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L607) | Make copied JSON metadata self-contained without altering CLI inputs. | malaria_dl_local_project/tests/test_model_execution_outputs.py |
| write_checkpoint_selection_report | [652](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L652) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| finalize_checkpoint_test_evaluation | [745](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L745) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| clear_final_test_artifacts | [770](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L770) | Prevent files from an older run from masquerading as current test output. | malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| clear_latest_run_artifacts | [779](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L779) | Clear mutable latest outputs while preserving immutable run snapshots. | Sin referencia nominal localizada |
| stage_latest_run_artifacts | [788](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L788) | Temporarily preserve the previous latest aliases until this run succeeds. | malaria_dl_local_project/tests/test_model_registry_e2.py |
| acquire_training_output_lock | [817](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L817) | Evita que dos trainings del mismo modelo mezclen aliases/checkpoints. | malaria_dl_local_project/tests/test_model_execution_outputs.py; malaria_dl_local_project/tests/test_model_registry_e2.py |
| release_training_output_lock | [840](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L840) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_model_execution_outputs.py |
| discard_latest_artifact_backup | [849](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L849) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |
| restore_latest_artifact_backup | [860](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L860) | Remove partial latest outputs and restore the last successful aliases. | malaria_dl_local_project/tests/test_model_registry_e2.py |
| evaluate_selected_checkpoint_once | [874](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L874) | Run the single final test pass after validation-based model selection. | malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| evaluate_selected_checkpoint_if_enabled | [920](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L920) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py |
| main | [926](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L926) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_campaigns_api_swv22.py; backend_api/tests/test_lineage_children_postgres.py; backend_api/tests/test_scientific_report.py; … (128 referencias nominales; ver CSV) |
| ValidationEarlyStopping.__init__ | [70](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L70) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | backend_api/tests/test_scientific_report.py; backend_api/tests/test_cell_classification_postgres.py; backend_api/tests/test_smear_reset_tool.py; … (62 referencias nominales; ver CSV) |
| ValidationEarlyStopping.on_train_begin | [75](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L75) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_early_stopping_policy.py |
| ValidationEarlyStopping.on_epoch_end | [79](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L79) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_max_epochs_main_smoke.py; malaria_dl_local_project/tests/test_clinical_validation_callback.py; malaria_dl_local_project/tests/test_campaign_executor_e5.py; … (4 referencias nominales; ver CSV) |
| display | [405](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L405) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | malaria_dl_local_project/tests/test_input_contract_e3.py; frontend/tests/cell-review-workspace.test.mjs; frontend/tests/deployments-inline-review.test.mjs; … (4 referencias nominales; ver CSV) |
| rewrite | [616](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py#L616) | Contrato inferible del cuerpo; ver llamadas y retornos, sin afirmar ejecución. | Sin referencia nominal localizada |

## Fichas semánticas de funciones centrales

| Función | Tipo de operación | Entradas | Algoritmo / fórmula | Salida / persistencia | Consumidor / límite |
|---|---|---|---|---|---|
| compute_clinical_metrics | Calcula | y_true,y_scores,threshold | sklearn y cocientes binarios; score float32 | dict clínico; llamador persiste | Callbacks y evaluación; no todas las claves se grafican |
| compile_binary_model | Configura | Keras model,learning_rate,optimizer_config | BCE y métricas Keras | model compilado | TRAIN; no es cálculo final sklearn |
| collect_predictions | Calcula / adapta | modelo,dataset,threshold | inferencia de validación en callback; evento de scores | samples y métricas | Selección/calibración y eventos por época |
| find_threshold_for_target_recall | Calcula | labels,scores,target_recall,min_specificity,beta | grid de scores únicos, filtros y orden lexicográfico | dict threshold y tasas | TRAIN y auto threshold; no escribe solo por llamarlo |
| verify_rows | Valida / calcula | identity,rows | población exacta, reconstruye decisiones, hash filas | verification con métricas; TEST amplía campos | attempt verification; hashes VAL preservados |
| metric_dto | Lee / transforma | row run_clinical_metrics | alias a nueve indicadores y undefined_reason | DTO clínico | ScientificReportService→ClinicalMetrics |
| assessment_metrics | Lee / valida | connection,selection | intento/identity/TRAIN/split/checkpoint/estado | clinical desde verification.metrics | No recalcula métricas faltantes |
| checkpoint_evidence | Valida / transforma | record,run_id | coherencia metadata epoch/phase/ownership | DTO file_availability not_checked | Curvas/arquitectura; no verifica archivo |
| validate_samples | Valida / calcula | samples,t,expected | reaplica >=, unicidad, finitud y matriz | indexed,counts,issues | Consenso, rechaza contradicciones |
| consensus | Calcula | populations,thresholds,filters,pagination | intersección, categorías, acuerdo, overlap,oracle | dict de población+tabla paginada | ConsensusResults; no ensemble |
| KerasRuntime.represent | Extrae | samples | forward de GAP y salida en el mismo grafo | features float32,scores | represent_reserved; no se ejecutó aquí |
| project | Calcula | features,spec,seed | PCA full centrado≤50; UMAP2D sobre features | pca,pca_variance,umap | REPRESENT escribe4arrays; no se volvió a ajustar |
| linear_cka | Calcula | X,Y alineados | centrado y normas Frobenius | float o None | cka_matrix; sin kernelRBF ni archivo |
| representation_evidence | Lee / valida | repo,connection,selection | coincidencia exacta de intento y SHA/bytes/shape | DTO y embeddings cargados | ScientificRepresentations |
| compute_gradcam_artifacts | Calcula | model,image,class,layer,invert,preprocess | gradientes→media→suma→ReLU→normalize→resize | heat,overlay,layer | KerasRuntime.explain; no persiste por sí sola |
| KerasRuntime.explain | Calcula / delega | sample e identity.explanation | GradCAM/LIME/GradientExplainer sobre checkpoint | heat,overlay,result | execute_reserved→save_artifacts |
| OpenCLIPRuntime.explain | Calcula / delega | sample y spec | LIME o expectedgradients por chunks100 | map/overlay/meta | No Grad-CAMViT |
| attribution_overlay | Visualiza / transforma | rgb,heat | abs y normalize;0.6RGB+0.4color | RGB float | LIME/SHAP overlay; signo perdido |
| save_artifacts | Persiste archivos | root,target,heat,overlay | creación exclusiva NPY/PNG,fsync,link yhash | payload path/bytes/SHA/IDs | BD registra después; no se ejecutó |
| normalize_keras | Calcula estructura | runtime records,family | aplano grafo,formas,pesos por reglas | layers,blocks,phases,paramcounts | ArchitectureDetail; sin leer pesos |
| VitStructureService.read | Lee / genera caché | base,input_size | lectura porSHA o proceso de derivación | estructura JSON | Rama no invocada por efectos |
| TrainingTrajectoryService.read | Lee / valida / adapta | TRAIN,datasource | scoresVALporépoca; población constante y IDporpathúnico | matriz y samples | Vistascomplementarias; thresholdTRAIN0.5 |
| cluster_interval | Calcula estadística | rows,spec,paired opcional | bootstrap de pacientes completos,percentiles | IC o razones | Subsistema science; no campo delreporte clínico |
| curveSummary | Calcula resumen | CurveEvidence | conteo fases ygap a checkpoint | KPIs | No clasifica sobreajuste automáticamente |
| consensusFilterParams | Adapta | MRTcolumnfilters | normaliza label/sample/rangos a request | paramsbackend | No filtra solo página |
| ProjectionChart | Representa | run,projection,colorBy | agrupa coords persistidas porclase/outcome | scatter ypin | No ajusta PCA/UMAP ni deriva etiqueta descore redondeado |

Los campos completos de archivo/línea, controles, referencias a pruebas y consumidores textuales permanecen en functions.csv. Para las funciones runtime, describir su cálculo no significa que se ejecutaran durante la auditoría. Las fichas05 y06 contienen fórmulas y ejecuciones verificadas.

TypeScript se inspeccionó con AST de la dependencia local: funciones, métodos del cliente API y callbacks identificados por línea. [Índice AST](evidence/typescript_functions.json). El CSV distingue calcula/lee/adapta/visualiza en las fichas centrales; el índice amplio conserva llamadas y retornos del cuerpo.
