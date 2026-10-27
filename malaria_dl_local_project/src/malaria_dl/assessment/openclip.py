"""Zero-shot OpenCLIP assessments over a logical TRAIN: identity, decision and runtime.

The registered version carries the frozen transform, prompts and dependency bytes. Scores are
relative similarities between the two prompts, never a clinically calibrated probability.
"""

from copy import deepcopy

from ..campaigns.contracts import digest
from ..data.input_contract import MAPPING
from .contracts import require

SCHEMA = "openclip_input_v1"
FRAMEWORK = "pytorch_openclip"
SOURCE_KIND = "logical_train_registered_artifact"
CLASS_ORDER = ["uninfected", "parasitized"]
DEPENDENCY_ROLES = {"model_config", "text_config", "tokenizer_config", "vocabulary"}
REPRESENTATION_LAYER = "encode_image_l2"
SHAP_CHUNK = 100
ARGMAX_DECISION = "zero_shot_two_prompt_argmax_v1"
# Fixed before calibrating; same policy as the Keras campaigns. A change is a new version.
CALIBRATION_POLICY = {"version": "zero_shot_val_calibration_v1", "split": "val", "purpose": "development",
                      "reference_decision": ARGMAX_DECISION, "target_recall": 0.98,
                      "min_specificity": 0.0, "beta": 2.0}


def is_openclip(binding):
    return (binding.get("input_contract") or {}).get("schema_version") == SCHEMA


def input_contract(model_name, preprocessing, class_mapping, input_signature, output_signature):
    """Location-independent identity of the frozen zero-shot protocol."""
    from ..pretrained.registration import preprocessing_identity

    return validate_input_contract({
        "schema_version": SCHEMA,
        "architecture": model_name,
        "framework": FRAMEWORK,
        "external": preprocessing_identity(deepcopy(preprocessing)),
        "label_mapping": deepcopy(class_mapping),
        "input": deepcopy(input_signature),
        "output": deepcopy(output_signature),
    })


def validate_input_contract(c):
    require(isinstance(c, dict) and set(c) == {
        "schema_version", "architecture", "framework", "external", "label_mapping", "input", "output",
    } and c["schema_version"] == SCHEMA and c["framework"] == FRAMEWORK
        and isinstance(c["architecture"], str) and c["architecture"], "OPENCLIP_CONTRACT_INVALID")
    external = c["external"]
    require(isinstance(external, dict) and external.get("mode") == "openclip_original"
            and external.get("class_order") == CLASS_ORDER
            and isinstance(external.get("prompts"), list) and len(external["prompts"]) == 2
            and all(isinstance(p, str) and p for p in external["prompts"]),
            "OPENCLIP_PROMPTS_INVALID")
    dependencies = external.get("dependencies") or []
    require({d.get("role") for d in dependencies} == DEPENDENCY_ROLES
            and len(dependencies) == len(DEPENDENCY_ROLES)
            and all(set(d) == {"role", "sha256", "bytes"} for d in dependencies),
            "OPENCLIP_DEPENDENCIES_INVALID")
    require(all(c["label_mapping"].get(k) == v for k, v in MAPPING.items()), "LABEL_MAPPING_INVALID")
    output = c["output"]
    require(isinstance(output, dict) and output.get("activation") == "softmax"
            and output.get("shape") == [None, 2] and output.get("class_order") == CLASS_ORDER,
            "OPENCLIP_OUTPUT_INVALID")
    return c


def decision(requested, protocol, contract, calibration=None):
    """`auto` is the two-prompt argmax rule implied by the registered softmax output.

    softmax(...)[parasitized] >= 0.5 selects the parasitized prompt (ties included). It is
    fixed by the version before any VAL/TEST, so TEST needs no prior EVALUATE. `clinical`
    is the threshold calibrated on the VAL scores of that argmax EVALUATE (see
    `calibration`); the scores themselves are never recalibrated. Explicit values follow
    the protocol allowance.
    """
    from .contracts import threshold

    rule = {"calibrator": None, "score_domain": "raw", "positive_class": 1, "comparison": ">="}
    if requested == "clinical":
        require(isinstance(calibration, dict), "CLINICAL_THRESHOLD_EVIDENCE_REQUIRED")
        source = {key: calibration[key] for key in ("evaluation_attempt_id", "rows_sha256", "policy")}
        return {"requested": "clinical", "effective": calibration["result"]["threshold_selected"],
                "source": {"version": CALIBRATION_POLICY["version"], **source,
                           "sha256": digest(calibration["result"])}, **rule}
    if requested != "auto":
        return threshold(requested, protocol, None)
    return {
        "requested": "auto",
        "effective": 0.5,
        "source": {"version": ARGMAX_DECISION,
                   "sha256": digest({"output": contract["output"], "class_order": CLASS_ORDER,
                                     "comparison": ">="})},
        **rule,
    }


