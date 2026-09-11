from src.malaria_dl.data.governed_dataset import dataset_uuid_arg, GovernedDatasetError
from src.malaria_dl.persistence.dataset_evidence import verify_dataset_for_execution, bind_dataset_evidence_to_run
import argparse
import warnings
from pathlib import Path

import tensorflow as tf

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_CHOICES,
    LABEL_MAPPING_VERSION,
    LEGACY_TFDS_LABEL_MAPPING_VERSION,
    POSITIVE_LABEL,
    label_mapping_metadata,
)
from src.data import add_data_source_args, dataset_tracking_metadata, load_malaria_splits
from src.metrics import collect_predictions, evaluate_binary_predictions
from src.malaria_dl.evaluation.evaluation_terminal_service import (
    finalize_evaluation_with_lineage,
)
from src.model_metadata import resolve_threshold_for_checkpoint, verify_checkpoint_metadata
from src.preprocessing import PREPROCESSING_CHOICES


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Evalúa un modelo Keras guardado.")
    source=parser.add_mutually_exclusive_group()
    source.add_argument("--model-version-id", help="UUID de la model version inmutable.")
    source.add_argument("--checkpoint", "--model-path", dest="checkpoint", help="LEGACY: ruta a .keras")
    parser.add_argument("--img-size", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--threshold",
        default="0.5",
        help="Umbral numérico o 'clinical' para usar model_metadata.json.",
    )
    parser.add_argument(
        "--positive-label",
        default=POSITIVE_LABEL,
        help="Clase clínica positiva. Este proyecto usa parasitized.",
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
        help="Modo de preprocesamiento usado por el checkpoint.",
    )
    add_data_source_args(parser, governed=True)
    parser.add_argument(
        "--dataset-version-id", type=dataset_uuid_arg,
        help="UUID gobernado; debe coincidir con el dataset heredado del TRAIN.",
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    parser.add_argument(
        "--source-training-run-id",
        "--parent-run-id",
        dest="source_training_run_id",
        help="UUID del run de entrenamiento que generó el checkpoint.",
    )
    parser.add_argument(
        "--require-lineage",
        action="store_true",
        help=(
            "Fallar si --track-db está activo y no se puede resolver el "
            "entrenamiento origen."
        ),
    )
    parser.add_argument("--expected-dataset-evidence-id", type=dataset_uuid_arg, default=None)
    args = parser.parse_args(argv)
    if not (args.model_version_id or args.checkpoint or args.source_training_run_id):
        parser.error("indique --model-version-id, --source-training-run-id o --checkpoint")
    return args


def track_source_training_lineage(
    args,
    checkpoint,
    model_name,
    run_context,
    relationship_type="evaluates_checkpoint_from",
):
    """Resuelve y registra el entrenamiento origen de un run ya creado."""
    if not getattr(args, "track_db", False):
        return None

    child_run_id = (run_context or {}).get("run_id")
    if not child_run_id:
        warning = (
            "No se pudo crear el run de evaluación en PostgreSQL; "
            "no es posible registrar su linaje."
        )
        if getattr(args, "require_lineage", False):
            raise RuntimeError(warning)
        warnings.warn(warning, RuntimeWarning, stacklevel=2)
        return {"status": "unresolved", "message": warning}

    from src.run_lineage import (
        LineageResolutionError,
        mark_lineage_unresolved,
        resolve_source_training_run,
    )
    from src.malaria_dl.evaluation.evaluation_training_lineage_service import (
        EVALUATION_RELATIONSHIP_TYPE,
        create_or_confirm_evaluation_training_lineage,
    )

    if relationship_type != EVALUATION_RELATIONSHIP_TYPE:
        raise ValueError(
            "EVALUATE tracking requires evaluates_checkpoint_from"
        )

    checkpoint_path = str(checkpoint)

    def unresolved_or_raise(message, resolution=None, cause=None):
        result = resolution or {
            "status": "unresolved",
            "confidence": "unknown",
            "message": message,
        }
        effective_message = str(message)
        try:
            mark_lineage_unresolved(
                child_run_id=child_run_id,
                checkpoint_path=checkpoint_path,
                warning=effective_message,
            )
        except Exception as metadata_error:
            effective_message = (
                f"{effective_message} No se pudo guardar metadata de linaje: "
                f"{metadata_error}"
            )
        if getattr(args, "require_lineage", False):
            error = RuntimeError(effective_message)
            if cause is not None:
                raise error from cause
            raise error
        warnings.warn(effective_message, RuntimeWarning, stacklevel=2)
        return result

    try:
        resolution = resolve_source_training_run(
            source_training_run_id=getattr(args, "source_training_run_id", None),
            checkpoint_path=checkpoint_path,
            model_name=model_name,
        )
    except LineageResolutionError:
        # Un UUID explícito inexistente o no-training siempre es un error de uso.
        raise
    except Exception as exc:
        return unresolved_or_raise(
            f"No se pudo resolver el linaje de la evaluación: {exc}",
            cause=exc,
        )
    if resolution.get("status") == "resolved":
        parent_run_id = resolution.get("training_run_id") or resolution.get("id")
        if not parent_run_id:
            return unresolved_or_raise(
                "La resolución de linaje no entregó un training_run_id.",
            )
        confidence = resolution.get("confidence") or (
            "explicit"
            if getattr(args, "source_training_run_id", None)
            else "inferred_exact_checkpoint"
        )
        lineage_result = create_or_confirm_evaluation_training_lineage(
            training_run_id=parent_run_id,
            evaluation_run_id=child_run_id,
            model_version_id=resolution.get("model_version_id"),
            checkpoint_artifact_id=resolution.get(
                "checkpoint_artifact_id"
            ),
            checkpoint_path=checkpoint_path,
            confidence=confidence,
            metadata={"phase": "evaluation_started"},
        )
        resolution["lineage_id"] = str(lineage_result.lineage_id)
        resolution["lineage_created"] = lineage_result.created
        return resolution

    warning = resolution.get("message") or (
        "No se pudo inferir de forma única el training_run_id. "
        "Use --source-training-run-id."
    )
    return unresolved_or_raise(warning, resolution=resolution)



def main():
    from ..assessment.cli import main as governed_main
    return governed_main("evaluate")

if __name__ == "__main__":
    raise SystemExit(main())
