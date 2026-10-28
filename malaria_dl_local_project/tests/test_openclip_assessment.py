"""Zero-shot OpenCLIP assessments over a logical TRAIN; synthetic, no database or real weights."""

import sys
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.malaria_dl.assessment import lineage, openclip, runtime, service
from src.malaria_dl.assessment.contracts import AssessmentError, identity, verify_rows
from src.malaria_dl.assessment.service import explanation_spec, run
from src.malaria_dl.execution.artifacts import file_identity
from test_assessment_e6 import MemoryRepository

PROMPTS = [
    "a microscopy image of an uninfected red blood cell.",
    "a microscopy image of a red blood cell infected with malaria parasites.",
]
MAPPING = {"0": "uninfected", "1": "parasitized", "positive_class": 1, "positive_label": "parasitized"}
OUTPUT = {"shape": [None, 2], "meaning": "relative_similarity_not_clinically_calibrated",
          "activation": "softmax", "score_name": "score_parasitized",
          "class_order": ["uninfected", "parasitized"]}


def preprocessing():
    return {
        "mode": "openclip_original", "prompts": list(PROMPTS), "class_order": ["uninfected", "parasitized"],
        "dependencies": [{"role": role, "path": f"/cache/{role}", "name": role, "sha256": "b" * 64,
                          "bytes": 1, "artifact_id": str(uuid4())}
                         for role in sorted(openclip.DEPENDENCY_ROLES)],
    }


def contract():
    return openclip.input_contract("biomedclip_zero_shot", preprocessing(), MAPPING,
                                   {"shape": [None, 224, 224, 3]}, OUTPUT)


PROTOCOL = {"version": "exec1", "splits": ["val"], "purposes": ["development"],
            "allowed_numeric_thresholds": []}


def binding(tmp_path):
    p = tmp_path / "open_clip_pytorch_model.bin"
    p.write_bytes(b"synthetic weights")
    return {"training_run_id": str(uuid4()), "model_version_id": str(uuid4()),
            "checkpoint_artifact_id": str(uuid4()), "path": str(p), **file_identity(p),
            "input_contract": contract(), "dependencies": [],
            "source": {"kind": openclip.SOURCE_KIND, "framework": openclip.FRAMEWORK,
                       "dataset_selection": "explicit"}}


def samples():
    return [{"sample_id": str(uuid4()), "patient_id": str(uuid4()), "label": i, "split": "val",
             "sha256": "a" * 64, "relative_path": f"val/{i}.png"} for i in (0, 1)]


def test_contract_is_location_independent_and_strict():
    c = contract()
    assert all(set(d) == {"role", "sha256", "bytes"} for d in c["external"]["dependencies"])
    for mutate, code in [
        (lambda c: c["external"].update(prompts=PROMPTS[:1]), "OPENCLIP_PROMPTS_INVALID"),
        (lambda c: c["external"].update(class_order=["parasitized", "uninfected"]), "OPENCLIP_PROMPTS_INVALID"),
        (lambda c: c["external"]["dependencies"].pop(), "OPENCLIP_DEPENDENCIES_INVALID"),
        (lambda c: c["output"].update(activation="sigmoid"), "OPENCLIP_OUTPUT_INVALID"),
        (lambda c: c["label_mapping"].update({"1": "uninfected"}), "LABEL_MAPPING_INVALID"),
        (lambda c: c.update(framework="tensorflow"), "OPENCLIP_CONTRACT_INVALID"),
    ]:
        broken = deepcopy(c)
        mutate(broken)
        with pytest.raises(AssessmentError, match=code):
            openclip.validate_input_contract(broken)


