"""Versioned input evidence. Historical resolution never consults current defaults."""

from copy import deepcopy

SCHEMA = "malaria_input_v1"
MAPPING = {
    "0": "uninfected",
    "1": "parasitized",
    "positive_class": 1,
    "positive_label": "parasitized",
}
INTERNAL_DENSENET = "densenet_imagenet_channel_mean_std"


class InputContractError(ValueError):
    pass


def make_input_contract(architecture, adapter_version, shape, mode, internal=None):
    """For new resolved configurations or explicitly authored synthetic fixtures only."""
    return validate_input_contract(
        {
            "schema_version": SCHEMA,
            "architecture": architecture,
            "adapter_version": adapter_version,
            "shape": [None, *shape],
            "dtype": "float32",
            "channels": 3,
            "source_order": "RGB",
            "source_scale": "0_255",
            "decode": "tf_decode_image_rgb_v1",
            "resize": {"method": "bilinear", "antialias": False, "location": "loader"},
            "external": {
                "mode": mode,
                "version": "tf_preprocessing_v1",
                "location": "loader",
                "output_order": "BGR" if mode == "vgg16_imagenet" else "RGB",
            },
            "internal": {"mode": internal, "location": "model" if internal else "none"},
            "label_mapping": deepcopy(MAPPING),
            "output": {
                "shape": [None, 1],
                "dtype": "float32",
                "meaning": "probability_parasitized",
                "activation": "sigmoid",
            },
        }
    )


def validate_input_contract(value):
    if not isinstance(value, dict):
        raise InputContractError("INPUT_CONTRACT_MISSING")
    c = deepcopy(value)
    expected = {
        "schema_version",
        "architecture",
        "adapter_version",
        "shape",
        "dtype",
        "channels",
        "source_order",
        "source_scale",
        "decode",
        "resize",
        "external",
        "internal",
        "label_mapping",
        "output",
    }
    if set(c) != expected or c["schema_version"] != SCHEMA:
        raise InputContractError("INPUT_CONTRACT_INCOMPLETE_OR_UNSUPPORTED")
    if (
        not isinstance(c["architecture"], str)
        or not c["architecture"]
        or not isinstance(c["adapter_version"], str)
        or not c["adapter_version"]
    ):
        raise InputContractError("INPUT_IDENTITY_MISSING")
    shape = c["shape"]
    if (
        not isinstance(shape, list)
        or len(shape) != 4
        or shape[0] is not None
        or any(type(x) is not int or x < 1 for x in shape[1:])
        or shape[3] != 3
    ):
        raise InputContractError("INPUT_SHAPE_INVALID")
    if (
        c["dtype"] != "float32"
        or c["channels"] != 3
        or c["source_order"] != "RGB"
        or c["source_scale"] != "0_255"
        or c["decode"] != "tf_decode_image_rgb_v1"
        or c["resize"]
        != {"method": "bilinear", "antialias": False, "location": "loader"}
    ):
        raise InputContractError("INPUT_TRANSFORM_UNSUPPORTED")
    if not isinstance(c["external"], dict) or not isinstance(c["internal"], dict):
        raise InputContractError("INPUT_TRANSFORM_INVALID")
    mode = c["external"].get("mode")
    if mode not in ("rescale_0_1", "vgg16_imagenet") or c["external"] != {
        "mode": mode,
        "version": "tf_preprocessing_v1",
        "location": "loader",
        "output_order": "BGR" if mode == "vgg16_imagenet" else "RGB",
    }:
        raise InputContractError("INPUT_EXTERNAL_TRANSFORM_INVALID")
    internal = (c["internal"] or {}).get("mode")
    if c["internal"] != {
        "mode": internal,
        "location": "model" if internal else "none",
    } or internal not in (None, INTERNAL_DENSENET):
        raise InputContractError("INPUT_INTERNAL_TRANSFORM_INVALID")
    if c["architecture"] == "densenet121" and (
        internal != INTERNAL_DENSENET or mode != "rescale_0_1"
    ):
        raise InputContractError("DENSENET_INPUT_CONFLICT")
    if c["architecture"] != "densenet121" and internal is not None:
        raise InputContractError("INPUT_ARCHITECTURE_CONFLICT")
    if c["architecture"] != "vgg16" and mode == "vgg16_imagenet":
        raise InputContractError("INPUT_ARCHITECTURE_CONFLICT")
    if c["label_mapping"] != MAPPING or c["output"] != {
        "shape": [None, 1],
        "dtype": "float32",
        "meaning": "probability_parasitized",
        "activation": "sigmoid",
    }:
        raise InputContractError("INPUT_OUTPUT_MAPPING_CONFLICT")
    return c


