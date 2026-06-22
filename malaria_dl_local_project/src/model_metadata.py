import json
from pathlib import Path

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
)


MODEL_METADATA_FILENAME = "model_metadata.json"


def build_model_metadata(
    model_name,
    threshold_default=0.5,
    preprocessing="rescale_0_1",
    checkpoint_monitor="val_auc",
    early_stopping_monitor="val_auc",
    optimizer="adam",
    learning_rate=None,
    extra=None,
):
    metadata = {
        "model_name": model_name,
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "class_names": CLASS_NAMES,
        "negative_class_index": NEGATIVE_CLASS_INDEX,
        "negative_class_name": NEGATIVE_LABEL,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "positive_class_name": POSITIVE_LABEL,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        "threshold_default": float(threshold_default),
        "preprocessing": preprocessing,
        "checkpoint_monitor": checkpoint_monitor,
        "early_stopping_monitor": early_stopping_monitor,
        "optimizer": optimizer,
        "learning_rate": None if learning_rate is None else float(learning_rate),
    }
    if extra:
        metadata.update(extra)
    return metadata


def metadata_path_for_checkpoint(checkpoint):
    checkpoint = Path(checkpoint)
    return checkpoint.parent / MODEL_METADATA_FILENAME


def write_model_metadata(output_dir, metadata):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / MODEL_METADATA_FILENAME
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return metadata_path


def load_model_metadata_for_checkpoint(checkpoint):
    metadata_path = metadata_path_for_checkpoint(checkpoint)
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def verify_checkpoint_metadata(
    checkpoint,
    expected_label_mapping=LABEL_MAPPING_VERSION,
    expected_raw_score_meaning=RAW_MODEL_SCORE_MEANING,
    warn=True,
):
    metadata = load_model_metadata_for_checkpoint(checkpoint)
    warnings = []
    if metadata is None:
        warnings.append(
            "No se pudo verificar label mapping del checkpoint. "
            "Este modelo debe estar entrenado con 0 = uninfected, "
            "1 = parasitized."
        )
    else:
        label_mapping_version = metadata.get("label_mapping_version")
        raw_model_score_meaning = metadata.get("raw_model_score_meaning")
        class_names = metadata.get("class_names")
        if label_mapping_version != expected_label_mapping:
            warnings.append(
                "El label mapping del checkpoint "
                f"({label_mapping_version}) no coincide con el solicitado "
                f"({expected_label_mapping})."
            )
        if raw_model_score_meaning != expected_raw_score_meaning:
            warnings.append(
                "El significado de raw_model_score del checkpoint "
                f"({raw_model_score_meaning}) no coincide con "
                f"{expected_raw_score_meaning}."
            )
        if class_names != CLASS_NAMES:
            warnings.append(
                f"El orden de clases del checkpoint ({class_names}) no coincide "
                f"con {CLASS_NAMES}."
            )

    if warn:
        for warning in warnings:
            print(f"WARNING: {warning}")

    return {"metadata": metadata, "warnings": warnings}
