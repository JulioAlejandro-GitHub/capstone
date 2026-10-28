"""BiomedCLIP Linear Probing / Fine-tuning: engine pieces with synthetic data, no database."""
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from src.malaria_dl.assessment import openclip
from src.malaria_dl.assessment.contracts import AssessmentError
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution import artifacts, local_launch

torch = pytest.importorskip("torch")
from src.malaria_dl.execution import train_torch  # noqa: E402
from src.malaria_dl.models import biomedclip_training  # noqa: E402

RECIPE = {
    "embedding": "openclip_encode_image_l2_v1",
    "head": {"type": "linear", "in_features": 512, "out_features": 1, "activation": "sigmoid", "loss": "bce_with_logits"},
    "base_model": {
        "name": "biomedclip_zero_shot", "model_version_id": "3fd16a84-b5c7-442b-916b-e0438bb0f3e5",
        "training_run_id": "31d27b2d-6e90-4530-a589-ae92c91281df", "repository": "r", "revision": "v",
        "checkpoint": {"role": "checkpoint", "sha256": "a" * 64, "bytes": 1},
        "dependencies": [{"role": role, "sha256": "b" * 64, "bytes": 1} for role in sorted(openclip.DEPENDENCY_ROLES)],
    },
}


def contract(**changes):
    value = openclip.supervised_input_contract("biomedclip_linear", "1.0", [224, 224, 3], RECIPE)
    value.update(changes)
    return value


def test_supervised_contract_is_strict_and_validated_from_the_common_entry_point():
    from src.malaria_dl.data.input_contract import validate_input_contract

    assert validate_input_contract(contract())["schema_version"] == "openclip_supervised_input_v1"
    assert artifacts.checkpoint_framework(contract()) == "pytorch_openclip"
    assert artifacts.checkpoint_framework({"schema_version": "malaria_input_v1"}) == "keras"
    for broken, code in [
        (contract(input={"shape": [None, 200, 200, 3]}), "INPUT_SHAPE_FIXED_BY_BASE"),
        (contract(output={"shape": [None, 2], "activation": "softmax", "meaning": "x"}), "OPENCLIP_OUTPUT_INVALID"),
        (contract(framework="keras"), "OPENCLIP_CONTRACT_INVALID"),
    ]:
        with pytest.raises(AssessmentError, match=code):
            validate_input_contract(broken)
    missing = contract()
    missing["external"]["base_model"]["dependencies"].pop()
    with pytest.raises(AssessmentError, match="OPENCLIP_DEPENDENCIES_INVALID"):
        validate_input_contract(missing)


def test_samples_follow_the_keras_loader_order(tmp_path):
    for split, names in (("val", {"uninfected": ["b.png", "a.png"], "parasitized": ["c.png", "skip.txt"]}),):
        for label, files in names.items():
            (tmp_path / split / label).mkdir(parents=True)
            for name in files:
                (tmp_path / split / label / name).write_bytes(b"x")
    assert train_torch.directory_samples(tmp_path, "val") == [
        ("val/uninfected/a.png", 0), ("val/uninfected/b.png", 0), ("val/parasitized/c.png", 1)]


def test_early_stopping_reproduces_keras_3():
    model = torch.nn.Linear(1, 1)
    stopper = train_torch.EarlyStopping(patience=2, min_delta=0.1, restore_best_weights=True)
    with torch.no_grad():
        model.weight.fill_(1.0)
    assert not stopper.update(0, 0.5, model)
    with torch.no_grad():
        model.weight.fill_(2.0)
    # Not an improvement unless current - min_delta > best.
    assert not stopper.update(1, 0.55, model)
    assert stopper.update(2, 0.58, model) and stopper.stopped_epoch == 2 and stopper.best_epoch == 0
    stopper.finish(model)
    assert float(model.weight) == 1.0  # Keras 3 restores the best weights at the end of the phase


def test_optimizers_map_keras_parameters_and_reject_what_torch_cannot_honour():
    from src.malaria_dl.models.optimizers import optimizer_config

    groups = [{"params": [torch.nn.Parameter(torch.zeros(1))], "lr": 1e-3}]
    adamw = train_torch.optimizer("adamw", optimizer_config("adamw", {}), groups)
    assert isinstance(adamw, torch.optim.AdamW) and adamw.defaults["eps"] == 1e-7
    assert adamw.defaults["weight_decay"] == 0.004 and adamw.param_groups[0]["lr"] == 1e-3
    assert isinstance(train_torch.optimizer("sgd", optimizer_config("sgd", {}), groups), torch.optim.SGD)
    assert isinstance(train_torch.optimizer("adadelta", optimizer_config("adadelta", {}), groups), torch.optim.Adadelta)
    for name, change in (("adam", {"weight_decay": 0.1}), ("adamw", {"clipnorm": 1.0}), ("adam", {"use_ema": True})):
        with pytest.raises(CampaignError, match="UNSUPPORTED_OPTIMIZER_PARAMETER_FOR_TORCH"):
            train_torch.optimizer(name, optimizer_config(name, change), groups)


