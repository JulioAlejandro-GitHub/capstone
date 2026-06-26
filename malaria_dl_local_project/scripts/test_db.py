import sys
from pathlib import Path

from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection, test_connection
from src.run_tracker import (
    create_experiment,
    finish_run,
    get_or_create_dataset,
    get_or_create_model,
    log_artifact,
    log_checkpoint_policy,
    log_classification_report,
    log_clinical_metrics,
    log_confusion_matrix,
    log_environment_packages,
    log_explainability_result,
    log_image_predictions,
    log_metric,
    log_prediction,
    log_run_io_record,
    log_threshold_calibration,
    start_run,
)


def fetch_required_mapping(connection, sql, params, description):
    row = connection.execute(text(sql), params).mappings().first()
    if row is None:
        raise RuntimeError(f"No se encontró fila requerida: {description}")
    return row


def main():
    print("Probando conexión a PostgreSQL local...")
    info = test_connection()
    print(f"Conexión OK: {info['database_name']} ({info['user_name']})")

    experiment_id = create_experiment(
        name="DB Smoke Test Experiment",
        description="Experimento de prueba para validar tracking PostgreSQL.",
        project_name="malaria_dl_local_project",
        metadata={"source": "scripts/test_db.py"},
    )
    print(f"experiment_id={experiment_id}")

    dataset_id = get_or_create_dataset(
        name="DB Smoke Test Dataset",
        source="local smoke test",
        version="v1",
        description="Dataset sintético mínimo para validar inserciones.",
        total_images=2,
        num_classes=2,
        class_names=["parasitized", "uninfected"],
        class_distribution={"parasitized": 1, "uninfected": 1},
        metadata={"source": "scripts/test_db.py"},
    )
    print(f"dataset_id={dataset_id}")

    model_id = get_or_create_model(
        name="db_smoke_test_model",
        model_type="test_model",
        framework="pytest/manual",
        architecture="dummy",
        description="Modelo ficticio para prueba de tracking.",
        input_shape="(200, 200, 3)",
        output_shape="(1)",
        metadata={"source": "scripts/test_db.py"},
    )
    print(f"model_id={model_id}")

    run_id = start_run(
        experiment_id=experiment_id,
        model_id=model_id,
        dataset_id=dataset_id,
        run_name="db_smoke_test_run",
        run_type="evaluation",
        command="python scripts/test_db.py",
        script_name="scripts/test_db.py",
        parameters={"threshold": 0.5, "num_samples": 2},
        random_seed=42,
        metadata={"source": "scripts/test_db.py"},
    )
    print(f"run_id={run_id}")

    log_metric(run_id, "accuracy", 0.95, split_name="test")
    log_metric(run_id, "precision", 0.94, split_name="test")
    log_metric(run_id, "recall", 0.96, split_name="test")
    log_metric(run_id, "f1_score", 0.95, split_name="test")
    log_metric(run_id, "auc", 0.98, split_name="test")

    log_confusion_matrix(
        run_id,
        split_name="test",
        labels=["parasitized", "uninfected"],
        matrix=[[1, 0], [0, 1]],
        true_positive=1,
        true_negative=1,
        false_positive=0,
        false_negative=0,
    )

    log_classification_report(
        run_id,
        split_name="test",
        class_name="parasitized",
        precision_value=1.0,
        recall_value=1.0,
        f1_score=1.0,
        support=1,
    )
    log_classification_report(
        run_id,
        split_name="test",
        class_name="uninfected",
        precision_value=1.0,
        recall_value=1.0,
        f1_score=1.0,
        support=1,
    )

    prediction_id = log_prediction(
        run_id,
        dataset_id=dataset_id,
        image_id="smoke-0001",
        image_path="data/smoke/0001.png",
        true_label="parasitized",
        predicted_label="parasitized",
        score=0.93,
        score_positive_label=0.93,
        threshold=0.5,
        is_correct=True,
        case_type="true_positive",
    )

    log_artifact(
        run_id,
        artifact_type="metrics_json",
        name="smoke_metrics.json",
        path="outputs/smoke/metrics.json",
        mime_type="application/json",
    )

    log_explainability_result(
        run_id,
        prediction_id=prediction_id,
        method="gradcam",
        image_path="data/smoke/0001.png",
        output_path="outputs/explainability/gradcam/smoke.png",
        true_label="parasitized",
        predicted_label="parasitized",
        score=0.93,
        case_type="true_positive",
        last_conv_layer="block5_conv3",
        explanation_parameters={"img_size": 200},
        success=True,
    )

    log_environment_packages(
        run_id,
        packages=[
            {"package_name": "tensorflow", "package_version": "2.17.1"},
            {"package_name": "SQLAlchemy", "package_version": "2.x"},
            {"package_name": "psycopg", "package_version": "3.x"},
        ],
    )

    clinical_metrics = {
        "accuracy": 1.0,
        "precision_parasitized": 1.0,
        "recall_parasitized": 1.0,
        "sensitivity_parasitized": 1.0,
        "specificity": 1.0,
        "f1_parasitized": 1.0,
        "f2_parasitized": 1.0,
        "roc_auc_parasitized": 1.0,
        "pr_auc_parasitized": 1.0,
        "balanced_accuracy": 1.0,
        "confusion_matrix": [[1, 0], [0, 1]],
        "classification_report_dict": {
            "uninfected": {"precision": 1.0, "recall": 1.0, "f1-score": 1.0},
            "parasitized": {"precision": 1.0, "recall": 1.0, "f1-score": 1.0},
        },
        "prediction_collapse": {"collapsed": False},
        "n_pred_uninfected": 1,
        "n_pred_parasitized": 1,
        "percent_pred_uninfected": 50.0,
        "percent_pred_parasitized": 50.0,
        "threshold_used": 0.42,
        "threshold_source": "validation_calibration",
        "label_mapping_version": "clinical_v1_parasitized_positive",
        "raw_model_score_meaning": "probability_parasitized",
    }
    log_clinical_metrics(
        run_id,
        clinical_metrics,
        split_name="test",
        model_id=model_id,
        model_name="db_smoke_test_model",
        threshold_used=0.42,
        threshold_source="validation_calibration",
    )

    log_checkpoint_policy(
        run_id,
        {
            "checkpoint_policy": "max_recall_with_specificity_floor",
            "checkpoint_policy_config": {"min_recall": 0.95},
            "selected_epoch": 1,
            "policy_satisfied": True,
            "selected_metric": "val_f2_parasitized",
            "selected_metric_value": 0.99,
            "val_recall_parasitized": 1.0,
            "val_f2_parasitized": 1.0,
            "val_specificity": 1.0,
            "val_auc": 1.0,
            "val_pr_auc_parasitized": 1.0,
            "val_balanced_accuracy": 1.0,
            "prediction_collapse_detected": False,
            "all_epochs_collapsed": False,
            "checkpoint_path": "outputs/smoke/best_model.keras",
            "checkpoint_policy_summary_path": "outputs/smoke/checkpoint_policy_summary.json",
            "model_metadata_path": "outputs/smoke/model_metadata.json",
        },
        model_name="db_smoke_test_model",
    )

    log_threshold_calibration(
        run_id,
        {
            "threshold_policy": "target_recall",
            "threshold_source": "validation_calibration",
            "threshold_selected": 0.42,
            "default_threshold": 0.5,
            "target_recall": 0.95,
            "target_recall_satisfied": True,
            "min_specificity": 0.5,
            "selected_metrics": {
                "recall_parasitized": 1.0,
                "specificity": 1.0,
                "precision_parasitized": 1.0,
                "f1_parasitized": 1.0,
                "f2_parasitized": 1.0,
                "balanced_accuracy": 1.0,
                "pr_auc_parasitized": 1.0,
                "roc_auc_parasitized": 1.0,
            },
            "default_threshold_metrics": {"recall_parasitized": 1.0},
            "candidate_count": 101,
            "calibration_split": "val",
            "threshold_calibration_path": "outputs/smoke/threshold_calibration.json",
            "model_metadata_path": "outputs/smoke/model_metadata.json",
        },
        model_name="db_smoke_test_model",
    )

    log_image_predictions(
        run_id,
        [
            {
                "image_id": None,
                "split_name": "test",
                "usage_context": "evaluation",
                "filename": "0001.png",
                "relative_path": "data/smoke/0001.png",
                "true_label": 1,
                "true_label_name": "parasitized",
                "predicted_label": 1,
                "predicted_label_name": "parasitized",
                "probability_parasitized": 0.93,
                "probability_uninfected": 0.07,
                "raw_model_score": 0.93,
                "threshold_used": 0.42,
                "threshold_source": "validation_calibration",
                "is_correct": True,
                "case_type": "true_positive",
                "metadata": {"source": "scripts/test_db.py"},
            }
        ],
    )

    log_run_io_record(
        run_id,
        script_name="scripts/test_db.py",
        run_type="evaluation",
        model_name="db_smoke_test_model",
        command="python scripts/test_db.py",
        input_parameters={"threshold": 0.42, "num_samples": 2},
        output_results={"accuracy": 1.0, "recall_parasitized": 1.0},
        output_artifacts=[{"path": "outputs/smoke/metrics.json", "exists": False}],
        dataset_metadata={"source": "synthetic_smoke_test"},
        model_metadata={"architecture": "dummy"},
        clinical_metadata={
            "positive_label": "parasitized",
            "probability_meaning": "probability_parasitized",
            "threshold_source": "validation_calibration",
        },
        metadata={"source": "scripts/test_db.py"},
    )

    finish_run(run_id, metadata={"completed_by": "scripts/test_db.py"})

    print("Filas desde vistas de tracking:")
    with get_connection() as connection:
        dashboard_row = fetch_required_mapping(
            connection,
            """
            SELECT *
            FROM vw_run_dashboard
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
            "vw_run_dashboard",
        )
        clinical_row = fetch_required_mapping(
            connection,
            """
            SELECT *
            FROM vw_clinical_run_summary
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
            "vw_clinical_run_summary",
        )
        checkpoint_row = fetch_required_mapping(
            connection,
            """
            SELECT *
            FROM vw_checkpoint_policy_summary
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
            "vw_checkpoint_policy_summary",
        )
        threshold_row = fetch_required_mapping(
            connection,
            """
            SELECT *
            FROM vw_threshold_calibration_summary
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
            "vw_threshold_calibration_summary",
        )
        artifacts_row = fetch_required_mapping(
            connection,
            """
            SELECT *
            FROM vw_run_artifacts_summary
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
            "vw_run_artifacts_summary",
        )
        image_prediction_row = fetch_required_mapping(
            connection,
            """
            SELECT *
            FROM vw_run_image_predictions_summary
            WHERE run_id = :run_id
            """,
            {"run_id": run_id},
            "vw_run_image_predictions_summary",
        )

    print(dict(dashboard_row))
    print(
        {
            "clinical_model": clinical_row["model_name"],
            "threshold_used": clinical_row["threshold_used"],
            "checkpoint_policy": checkpoint_row["checkpoint_policy"],
            "threshold_selected": threshold_row["threshold_selected"],
            "artifact_type": artifacts_row["artifact_type"],
            "prediction_case_type": image_prediction_row["case_type"],
        }
    )
    print("Prueba de base de datos completada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Error probando PostgreSQL local.")
        print(str(exc))
        print(
            "Si la base no existe, créala con: "
            "createdb -h localhost -p 5432 -U postgres malaria_experiments"
        )
        raise SystemExit(1) from exc
