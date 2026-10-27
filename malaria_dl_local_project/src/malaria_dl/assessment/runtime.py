"""Lazy model runtime. No structured result sidecars or calibration fitting."""

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from ..data.governed_dataset import local_dataset_root
from ..execution.artifacts import file_identity
from ..execution.storage_paths import local_scientific_path
from .contracts import require


class KerasRuntime:
    def __init__(self, value):
        import tensorflow as tf

        from ..data.input_contract import validate_model_input
        from ..execution.accelerator import configure

        # Same graph semantics as TRAIN; SHAP/LIME and Grad-CAM also run in graph mode.
        self.accelerator = configure(tf)
        tf.keras.utils.set_random_seed(value["seed"])
        tf.config.experimental.enable_op_determinism()
        self.value = value
        self.dataset_root = local_dataset_root(value["dataset"]["dataset_root"])
        self.tf = tf
        self.model = tf.keras.models.load_model(local_scientific_path(value["model"]["path"]), compile=False)
        validate_model_input(self.model, value["model"]["input_contract"])

    def images(self, samples):
        from ..data.preprocessing import apply_model_preprocessing

        tf = self.tf
        contract = self.value["model"]["input_contract"]
        images = []
        for s in samples:
            contents = verified_sample_bytes(self.value, self.dataset_root, s)
            rgb = tf.io.decode_image(contents, channels=3, expand_animations=False)
            rgb = tf.image.resize(
                rgb, contract["shape"][1:3], method="bilinear", antialias=False
            )
            images.append(apply_model_preprocessing(rgb, contract["external"]["mode"]))
        return tf.stack(images)

    def predict(self, samples):
        import numpy as np

        output = np.asarray(self.model(self.images(samples), training=False))
        require(output.shape == (len(samples), 1), "MODEL_OUTPUT_SHAPE_CONFLICT")
        return output[:, 0].tolist()

    def represent(self, samples):
        """Pooled features and raw scores from one forward pass of the same graph."""
        import numpy as np

        from .representation import pooling_layer

        if not hasattr(self, "features"):
            self.layer = pooling_layer(self.model)
            self.features = self.tf.keras.Model(inputs=self.model.inputs,
                                                outputs=[self.layer.output, self.model.outputs[0]])
        pooled, output = self.features(self.images(samples), training=False)
        pooled, output = np.asarray(pooled), np.asarray(output)
        require(pooled.ndim == 2 and pooled.shape[0] == len(samples)
                and output.shape == (len(samples), 1), "MODEL_OUTPUT_SHAPE_CONFLICT")
        require(np.isfinite(pooled).all(), "REPRESENTATION_NONFINITE")
        return pooled.astype("float32"), output[:, 0].tolist()

    def explain(self, sample):
        import numpy as np

        from ..data.preprocessing import (
            display_images_to_model_inputs,
            model_image_to_display,
        )

        spec = self.value["explanation"]
        tensor = self.images([sample]).numpy()[0]
        mode = self.value["model"]["input_contract"]["external"]["mode"]
        rgb = model_image_to_display(tensor, mode)
        if spec["method"] == "gradcam":
            from ..explainability.pipeline import compute_gradcam_artifacts

            heat, overlay, layer = compute_gradcam_artifacts(
                self.model,
                tensor,
                spec["class"],
                last_conv_layer_name=spec["layer"],
                invert_scalar_output=spec["class"] == 0,
                preprocessing_mode=mode,
            )
            return (
                heat,
                overlay,
                {"layer": layer, "score_explained": "raw", "class": spec["class"]},
            )
        if spec["method"] == "lime":
            from lime.lime_image import LimeImageExplainer

            def predict(images):
                p = np.asarray(
                    self.model(
                        display_images_to_model_inputs(images, mode), training=False
                    )
                ).reshape(-1)
                return np.stack([1 - p, p], axis=1)

            explanation = LimeImageExplainer(
                random_state=self.value["seed"]
            ).explain_instance(
                rgb,
                predict,
                labels=(spec["class"],),
                top_labels=None,
                num_samples=spec["num_samples"],
                batch_size=self.value["batch_size"],
                random_seed=self.value["seed"],
            )
            weights = dict(explanation.local_exp[spec["class"]])
            heat = np.vectorize(lambda k: weights.get(k, 0.0))(
                explanation.segments
            ).astype("float32")
        else:
            import shap

            background = self.images(spec["background"]).numpy()
            # SHAP calls Keras with a list even for a single input. Expose the
            # same graph and shared weights with that input structure; do not
            # clone/reload the checkpoint or suppress Keras warnings.
            shap_model = self.tf.keras.Model(
                inputs=self.model.inputs, outputs=self.model.outputs[0]
            )
            explainer = shap.GradientExplainer(shap_model, background)
            values = explainer.shap_values(
                tensor[None], nsamples=spec["num_samples"], rseed=self.value["seed"]
            )
            if isinstance(values, list):
                require(len(values) == 1, "SHAP_OUTPUT_CONFLICT")
                values = values[0]
            values = np.asarray(values).squeeze()
            require(values.shape == tensor.shape, "SHAP_OUTPUT_CONFLICT")
            heat = values.sum(axis=-1) * (1 if spec["class"] == 1 else -1)
        require(np.isfinite(heat).all(), "ATTRIBUTION_NONFINITE")
        return heat, attribution_overlay(rgb, heat), {"score_explained": "raw", "class": spec["class"]}


