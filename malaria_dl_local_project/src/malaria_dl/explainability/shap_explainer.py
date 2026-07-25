"""SHAP implementation loaded only when requested by the pipeline."""
from .pipeline import explain_with_shap
__all__ = ["explain_with_shap"]
