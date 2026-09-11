import argparse
from pathlib import Path

from src.config import (
    LABEL_MAPPING_CHOICES,
    LABEL_MAPPING_VERSION,
)
from src.data import (
    add_data_source_args,
)
from src.inference_pipeline import (
    probability_rows_from_predictions,  # noqa: F401 -- historical helper re-export
)
from src.model_metadata import (
    resolve_threshold_for_checkpoint,
)
from src.preprocessing import PREPROCESSING_CHOICES

ENSEMBLE_CLINICAL_THRESHOLD_ERROR = (
    "No clinical threshold found for ensemble. "
    "Calibrate ensemble threshold first or use numeric threshold."
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Ensemble ponderado de modelos Keras.")
    parser.add_argument(
        "--models", nargs="+", required=True, help="Rutas a modelos .keras"
    )
    parser.add_argument(
        "--weights", nargs="+", type=float, default=None, help="Pesos del ensemble"
    )
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--threshold",
        default="0.5",
        help=(
            "Umbral numérico o 'clinical'. Para 'clinical' se requiere "
            "--threshold-metadata-checkpoint con metadata calibrada del ensemble."
        ),
    )
    parser.add_argument(
        "--threshold-metadata-checkpoint",
        default=None,
        help=(
            "Ruta a un artefacto dentro del directorio que contiene model_metadata.json "
            "del ensemble calibrado."
        ),
    )
    parser.add_argument(
        "--label-mapping",
        choices=LABEL_MAPPING_CHOICES,
        default=LABEL_MAPPING_VERSION,
        help="Convención del checkpoint. Usa legacy_tfds solo para modelos antiguos.",
    )
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help="Modo de preprocesamiento aplicado a todos los modelos del ensemble.",
    )
    add_data_source_args(parser)
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args(argv)


def resolve_ensemble_threshold(
    threshold, model_paths, threshold_metadata_checkpoint=None
):
    if isinstance(threshold, str) and threshold.strip().lower() == "clinical":
        if not threshold_metadata_checkpoint:
            raise ValueError(ENSEMBLE_CLINICAL_THRESHOLD_ERROR)
        try:
            return resolve_threshold_for_checkpoint(
                threshold,
                Path(threshold_metadata_checkpoint),
            )
        except ValueError as exc:
            raise ValueError(ENSEMBLE_CLINICAL_THRESHOLD_ERROR) from exc

    return resolve_threshold_for_checkpoint(threshold, model_paths[0])


def main(argv=None):
    """E8 replaces legacy TEST inference/CSV with governed probability artifacts."""
    from ..science.ensemble_cli import main as governed_main

    return governed_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
