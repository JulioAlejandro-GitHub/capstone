import os
import platform
import sys
from pathlib import Path

import numpy as np

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_METADATA,
    LABEL_MAPPING_VERSION,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
    label_mapping_metadata,
)
from src.decision import probability_by_class_from_scalar_score


EXPERIMENT_NAME = "Capstone Malaria Classification"
EXPERIMENT_METADATA = {
    "project": "Capstone MIA 2026",
    "domain": "medical computer vision",
    "task": "malaria cell classification",
    "tracking_version": "1.0",
    "label_mapping_version": LABEL_MAPPING_VERSION,
    "label_mapping": LABEL_MAPPING_METADATA,
    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
}

DATASET_NAME = "NIH/NLM Malaria Cell Images"
DATASET_VERSION = "tfds-malaria-clinical-v1"
DATASET_CLASS_NAMES = CLASS_NAMES
DATASET_CLASS_DISTRIBUTION = {"parasitized": 13779, "uninfected": 13779}
_REGISTERED_PHYSICAL_SPLITS = set()


def args_to_parameters(args, extra=None):
    parameters = vars(args).copy()
    if extra:
        parameters.update(extra)
    return parameters


def json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value


def artifact_record(path, artifact_type=None, metadata=None):
    path = Path(path)
    try:
        from src.run_tracker import infer_artifact_type

        inferred_type = artifact_type or infer_artifact_type(path)
    except Exception:
        inferred_type = artifact_type or "other"
    return {
        "artifact_type": inferred_type,
        "path": str(path),
        "exists": path.exists(),
        "file_size_bytes": path.stat().st_size if path.exists() else None,
        "metadata": metadata or {},
    }


def output_artifacts_from_directory(output_dir, artifact_type=None):
    if output_dir is None:
        return []
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return [artifact_record(output_dir, artifact_type=artifact_type)]
    return [
        artifact_record(path, artifact_type=artifact_type)
        for path in sorted(item for item in output_dir.rglob("*") if item.is_file())
    ]


def runtime_io_metadata():
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "working_directory": os.getcwd(),
    }


def model_name_from_train_arg(model_name):
    if model_name == "vgg16":
        return "vgg16_transfer_learning"
    return model_name


def model_name_from_checkpoint(checkpoint):
    checkpoint = Path(checkpoint)
    parts = {part.lower() for part in checkpoint.parts}
    if "vgg16" in parts:
        return "vgg16_transfer_learning"
    if "custom_cnn" in parts:
        return "custom_cnn"
    if "ensemble" in parts:
        return "ensemble"
    if "cnn_features_svm" in parts:
        return "cnn_features_svm"
    if "tta" in parts:
        return "tta"
    return checkpoint.parent.name or checkpoint.stem


def model_defaults(model_name):
    defaults = {
        "custom_cnn": {
            "model_type": "cnn",
            "framework": "tensorflow/keras",
            "architecture": "custom sequential CNN",
        },
        "vgg16_transfer_learning": {
            "model_type": "transfer_learning",
            "framework": "tensorflow/keras",
            "architecture": "VGG16 + custom binary head",
            "pretrained": True,
            "pretrained_source": "imagenet",
        },
        "cnn_features_svm": {
            "model_type": "svm",
            "framework": "scikit-learn",
            "architecture": "CNN feature extractor + SVM RBF",
        },
        "ensemble": {
            "model_type": "ensemble",
            "framework": "tensorflow/keras",
            "architecture": "weighted average ensemble",
        },
        "tta": {
            "model_type": "inference_strategy",
            "framework": "tensorflow/keras",
            "architecture": "test time augmentation",
        },
    }
    return defaults.get(
        model_name,
        {
            "model_type": "unknown",
            "framework": None,
            "architecture": None,
        },
    )


