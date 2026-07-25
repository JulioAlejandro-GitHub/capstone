"""Stable registry of supported model architecture names."""
from .architectures import (
    build_custom_cnn,
    build_densenet121_transfer,
    build_vgg16_transfer,
)
MODEL_REGISTRY = {
    "custom_cnn": build_custom_cnn,
    "vgg16": build_vgg16_transfer,
    "densenet121": build_densenet121_transfer,
}
__all__ = ["MODEL_REGISTRY"]

