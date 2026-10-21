"""Local GPU execution guard: Metal graph semantics must equal eager/CPU before any science.

Regression for pilot runs cf66a654/d1be1e59 (tensorflow-metal 1.2.0 computed Dense+ReLU wrongly
in graph mode). Runs on the CPU test environment; no database, no TRAIN.
"""
from contextlib import nullcontext
from pathlib import Path

import pytest

from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution import accelerator, local_launch, repository as module


def test_configure_disables_the_meta_optimizer_and_records_the_canary():
    import tensorflow as tf
    info = accelerator.configure(tf, require_gpu=False)
    assert tf.config.optimizer.get_experimental_options()["disable_meta_optimizer"] is True
    assert info["graph_meta_optimizer"] == "disabled"
    assert info["canary"]["operation"] == "relu(bias_add(matmul))"
    assert info["canary"]["max_abs_error"] <= accelerator.GRAPH_TOLERANCE
    assert isinstance(info["gpu_devices"], list)


def test_graph_divergence_stops_before_any_science(monkeypatch):
    import tensorflow as tf
    monkeypatch.setattr(accelerator, "canary_error", lambda tf: 5.01)  # value observed on Metal
    with pytest.raises(CampaignError, match="ACCELERATOR_GRAPH_DIVERGENCE"):
        accelerator.configure(tf, require_gpu=False)


def test_nan_canary_is_divergence(monkeypatch):
    import tensorflow as tf
    monkeypatch.setattr(accelerator, "canary_error", lambda tf: float("nan"))
    with pytest.raises(CampaignError, match="ACCELERATOR_GRAPH_DIVERGENCE"):
        accelerator.configure(tf, require_gpu=False)


def test_local_execution_without_gpu_is_rejected():
    import tensorflow as tf
    if tf.config.list_physical_devices("GPU"):
        pytest.skip("this environment has a GPU")
    with pytest.raises(CampaignError, match="LOCAL_GPU_REQUIRED"):
        accelerator.configure(tf, require_gpu=True)


@pytest.mark.parametrize("environ,expected", [
    ({"CAPSTONE_LOCAL_TRAIN": "1"}, True), ({}, False), ({"CAPSTONE_LOCAL_TRAIN": "0"}, False)])
def test_gpu_is_required_only_for_bootstrapped_local_runs(environ, expected, monkeypatch):
    monkeypatch.setattr(accelerator, "Path", lambda p: type("P", (), {"exists": lambda self: False})())
    assert accelerator.gpu_required(environ) is expected


def test_docker_never_requires_a_gpu(monkeypatch):
    monkeypatch.setattr(accelerator, "Path", lambda p: type("P", (), {"exists": lambda self: True})())
    assert accelerator.gpu_required({"CAPSTONE_LOCAL_TRAIN": "1"}) is False


def test_train_configures_before_datasets_and_models():
    source = (Path(accelerator.__file__).parent / "train.py").read_text()
    assert source.index("accelerator = configure(tf)") < source.index("make_image_dataset_from_directory(")
    assert source.index("accelerator = configure(tf)") < source.index("adapter.build(r)")
    assert '"accelerator": accelerator' in source


def test_assessment_runtime_configures_before_loading_the_checkpoint(monkeypatch):
    from src.malaria_dl.assessment import runtime
    def stop(tf, **kwargs):
        raise CampaignError("ACCELERATOR_GRAPH_DIVERGENCE")
    monkeypatch.setattr(accelerator, "configure", stop)
    monkeypatch.setattr("tensorflow.keras.models.load_model", lambda *a, **k: pytest.fail("checkpoint loaded"))
    with pytest.raises(CampaignError, match="ACCELERATOR_GRAPH_DIVERGENCE"):
        runtime.KerasRuntime({"seed": 1, "dataset": {"dataset_root": "/tmp"}, "model": {"path": "/x"}})


@pytest.mark.parametrize("accelerator_info,expected", [
    ({"gpu_devices": ["/physical_device:GPU:0"]}, (True, '["/physical_device:GPU:0"]')),
    ({"gpu_devices": []}, (False, "[]")),
    (None, (None, None)),
])
def test_runtime_projection_fills_gpu_columns(accelerator_info, expected, monkeypatch):
    calls = []
    monkeypatch.setattr(module, "execute", lambda c, sql, **params: calls.append((sql, params)))
    runtime = {"host": "h", "packages": {"keras": "3"}}
    if accelerator_info is not None:
        runtime["accelerator"] = accelerator_info
    module.ExecutionRepository.project_runtime(None, "00000000-0000-4000-8000-000000000001", runtime)
    sql, params = calls[0]
    assert "gpu_available=COALESCE" in sql and "gpu_devices=COALESCE" in sql
    assert (params["gpu_available"], params["gpu_devices"]) == expected


def test_launcher_accepts_only_the_metal_environment():
    find = lambda m: object()
    assert local_launch.environment_problem("/x/.venv-metal", "/usr", (3, 12), find) is None
    assert "intérprete activo" in local_launch.environment_problem("/x/.venv-local-train", "/usr", (3, 12), find)
    assert local_launch.VENV == ".venv-metal"


def test_canary_feeds_arguments_so_the_device_kernel_runs():
    # An all-constant graph is folded on the CPU and hid the Metal fault (error 1e-6 instead of 5.0).
    source = Path(accelerator.__file__).read_text()
    assert "tf.function(dense_relu)(*inputs)" in source and "def dense_relu(x, kernel, bias)" in source


def test_canary_detects_the_metal_fault_without_the_fix():
    """Fresh interpreter without the optimizer change: Metal 1.2.0 must be reported as divergent."""
    import importlib.metadata
    import subprocess
    import sys
    try:
        importlib.metadata.version("tensorflow-metal")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("tensorflow-metal not installed in this environment")
    code = ("import tensorflow as tf; from src.malaria_dl.execution import accelerator as a; "
            "print(a.canary_error(tf) if tf.config.list_physical_devices('GPU') else 'no-gpu')")
    root = Path(accelerator.__file__).resolve().parents[3]
    out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True,
                         env={**__import__("os").environ, "PYTHONPATH": str(root)}).stdout.strip().splitlines()[-1]
    if out == "no-gpu":
        pytest.skip("no GPU visible")
    assert float(out) > accelerator.GRAPH_TOLERANCE
