"""Uniform uncompiled builds. The common engine compiles once per phase."""

from dataclasses import dataclass


@dataclass
class AdapterResult:
    model: object
    backbone: object | None
    input_contract: dict
    output_contract: dict
    phases: tuple[str, ...]
    serialization: str = "keras_v3"

    def trainable_layers(self):
        layers = (
            self.backbone.layers if self.backbone is not None else self.model.layers
        )
        return [layer.name for layer in layers if layer.trainable]


class BaseAdapter:
    def build(self, config):
        raise NotImplementedError

    def set_phase(self, built, config, phase):
        if phase not in built.phases:
            raise ValueError("UNSUPPORTED_PHASE:" + phase)
        if built.backbone is not None:
            layers = built.backbone.layers
            count = config["model"]["fine_tune_layers"] if phase == "fine_tuning" else 0
            if count > len(layers):
                raise ValueError("FINE_TUNE_LAYERS_EXCEED_BACKBONE")
            for index, layer in enumerate(layers):
                layer.trainable = index >= len(layers) - count
        return built.trainable_layers()

    def result(self, model, backbone, config):
        return AdapterResult(
            model,
            backbone,
            dict(
                shape=config["model"]["input_shape"],
                preprocessing=config["model"]["preprocessing"],
                dtype="float32",
            ),
            dict(
                shape=[None, 1], activation="sigmoid", meaning="probability_parasitized"
            ),
            ("base", "fine_tuning") if backbone is not None else ("base",),
        )


class CustomCNNAdapter(BaseAdapter):
    def build(self, config):
        from .architectures import build_custom_cnn

        m = config["model"]
        model = build_custom_cnn(
            input_shape=tuple(m["input_shape"]),
            l2_weight=m["l2"],
            dropout_rate=m["dropout"],
            compile_model=False,
        )
        return self.result(model, None, config)


class VGG16Adapter(BaseAdapter):
    def build(self, config):
        from .architectures import build_vgg16_transfer

        m = config["model"]
        model, base = build_vgg16_transfer(
            input_shape=tuple(m["input_shape"]),
            weights=None if m["weights"] == "none" else m["weights"],
            dropout_rate=m["dropout"],
            compile_model=False,
        )
        return self.result(model, base, config)


class DenseNet121Adapter(BaseAdapter):
    def build(self, config):
        from .architectures import build_densenet121_transfer

        m = config["model"]
        model, base = build_densenet121_transfer(
            input_shape=tuple(m["input_shape"]),
            weights=None if m["weights"] == "none" else m["weights"],
            dropout_rate=m["dropout"],
            compile_model=False,
        )
        return self.result(model, base, config)


def compile_phase(adapter, built, resolved, phase):
    from .architectures import compile_binary_model
    from copy import deepcopy

    expected_shape = (None, *resolved["model"]["input_shape"])
    if built.model.input_shape != expected_shape or built.model.output_shape != (
        None,
        1,
    ):
        raise ValueError("ADAPTER_SIGNATURE_MISMATCH")
    if getattr(built.model.layers[-1].activation, "__name__", None) != "sigmoid":
        raise ValueError("ADAPTER_OUTPUT_CONTRACT_MISMATCH")
    if phase == "base" and getattr(built.model, "optimizer", None) is not None:
        raise ValueError("ADAPTER_MUST_RETURN_UNCOMPILED_MODEL")
    layers = adapter.set_phase(built, resolved, phase)
    options = deepcopy(resolved["optimizer"]["parameters"])
    if phase == "fine_tuning":
        options["learning_rate"] = resolved["optimizer"]["fine_tune_learning_rate"]
    compile_binary_model(
        built.model,
        optimizer_name=resolved["optimizer"]["name"],
        optimizer_config=options,
    )
    runtime = built.model.optimizer.get_config()
    # Every version-specific default (including Keras extras) is recorded below.
    for key, expected in options.items():
        actual = runtime.get(key)
        if isinstance(expected, float):
            import math

            equal = isinstance(actual, (int, float)) and math.isclose(
                actual, expected, rel_tol=1e-6, abs_tol=1e-12
            )
        else:
            equal = actual == expected
        if not equal:
            raise ValueError("OPTIMIZER_RUNTIME_MISMATCH:" + key)
    return dict(
        phase=phase,
        trainable_layers=layers,
        optimizer=runtime,
        optimizer_class=type(built.model.optimizer).__name__,
        loss=built.model.loss.get_config(),
        optimizer_state="new; reset at phase transition",
        input_contract=built.input_contract,
        output_contract=built.output_contract,
        architecture=built.model.get_config(),
        compile=built.model.get_compile_config(),
    )
