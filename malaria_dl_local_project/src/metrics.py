"""Legacy adapter for canonical clinical metrics."""
from importlib import import_module
_implementation = import_module("src.malaria_dl.evaluation.clinical_metrics")
__all__ = [name for name in vars(_implementation) if not name.startswith("_")]
globals().update({name: getattr(_implementation, name) for name in __all__})
