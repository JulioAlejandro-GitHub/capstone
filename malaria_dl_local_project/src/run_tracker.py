import getpass
import mimetypes
import json
import os
import platform as platform_module
import shlex
import socket
import subprocess
import sys
import traceback
import warnings
from importlib import metadata as importlib_metadata
from pathlib import Path

from sqlalchemy import text

from src.config import LABEL_MAPPING_VERSION, RAW_MODEL_SCORE_MEANING
from src.db import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _json(value, default=None):
    if value is None:
        value = {} if default is None else default
    return json.dumps(value, ensure_ascii=False)


def _warn(message):
    warnings.warn(f"[run_tracker] {message}", RuntimeWarning, stacklevel=2)


def _run_git_command(args):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def _tensorflow_environment():
    try:
        import tensorflow as tf

        gpu_devices = [device.name for device in tf.config.list_physical_devices("GPU")]
        return {
            "tensorflow_version": tf.__version__,
            "keras_version": getattr(tf.keras, "__version__", None),
            "gpu_available": bool(gpu_devices),
            "gpu_devices": gpu_devices,
        }
    except Exception:
        return {
            "tensorflow_version": None,
            "keras_version": None,
            "gpu_available": None,
            "gpu_devices": [],
        }


def collect_runtime_environment():
    tf_env = _tensorflow_environment()
    return {
        "user_name": getpass.getuser(),
        "host_name": socket.gethostname(),
        "working_directory": os.getcwd(),
        "git_commit": _run_git_command(["rev-parse", "HEAD"]),
        "git_branch": _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]),
        "python_version": sys.version,
        "tensorflow_version": tf_env["tensorflow_version"],
        "keras_version": tf_env["keras_version"],
        "platform": platform_module.platform(),
        "machine": platform_module.machine(),
        "processor": platform_module.processor(),
        "gpu_available": tf_env["gpu_available"],
        "gpu_devices": tf_env["gpu_devices"],
    }


def collect_environment_info():
    return collect_runtime_environment()


def get_command_line():
    return " ".join(shlex.quote(part) for part in sys.argv)