def verified_sample_bytes(value, dataset_root, sample):
    """Authorized sample of this identity, inside the governed root, with its recorded bytes."""
    allowed = value["samples"] + (value.get("explanation") or {}).get("background", [])
    require(sample in allowed, "SAMPLE_NOT_AUTHORIZED")
    require(sample["split"] == value["split"], "SAMPLE_NOT_AUTHORIZED")
    path = dataset_root / sample["relative_path"]
    require(
        path.resolve().is_relative_to(dataset_root.resolve())
        and Path(sample["relative_path"]).parts[0] == sample["split"],
        "SAMPLE_PATH_CONFLICT",
    )
    require(path.is_file() and not path.is_symlink(), "SAMPLE_FILE_INVALID")
    contents = path.read_bytes()
    require(
        hashlib.sha256(contents).hexdigest() == sample["sha256"],
        "SAMPLE_CONTENT_CHANGED",
    )
    return contents


def attribution_overlay(rgb, heat):
    import numpy as np

    magnitude = np.abs(heat)
    magnitude = magnitude / magnitude.max() if magnitude.max() else magnitude
    color = np.stack([magnitude, np.zeros_like(magnitude), 1 - magnitude], axis=-1)
    return np.clip(0.6 * rgb + 0.4 * color, 0, 1)


def runtime_for(value):
    """Dispatch on the frozen input contract of the identity, never on the model name."""
    from .openclip import OpenCLIPRuntime, is_openclip

    return (OpenCLIPRuntime if is_openclip(value["model"]) else KerasRuntime)(value)


def save_arrays(root, sample_id, arrays):
    """Population matrices of REPRESENT, with the same exclusive creation as EXPLAIN artifacts."""
    import numpy as np

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    payloads = []
    for role, data in arrays.items():
        require(np.isfinite(data).all(), "REPRESENTATION_NONFINITE")
        artifact = str(uuid4())
        path = root / (artifact + ".npy")
        temporary = root / (artifact + ".npy.partial")
        with temporary.open("xb") as stream:
            np.save(stream, np.asarray(data), allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        temporary.unlink()
        payloads.append({"artifact_id": artifact, "sample_id": sample_id, "role": role, "path": str(path),
                         "state": "finalized", "shape": list(np.shape(data)), **file_identity(path)})
    return payloads


def save_artifacts(root, sample_id, heat, overlay):
    """Exclusive binary creation; failures leave evidence, never overwrite a prior attempt."""
    import numpy as np
    from PIL import Image

    require(
        np.isfinite(heat).all() and np.isfinite(overlay).all(), "ATTRIBUTION_NONFINITE"
    )
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    payloads = []
    for role, suffix, data in [("map", ".npy", heat), ("overlay", ".png", overlay)]:
        artifact = str(uuid4())
        path = root / (artifact + suffix)
        temporary = root / (artifact + suffix + ".partial")
        with temporary.open("xb") as stream:
            if role == "map":
                np.save(stream, np.asarray(data, dtype="float32"), allow_pickle=False)
            else:
                Image.fromarray((np.clip(data, 0, 1) * 255).astype("uint8")).save(
                    stream, format="PNG"
                )
            stream.flush()
            os.fsync(stream.fileno())
        # link is atomic and refuses an existing destination (unlike replace).
        os.link(temporary, path)
        temporary.unlink()
        payloads.append(
            {
                "artifact_id": artifact,
                "sample_id": sample_id,
                "role": role,
                "path": str(path),
                "state": "finalized",
                **file_identity(path),
            }
        )
    return payloads