def calibration(repository, binding, dataset):
    """Recompute the VAL threshold from the single verified argmax EVALUATE of this model and dataset.

    The reference rows are re-verified against their attempt before use, so the threshold is
    reconstructible from persisted evidence alone. TEST rows are never a calibration source.
    """
    from ..evaluation.threshold_calibration import find_threshold_for_target_recall
    from .service import verify

    policy = CALIBRATION_POLICY
    references = []
    for attempt in repository.verified_evaluations(binding["training_run_id"]):
        value = repository.identity(attempt["identity_id"])
        if (value["model"] == binding and value["dataset"] == dataset and value["split"] == policy["split"]
                and value["purpose"] == policy["purpose"]
                and value["decision"]["source"]["version"] == policy["reference_decision"]):
            references.append((attempt, value))
    require(references, "CALIBRATION_REFERENCE_REQUIRED")
    require(len(references) == 1, "CALIBRATION_REFERENCE_AMBIGUOUS")
    attempt, value = references[0]
    verification = verify(repository, attempt, value)
    rows = sorted(repository.results(attempt["id"]), key=lambda r: r["sample_id"])
    result = find_threshold_for_target_recall(
        [r["label"] for r in rows], [r["raw_score"] for r in rows],
        target_recall=policy["target_recall"], min_specificity=policy["min_specificity"],
        beta=policy["beta"])
    result.pop("created_at", None)  # the identity must not depend on when it was recomputed
    require(result["calibration_split"] == "val" and result["threshold_selected"] == result["threshold_used"],
            "CLINICAL_THRESHOLD_EVIDENCE_REQUIRED")
    return {"evaluation_attempt_id": str(attempt["id"]), "rows_sha256": verification["sha256"],
            "policy": dict(policy), "result": result}


def registered_dependencies(connection, training_run_id, preprocessing):
    """Bind the frozen dependency bytes to this TRAIN's registered artifacts."""
    from ..campaigns.repository import execute, identifier
    from ..execution.storage_paths import local_scientific_path
    from ..pretrained.registration import resolve_dependencies

    rows = execute(connection, """
        SELECT id::text artifact_id, metadata->>'role' AS role, path, checksum AS sha256,
               file_size_bytes AS bytes, artifact_status AS status
        FROM artifacts WHERE run_id=CAST(:id AS uuid) AND artifact_type='model_dependency'
    """, id=identifier(training_run_id)).mappings().all()
    try:
        resolved = resolve_dependencies(preprocessing, [dict(r) for r in rows], local_scientific_path)
    except (ValueError, OSError, KeyError):
        require(False, "MODEL_DEPENDENCY_INVALID")
    return sorted(({k: d[k] for k in ("role", "artifact_id", "path", "sha256", "bytes")}
                   for d in resolved["dependencies"]), key=lambda d: d["role"])


class _Layer:
    name = REPRESENTATION_LAYER


