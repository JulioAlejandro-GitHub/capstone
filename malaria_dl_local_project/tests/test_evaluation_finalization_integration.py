from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.config import LABEL_MAPPING_VERSION, POSITIVE_LABEL
from src.malaria_dl.evaluation import evaluator
from src.malaria_dl.governance.services.model_version_resolver import (
    ResolvedModelVersion,
)


def _args(model_version_id):
    return SimpleNamespace(
        model_version_id=model_version_id,
        checkpoint=None,
        source_training_run_id=None,
        require_lineage=True,
        dataset_version_id=None,
        dataset_dir="unused",
        data_source="physical",
        preprocessing="auto",
        label_mapping=LABEL_MAPPING_VERSION,
        positive_label=POSITIVE_LABEL,
        threshold="0.5",
        track_db=True,
        img_size=200,
        batch_size=4,
    )


def _resolved(checkpoint, model_version_id, training_run_id):
    return ResolvedModelVersion(
        model_version_id=str(model_version_id),
        source_training_run_id=str(training_run_id),
        checkpoint_artifact_id=str(uuid4()),
        checkpoint_path=checkpoint,
        checkpoint_sha256="0" * 64,
        model_name="custom_cnn",
        status="candidate",
        preprocessing={"mode": "rescale_0_1"},
        class_mapping={
            "0": "uninfected",
            "1": "parasitized",
            "positive_class": 1,
            "positive_label": "parasitized",
        },
        input_signature={},
        output_signature={},
    )


def _runtime(checkpoint, *, finalizer_side_effect=None):
    model_version_id = uuid4()
    training_run_id = uuid4()
    evaluation_run_id = uuid4()
    resolved = _resolved(checkpoint, model_version_id, training_run_id)
    tracker = Mock()
    run_context = {
        "run_id": str(evaluation_run_id),
        "tracker": tracker,
    }
    stack = ExitStack()
    stack.enter_context(patch.object(evaluator, "parse_args", return_value=_args(model_version_id)))
    stack.enter_context(
        patch(
            "src.model_version_resolver.ModelVersionResolver.resolve",
            return_value=resolved,
        )
    )
    stack.enter_context(
        patch(
            "src.malaria_dl.data.governed_dataset.resolve_training_run_dataset",
            return_value=None,
        )
    )
    stack.enter_context(patch.object(evaluator, "verify_checkpoint_metadata"))
    stack.enter_context(
        patch.object(evaluator, "dataset_tracking_metadata", return_value={})
    )
    stack.enter_context(
        patch.object(
            evaluator,
            "resolve_threshold_for_checkpoint",
            return_value={"threshold_used": 0.5, "threshold_source": "explicit"},
        )
    )
    stack.enter_context(
        patch.object(evaluator, "load_malaria_splits", return_value=(None, None, object(), None))
    )
    stack.enter_context(patch.object(evaluator.tf.keras.models, "load_model", return_value=object()))
    stack.enter_context(
        patch.object(evaluator, "collect_predictions", return_value=([0], [0], [0.1]))
    )
    stack.enter_context(
        patch.object(evaluator, "evaluate_binary_predictions", return_value={"accuracy": 1.0})
    )
    stack.enter_context(
        patch.object(
            evaluator,
            "track_source_training_lineage",
            return_value={"confidence": "explicit"},
        )
    )
    stack.enter_context(
        patch("src.tracking_integration.start_tracking_run", return_value=run_context)
    )
    for name in (
        "log_metrics_and_reports",
        "log_predictions",
        "log_output_artifacts",
        "record_run_dataset_images",
        "record_run_io",
    ):
        stack.enter_context(patch(f"src.tracking_integration.{name}"))
    stack.enter_context(
        patch("src.tracking_integration.output_artifacts_from_directory", return_value=[])
    )
    stack.enter_context(
        patch("src.tracking_integration.clinical_metrics_for_tracking", return_value={})
    )
    generic_finish = stack.enter_context(
        patch("src.tracking_integration.finish_tracking_run")
    )
    failure = stack.enter_context(
        patch("src.tracking_integration.fail_evaluation_tracking_run")
    )
    finalizer = stack.enter_context(
        patch.object(
            evaluator,
            "finalize_evaluation_with_lineage",
            side_effect=finalizer_side_effect,
        )
    )
    return stack, finalizer, failure, generic_finish, evaluation_run_id, resolved


def test_evaluator_main_uses_strict_finalizer_without_safe_tracking(tmp_path):
    checkpoint = tmp_path / "model.keras"
    checkpoint.write_bytes(b"test checkpoint")
    stack, finalizer, failure, generic_finish, run_id, resolved = _runtime(
        checkpoint
    )
    with stack:
        evaluator.main()

    finalizer.assert_called_once()
    assert finalizer.call_args.kwargs["evaluation_run_id"] == str(run_id)
    assert finalizer.call_args.kwargs["training_run_id"] == (
        resolved.source_training_run_id
    )
    assert finalizer.call_args.kwargs["model_version_id"] == (
        resolved.model_version_id
    )
    assert finalizer.call_args.kwargs["checkpoint_artifact_id"] == (
        resolved.checkpoint_artifact_id
    )
    assert finalizer.call_args.kwargs["summary"]["status_detail"] == (
        "evaluation completed"
    )
    generic_finish.assert_not_called()
    failure.assert_not_called()


def test_finalizer_error_fails_main_and_never_reports_success(tmp_path, capsys):
    checkpoint = tmp_path / "model.keras"
    checkpoint.write_bytes(b"test checkpoint")
    expected = RuntimeError("strict finalization failed")
    stack, finalizer, failure, generic_finish, _, _ = _runtime(
        checkpoint, finalizer_side_effect=expected
    )
    with stack:
        with pytest.raises(RuntimeError, match="strict finalization failed"):
            evaluator.main()

    finalizer.assert_called_once()
    failure.assert_called_once()
    generic_finish.assert_not_called()
    assert "evaluation completed" not in capsys.readouterr().out.lower()