def test_auto_decision_is_the_registered_argmax_rule_and_clinical_is_rejected():
    decision = openclip.decision("auto", PROTOCOL, contract())
    assert decision["effective"] == 0.5 and decision["comparison"] == ">="
    assert decision["source"]["version"] == "zero_shot_two_prompt_argmax_v1"
    assert decision["calibrator"] is None and decision["score_domain"] == "raw"
    with pytest.raises(AssessmentError, match="CLINICAL_THRESHOLD_EVIDENCE_REQUIRED"):
        openclip.decision("clinical", PROTOCOL, contract())
    with pytest.raises(AssessmentError, match="THRESHOLD_NOT_ALLOWED_BY_PROTOCOL"):
        openclip.decision("0.3", PROTOCOL, contract())
    allowed = {**PROTOCOL, "allowed_numeric_thresholds": [0.3]}
    assert openclip.decision("0.3", allowed, contract())["effective"] == 0.3


def test_logical_train_requires_an_explicit_dataset():
    with pytest.raises(AssessmentError, match="DATASET_VERSION_REQUIRED_FOR_LOGICAL_TRAIN"):
        lineage.logical_train_binding(None, None, None, None)


def install(monkeypatch, tmp_path, observed):
    model, population = binding(tmp_path), samples()
    dataset = {"dataset_version_id": str(uuid4()), "dataset_root": str(tmp_path)}

    def resolve(repository, training_run_id, model_version_id, dataset_version_id):
        observed["dataset_version_id"] = dataset_version_id
        return deepcopy(model), deepcopy(dataset), None

    def dataset_samples(*args, **kwargs):
        observed["training_run_id"] = kwargs["training_run_id"]
        return deepcopy(population)

    monkeypatch.setattr(service, "resolve", resolve)
    monkeypatch.setattr(service, "dataset_samples", dataset_samples)
    monkeypatch.setattr(service, "inference_environment", lambda *a: {"source": "synthetic"})
    monkeypatch.setattr(service, "inference_options",
                        lambda *a: pytest.fail("a logical TRAIN has no execution profile"))
    return model


def options(**extra):
    return {"split": "val", "purpose": "development", "protocol": PROTOCOL,
            "requested_threshold": "auto", "seed": 7, "batch_size": 2, **extra}


def test_prepare_uses_explicit_dataset_options_and_zero_shot_decision(monkeypatch, tmp_path):
    observed = {}
    install(monkeypatch, tmp_path, observed)
    dataset_version_id = str(uuid4())
    value = service.prepare(None, training_run_id=str(uuid4()), dataset_version_id=dataset_version_id, **options())
    assert observed == {"dataset_version_id": dataset_version_id, "training_run_id": None}
    assert value["decision"]["source"]["version"] == "zero_shot_two_prompt_argmax_v1"
    assert (value["seed"], value["batch_size"]) == (7, 2)
    for missing in ({"seed": "auto"}, {"batch_size": None}):
        with pytest.raises(AssessmentError, match="SEED_AND_BATCH_SIZE_REQUIRED_FOR_LOGICAL_TRAIN"):
            service.prepare(None, training_run_id=str(uuid4()), **options(**missing))


def test_prepare_rejects_gradcam_and_accepts_model_agnostic_methods(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, {})
    with pytest.raises(AssessmentError, match="EXPLANATION_METHOD_UNSUPPORTED_FOR_FRAMEWORK"):
        service.prepare(None, training_run_id=str(uuid4()),
                        explanation=explanation_spec("gradcam", None, 1, None, []), **options())
    value = service.prepare(None, training_run_id=str(uuid4()),
                            explanation=explanation_spec("lime", None, 1, 1000, []), **options())
    assert value["kind"] == "explain" and value["explanation"]["method"] == "lime"


def test_runtime_dispatch_follows_the_frozen_contract(monkeypatch, tmp_path):
    monkeypatch.setattr(openclip, "OpenCLIPRuntime", lambda value: "openclip")
    monkeypatch.setattr(runtime, "KerasRuntime", lambda value: "keras")
    assert runtime.runtime_for({"model": binding(tmp_path)}) == "openclip"
    assert runtime.runtime_for({"model": {"input_contract": {"schema_version": "malaria_input_v1"}}}) == "keras"


class ScoreRuntime:
    def __init__(self, value):
        self.value = value

    def predict(self, batch):
        return [0.5 if s["label"] else 0.4999 for s in batch]


