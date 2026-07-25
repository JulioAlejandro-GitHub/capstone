"""Immutable clinical label convention used by every pipeline."""

NEGATIVE_CLASS_INDEX = 0
POSITIVE_CLASS_INDEX = 1
NEGATIVE_LABEL = "uninfected"
POSITIVE_LABEL = "parasitized"
RAW_MODEL_SCORE_MEANING = "probability_parasitized"

__all__ = [
    "NEGATIVE_CLASS_INDEX",
    "POSITIVE_CLASS_INDEX",
    "NEGATIVE_LABEL",
    "POSITIVE_LABEL",
    "RAW_MODEL_SCORE_MEANING",
]