class Visual(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.trunk = torch.nn.Module()
        self.trunk.patch_embed = torch.nn.Linear(1, 1)
        self.trunk.blocks = torch.nn.ModuleList(torch.nn.Linear(1, 1) for _ in range(12))
        self.trunk.norm = torch.nn.LayerNorm(1)
        self.head = torch.nn.Module()
        self.head.proj = torch.nn.Linear(1, 1, bias=False)


class Classifier(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.visual = Visual()
        self.head = torch.nn.Linear(512, 1)


def test_trainable_names_partial_and_total():
    model = Classifier()
    assert biomedclip_training.trainable_names(model, 0) == ["head.weight", "head.bias"]
    partial = biomedclip_training.trainable_names(model, 2)
    assert {n.split(".")[3] for n in partial if ".blocks." in n} == {"10", "11"}
    assert set(biomedclip_training.TOP_PARAMETERS) <= set(partial) and "visual.trunk.patch_embed.weight" not in partial
    assert biomedclip_training.trainable_names(model, 12) == [n for n, _ in model.named_parameters()]
    with pytest.raises(CampaignError, match="INVALID_FINE_TUNE_LAYERS"):
        biomedclip_training.trainable_names(model, 13)
    assert biomedclip_training.set_trainable(model, partial) == partial


def test_checkpoint_keeps_only_trained_parameters_and_its_base_identity(tmp_path):
    model = Classifier()
    names = biomedclip_training.trainable_names(model, 1)
    identity = {"architecture": "biomedclip_fine_tuning", "base_model": RECIPE["base_model"]}
    path = tmp_path / "epoch_1.pt"
    biomedclip_training.save_checkpoint(path, model, names, identity)
    payload = torch.load(path, map_location="cpu", weights_only=True)
    assert payload["schema"] == biomedclip_training.CHECKPOINT_SCHEMA and set(payload["state"]) == set(names)
    assert not path.with_name("epoch_1.pt.partial").exists()
    with pytest.raises(CampaignError, match="ARTIFACT_ALREADY_EXISTS"):
        biomedclip_training.save_checkpoint(path, model, names, identity)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["epoch_1.pt"]  # no orphan partial


def test_checkpoint_of_another_base_is_rejected(tmp_path, monkeypatch):
    model = Classifier()
    other = deepcopy(RECIPE["base_model"])
    other["checkpoint"]["sha256"] = "c" * 64
    path = tmp_path / "epoch_1.pt"
    biomedclip_training.save_checkpoint(path, model, ["head.weight", "head.bias"],
                                        {"architecture": "biomedclip_linear", "base_model": other})
    monkeypatch.setattr(biomedclip_training, "base_files", lambda *a: pytest.fail("identity is checked first"))
    with pytest.raises(CampaignError, match="CHECKPOINT_IDENTITY_CONFLICT"):
        biomedclip_training.load_classifier(path, contract())


def test_each_framework_runs_in_its_own_local_environment(monkeypatch):
    monkeypatch.setattr(local_launch, "in_docker", lambda: False)
    monkeypatch.setattr(sys, "prefix", str(local_launch.PROJECT_ROOT / ".venv-metal"))
    assert local_launch.framework_python("keras", "/current/python") == "/current/python"
    assert local_launch.framework_python("pytorch_openclip", "/current/python") == str(
        local_launch.PROJECT_ROOT / ".venv-torch" / "bin" / "python")
    monkeypatch.setattr(local_launch, "in_docker", lambda: True)
    assert local_launch.framework_python("pytorch_openclip", "/current/python") == "/current/python"
    assert set(local_launch.ALLOWED_VENVS) == {".venv-metal", ".venv-torch"}
    assert "tensorflow" not in local_launch.ALLOWED_VENVS[".venv-torch"]
    assert "torch" not in local_launch.ALLOWED_VENVS[".venv-metal"]


def test_mps_is_required_without_cpu_fallback(monkeypatch):
    monkeypatch.setenv("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    with pytest.raises(CampaignError, match="TORCH_MPS_REQUIRED"):
        biomedclip_training.device()


def test_versioned_configurations_resolve_without_a_keras_input_contract(monkeypatch):
    from src.malaria_dl.models import registry
    from src.malaria_dl.models.configuration import resolve_config

    monkeypatch.setattr(registry, "registered_models", lambda: tuple(registry.MODEL_REGISTRY))
    linear = resolve_config("biomedclip_linear", None, None, batch=True)["resolved"]
    fine = resolve_config("biomedclip_fine_tuning", None, {"model": {"fine_tune_layers": 12}})["resolved"]
    assert linear["input_contract"]["schema_version"] == "openclip_supervised_input_v1"
    assert linear["model"]["fine_tune_layers"] == 0 and linear["recipe"]["augmentation"] == {}
    assert fine["model"]["fine_tune_layers"] == 12 and fine["execution"]["fine_tune_epochs"] > 0
    for change, code in (({"model": {"fine_tune_layers": 13}}, "INVALID_FINE_TUNE_LAYERS"),
                         ({"model": {"weights": "imagenet"}}, "INCOMPATIBLE_WEIGHTS"),
                         ({"recipe": {"encoder": "frozen"}}, "UNSUPPORTED_RECIPE_CHANGE")):
        with pytest.raises((ValueError, CampaignError), match=code):
            resolve_config("biomedclip_fine_tuning", None, change)
