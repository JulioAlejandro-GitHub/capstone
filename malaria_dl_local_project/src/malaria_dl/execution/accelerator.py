"""Graph-execution safety for TRAIN and assessments on the local accelerator.

tensorflow-metal 1.2.0 (TensorFlow 2.17, Keras 3) computes relu(bias_add(matmul)) wrongly in
graph mode when TensorFlow's meta optimizer runs, so a Keras Dense(activation="relu") gives
different outputs and gradients under `fit`/`predict` than eagerly or on CPU (pilot runs
cf66a654 and d1be1e59). Disabling the meta optimizer restores exact eager/CPU results. The
canary re-checks that on the active device before any science, so a library change cannot
reintroduce the divergence silently.
"""
import importlib.metadata
import os
from pathlib import Path

from ..campaigns.contracts import CampaignError

GRAPH_TOLERANCE = 1e-4
CANARY_OPERATION = "relu(bias_add(matmul))"


def gpu_required(environ=os.environ):
    """Local executions (bootstrapped launcher) run on the GPU; Docker stays on CPU."""
    return environ.get("CAPSTONE_LOCAL_TRAIN") == "1" and not Path("/.dockerenv").exists()


def canary_error(tf):
    """Largest deviation of eager and graph Dense+ReLU from the NumPy reference."""
    import numpy as np

    rng = np.random.default_rng(0)
    x = rng.standard_normal((8, 128)).astype(np.float32)
    kernel = (rng.standard_normal((128, 128)) * 0.1).astype(np.float32)
    bias = rng.standard_normal(128).astype(np.float32)
    reference = np.maximum(x @ kernel + bias, 0)
    # Arguments, not closure constants: an all-constant graph is folded on the CPU and
    # would never reach the faulty device kernel.
    inputs = [tf.constant(value) for value in (x, kernel, bias)]

    def dense_relu(x, kernel, bias):
        return tf.nn.relu(tf.nn.bias_add(tf.matmul(x, kernel), bias))

    eager = np.abs(dense_relu(*inputs).numpy() - reference).max()
    graph = np.abs(tf.function(dense_relu)(*inputs).numpy() - reference).max()
    return float(max(eager, graph))


def configure(tf, *, require_gpu=None):
    """Call right after importing TensorFlow, before building datasets or models."""
    tf.config.optimizer.set_experimental_options({"disable_meta_optimizer": True})
    gpus = [device.name for device in tf.config.list_physical_devices("GPU")]
    if (gpu_required() if require_gpu is None else require_gpu) and not gpus:
        raise CampaignError("LOCAL_GPU_REQUIRED")
    error = canary_error(tf)
    if not error <= GRAPH_TOLERANCE:
        raise CampaignError("ACCELERATOR_GRAPH_DIVERGENCE")
    try:
        metal = importlib.metadata.version("tensorflow-metal")
    except importlib.metadata.PackageNotFoundError:
        metal = None
    return {
        "gpu_devices": gpus,
        "tensorflow_metal": metal,
        "graph_meta_optimizer": "disabled",
        "canary": {"operation": CANARY_OPERATION, "max_abs_error": error, "tolerance": GRAPH_TOLERANCE},
    }
