"""Grad-CAM implementation exports."""
from .pipeline import explain_with_gradcam, find_last_conv_layer
__all__ = ["explain_with_gradcam", "find_last_conv_layer"]

