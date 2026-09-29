"""Reviewed E10 table policy and filesystem boundaries (RESET.3 / STORAGE.CLEAN.1)."""
from pathlib import Path

PROTECTED_TABLES = (
    'roles', 'users', 'user_roles', 'datasets', 'dataset_versions',
    'dataset_version_sources', 'clinical_identities', 'dataset_source_records',
    'identity_evidence', 'dataset_materializations', 'dataset_split_assignments',
    'dataset_split_images', 'dataset_split_statistics', 'dataset_split_validation_checks',
    'dataset_materialization_activations', 'dataset_splits', 'models',
)
TECHNICAL_TABLES = ('alembic_version', 'schema_migrations', 'experiment_execution_gate')
HISTORY_TABLES = ('artifacts', 'assessment_artifacts', 'assessment_attempts', 'assessment_campaign_consumers', 'assessment_final_locks', 'assessment_identities', 'assessment_results', 'audit_events', 'blood_samples', 'campaign_attempts', 'campaign_configurations', 'campaign_controlled_requests', 'campaign_execution_events', 'campaign_members', 'campaign_technical_revisions', 'cell_classification_events', 'cell_classification_inputs', 'cell_classification_reviews', 'cell_classification_runs', 'cell_crops', 'cell_detection_events', 'cell_detection_runs', 'cell_detections', 'cell_explanations', 'cell_predictions', 'classification_reports', 'confusion_matrices', 'deployed_model_versions', 'environment_packages', 'errors', 'execution_logs', 'experiment_execution_events', 'experimental_campaigns', 'experiments', 'explainability_results', 'image_analysis_jobs', 'image_connected_components', 'image_ingestion_batches', 'image_quality_assessments', 'local_execution_jobs', 'microscopy_analysis_events', 'microscopy_analysis_run_images', 'microscopy_analysis_runs', 'microscopy_images', 'model_governance_backfill_audit', 'model_versions', 'predictions', 'quality_assessment_queue_items', 'quality_gate_decisions', 'research_subjects', 'run_checkpoint_policy', 'run_clinical_metrics', 'run_dataset_images', 'run_image_predictions', 'run_io_records', 'run_lineage', 'run_metrics', 'run_model_deployments', 'run_threshold_calibration', 'runs', 'scientific_cases', 'scientific_reviews', 'scientific_validation_annotation_events', 'scientific_validation_annotations', 'scientific_validation_classification_runs', 'scientific_validation_detection_runs', 'scientific_validation_images', 'scientific_validation_sessions', 'smear_analysis_summaries', 'smear_slides', 'stage2_model_publication_events', 'stage2_model_publications', 'synthetic_data_runs', 'train_execution_records', 'train_execution_revisions', 'train_execution_sessions', 'training_history')
EXPECTED_TABLES = frozenset(PROTECTED_TABLES + TECHNICAL_TABLES + HISTORY_TABLES)
PROTECTED_PATHS = (
    'malaria_dl_local_project/data', 'malaria_dataset_split_project',
    'malaria_dl_local_project/configs', 'malaria_dl_local_project/src',
    'alembic', 'backend_api', 'frontend', 'data', 'backups', '.git',
    'scripts', 'docs', 'var/maintenance',
)
MARKERS = frozenset(('.gitkeep', '.DS_Store', '.training.lock'))
# Producer contracts: trainer.RESERVED_ARTIFACT_BASENAMES plus registered outputs.
GENERATED_NAMES = frozenset((
    'best_model.keras','final_model.keras','model.keras','training_history.csv',
    'combined_training_history.csv','training_base_log.csv','training_log.csv',
    'fine_tuning_log.csv','combined_accuracy.png','combined_loss.png',
    'combined_training_curves.png','checkpoint_selection.json',
    'checkpoint_policy_summary.json','model_metadata.json','model_execution_summary.json',
    'model_execution_summary.md','test_metrics.json','test_predictions.csv',
    'test_confusion_matrix.csv','classification_report.json','threshold_calibration.json',
    'best_model_predictions.csv','best_model_confusion_matrix.csv','best_model_metrics.json',
))
RELEASE_NAMES = frozenset(('model.keras','model.h5','model.hdf5','signature.json','signatures.json',
                         'class_mapping.json','threshold.json','checksums.sha256','manifest.json',
                         'preprocessing.json','evaluation_summary.json','explainability_summary.json','model_card.md'))

def protected(path, project):
    path = Path(path).resolve()
    return any(path.is_relative_to(Path(project).resolve() / p) for p in PROTECTED_PATHS)
