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
    log_classification_report,
    log_confusion_matrix,
    log_environment_packages,
    log_explainability_result,
    log_metric,
    log_prediction,
    start_run,
)


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

    finish_run(run_id, metadata={"completed_by": "scripts/test_db.py"})

    print("Fila desde vw_run_dashboard:")
    with get_connection() as connection:
        row = connection.execute(
            text(
                """
                SELECT *
                FROM vw_run_dashboard
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        ).mappings().one()

    print(dict(row))
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