def safe_track(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as exc:
        _warn(f"{getattr(function, '__name__', 'tracking')} falló: {exc}")
        return None


def compute_case_type(true_label, predicted_label, positive_label="parasitized"):
    if true_label is None or predicted_label is None:
        return "unknown"

    if true_label == positive_label and predicted_label == positive_label:
        return "true_positive"
    if true_label != positive_label and predicted_label != positive_label:
        return "true_negative"
    if true_label != positive_label and predicted_label == positive_label:
        return "false_positive"
    if true_label == positive_label and predicted_label != positive_label:
        return "false_negative"
    return "unknown"


def _query_one(sql, params=None):
    try:
        with get_connection() as connection:
            row = connection.execute(text(sql), params or {}).first()
            return row
    except Exception as exc:
        _warn(str(exc))
        return None


def _execute_returning_id(sql, params=None):
    try:
        with get_connection() as connection:
            row = connection.execute(text(sql), params or {}).first()
            return str(row[0]) if row else None
    except Exception as exc:
        _warn(str(exc))
        return None


def _execute(sql, params=None):
    try:
        with get_connection() as connection:
            connection.execute(text(sql), params or {})
            return True
    except Exception as exc:
        _warn(str(exc))
        return False


def create_experiment(name, description=None, project_name=None, metadata=None):
    existing = _query_one(
        "SELECT id FROM experiments WHERE name = :name LIMIT 1",
        {"name": name},
    )
    if existing:
        return str(existing[0])

    return _execute_returning_id(
        """
        INSERT INTO experiments (name, description, project_name, metadata)
        VALUES (:name, :description, :project_name, CAST(:metadata AS jsonb))
        RETURNING id
        """,
        {
            "name": name,
            "description": description,
            "project_name": project_name,
            "metadata": _json(metadata),
        },
    )


def get_or_create_dataset(
    name,
    source=None,
    version=None,
    description=None,
    total_images=None,
    num_classes=None,
    class_names=None,
    class_distribution=None,
    license=None,
    url=None,
    local_path=None,
    checksum=None,
    metadata=None,
):
    existing = _query_one(
        """
        SELECT id
        FROM datasets
        WHERE name = :name
          AND COALESCE(version, '') = COALESCE(:version, '')
        LIMIT 1
        """,
        {"name": name, "version": version},
    )
    if existing:
        return str(existing[0])

    return _execute_returning_id(
        """
        INSERT INTO datasets (
            name, source, version, description, total_images, num_classes,
            class_names, class_distribution, license, url, local_path, checksum,
            metadata
        )
        VALUES (
            :name, :source, :version, :description, :total_images, :num_classes,
            :class_names, CAST(:class_distribution AS jsonb), :license, :url,
            :local_path, :checksum, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "name": name,
            "source": source,
            "version": version,
            "description": description,
            "total_images": total_images,
            "num_classes": num_classes,
            "class_names": class_names,
            "class_distribution": _json(class_distribution),
            "license": license,
            "url": url,
            "local_path": local_path,
            "checksum": checksum,
            "metadata": _json(metadata),
        },
    )


def get_or_create_model(
    name,
    model_type,
    framework=None,
    architecture=None,
    description=None,
    input_shape=None,
    output_shape=None,
    num_parameters=None,
    pretrained=False,
    pretrained_source=None,
    metadata=None,
):
    existing = _query_one(
        "SELECT id FROM models WHERE name = :name LIMIT 1",
        {"name": name},
    )
    if existing:
        return str(existing[0])

    return _execute_returning_id(
        """
        INSERT INTO models (
            name, model_type, framework, architecture, description,
            input_shape, output_shape, num_parameters, pretrained,
            pretrained_source, metadata
        )
        VALUES (
            :name, :model_type, :framework, :architecture, :description,
            :input_shape, :output_shape, :num_parameters, :pretrained,
            :pretrained_source, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "name": name,
            "model_type": model_type,
            "framework": framework,
            "architecture": architecture,
            "description": description,
            "input_shape": input_shape,
            "output_shape": output_shape,
            "num_parameters": num_parameters,
            "pretrained": pretrained,
            "pretrained_source": pretrained_source,
            "metadata": _json(metadata),
        },
    )


def start_run(
    experiment_id=None,
    model_id=None,
    dataset_id=None,
    run_name=None,
    run_type="training",
    command=None,
    script_name=None,
    parameters=None,
    random_seed=None,
    notes=None,
    metadata=None,
):
    env = collect_runtime_environment()
    return _execute_returning_id(
        """
        INSERT INTO runs (
            experiment_id, model_id, dataset_id, run_name, run_type, status,
            command, script_name, started_at, user_name, host_name,
            working_directory, git_commit, git_branch, python_version,
            tensorflow_version, keras_version, platform, machine, processor,
            gpu_available, gpu_devices, random_seed, parameters, notes, metadata
        )
        VALUES (
            :experiment_id, :model_id, :dataset_id, :run_name, :run_type, 'started',
            :command, :script_name, NOW(), :user_name, :host_name,
            :working_directory, :git_commit, :git_branch, :python_version,
            :tensorflow_version, :keras_version, :platform, :machine, :processor,
            :gpu_available, CAST(:gpu_devices AS jsonb), :random_seed,
            CAST(:parameters AS jsonb), :notes, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "dataset_id": dataset_id,
            "run_name": run_name,
            "run_type": run_type,
            "command": command,
            "script_name": script_name,
            "random_seed": random_seed,
            "notes": notes,
            "parameters": _json(parameters),
            "metadata": _json(metadata),
            "gpu_devices": _json(env["gpu_devices"], default=[]),
            **{key: value for key, value in env.items() if key != "gpu_devices"},
        },
    )


def finish_run(run_id, metrics=None, metadata=None):
    if not run_id:
        _warn("finish_run omitido porque run_id es None.")
        return False

    success = _execute(
        """
        UPDATE runs
        SET status = 'completed',
            finished_at = NOW(),
            duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
            updated_at = NOW(),
            metadata = metadata || CAST(:metadata AS jsonb)
        WHERE id = :run_id
        """,
        {"run_id": run_id, "metadata": _json(metadata)},
    )

    if metrics:
        log_metrics_bulk(run_id, metrics)
    return success


def fail_run(run_id, error=None, script_name=None, metadata=None):
    if not run_id:
        _warn("fail_run omitido porque run_id es None.")
        return False

    success = _execute(
        """
        UPDATE runs
        SET status = 'failed',
            finished_at = NOW(),
            duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
            updated_at = NOW(),
            metadata = metadata || CAST(:metadata AS jsonb)
        WHERE id = :run_id
        """,
        {"run_id": run_id, "metadata": _json(metadata)},
    )
    if error is not None:
        log_error(
            run_id=run_id,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            script_name=script_name,
        )
    return success


def log_metric(
    run_id,
    metric_name,
    metric_value,
    metric_unit=None,
    split_name=None,
    class_name=None,
    step=None,
    epoch=None,
    metadata=None,
):
    if not run_id:
        _warn("log_metric omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO run_metrics (
            run_id, metric_name, metric_value, metric_unit, split_name,
            class_name, step, epoch, metadata
        )
        VALUES (
            :run_id, :metric_name, :metric_value, :metric_unit, :split_name,
            :class_name, :step, :epoch, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "split_name": split_name,
            "class_name": class_name,
            "step": step,
            "epoch": epoch,
            "metadata": _json(metadata),
        },
    )


def log_metrics_bulk(run_id, metrics, split_name=None, metadata=None):
    if isinstance(metrics, dict):
        metric_items = metrics.items()
    else:
        metric_items = metrics

    ids = []
    for item in metric_items:
        if isinstance(item, dict):
            metric_id = log_metric(run_id, metadata=metadata, **item)
        else:
            name, value = item
            metric_id = log_metric(
                run_id,
                metric_name=name,
                metric_value=value,
                split_name=split_name,
                metadata=metadata,
            )
        ids.append(metric_id)
    return ids


def log_training_history(run_id, epoch, metadata=None, **values):
    if not run_id:
        _warn("log_training_history omitido porque run_id es None.")
        return None

    allowed = {
        "loss",
        "accuracy",
        "precision_value",
        "recall_value",
        "auc",
        "val_loss",
        "val_accuracy",
        "val_precision",
        "val_recall",
        "val_auc",
        "learning_rate",
    }
    params = {key: values.get(key) for key in allowed}
    params.update({"run_id": run_id, "epoch": epoch, "metadata": _json(metadata)})

    return _execute_returning_id(
        """
        INSERT INTO training_history (
            run_id, epoch, loss, accuracy, precision_value, recall_value, auc,
            val_loss, val_accuracy, val_precision, val_recall, val_auc,
            learning_rate, metadata
        )
        VALUES (
            :run_id, :epoch, :loss, :accuracy, :precision_value, :recall_value,
            :auc, :val_loss, :val_accuracy, :val_precision, :val_recall,
            :val_auc, :learning_rate, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        params,
    )


def log_confusion_matrix(
    run_id,
    matrix,
    split_name=None,
    labels=None,
    true_positive=None,
    true_negative=None,
    false_positive=None,
    false_negative=None,
    metadata=None,
):
    if not run_id:
        _warn("log_confusion_matrix omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO confusion_matrices (
            run_id, split_name, labels, matrix, true_positive, true_negative,
            false_positive, false_negative, metadata
        )
        VALUES (
            :run_id, :split_name, :labels, CAST(:matrix AS jsonb),
            :true_positive, :true_negative, :false_positive, :false_negative,
            CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "split_name": split_name,
            "labels": labels,
            "matrix": _json(matrix),
            "true_positive": true_positive,
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "metadata": _json(metadata),
        },
    )


def log_classification_report(
    run_id,
    split_name,
    class_name,
    precision_value,
    recall_value,
    f1_score,
    support,
    metadata=None,
):
    if not run_id:
        _warn("log_classification_report omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO classification_reports (
            run_id, split_name, class_name, precision_value, recall_value,
            f1_score, support, metadata
        )
        VALUES (
            :run_id, :split_name, :class_name, :precision_value, :recall_value,
            :f1_score, :support, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "split_name": split_name,
            "class_name": class_name,
            "precision_value": precision_value,
            "recall_value": recall_value,
            "f1_score": f1_score,
            "support": support,
            "metadata": _json(metadata),
        },
    )


