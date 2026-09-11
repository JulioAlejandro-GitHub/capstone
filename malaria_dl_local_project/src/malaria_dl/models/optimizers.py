"""Lazy optimizer names, versioned explicit defaults and sole construction factory."""

from copy import deepcopy
import math

_COMMON = dict(
    weight_decay=None,
    clipnorm=None,
    global_clipnorm=None,
    clipvalue=None,
    use_ema=False,
    ema_momentum=0.99,
    ema_overwrite_frequency=None,
    loss_scale_factor=None,
    gradient_accumulation_steps=None,
)
OPTIMIZER_DEFAULTS = {
    "adam": dict(
        _COMMON,
        learning_rate=1e-4,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-7,
        amsgrad=False,
    ),
    "adamw": dict(
        _COMMON,
        learning_rate=1e-4,
        weight_decay=0.004,
        beta_1=0.9,
        beta_2=0.999,
        epsilon=1e-7,
        amsgrad=False,
    ),
    "sgd": dict(_COMMON, learning_rate=1e-4, momentum=0.9, nesterov=False),
    "adadelta": dict(_COMMON, learning_rate=1e-4, rho=0.95, epsilon=1e-7),
}
BATCH_LEARNING_RATES = {
    "adam": (1e-4, 1e-5),
    "adamw": (1e-4, 1e-5),
    "sgd": (1e-3, 1e-4),
    "adadelta": (1.0, 1.0),
}


def optimizer_config(name, overrides=None):
    if name not in OPTIMIZER_DEFAULTS:
        raise ValueError("UNKNOWN_OPTIMIZER:" + str(name))
    result = deepcopy(OPTIMIZER_DEFAULTS[name])
    for key, value in (overrides or {}).items():
        if key not in result:
            raise ValueError("INCOMPATIBLE_OPTIMIZER_PARAMETER:" + key)
        default = result[key]
        if isinstance(default, bool):
            if type(value) is not bool:
                raise ValueError("INVALID_OPTIMIZER_PARAMETER:" + key)
        elif value is not None:
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("INVALID_OPTIMIZER_PARAMETER:" + key)
            if (
                key
                in (
                    "learning_rate",
                    "epsilon",
                    "clipnorm",
                    "global_clipnorm",
                    "clipvalue",
                    "loss_scale_factor",
                )
                and value <= 0
            ):
                raise ValueError("INVALID_OPTIMIZER_PARAMETER:" + key)
            if (
                key in ("beta_1", "beta_2", "rho", "momentum", "ema_momentum")
                and value >= 1
            ):
                raise ValueError("INVALID_OPTIMIZER_PARAMETER:" + key)
        elif default is not None:
            raise ValueError("INVALID_OPTIMIZER_PARAMETER:" + key)
        result[key] = value
    if (
        sum(result[k] is not None for k in ("clipnorm", "global_clipnorm", "clipvalue"))
        > 1
    ):
        raise ValueError("INCOMPATIBLE_GRADIENT_CLIPPING")
    for key in ("ema_overwrite_frequency", "gradient_accumulation_steps"):
        value = result[key]
        if value is not None and (
            type(value) is not int
            or value < (2 if key == "gradient_accumulation_steps" else 1)
        ):
            raise ValueError("INVALID_OPTIMIZER_PARAMETER:" + key)
    if not result["use_ema"] and result["ema_overwrite_frequency"] is not None:
        raise ValueError("IGNORED_EMA_PARAMETER")
    return result


def build_optimizer(optimizer_name="adam", learning_rate=1e-4, *, config=None):
    import tensorflow as tf

    values = optimizer_config(
        optimizer_name,
        config if config is not None else {"learning_rate": learning_rate},
    )
    classes = dict(adam="Adam", adamw="AdamW", sgd="SGD", adadelta="Adadelta")
    return getattr(tf.keras.optimizers, classes[optimizer_name])(**values)