def resolve_checkpoint_input(
    preprocessing,
    input_signature,
    output_signature=None,
    mapping=None,
    *,
    architecture=None,
    img_size=None,
    mode="auto",
    label_mapping=None,
):
    c = validate_input_contract((preprocessing or {}).get("input_contract"))
    persisted_mode = (preprocessing or {}).get("mode") or (preprocessing or {}).get(
        "preprocessing"
    )
    if persisted_mode != c["external"]["mode"]:
        raise InputContractError("INPUT_PREPROCESSING_SNAPSHOT_CONFLICT")
    signature = input_signature or {}
    if (signature.get("shape") or signature.get("input_shape")) != c[
        "shape"
    ] or signature.get("dtype") != c["dtype"]:
        raise InputContractError("INPUT_SIGNATURE_SNAPSHOT_CONFLICT")
    if output_signature is not None and (
        (output_signature.get("shape") or output_signature.get("output_shape"))
        != c["output"]["shape"]
        or output_signature.get("dtype") != "float32"
    ):
        raise InputContractError("OUTPUT_SIGNATURE_SNAPSHOT_CONFLICT")
    if mapping is not None and any(mapping.get(k) != v for k, v in MAPPING.items()):
        raise InputContractError("INPUT_MAPPING_SNAPSHOT_CONFLICT")
    # Historical alias is explicit; no current descriptor/config lookup.
    if (
        architecture is not None
        and {"vgg16_transfer_learning": "vgg16"}.get(architecture, architecture)
        != c["architecture"]
    ):
        raise InputContractError("INPUT_ARCHITECTURE_SNAPSHOT_CONFLICT")
    if img_size is not None and c["shape"][1:3] != [img_size, img_size]:
        raise InputContractError("INPUT_SIZE_OVERRIDE_CONFLICT")
    if mode not in (None, "auto", c["external"]["mode"]):
        raise InputContractError("INPUT_PREPROCESSING_OVERRIDE_CONFLICT")
    if label_mapping is not None:
        from src.config import LABEL_MAPPING_VERSION

        if label_mapping != LABEL_MAPPING_VERSION:
            raise InputContractError("INPUT_LABEL_OVERRIDE_CONFLICT")
    return c


def validate_model_input(model, contract):
    c = validate_input_contract(contract)
    if tuple(model.input_shape) != tuple(c["shape"]) or tuple(model.output_shape) != (
        None,
        1,
    ):
        raise InputContractError("LOADED_MODEL_SIGNATURE_CONFLICT")
    if (
        str(model.inputs[0].dtype) != "float32"
        or str(model.outputs[0].dtype) != "float32"
    ):
        raise InputContractError("LOADED_MODEL_DTYPE_CONFLICT")
    if (
        getattr(getattr(model.layers[-1], "activation", None), "__name__", None)
        != "sigmoid"
    ):
        raise InputContractError("LOADED_MODEL_OUTPUT_CONFLICT")
    layers = list(model.layers)

    # Detect an added external transform inside a graph to avoid double processing.
    def walk(items):
        for layer in items:
            yield layer
            if hasattr(layer, "layers"):
                yield from walk(layer.layers)

    normalizations = [
        l for l in walk(layers) if type(l).__name__ in ("Normalization", "Rescaling")
    ]
    if c["internal"]["mode"] is None and normalizations:
        raise InputContractError("UNDECLARED_INTERNAL_NORMALIZATION")
    if c["internal"]["mode"] == INTERNAL_DENSENET:
        if (
            len(normalizations) != 1
            or normalizations[0].name != "densenet_imagenet_normalization"
        ):
            raise InputContractError("DENSENET_NORMALIZATION_MISSING")
        import numpy as np

        layer = normalizations[0]
        if not np.allclose(
            layer.mean.numpy().reshape(-1), [0.485, 0.456, 0.406], rtol=0, atol=1e-7
        ) or not np.allclose(
            layer.variance.numpy().reshape(-1),
            np.square([0.229, 0.224, 0.225]),
            rtol=0,
            atol=1e-7,
        ):
            raise InputContractError("DENSENET_NORMALIZATION_CONFLICT")
    return c


def decode_rgb(contents):
    import tensorflow as tf

    return tf.cast(
        tf.io.decode_image(contents, channels=3, expand_animations=False), tf.float32
    )


def transform_rgb(image, contract):
    import tensorflow as tf

    from .preprocessing import apply_model_preprocessing

    c = validate_input_contract(contract)
    image = tf.convert_to_tensor(image)
    if image.shape.rank not in (3, 4) or image.shape[-1] != 3:
        raise InputContractError("SOURCE_RGB_SHAPE_INVALID")
    # Domain comes from the controlled decoder/contract, never pixel extrema.
    resized = tf.image.resize(
        tf.cast(image, tf.float32), c["shape"][1:3], method="bilinear", antialias=False
    )
    return apply_model_preprocessing(resized, c["external"]["mode"])


def transform_bytes(contents, contract):
    return transform_rgb(decode_rgb(contents), contract)