def log_prediction(
    run_id,
    dataset_id=None,
    image_id=None,
    image_path=None,
    true_label=None,
    predicted_label=None,
    score=None,
    score_positive_label=None,
    threshold=None,
    is_correct=None,
    case_type="unknown",
    metadata=None,
):
    if not run_id:
        _warn("log_prediction omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO predictions (
            run_id, dataset_id, image_id, image_path, true_label, predicted_label,
            score, score_positive_label, threshold, is_correct, case_type, metadata
        )
        VALUES (
            :run_id, :dataset_id, :image_id, :image_path, :true_label,
            :predicted_label, :score, :score_positive_label, :threshold,
            :is_correct, :case_type, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "image_id": image_id,
            "image_path": image_path,
            "true_label": true_label,
            "predicted_label": predicted_label,
            "score": score,
            "score_positive_label": score_positive_label,
            "threshold": threshold,
            "is_correct": is_correct,
            "case_type": case_type,
            "metadata": _json(metadata),
        },
    )


def log_artifact(
    run_id,
    artifact_type,
    path,
    name=None,
    mime_type=None,
    file_size_bytes=None,
    checksum=None,
    metadata=None,
):
    if not run_id:
        _warn("log_artifact omitido porque run_id es None.")
        return None

    if file_size_bytes is None and path and Path(path).exists():
        file_size_bytes = Path(path).stat().st_size

    return _execute_returning_id(
        """
        INSERT INTO artifacts (
            run_id, artifact_type, name, path, mime_type, file_size_bytes,
            checksum, metadata
        )
        VALUES (
            :run_id, :artifact_type, :name, :path, :mime_type, :file_size_bytes,
            :checksum, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "artifact_type": artifact_type,
            "name": name,
            "path": path,
            "mime_type": mime_type,
            "file_size_bytes": file_size_bytes,
            "checksum": checksum,
            "metadata": _json(metadata),
        },
    )


def log_artifacts_from_directory(run_id, directory, artifact_type=None):
    if not run_id:
        _warn("log_artifacts_from_directory omitido porque run_id es None.")
        return []

    directory = Path(directory)
    if not directory.exists():
        _warn(f"No existe la carpeta de artefactos: {directory}")
        return []

    artifact_ids = []
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        inferred_type = artifact_type or infer_artifact_type(path)
        artifact_ids.append(
            log_artifact(
                run_id=run_id,
                artifact_type=inferred_type,
                name=path.name,
                path=str(path),
                mime_type=mimetypes.guess_type(path)[0],
            )
        )
    return artifact_ids


def log_run_io_record(
    run_id,
    script_name,
    command=None,
    input_parameters=None,
    output_results=None,
    output_artifacts=None,
    dataset_metadata=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
    raw_model_score_meaning=RAW_MODEL_SCORE_MEANING,
    metadata=None,
):
    if not run_id:
        _warn("log_run_io_record omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO run_io_records (
            run_id, script_name, command, input_parameters, output_results,
            output_artifacts, dataset_metadata, label_mapping_version,
            raw_model_score_meaning, metadata
        )
        VALUES (
            :run_id, :script_name, :command, CAST(:input_parameters AS jsonb),
            CAST(:output_results AS jsonb), CAST(:output_artifacts AS jsonb),
            CAST(:dataset_metadata AS jsonb), :label_mapping_version,
            :raw_model_score_meaning, CAST(:metadata AS jsonb)
        )
        RETURNING run_io_id
        """,
        {
            "run_id": run_id,
            "script_name": script_name,
            "command": command,
            "input_parameters": _json(input_parameters),
            "output_results": _json(output_results),
            "output_artifacts": _json(output_artifacts, default=[]),
            "dataset_metadata": _json(dataset_metadata),
            "label_mapping_version": label_mapping_version,
            "raw_model_score_meaning": raw_model_score_meaning,
            "metadata": _json(metadata),
        },
    )


