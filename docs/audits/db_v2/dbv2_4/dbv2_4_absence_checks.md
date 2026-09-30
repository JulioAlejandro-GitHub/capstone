# DBV2.4 — Absence checks

All 87 non-authorized public tables in BD-v2 hold 0 rows (only technical baseline rows: alembic_version = 1, experiment_execution_gate = 1, both present before DBV2.4). Therefore every one is **empty because baseline created it empty**; rows transferred = 0.

| family | tables_checked | rows |
|---|---|---|
| audit_events | audit_events | 0 |
| experiments / runs | experiments, runs, run_metrics, run_clinical_metrics, training_history, predictions | 0 |
| campaigns | experimental_campaigns, campaign_members, campaign_attempts, campaign_configurations | 0 |
| evaluations / calibration / ensembles | evaluations, run_threshold_calibration | 0 |
| TRAIN / E10 | experiment_execution_events, train_execution_revisions | 0 |
| XAI | xai_artifacts, xai_evaluation_members, xai_evaluation_protocols, xai_evidence, xai_interpretations, xai_method_configurations, xai_quantitative_evaluations, xai_region_attributions, xai_specialist_reviews | 0 |
| publication / deployment | model_versions | 0 |
| clinical workflow / smear | cell_classification_runs, cell_predictions, smear_analysis_summaries | 0 |

- unauthorized transferred rows = 0
- audit_events transferred = 0
- XAI history transferred = 0 (structure present: 9 tables)
- E10 history transferred = 0

Full per-table counts: `verification_after_restart.json` → absence.baseline_empty_tables.