class OpenCLIPRuntime:
    """Same interface as KerasRuntime; CPU/fp32 with the original OpenCLIP transform."""

    def __init__(self, value):
        import numpy as np
        import torch

        from ..data.governed_dataset import local_dataset_root
        from ..execution.storage_paths import local_scientific_path
        from ..models.openclip_inference import OpenCLIPClassifier, image_transform
        from ..pretrained.registration import verified_file

        model = value["model"]
        contract = validate_input_contract(model["input_contract"])
        torch.manual_seed(value["seed"])
        np.random.seed(value["seed"])
        dependencies = [verified_file(d) for d in model["dependencies"]]
        require(sorted((d["role"], d["sha256"], d["bytes"]) for d in dependencies)
                == sorted((d["role"], d["sha256"], d["bytes"]) for d in contract["external"]["dependencies"]),
                "MODEL_DEPENDENCY_INVALID")
        self.profile = {**contract["external"], "dependencies": dependencies}
        self.value = value
        self.dataset_root = local_dataset_root(value["dataset"]["dataset_root"])
        self.classifier = OpenCLIPClassifier(local_scientific_path(model["path"]), self.profile, model["sha256"])
        self.transform = image_transform(self.profile)
        normalize = self.transform.transforms[-1]
        self.mean = np.asarray(normalize.mean, dtype="float32")[:, None, None]
        self.std = np.asarray(normalize.std, dtype="float32")[:, None, None]
        self.layer = _Layer()
        self.torch = torch

    def images(self, samples):
        """Normalized NCHW float32, from verified bytes through the registered transform."""
        import io

        import numpy as np
        from PIL import Image

        from .runtime import verified_sample_bytes

        tensors = []
        for s in samples:
            with Image.open(io.BytesIO(verified_sample_bytes(self.value, self.dataset_root, s))) as image:
                tensors.append(self.transform(image.convert("RGB")).numpy())
        return np.stack(tensors).astype("float32")

    def _scores(self, batch):
        result = self.classifier.predict(batch)
        require(result.shape == (len(batch), 2), "MODEL_OUTPUT_SHAPE_CONFLICT")
        return result

    def predict(self, samples):
        return self._scores(self.images(samples))[:, 1].tolist()

    def represent(self, samples):
        """L2-normalized image embeddings and raw scores from one forward pass."""
        import numpy as np

        torch = self.torch
        model = self.classifier.model
        with torch.inference_mode():
            features = model.encode_image(torch.from_numpy(self.images(samples)), normalize=True)
            scores = (model.logit_scale.exp() * features @ self.classifier.text_features.T).softmax(dim=-1)
        features, scores = features.cpu().numpy(), scores.cpu().numpy()
        require(features.ndim == 2 and features.shape[0] == len(samples)
                and scores.shape == (len(samples), 2), "MODEL_OUTPUT_SHAPE_CONFLICT")
        require(np.isfinite(features).all(), "REPRESENTATION_NONFINITE")
        return features.astype("float32"), scores[:, 1].tolist()

    def display(self, tensor):
        """Undo only the normalization: the resized and cropped RGB image in [0, 1]."""
        import numpy as np

        return np.clip(tensor * self.std + self.mean, 0, 1).transpose(1, 2, 0)

    def from_display(self, images):
        import numpy as np

        values = np.asarray(images, dtype="float32").transpose(0, 3, 1, 2)
        return ((values - self.mean) / self.std).astype("float32")

    def explain(self, sample):
        import numpy as np

        from .runtime import attribution_overlay

        spec = self.value["explanation"]
        require(spec["method"] in ("lime", "shap"), "EXPLANATION_METHOD_UNSUPPORTED_FOR_FRAMEWORK")
        tensor = self.images([sample])[0]
        rgb = self.display(tensor)
        if spec["method"] == "lime":
            from lime.lime_image import LimeImageExplainer

            explanation = LimeImageExplainer(random_state=self.value["seed"]).explain_instance(
                rgb.astype("float64"),
                lambda images: self._scores(self.from_display(images)),
                labels=(spec["class"],),
                top_labels=None,
                num_samples=spec["num_samples"],
                batch_size=self.value["batch_size"],
                random_seed=self.value["seed"],
            )
            weights = dict(explanation.local_exp[spec["class"]])
            heat = np.vectorize(lambda k: weights.get(k, 0.0))(explanation.segments).astype("float32")
        else:
            import shap

            torch = self.torch
            # A ViT backward over shap's default batch of 50 exceeds the backend memory.
            explainer = shap.GradientExplainer(_PositiveScore(self.classifier),
                                               torch.from_numpy(self.images(spec["background"])),
                                               batch_size=self.value["batch_size"])
            # Expected gradients is a mean over samples: shap materializes all of them at once
            # (float64 deltas plus gradients), so draw fixed-size chunks with derived seeds and
            # take the sample-weighted mean of the chunk estimates.
            total, chunks = np.zeros(tensor.shape, dtype="float64"), 0
            for index, start in enumerate(range(0, spec["num_samples"], SHAP_CHUNK)):
                size = min(SHAP_CHUNK, spec["num_samples"] - start)
                values = explainer.shap_values(torch.from_numpy(tensor[None]), nsamples=size,
                                               rseed=self.value["seed"] + index)
                if isinstance(values, list):
                    require(len(values) == 1, "SHAP_OUTPUT_CONFLICT")
                    values = values[0]
                values = np.asarray(values).squeeze()
                require(values.shape == tensor.shape, "SHAP_OUTPUT_CONFLICT")
                total += values * size
                chunks += 1
            heat = (total / spec["num_samples"]).sum(axis=0).astype("float32") * (1 if spec["class"] == 1 else -1)
            require(np.isfinite(heat).all(), "ATTRIBUTION_NONFINITE")
            return heat, attribution_overlay(rgb, heat), {"score_explained": "raw", "class": spec["class"],
                                                          "shap_chunk_size": SHAP_CHUNK, "shap_chunks": chunks}
        require(np.isfinite(heat).all(), "ATTRIBUTION_NONFINITE")
        return heat, attribution_overlay(rgb, heat), {"score_explained": "raw", "class": spec["class"]}


def _PositiveScore(classifier):
    """Differentiable parasitized score; text features are constants of the frozen prompts."""
    import torch

    class PositiveScore(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = classifier.model
            # Inference-mode tensors cannot enter autograd; a clone outside it can.
            self.register_buffer("text", classifier.text_features.clone())

        def forward(self, images):
            features = self.model.encode_image(images, normalize=True)
            scores = (self.model.logit_scale.exp() * features @ self.text.T).softmax(dim=-1)
            return scores[:, 1:2]

    return PositiveScore().eval()