def log_run_dataset_images(run_id, image_rows):
    if not run_id:
        _warn("log_run_dataset_images omitido porque run_id es None.")
        return {"total": 0, "inserted_or_updated": 0}
    if not image_rows:
        return {"total": 0, "inserted_or_updated": 0}

    sql = text(
        """
        INSERT INTO run_dataset_images (
            run_id, image_id, split_name, usage_context, class_index,
            class_name, relative_path, filename, batch_index, sample_index,
            used_for_training, used_for_validation, used_for_test, metadata
        )
        VALUES (
            :run_id, :image_id, :split_name, :usage_context, :class_index,
            :class_name, :relative_path, :filename, :batch_index, :sample_index,
            :used_for_training, :used_for_validation, :used_for_test,
            CAST(:metadata AS jsonb)
        )
        ON CONFLICT (run_id, image_id, usage_context)
        DO UPDATE SET
            split_name = EXCLUDED.split_name,
            class_index = EXCLUDED.class_index,
            class_name = EXCLUDED.class_name,
            relative_path = EXCLUDED.relative_path,
            filename = EXCLUDED.filename,
            batch_index = EXCLUDED.batch_index,
            sample_index = EXCLUDED.sample_index,
            used_for_training = EXCLUDED.used_for_training,
            used_for_validation = EXCLUDED.used_for_validation,
            used_for_test = EXCLUDED.used_for_test,
            metadata = run_dataset_images.metadata || EXCLUDED.metadata
        RETURNING run_dataset_image_id
        """
    )
    try:
        inserted_or_updated = 0
        with get_connection() as connection:
            for row in image_rows:
                params = {
                    "run_id": run_id,
                    "image_id": row["image_id"],
                    "split_name": row["split_name"],
                    "usage_context": row["usage_context"],
                    "class_index": row["class_index"],
                    "class_name": row["class_name"],
                    "relative_path": row["relative_path"],
                    "filename": row["filename"],
                    "batch_index": row.get("batch_index"),
                    "sample_index": row.get("sample_index"),
                    "used_for_training": bool(row.get("used_for_training", False)),
                    "used_for_validation": bool(row.get("used_for_validation", False)),
                    "used_for_test": bool(row.get("used_for_test", False)),
                    "metadata": _json(row.get("metadata")),
                }
                result = connection.execute(sql, params).first()
                if result:
                    inserted_or_updated += 1
        return {
            "total": len(image_rows),
            "inserted_or_updated": inserted_or_updated,
        }
    except Exception as exc:
        _warn(str(exc))
        return {"total": len(image_rows), "inserted_or_updated": 0}


