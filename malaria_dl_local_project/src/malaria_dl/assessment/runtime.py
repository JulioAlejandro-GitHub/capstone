"""Lazy model runtime. No structured result sidecars or calibration fitting."""

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from ..execution.artifacts import file_identity
from .contracts import require


class KerasRuntime:
    def __init__(self, value):
        import tensorflow as tf

        from ..data.input_contract import validate_model_input

        tf.keras.utils.set_random_seed(value["seed"])
        tf.config.experimental.enable_op_determinism()
        self.value = value
        self.tf = tf
        self.model = tf.keras.models.load_model(value["model"]["path"], compile=False)
        validate_model_input(self.model, value["model"]["input_contract"])

    def images(self, samples):
        from ..data.preprocessing import apply_model_preprocessing

        tf = self.tf
        contract = self.value["model"]["input_contract"]
        images = []
        for s in samples:
            path = Path(self.value["dataset"]["dataset_root"]) / s["relative_path"]
            require(
                path.resolve().is_relative_to(
                    Path(self.value["dataset"]["dataset_root"]).resolve()
                ),
                "SAMPLE_PATH_CONFLICT",
            )
            require(path.is_file() and not path.is_symlink(), "SAMPLE_FILE_INVALID")
            contents = path.read_bytes()
            require(
                hashlib.sha256(contents).hexdigest() == s["sha256"],
                "SAMPLE_CONTENT_CHANGED",
            )
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
            explainer = shap.GradientExplainer(self.model, background)
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
        magnitude = np.abs(heat)
        magnitude = magnitude / magnitude.max() if magnitude.max() else magnitude
        color = np.stack([magnitude, np.zeros_like(magnitude), 1 - magnitude], axis=-1)
        overlay = np.clip(0.6 * rgb + 0.4 * color, 0, 1)
        return heat, overlay, {"score_explained": "raw", "class": spec["class"]}


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