def start_tracking_run(
    args,
    run_type,
    script_name,
    model_name,
    run_name=None,
    parameters=None,
    random_seed=None,
):
    from src import run_tracker as tracker

    experiment_id = tracker.safe_track(
        tracker.create_experiment,
        name=EXPERIMENT_NAME,
        description="Experimentos de clasificación de malaria con trazabilidad ML.",
        project_name="malaria_dl_local_project",
        metadata=EXPERIMENT_METADATA,
    )
    dataset_id = tracker.safe_track(
        tracker.get_or_create_dataset,
        name=DATASET_NAME,
        source="TensorFlow Datasets / NIH NLM",
        version=DATASET_VERSION,
        description="NIH/NLM Malaria Cell Images para clasificación binaria.",
        total_images=27558,
        num_classes=2,
        class_names=DATASET_CLASS_NAMES,
        class_distribution=DATASET_CLASS_DISTRIBUTION,
        url="https://www.tensorflow.org/datasets/catalog/malaria",
        metadata={
            "task_type": "binary_classification",
            "label_mapping_version": LABEL_MAPPING_VERSION,
            "label_mapping": LABEL_MAPPING_METADATA,
            "tfds_original_class_names": ["parasitized", "uninfected"],
            "class_names": CLASS_NAMES,
            "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        },
    )

    defaults = model_defaults(model_name)
    model_id = tracker.safe_track(
        tracker.get_or_create_model,
        name=model_name,
        input_shape=f"({getattr(args, 'img_size', 200)}, {getattr(args, 'img_size', 200)}, 3)",
        output_shape="(1)",
        metadata={
            "tracking_source": script_name,
            "label_mapping_version": LABEL_MAPPING_VERSION,
            "label_mapping": LABEL_MAPPING_METADATA,
            "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        },
        **defaults,
    )

    run_id = tracker.safe_track(
        tracker.start_run,
        experiment_id=experiment_id,
        model_id=model_id,
        dataset_id=dataset_id,
        run_name=run_name or f"{script_name}:{model_name}",
        run_type=run_type,
        command=tracker.get_command_line(),
        script_name=script_name,
        parameters=(
            {
                **(parameters if parameters is not None else args_to_parameters(args)),
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": LABEL_MAPPING_METADATA,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
            }
        ),
        random_seed=random_seed,
        metadata={
            "tracking_version": "1.0",
            "label_mapping_version": LABEL_MAPPING_VERSION,
            "label_mapping": LABEL_MAPPING_METADATA,
            "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        },
    )

    if not run_id:
        print("Warning: tracking PostgreSQL desactivado para esta ejecución; no se pudo iniciar run.")

    return {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "dataset_id": dataset_id,
        "model_id": model_id,
        "model_name": model_name,
        "tracker": tracker,
    }


def fail_tracking_run(context, error, script_name):
    if not context or not context.get("run_id"):
        return
    tracker = context["tracker"]
    tracker.safe_track(
        tracker.fail_run,
        context["run_id"],
        error=error,
        script_name=script_name,
    )


def finish_tracking_run(context, metadata=None):
    if not context or not context.get("run_id"):
        return
    tracker = context["tracker"]
    tracker.safe_track(tracker.finish_run, context["run_id"], metadata=metadata)


def numeric_metric_items(metrics):
    aliases = {
        "precision_macro": "precision",
        "recall_macro": "recall",
        "f1_macro": "f1_score",
    }
    for name, value in metrics.items():
        if isinstance(value, (int, float, np.integer, np.floating)):
            yield name, float(value)
            if name in aliases:
                yield aliases[name], float(value)


def log_metrics_and_reports(context, metrics, class_names, split_name="test"):
    if not context or not context.get("run_id") or not metrics:
        return
    tracker = context["tracker"]
    run_id = context["run_id"]

    for name, value in numeric_metric_items(metrics):
        tracker.safe_track(
            tracker.log_metric,
            run_id,
            metric_name=name,
            metric_value=value,
            split_name=split_name,
        )

    cm = metrics.get("confusion_matrix")
    if cm is not None:
        true_negative = false_positive = false_negative = true_positive = None
        if len(cm) == 2 and len(cm[0]) == 2 and len(cm[1]) == 2:
            true_negative = int(cm[0][0])
            false_positive = int(cm[0][1])
            false_negative = int(cm[1][0])
            true_positive = int(cm[1][1])
        tracker.safe_track(
            tracker.log_confusion_matrix,
            run_id,
            matrix=cm,
            split_name=split_name,
            labels=list(class_names),
            true_positive=true_positive,
            true_negative=true_negative,
            false_positive=false_positive,
            false_negative=false_negative,
        )

    report = metrics.get("classification_report_dict") or {}
    for class_name in class_names:
        values = report.get(class_name)
        if not values:
            continue
        tracker.safe_track(
            tracker.log_classification_report,
            run_id,
            split_name=split_name,
            class_name=class_name,
            precision_value=values.get("precision"),
            recall_value=values.get("recall"),
            f1_score=values.get("f1-score"),
            support=values.get("support"),
        )


def log_predictions(
    context,
    y_true,
    y_pred,
    y_score,
    class_names,
    threshold=0.5,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    if not context or not context.get("run_id"):
        return
    tracker = context["tracker"]
    run_id = context["run_id"]
    dataset_id = context.get("dataset_id")
    positive_label = POSITIVE_LABEL if POSITIVE_LABEL in class_names else class_names[POSITIVE_CLASS_INDEX]
    mapping_metadata = label_mapping_metadata(label_mapping_version)
    raw_model_score_label = (
        POSITIVE_LABEL
        if mapping_metadata["raw_model_score_meaning"] == RAW_MODEL_SCORE_MEANING
        else NEGATIVE_LABEL
    )

    for index, (true_idx, pred_idx, score) in enumerate(zip(y_true, y_pred, y_score)):
        true_label = class_names[int(true_idx)]
        predicted_label = class_names[int(pred_idx)]
        probabilities = probability_by_class_from_scalar_score(
            score,
            class_names,
            label_mapping_version=label_mapping_version,
        )
        score_positive_label = probabilities.get(positive_label, float(score))
        tracker.safe_track(
            tracker.log_prediction,
            run_id,
            dataset_id=dataset_id,
            image_id=str(index),
            true_label=true_label,
            predicted_label=predicted_label,
            score=float(score),
            score_positive_label=float(score_positive_label),
            threshold=threshold,
            is_correct=bool(int(true_idx) == int(pred_idx)),
            case_type=tracker.compute_case_type(
                true_label,
                predicted_label,
                positive_label=positive_label,
            ),
            metadata={
                "dataset_index": index,
                "source": "tensorflow_datasets",
                "raw_model_score": float(score),
                "raw_model_score_label": raw_model_score_label,
                "raw_model_score_meaning": mapping_metadata["raw_model_score_meaning"],
                "probability_parasitized": probabilities.get(POSITIVE_LABEL),
                "probability_uninfected": probabilities.get(NEGATIVE_LABEL),
                "positive_label": positive_label,
                "positive_class_index": class_names.index(POSITIVE_LABEL),
                "label_mapping_version": label_mapping_version,
                "label_mapping": mapping_metadata,
            },
        )


def log_training_history(context, history, phase="training", epoch_offset=0):
    if not context or not context.get("run_id") or history is None:
        return
    tracker = context["tracker"]
    history_dict = getattr(history, "history", {}) or {}
    epochs = getattr(history, "epoch", list(range(len(next(iter(history_dict.values()), [])))))

    for index, epoch in enumerate(epochs):
        epoch_metadata = {
            "phase": phase,
            "recall_parasitized": get_history_value(
                history_dict,
                "recall_parasitized",
                index,
            ),
            "val_recall_parasitized": get_history_value(
                history_dict,
                "val_recall_parasitized",
                index,
            ),
        }
        values = {
            "loss": get_history_value(history_dict, "loss", index),
            "accuracy": get_history_value(history_dict, "accuracy", index),
            "precision_value": get_history_value(history_dict, "precision", index),
            "recall_value": get_history_value(history_dict, "recall", index),
            "auc": get_history_value(history_dict, "auc", index),
            "val_loss": get_history_value(history_dict, "val_loss", index),
            "val_accuracy": get_history_value(history_dict, "val_accuracy", index),
            "val_precision": get_history_value(history_dict, "val_precision", index),
            "val_recall": get_history_value(history_dict, "val_recall", index),
            "val_auc": get_history_value(history_dict, "val_auc", index),
            "learning_rate": get_history_value(history_dict, "learning_rate", index)
            or get_history_value(history_dict, "lr", index),
        }
        tracker.safe_track(
            tracker.log_training_history,
            context["run_id"],
            epoch=int(epoch) + epoch_offset,
            metadata=epoch_metadata,
            **values,
        )


def get_history_value(history_dict, key, index):
    values = history_dict.get(key)
    if values is None or index >= len(values):
        return None
    value = values[index]
    if isinstance(value, (np.integer, np.floating)):
        return float(value)
    return value


def log_output_artifacts(context, output_dir, artifact_type=None):
    if not context or not context.get("run_id") or output_dir is None:
        return
    tracker = context["tracker"]
    tracker.safe_track(
        tracker.log_artifacts_from_directory,
        context["run_id"],
        output_dir,
        artifact_type=artifact_type,
    )


def record_run_io(
    context,
    script_name,
    input_parameters,
    output_results,
    output_artifacts=None,
    dataset_metadata=None,
    command=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
    raw_model_score_meaning=RAW_MODEL_SCORE_MEANING,
    metadata=None,
):
    if not context or not context.get("run_id"):
        return None
    tracker = context["tracker"]
    io_metadata = {
        "source": "src.tracking_integration.record_run_io",
        **runtime_io_metadata(),
    }
    if metadata:
        io_metadata.update(metadata)

    return tracker.safe_track(
        tracker.log_run_io_record,
        context["run_id"],
        script_name=script_name,
        command=command or tracker.get_command_line(),
        input_parameters=json_safe(input_parameters),
        output_results=json_safe(output_results),
        output_artifacts=json_safe(output_artifacts or []),
        dataset_metadata=json_safe(dataset_metadata or {}),
        label_mapping_version=label_mapping_version,
        raw_model_score_meaning=raw_model_score_meaning,
        metadata=json_safe(io_metadata),
    )


def _normalize_split(split_name):
    return "val" if split_name == "validation" else split_name


def _usage_flags(split_name, usage_context):
    normalized_split = _normalize_split(split_name)
    return {
        "used_for_training": usage_context == "train" or normalized_split == "train",
        "used_for_validation": usage_context == "validation" or normalized_split == "val",
        "used_for_test": normalized_split == "test",
    }


def build_run_dataset_image_rows(
    registered_images,
    usage_context,
    metadata_by_sample_index=None,
    metadata_by_relative_path=None,
    batch_size=None,
):
    metadata_by_sample_index = metadata_by_sample_index or {}
    metadata_by_relative_path = metadata_by_relative_path or {}
    rows = []
    split_sample_index = {}

    for image in registered_images:
        split_name = _normalize_split(image["split_name"])
        sample_index = split_sample_index.get(split_name, 0)
        split_sample_index[split_name] = sample_index + 1
        relative_path = image["relative_path"]
        image_metadata = {
            "source": "physical_split",
            "dataset_dir": image.get("dataset_dir"),
            "label_mapping_version": image.get("label_mapping_version")
            or LABEL_MAPPING_VERSION,
            "label_mapping": LABEL_MAPPING_METADATA,
            "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        }
        image_metadata.update(metadata_by_sample_index.get(sample_index, {}))
        image_metadata.update(metadata_by_relative_path.get(relative_path, {}))

        rows.append(
            {
                "image_id": str(image["image_id"]),
                "split_name": split_name,
                "usage_context": usage_context,
                "class_index": int(image["class_index"]),
                "class_name": image["class_name"],
                "relative_path": relative_path,
                "filename": image["filename"],
                "sample_index": sample_index,
                "batch_index": None if not batch_size else sample_index // int(batch_size),
                "metadata": json_safe(image_metadata),
                **_usage_flags(split_name, usage_context),
            }
        )
    return rows


def record_run_dataset_images(
    context,
    dataset_info,
    usage_context,
    splits,
    metadata_by_sample_index=None,
    metadata_by_relative_path=None,
    batch_size=None,
    dataset_name="malaria_physical_split",
    dataset_source="tensorflow_datasets/malaria",
    compute_checksum=False,
):
    if not context or not context.get("run_id"):
        return None
    if not dataset_info or dataset_info.get("data_source") != "physical":
        return None

    dataset_dir = dataset_info.get("dataset_dir")
    if not dataset_dir:
        return None

    normalized_splits = [_normalize_split(split) for split in splits]
    tracker = context["tracker"]
    from src.dataset_registry import (
        load_registered_split_images,
        register_physical_split_images,
    )

    registration_key = (
        str(dataset_dir),
        dataset_name,
        dataset_source,
        bool(compute_checksum),
    )
    if registration_key not in _REGISTERED_PHYSICAL_SPLITS:
        registration = tracker.safe_track(
            register_physical_split_images,
            dataset_dir=dataset_dir,
            dataset_name=dataset_name,
            dataset_source=dataset_source,
            compute_checksum=compute_checksum,
        )
        if not registration:
            return None
        _REGISTERED_PHYSICAL_SPLITS.add(registration_key)

    registered_images = tracker.safe_track(
        load_registered_split_images,
        dataset_dir=dataset_dir,
        splits=normalized_splits,
    )
    if not registered_images:
        return {"total": 0, "inserted_or_updated": 0}

    rows = build_run_dataset_image_rows(
        registered_images,
        usage_context=usage_context,
        metadata_by_sample_index=metadata_by_sample_index,
        metadata_by_relative_path=metadata_by_relative_path,
        batch_size=batch_size,
    )
    return tracker.safe_track(
        tracker.log_run_dataset_images,
        context["run_id"],
        rows,
    )


def log_model_version(
    context,
    version_name,
    best_model_path=None,
    final_model_path=None,
    metadata=None,
):
    if not context or not context.get("run_id") or not context.get("model_id"):
        return
    tracker = context["tracker"]
    model_metadata = {"source": "src.train"}
    if metadata:
        model_metadata.update(metadata)
    tracker.safe_track(
        tracker.log_model_version,
        context["model_id"],
        version_name=version_name,
        checkpoint_path=best_model_path or final_model_path,
        best_model_path=best_model_path,
        final_model_path=final_model_path,
        training_run_id=context["run_id"],
        metadata=model_metadata,
    )


def log_explainability_outputs(context, cases, summary_rows, output_dir):
    if not context or not context.get("run_id"):
        return
    tracker = context["tracker"]
    run_id = context["run_id"]
    prediction_ids = {}

    for case in cases:
        prediction_ids[case["case_id"]] = tracker.safe_track(
            tracker.log_prediction,
            run_id,
            dataset_id=context.get("dataset_id"),
            image_id=str(case["case_id"]),
            true_label=case["true_label"],
            predicted_label=case["predicted_label"],
            score=float(case["score_positive_label"]),
            score_positive_label=float(case["score_positive_label"]),
            threshold=float(case["threshold"]),
            is_correct=case["true_label"] == case["predicted_label"],
            case_type=case["case_type"],
            metadata={
                "dataset_index": case["case_id"],
                "source": "tensorflow_datasets",
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "label_mapping": LABEL_MAPPING_METADATA,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
                "probability_parasitized": case["score_positive_label"],
            },
        )

    for row in summary_rows:
        output_path = row.get("image_path") or None
        method = row.get("method")
        tracker.safe_track(
            tracker.log_explainability_result,
            run_id,
            prediction_id=prediction_ids.get(row.get("case_id")),
            method=method,
            image_path=None,
            output_path=output_path,
            true_label=row.get("true_label"),
            predicted_label=row.get("predicted_label"),
            score=row.get("score_positive_label"),
            case_type=row.get("case_type"),
            last_conv_layer=row.get("last_conv_layer") or None,
            explanation_parameters={
                "output_dir": str(output_dir),
                "label_mapping_version": LABEL_MAPPING_VERSION,
                "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
            },
            success=bool(row.get("success")),
            error_message=row.get("error") or None,
        )

        if output_path and Path(output_path).exists():
            artifact_type = {
                "lime": "lime_image",
                "shap": "shap_image",
                "gradcam": "gradcam_image",
            }.get(method, "other")
            tracker.safe_track(
                tracker.log_artifact,
                run_id,
                artifact_type=artifact_type,
                name=Path(output_path).name,
                path=output_path,
            )

    summary_path = Path(output_dir) / "explanation_summary.csv"
    if summary_path.exists():
        tracker.safe_track(
            tracker.log_artifact,
            run_id,
            artifact_type="other",
            name=summary_path.name,
            path=str(summary_path),
            mime_type="text/csv",
            metadata={"artifact_role": "explanation_summary"},
        )