def test_evaluate_runs_and_verifies_with_the_default_runtime_dispatch(monkeypatch, tmp_path):
    monkeypatch.setattr(openclip, "OpenCLIPRuntime", ScoreRuntime)
    value = identity(binding(tmp_path), {"dataset_version_id": str(uuid4()), "dataset_root": str(tmp_path)},
                     samples(), split="val", purpose="development", protocol=PROTOCOL,
                     decision=openclip.decision("auto", PROTOCOL, contract()),
                     code={"source": "synthetic"}, seed=7, batch_size=2)
    repository = MemoryRepository()
    attempt = run(repository, value, tmp_path)
    assert attempt["state"] == "verified"
    metrics = verify_rows(value, repository.results(attempt["id"]))["metrics"]
    # The tie at exactly 0.5 belongs to the parasitized prompt.
    assert (metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]) == (1, 1, 0, 0)


def test_shap_chunks_average_to_the_requested_sample_count(monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("torch")
    calls = []

    class Explainer:
        def __init__(self, model, data, batch_size):
            assert batch_size == 2

        def shap_values(self, x, nsamples, rseed):
            calls.append((nsamples, rseed))
            return np.full((1, 3, 4, 4, 1), float(rseed))

    monkeypatch.setitem(sys.modules, "shap", SimpleNamespace(GradientExplainer=Explainer))
    monkeypatch.setattr(openclip, "_PositiveScore", lambda classifier: None)
    runtime_ = object.__new__(openclip.OpenCLIPRuntime)
    runtime_.value = {"seed": 10, "batch_size": 2,
                      "explanation": {"method": "shap", "class": 1, "num_samples": 250, "background": []}}
    runtime_.classifier = None
    runtime_.device = "cpu"
    runtime_.mean, runtime_.std = np.zeros((3, 1, 1), "float32"), np.ones((3, 1, 1), "float32")
    runtime_.images = lambda batch: np.full((max(len(batch), 1), 3, 4, 4), 0.5, "float32")
    runtime_.torch = pytest.importorskip("torch")

    heat, overlay, result = runtime_.explain({"sample_id": "s"})
    assert calls == [(100, 10), (100, 11), (50, 12)]
    expected = 3 * (100 * 10 + 100 * 11 + 50 * 12) / 250
    assert heat.shape == (4, 4) and np.allclose(heat, expected)
    assert overlay.shape == (4, 4, 3)
    assert result == {"score_explained": "raw", "class": 1, "shap_chunk_size": 100, "shap_chunks": 3}


class CalibrationRepository(MemoryRepository):
    def verified_evaluations(self, training_run_id):
        return [deepcopy(a) for a in self.attempts.values()
                if a["state"] == "verified" and self.identities[a["identity_id"]]["kind"] == "evaluate"
                and self.identities[a["identity_id"]]["model"]["training_run_id"] == training_run_id]


SCORES = {0: [0.01, 0.03], 1: [0.02, 0.2]}


class FixedScores:
    def __init__(self, value):
        self.value = value

    def predict(self, batch):
        return [SCORES[s["label"]][int(s["relative_path"][-5])] for s in batch]


def calibration_population():
    return [{"sample_id": str(uuid4()), "patient_id": str(uuid4()), "label": label, "split": "val",
             "sha256": "a" * 64, "relative_path": f"val/{label}_{i}.png"}
            for label in (0, 1) for i in (0, 1)]


def reference_run(repository, model, dataset, population, threshold="auto", protocol=PROTOCOL):
    value = identity(model, dataset, population, split="val", purpose="development", protocol=protocol,
                     decision=openclip.decision(threshold, protocol, contract()),
                     code={"source": "synthetic"}, seed=7, batch_size=2)
    return run(repository, value, "/tmp/unused", FixedScores)


def test_clinical_threshold_is_recomputed_from_the_verified_val_argmax_evaluate(tmp_path):
    repository, model = CalibrationRepository(), binding(tmp_path)
    dataset = {"dataset_version_id": str(uuid4()), "dataset_root": str(tmp_path)}
    reference = reference_run(repository, model, dataset, calibration_population())

    evidence = openclip.calibration(repository, model, dataset)
    decision = openclip.decision("clinical", PROTOCOL, contract(), evidence)
    # Recall 1.0 is reached up to 0.02; specificity selects the highest of those thresholds.
    assert decision["effective"] == 0.02 and decision["requested"] == "clinical"
    assert decision["source"]["version"] == "zero_shot_val_calibration_v1"
    assert decision["source"]["evaluation_attempt_id"] == reference["id"]
    assert decision["source"]["rows_sha256"] == reference["verification"]["sha256"]
    assert decision["source"]["policy"]["target_recall"] == 0.98
    assert "created_at" not in evidence["result"]
    assert openclip.decision("clinical", PROTOCOL, contract(),
                             openclip.calibration(repository, model, dataset)) == decision


def test_calibration_reference_must_be_unique_and_of_the_same_model_and_dataset(tmp_path):
    repository, model = CalibrationRepository(), binding(tmp_path)
    dataset = {"dataset_version_id": str(uuid4()), "dataset_root": str(tmp_path)}
    with pytest.raises(AssessmentError, match="CALIBRATION_REFERENCE_REQUIRED"):
        openclip.calibration(repository, model, dataset)
    reference_run(repository, model, {**dataset, "dataset_version_id": str(uuid4())}, calibration_population())
    allowed = {**PROTOCOL, "allowed_numeric_thresholds": [0.3]}
    reference_run(repository, model, dataset, calibration_population(), "0.3", allowed)
    with pytest.raises(AssessmentError, match="CALIBRATION_REFERENCE_REQUIRED"):
        openclip.calibration(repository, model, dataset)
    reference_run(repository, model, dataset, calibration_population())
    reference_run(repository, model, dataset, calibration_population())
    with pytest.raises(AssessmentError, match="CALIBRATION_REFERENCE_AMBIGUOUS"):
        openclip.calibration(repository, model, dataset)


def test_calibration_rejects_altered_reference_rows(tmp_path):
    repository, model = CalibrationRepository(), binding(tmp_path)
    dataset = {"dataset_version_id": str(uuid4()), "dataset_root": str(tmp_path)}
    reference = reference_run(repository, model, dataset, calibration_population())
    row = next(iter(repository.rows[reference["id"]].values()))
    row["raw_score"] = 0.9
    with pytest.raises(AssessmentError):
        openclip.calibration(repository, model, dataset)


def test_clinical_requires_calibration_evidence():
    with pytest.raises(AssessmentError, match="CLINICAL_THRESHOLD_EVIDENCE_REQUIRED"):
        openclip.decision("clinical", PROTOCOL, contract(), None)


def test_activation_prefers_the_calibrated_val_evaluate_only_for_zero_shot(tmp_path):
    from src.malaria_dl.governance.eligibility import select_evaluation

    def evaluation(split, source, zero_shot=True):
        return {"evaluation_source_kind": "assessment_e6", "evaluation_attempt_id": str(uuid4()),
                "evaluation_identity_id": str(uuid4()), "evaluation_status": "verified",
                "evaluation_finished_at": "now", "evaluation_verified_evidence": True,
                "evaluation_link_valid": True, "evaluation_split": split,
                "evaluation_decision_source": source,
                "model_binding": binding(tmp_path) if zero_shot else
                {"input_contract": {"schema_version": "malaria_input_v1"}}}

    test = evaluation("test", "zero_shot_val_calibration_v1")
    calibrated = evaluation("val", "zero_shot_val_calibration_v1")
    argmax = evaluation("val", "zero_shot_two_prompt_argmax_v1")
    assert select_evaluation([test, argmax, calibrated]) is calibrated
    assert select_evaluation([test, argmax]) is test
    keras_test = evaluation("test", "e5_val_threshold_v1", zero_shot=False)
    keras_val = evaluation("val", "e5_val_threshold_v1", zero_shot=False)
    assert select_evaluation([keras_test, keras_val]) is keras_test
    assert select_evaluation([]) is None
