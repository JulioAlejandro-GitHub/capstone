"""Governed execution and readback verification, with injectable synthetic runtime."""

import importlib.metadata
from pathlib import Path
from typing import Any

from ..campaigns.contracts import digest
from ..campaigns.repository import execute, identifier
from ..campaigns.service import planning_environment
from ..execution.artifacts import file_identity
from .contracts import (
    identity,
    prediction,
    require,
    threshold,
    validate_split_protocol,
    verify_rows,
)
from .lineage import dataset_samples, resolve
from .runtime import KerasRuntime, save_artifacts


def explanation_spec(method, layer, class_id, num_samples, background):
    require(
        method in ("gradcam", "lime", "shap")
        and type(class_id) is int
        and class_id in (0, 1),
        "EXPLANATION_METHOD_INVALID",
    )
    if method in ("lime", "shap") and num_samples is None:
        num_samples = 1000
    require(
        (method == "gradcam" and num_samples is None)
        or (method != "gradcam" and type(num_samples) is int and 1000 <= num_samples <= 5000),
        "EXPLANATION_PARAMETERS_INVALID",
    )
    require(
        layer is None or isinstance(layer, str) and bool(layer),
        "TARGET_LAYER_INVALID",
    )
    require(method == "gradcam" or layer is None, "UNUSED_TARGET_LAYER")
    require(
        (method == "shap" and bool(background))
        or (method != "shap" and not background),
        "BACKGROUND_CONTRACT_REQUIRED",
    )
    return {
        "method": method,
        "version": "e6_attribution_v1",
        "layer": layer,
        "class": class_id,
        "num_samples": num_samples,
        "background": background,
        "score_explained": "raw",
    }


def inference_options(repository: Any, training_run_id: str, seed: int | str,
                      batch_size: int | None, operation: str) -> tuple[int, int]:
    """Use the persisted operation profile, then the TRAIN execution profile.

    Current model configurations have no separate inference profile. Keeping the
    persisted execution batch is the minimal fallback; never impose a global 64.
    """
    if seed == "auto" or batch_size is None:
        with repository.transaction(readonly=True) as connection:
            configuration = execute(connection, """
                SELECT execution_parameters->'model_configuration_e2'->'configuration'
                FROM runs WHERE id=CAST(:id AS uuid) AND run_type='training'
            """, id=identifier(training_run_id)).scalar_one_or_none()
        require(isinstance(configuration, dict), "TRAIN_CONFIGURATION_REQUIRED")
        resolved = configuration.get("resolved", {})
        execution = resolved.get("execution", {})
        if seed == "auto":
            seed = execution.get("seed")
        if batch_size is None:
            batch_size = resolved.get(operation, {}).get("batch_size")
            if batch_size is None:
                batch_size = resolved.get("inference", {}).get("batch_size")
            if batch_size is None:
                batch_size = execution.get("batch_size")
    require(type(seed) is int and type(batch_size) is int and batch_size > 0,
            "INFERENCE_OPTIONS_INVALID")
    return seed, batch_size


def select_explanation_samples(repository: Any, dataset: dict, split: str, samples: list[dict],
                               max_images: int | str, sample_id: str | None) -> tuple[list[dict], dict]:
    """Select authorized targets in SQL before constructing the scientific identity."""
    require(max_images == "all" or type(max_images) is int and max_images > 0,
            "MAX_IMAGES_INVALID")
    require(sample_id is None or max_images == "all", "SAMPLE_SELECTION_CONFLICT")
    selected = samples
    if sample_id is not None or max_images != "all":
        with repository.transaction(readonly=True) as connection:
            ids = list(execute(connection, """
                SELECT source_record_id FROM dataset_split_assignments
                WHERE dataset_version_id=CAST(:dataset AS uuid) AND split_name=:split
                  AND (CAST(:sample AS uuid) IS NULL OR source_record_id=CAST(:sample AS uuid))
                ORDER BY source_record_id LIMIT :limit
            """, dataset=dataset["dataset_version_id"], split=split,
                sample=identifier(sample_id) if sample_id else None,
                limit=None if max_images == "all" else max_images).scalars())
        by_id = {sample["sample_id"]: sample for sample in samples}
        require(bool(ids) and all(str(item) in by_id for item in ids), "EXPLANATION_SAMPLE_SELECTION_EMPTY")
        selected = [by_id[str(item)] for item in ids]
    require(bool(selected), "EXPLANATION_SAMPLE_SELECTION_EMPTY")
    return selected, {"eligible_count": len(samples), "requested_max_images": max_images,
                      "requested_sample_id": sample_id, "selected_count": len(selected),
                      "sample_ids": [sample["sample_id"] for sample in selected]}