def infer_artifact_type(path):
    path = Path(path)
    name = path.name.lower()
    suffix = path.suffix.lower()

    if name == "best_model.keras":
        return "model_checkpoint"
    if name == "final_model.keras":
        return "final_model"
    if suffix == ".keras":
        return "model_checkpoint"
    if suffix == ".joblib":
        return "final_model"
    if name.endswith("_metrics.json"):
        return "metrics_json"
    if "confusion_matrix" in name:
        return "classification_report_csv" if suffix == ".csv" else "confusion_matrix_png"
    if "predictions" in name and suffix == ".csv":
        return "classification_report_csv"
    if suffix == ".png":
        return "other"
    if suffix in {".csv", ".json"}:
        return "other"
    return "other"


def log_model_version(
    model_id,
    version_name=None,
    checkpoint_path=None,
    final_model_path=None,
    best_model_path=None,
    training_run_id=None,
    metadata=None,
):
    if not model_id:
        _warn("log_model_version omitido porque model_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO model_versions (
            model_id, version_name, checkpoint_path, final_model_path,
            best_model_path, training_run_id, metadata
        )
        VALUES (
            :model_id, :version_name, :checkpoint_path, :final_model_path,
            :best_model_path, :training_run_id, CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "model_id": model_id,
            "version_name": version_name,
            "checkpoint_path": checkpoint_path,
            "final_model_path": final_model_path,
            "best_model_path": best_model_path,
            "training_run_id": training_run_id,
            "metadata": _json(metadata),
        },
    )


