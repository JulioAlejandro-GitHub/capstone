"""LIME implementation loaded only when requested by the pipeline."""
from .pipeline import explain_with_lime
__all__ = ["explain_with_lime"]