def prepare(
    repository,
    *,
    training_run_id=None,
    model_version_id=None,
    dataset_version_id=None,
    dataset_dir=None,
    model=None,
    split,
    purpose,
    protocol,
    requested_threshold,
    seed,
    batch_size,
    explanation=None,
    evaluation_id=None,
    max_images="all",
    sample_id=None,
    inspection=False,
    input_override=None,
    verification=None,
):
    validate_split_protocol(split, purpose, protocol)
    binding, dataset, calibration = resolve(
        repository, training_run_id, model_version_id
    )
    if model is not None:
        from ..models.registry import MODEL_REGISTRY

        architecture = binding["input_contract"]["architecture"]
        descriptor = MODEL_REGISTRY.get(architecture)
        names = (architecture, *(descriptor.aliases if descriptor else ()))
        require(model in names, "MODEL_TRAIN_CONFLICT")
    require(
        input_override is None or binding["input_contract"] == input_override,
        "INPUT_OVERRIDE_CONFLICT",
    )
    seed, batch_size = inference_options(repository, binding["training_run_id"], seed, batch_size,
                                         "explain" if explanation else "test" if split == "test" else "evaluate")
    decision = threshold(requested_threshold, protocol, calibration)
    samples = dataset_samples(
        repository, dataset, split, dataset_version_id, inspection=inspection,
        training_run_id=binding["training_run_id"], dataset_dir=dataset_dir,
        verification=verification, metadata_only=inspection and split == "test",
    )
    evaluation = None
    if evaluation_id:
        a = repository.attempt(evaluation_id)
        require(a["state"] == "verified", "EVALUATION_NOT_VERIFIED")
        parent = repository.identity(a["identity_id"])
        require(
            parent["kind"] == "evaluate"
            and parent["model"] == binding
            and parent["dataset"] == dataset
            and parent["samples"] == sorted(samples, key=lambda s: s["sample_id"])
            and parent["decision"] == decision
            and parent["purpose"] == purpose
            and parent["split"] == split
            and parent["protocol"] == protocol,
            "EXPLANATION_EVALUATION_CONFLICT",
        )
        verify(repository, a, parent)
        evaluation = {"attempt_id": str(a["id"]), "identity_hash": digest(parent)}
    require(explanation is not None or evaluation is None, "EVALUATE_CANNOT_EXPLAIN")
    if explanation:
        explanation = dict(explanation)
        if explanation["method"] == "shap":
            # Explicit references must belong to this operation's authorized split.
            # Never replace a historical TRAIN background silently with VAL images.
            background_samples = samples
            ids = set(explanation["background"])
            require(len(ids) == len(explanation["background"]), "BACKGROUND_AMBIGUOUS")
            explanation["background"] = sorted(
                [s for s in background_samples if s["sample_id"] in ids],
                key=lambda s: s["sample_id"],
            )
            require(
                len(explanation["background"]) == len(ids), "BACKGROUND_NOT_ACCREDITED"
            )
    if explanation:
        samples, selection = select_explanation_samples(
            repository, dataset, split, samples, max_images, sample_id)
        explanation["selection"] = selection
    value = identity(
        binding,
        dataset,
        samples,
        split=split,
        purpose=purpose,
        protocol=protocol,
        decision=decision,
        code=inference_environment(explanation),
        seed=seed,
        batch_size=batch_size,
        explanation=explanation,
        evaluation=evaluation,
    )
    return value