def log_explainability_result(
    run_id,
    method,
    prediction_id=None,
    image_path=None,
    output_path=None,
    true_label=None,
    predicted_label=None,
    score=None,
    case_type=None,
    last_conv_layer=None,
    explanation_parameters=None,
    success=True,
    error_message=None,
    metadata=None,
):
    if not run_id:
        _warn("log_explainability_result omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO explainability_results (
            run_id, prediction_id, method, image_path, output_path, true_label,
            predicted_label, score, case_type, last_conv_layer,
            explanation_parameters, success, error_message, metadata
        )
        VALUES (
            :run_id, :prediction_id, :method, :image_path, :output_path,
            :true_label, :predicted_label, :score, :case_type, :last_conv_layer,
            CAST(:explanation_parameters AS jsonb), :success, :error_message,
            CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "prediction_id": prediction_id,
            "method": method,
            "image_path": image_path,
            "output_path": output_path,
            "true_label": true_label,
            "predicted_label": predicted_label,
            "score": score,
            "case_type": case_type,
            "last_conv_layer": last_conv_layer,
            "explanation_parameters": _json(explanation_parameters),
            "success": success,
            "error_message": error_message,
            "metadata": _json(metadata),
        },
    )


def log_error(
    run_id,
    error_type=None,
    error_message=None,
    stack_trace=None,
    script_name=None,
    metadata=None,
):
    if not run_id:
        _warn("log_error omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO errors (
            run_id, error_type, error_message, stack_trace, script_name, metadata
        )
        VALUES (
            :run_id, :error_type, :error_message, :stack_trace, :script_name,
            CAST(:metadata AS jsonb)
        )
        RETURNING id
        """,
        {
            "run_id": run_id,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "script_name": script_name,
            "metadata": _json(metadata),
        },
    )


def log_environment_packages(run_id, packages=None):
    if not run_id:
        _warn("log_environment_packages omitido porque run_id es None.")
        return []

    if packages is None:
        packages = sorted(
            (dist.metadata["Name"], dist.version)
            for dist in importlib_metadata.distributions()
            if dist.metadata.get("Name")
        )

    inserted = []
    for package in packages:
        if isinstance(package, dict):
            package_name = package.get("package_name") or package.get("name")
            package_version = package.get("package_version") or package.get("version")
        else:
            package_name, package_version = package

        inserted.append(
            _execute_returning_id(
                """
                INSERT INTO environment_packages (
                    run_id, package_name, package_version
                )
                VALUES (:run_id, :package_name, :package_version)
                RETURNING id
                """,
                {
                    "run_id": run_id,
                    "package_name": package_name,
                    "package_version": package_version,
                },
            )
        )

    return inserted


def log_execution_log(run_id, log_level, message, source=None, metadata=None):
    if not run_id:
        _warn("log_execution_log omitido porque run_id es None.")
        return None

    return _execute_returning_id(
        """
        INSERT INTO execution_logs (run_id, log_level, message, source, metadata)
        VALUES (:run_id, :log_level, :message, :source, CAST(:metadata AS jsonb))
        RETURNING id
        """,
        {
            "run_id": run_id,
            "log_level": log_level,
            "message": message,
            "source": source,
            "metadata": _json(metadata),
        },
    )
