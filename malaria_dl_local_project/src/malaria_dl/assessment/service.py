"""Governed execution and readback verification, with injectable synthetic runtime."""

import importlib.metadata
from pathlib import Path
from typing import Any

from ..data.sample_repository import select_dataset_sample_ids
from ..campaigns.contracts import digest
from ..campaigns.repository import execute, identifier
from ..campaigns.service import planning_environment
from ..execution.artifacts import file_identity
from .contracts import (
    identity,
    prediction,
    probability,
    require,
    threshold,
    validate_split_protocol,
    verify_rows,
)
from .lineage import dataset_samples, resolve
from .representation import ROLES
from .openclip import calibration as zero_shot_calibration, decision as zero_shot_decision, is_openclip
from .runtime import runtime_for, save_artifacts, save_arrays


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
            ids = select_dataset_sample_ids(
                connection, dataset["dataset_version_id"], split,
                identifier(sample_id) if sample_id else None,
                None if max_images == "all" else max_images,
            )
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
    representation=None,
):
    validate_split_protocol(split, purpose, protocol)
    require(representation is None or (explanation is None and evaluation_id is None and max_images == "all"
                                        and sample_id is None), "REPRESENTATION_SELECTION_CONFLICT")
    binding, dataset, calibration = resolve(
        repository, training_run_id, model_version_id, dataset_version_id
    )
    zero_shot = is_openclip(binding)
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
    if zero_shot:
        # A logical TRAIN persisted no execution profile to inherit seed or batch from.
        require(type(seed) is int and type(batch_size) is int and batch_size > 0,
                "SEED_AND_BATCH_SIZE_REQUIRED_FOR_LOGICAL_TRAIN")
        require(explanation is None or explanation["method"] in ("lime", "shap"),
                "EXPLANATION_METHOD_UNSUPPORTED_FOR_FRAMEWORK")
        decision = zero_shot_decision(
            requested_threshold, protocol, binding["input_contract"],
            zero_shot_calibration(repository, binding, dataset) if requested_threshold == "clinical" else None)
    else:
        seed, batch_size = inference_options(repository, binding["training_run_id"], seed, batch_size,
                                             "explain" if explanation else "represent" if representation
                                             else "test" if split == "test" else "evaluate")
        decision = threshold(requested_threshold, protocol, calibration)
    samples = dataset_samples(
        repository, dataset, split, dataset_version_id, inspection=inspection,
        # The dataset of a logical TRAIN is the explicit selection, not TRAIN evidence.
        training_run_id=None if zero_shot else binding["training_run_id"], dataset_dir=dataset_dir,
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
        code=inference_environment(explanation, representation, zero_shot),
        seed=seed,
        batch_size=batch_size,
        explanation=explanation,
        evaluation=evaluation,
        representation=representation,
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
    elif value["kind"] == "represent":
        result = verify_representation(value, attempt, rows, artifacts)
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


def verify_representation(value, attempt, rows, artifacts):
    """Rows follow the ordered population; the four matrices exist, are intact and have its length."""
    import numpy as np

    from ..execution.storage_paths import local_scientific_path

    samples = value["samples"]
    by_id = {r["sample_id"]: r for r in rows}
    require(len(rows) == len(samples) and set(by_id) == {s["sample_id"] for s in samples},
            "REPRESENTATIONS_INCOMPLETE")
    roles = {a["role"]: a for a in artifacts}
    require(len(artifacts) == len(ROLES) and set(roles) == set(ROLES)
            and all(a["sample_id"] == samples[0]["sample_id"] for a in artifacts),
            "REPRESENTATION_ARTIFACTS_INCOMPLETE")
    for index, s in enumerate(samples):
        r = by_id[s["sample_id"]]
        require(r["specification"] == value["representation"] and r["label"] == s["label"]
                and r["patient_id"] == s["patient_id"] and r["result"]["row"] == index
                and r["result"]["predicted"] == int(r["result"]["raw_score"] >= value["decision"]["effective"])
                and sorted(r["artifacts"]) == sorted(a["artifact_id"] for a in artifacts),
                "REPRESENTATION_RESULT_CONFLICT")
    for a in artifacts:
        require(
            Path(a["path"]).resolve().is_relative_to(Path(attempt["artifact_root"]).resolve())
            and file_identity(a["path"]) == {k: a[k] for k in ("sha256", "bytes")},
            "ASSESSMENT_ARTIFACT_CHANGED",
        )
        shape = np.load(local_scientific_path(a["path"]), mmap_mode="r", allow_pickle=False).shape
        require(list(shape) == a["shape"] and (a["role"] == "pca_variance" or shape[0] == len(samples)),
                "REPRESENTATION_SHAPE_CONFLICT")
    return {"count": len(rows), "sha256": digest(sorted(rows, key=lambda r: r["sample_id"])),
            "artifacts_hash": digest(artifacts), "dimension": roles["embeddings"]["shape"][1]}


def represent_reserved(repository, value, attempt, runtime):
    """One forward pass per batch, projections over the whole population, then rows that cite them."""
    import numpy as np

    from .representation import project

    samples, features, scores = value["samples"], [], []
    for start in range(0, len(samples), value["batch_size"]):
        pooled, raw = runtime.represent(samples[start : start + value["batch_size"]])
        features.append(pooled)
        scores += raw
    features = np.concatenate(features)
    require(features.shape[0] == len(samples) == len(scores), "REPRESENTATION_COUNT_CONFLICT")
    arrays = {"embeddings": features, **project(features, value["representation"], value["seed"])}
    artifacts = save_arrays(attempt["artifact_root"], samples[0]["sample_id"], arrays)
    for artifact in artifacts:
        repository.artifact(attempt["id"], attempt["owner"], artifact)
    ids = [a["artifact_id"] for a in artifacts]
    rows = [{"sample_id": s["sample_id"], "patient_id": s["patient_id"], "label": s["label"],
             "specification": value["representation"],
             "result": {"row": index, "raw_score": probability(score), "layer": runtime.layer.name,
                        "predicted": int(score >= value["decision"]["effective"])},
             "artifacts": ids} for index, (s, score) in enumerate(zip(samples, scores))]
    for start in range(0, len(rows), 500):
        repository.write_batch(attempt["id"], attempt["owner"], rows[start : start + 500])


def reserve_execution(repository: Any, value: dict, artifact_root: str) -> tuple[dict, dict, bool]:
    """Reserve in the executing process before HTTP acknowledges the attempt."""
    from uuid import uuid4
    value = {**value, "execution_id": str(uuid4())}
    attempt, created = repository.reserve(value, artifact_root)
    return value, attempt, created


def run(repository, value, artifact_root, runtime_factory=runtime_for):
    value, attempt, created = reserve_execution(repository, value, artifact_root)
    if not created:
        if attempt["state"] == "verified":
            verify(repository, attempt, value)
        return attempt
    return execute_reserved(repository, value, attempt, runtime_factory)


def execute_reserved(repository: Any, value: dict, attempt: dict,
                     runtime_factory: Any = runtime_for) -> dict:
    """Same scientific execution for CLI and HTTP; no second algorithm pipeline."""
    require(repository.identity(attempt["identity_id"]) == value, "ASSESSMENT_IDENTITY_CONFLICT")
    require(attempt["state"] == "active", "ASSESSMENT_NOT_ACTIVE")
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
        if value["kind"] == "represent":
            represent_reserved(repository, value, attempt, runtime)
        for start in range(0, len(samples) if value["kind"] != "represent" else 0, value["batch_size"]):
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


def inference_environment(explanation=None, representation=None, zero_shot=False):
    result = planning_environment()
    packages = ["Pillow"]
    if zero_shot:
        packages += ["torch", "open_clip_torch", "transformers", "tokenizers", "timm"]
    if representation:
        packages += ["scikit-learn", "umap-learn"]
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