def verify(repository, attempt, value):
    require(
        repository.identity(attempt["identity_id"]) == value,
        "ASSESSMENT_IDENTITY_CONFLICT",
    )
    require(
        file_identity(value["model"]["path"])
        == {k: value["model"][k] for k in ("sha256", "bytes")},
        "CHECKPOINT_CONTENT_CHANGED",
    )
    rows = repository.results(attempt["id"])
    artifacts = repository.artifacts(attempt["id"])
    if value["kind"] == "evaluate":
        require(not artifacts, "UNEXPECTED_EVALUATION_ARTIFACT")
        result = verify_rows(value, rows)
    else:
        expected = {s["sample_id"] for s in value["samples"]}
        require(
            len(rows) == len(expected) and {r["sample_id"] for r in rows} == expected,
            "EXPLANATIONS_INCOMPLETE",
        )
        require(
            len(artifacts) == 2 * len(expected)
            and {(a["sample_id"], a["role"]) for a in artifacts}
            == {(s, r) for s in expected for r in ("map", "overlay")},
            "EXPLANATION_ARTIFACTS_INCOMPLETE",
        )
        for r in rows:
            require(
                r["specification"] == value["explanation"]
                and r["result"]["score_explained"] == "raw"
                and r["result"]["class"] == value["explanation"]["class"],
                "EXPLANATION_RESULT_CONFLICT",
            )
            require(
                sorted(r["artifacts"])
                == sorted(
                    a["artifact_id"]
                    for a in artifacts
                    if a["sample_id"] == r["sample_id"]
                ),
                "EXPLANATION_ARTIFACT_REFERENCE_CONFLICT",
            )
        for a in artifacts:
            require(
                Path(a["path"])
                .resolve()
                .is_relative_to(Path(attempt["artifact_root"]).resolve())
                and file_identity(a["path"]) == {k: a[k] for k in ("sha256", "bytes")},
                "ASSESSMENT_ARTIFACT_CHANGED",
            )
        result = {
            "count": len(rows),
            "sha256": digest(sorted(rows, key=lambda r: r["sample_id"])),
            "artifacts_hash": digest(artifacts),
        }
    if attempt["state"] == "verified":
        require(attempt["verification"] == result, "ASSESSMENT_VERIFICATION_CONFLICT")
    return result


def run(repository, value, artifact_root, runtime_factory=KerasRuntime):
    # Each invocation is new evidence, even with identical scientific parameters.
    from uuid import uuid4
    value = {**value, "execution_id": str(uuid4())}
    attempt, created = repository.reserve(value, artifact_root)
    if not created:
        if attempt["state"] == "verified":
            verify(repository, attempt, value)
        return attempt
    try:
        require(
            file_identity(value["model"]["path"])
            == {k: value["model"][k] for k in ("sha256", "bytes")},
            "CHECKPOINT_CONTENT_CHANGED",
        )
        runtime = runtime_factory(
            value
        )
        samples = value["samples"]
        for start in range(0, len(samples), value["batch_size"]):
            batch = samples[start : start + value["batch_size"]]
            if value["kind"] == "evaluate":
                scores = runtime.predict(batch)
                require(len(scores) == len(batch), "PREDICTION_COUNT_CONFLICT")
                rows = [
                    prediction(s, score, value["decision"])
                    for s, score in zip(batch, scores)
                ]
            else:
                rows = []
                for s in batch:
                    heat, overlay, result = runtime.explain(s)
                    artifacts = save_artifacts(
                        attempt["artifact_root"], s["sample_id"], heat, overlay
                    )
                    for artifact in artifacts:
                        repository.artifact(attempt["id"], attempt["owner"], artifact)
                    rows.append(
                        {
                            "sample_id": s["sample_id"],
                            "patient_id": s["patient_id"],
                            "specification": value["explanation"],
                            "result": result,
                            "artifacts": [a["artifact_id"] for a in artifacts],
                        }
                    )
            repository.write_batch(attempt["id"], attempt["owner"], rows)
        verification = verify(repository, attempt, value)
        repository.finish(attempt["id"], attempt["owner"], "verified", verification)
        confirmed = repository.attempt(attempt["id"])
        require(
            confirmed["state"] == "verified"
            and confirmed["verification"] == verification,
            "ASSESSMENT_FINALIZATION_UNCONFIRMED",
        )
        return confirmed
    except BaseException as original:
        try:
            repository.finish(
                attempt["id"],
                attempt["owner"],
                "failed",
                cause="ASSESSMENT_EXECUTION_FAILED",
            )
        except Exception:  # noqa: BLE001 -- retain the primary sanitized failure
            # Preserve primary diagnostic, do not claim cleanup or failed-state persistence succeeded.
            if hasattr(original, "add_note"):
                original.add_note("ASSESSMENT_FAILURE_STATE_UNCONFIRMED")
        raise


def inference_environment(explanation=None):
    result = planning_environment()
    packages = ["Pillow"]
    if explanation:
        packages += ["matplotlib"]
        if explanation["method"] == "lime":
            packages += ["lime", "scikit-image", "scikit-learn"]
        elif explanation["method"] == "shap":
            packages += ["shap", "scikit-learn"]
    result["inference_packages"] = {
        name: importlib.metadata.version(name) for name in packages
    }
    return result
