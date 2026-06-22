from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data"

# Convención oficial del proyecto:
# 0 = uninfected
# 1 = parasitized
# El score sigmoid representa probability_parasitized.
NEGATIVE_LABEL = "uninfected"
POSITIVE_LABEL = "parasitized"
NEGATIVE_CLASS_INDEX = 0
POSITIVE_CLASS_INDEX = 1
CLASS_NAMES = [NEGATIVE_LABEL, POSITIVE_LABEL]

LABEL_MAPPING_VERSION = "clinical_v1_parasitized_positive"
LEGACY_TFDS_LABEL_MAPPING_VERSION = "legacy_tfds_parasitized_zero"
LABEL_MAPPING_CHOICES = [
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
]

TFDS_ORIGINAL_CLASS_NAMES = ["parasitized", "uninfected"]

RAW_MODEL_SCORE_MEANING = "probability_parasitized"

LABEL_MAPPING_METADATA = {
    "version": LABEL_MAPPING_VERSION,
    "0": NEGATIVE_LABEL,
    "1": POSITIVE_LABEL,
    "negative_class_index": NEGATIVE_CLASS_INDEX,
    "negative_class_name": NEGATIVE_LABEL,
    "positive_class_index": POSITIVE_CLASS_INDEX,
    "positive_class_name": POSITIVE_LABEL,
    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
}

LEGACY_TFDS_LABEL_MAPPING_METADATA = {
    "version": LEGACY_TFDS_LABEL_MAPPING_VERSION,
    "0": POSITIVE_LABEL,
    "1": NEGATIVE_LABEL,
    "negative_class_index": 1,
    "negative_class_name": NEGATIVE_LABEL,
    "positive_class_index": 0,
    "positive_class_name": POSITIVE_LABEL,
    "raw_model_score_meaning": "probability_uninfected",
}


def label_mapping_metadata(version=LABEL_MAPPING_VERSION):
    if version == LABEL_MAPPING_VERSION:
        return dict(LABEL_MAPPING_METADATA)
    if version == LEGACY_TFDS_LABEL_MAPPING_VERSION:
        return dict(LEGACY_TFDS_LABEL_MAPPING_METADATA)
    raise ValueError(f"label_mapping_version no soportado: {version}")
