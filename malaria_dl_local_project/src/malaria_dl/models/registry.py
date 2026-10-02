"""Single, lazy registry for TRAIN discovery, validation and adapter resolution."""

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import re


@dataclass(frozen=True)
class ModelDescriptor:
    id: str
    aliases: tuple[str, ...]
    enabled: bool
    trainable: bool
    version: str
    adapter: str
    config_path: str
    input_contract: str
    output_contract: str
    strategies: tuple[str, ...]
    optimizers: tuple[str, ...]
    internal_preprocessing: str | None = None
    preprocessing_modes: tuple[str, ...] = ("rescale_0_1",)
    default_preprocessing: str = "rescale_0_1"

    def create_adapter(self):
        module, symbol = self.adapter.split(":")
        return getattr(import_module(module), symbol)()


MODEL_REGISTRY: dict[str, ModelDescriptor] = {}


def register(descriptor):
    from .optimizers import OPTIMIZER_DEFAULTS

    if not isinstance(descriptor, ModelDescriptor):
        raise ValueError("MODEL_DESCRIPTOR_REQUIRED")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", descriptor.id):
        raise ValueError("INVALID_MODEL_ID")
    if type(descriptor.enabled) is not bool or type(descriptor.trainable) is not bool:
        raise ValueError("INVALID_MODEL_CAPABILITY")
    if (
        not descriptor.version
        or not re.fullmatch(
            r"[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*", descriptor.adapter
        )
        or not Path(descriptor.config_path).is_file()
        or not descriptor.input_contract
        or not descriptor.output_contract
        or not descriptor.strategies
        or not descriptor.optimizers
        or not set(descriptor.optimizers).issubset(OPTIMIZER_DEFAULTS)
    ):
        raise ValueError("INCOMPLETE_MODEL_DESCRIPTOR")
    names = (descriptor.id, *descriptor.aliases)
    occupied = {name for d in MODEL_REGISTRY.values() for name in (d.id, *d.aliases)}
    if (
        any(not isinstance(n, str) or not n for n in names)
        or len(set(names)) != len(names)
        or occupied.intersection(names)
    ):
        raise ValueError("DUPLICATE_MODEL_ID_OR_AMBIGUOUS_ALIAS")
    MODEL_REGISTRY[descriptor.id] = descriptor


def model_catalog():
    """Rows of public.models: the only source of which models exist and their catalog metadata."""
    from sqlalchemy import text
    from ..campaigns.repository import connection_scope

    with connection_scope(readonly=True) as c:
        return tuple(
            dict(row)
            for row in c.execute(
                text(
                    "SELECT name, architecture, model_type, framework "
                    "FROM public.models ORDER BY name"
                )
            ).mappings()
        )


def registered_models():
    """Model names from the catalog (public.models), not the Python implementations."""
    return tuple(m["name"] for m in model_catalog())


def resolve_descriptor(name, *, executable=True):
    # public.models decides existence; MODEL_REGISTRY only says how Python implements it.
    matches = [d for d in MODEL_REGISTRY.values() if name in (d.id, *d.aliases)]
    if len(matches) > 1:
        raise ValueError("UNKNOWN_OR_AMBIGUOUS_MODEL:" + str(name))
    if (matches[0].id if matches else name) not in registered_models():
        raise ValueError("MODEL_NOT_REGISTERED:" + str(name))
    if not matches:
        raise ValueError("IMPLEMENTATION_NOT_AVAILABLE:" + str(name))
    descriptor = matches[0]
    if executable and not (descriptor.enabled and descriptor.trainable):
        raise ValueError("MODEL_NOT_EXECUTABLE:" + str(name))
    return descriptor


def enabled_models():
    # No implementation filter: a registered model without one fails in resolve_descriptor.
    return registered_models()


def model_arg(name):
    import argparse

    try:
        return resolve_descriptor(name).id
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


from .optimizers import OPTIMIZER_DEFAULTS

_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "models"
# Python implementations only: which models exist is decided by public.models.
for _id, _aliases, _adapter, _strategies, _internal in (
    ("custom_cnn", (), "CustomCNNAdapter", ("base",), None),
    (
        "vgg16",
        ("vgg16_transfer_learning",),
        "VGG16Adapter",
        ("base", "fine_tuning"),
        None,
    ),
    (
        "densenet121",
        (),
        "DenseNet121Adapter",
        ("base", "fine_tuning"),
        "densenet_imagenet_channel_mean_std",
    ),
):
    register(
        ModelDescriptor(
            _id,
            _aliases,
            True,
            True,
            "1.1" if _id == "vgg16" else "1.0",
            "src.malaria_dl.models.adapters:" + _adapter,
            str(_CONFIG / (_id + ".json")),
            "float32 RGB NHWC; explicit external preprocessing",
            "sigmoid probability_parasitized; uninfected=0, parasitized=1",
            _strategies,
            tuple(OPTIMIZER_DEFAULTS),
            _internal,
            ("vgg16_imagenet",) if _id == "vgg16" else ("rescale_0_1",),
            "vgg16_imagenet" if _id == "vgg16" else "rescale_0_1",
        )
    )
