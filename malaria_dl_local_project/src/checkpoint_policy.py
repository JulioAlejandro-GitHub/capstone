"""Legacy adapter for canonical checkpoint policy."""
from importlib import import_module
_implementation = import_module("src.malaria_dl.training.checkpoint_policy")
__all__ = [name for name in vars(_implementation) if not name.startswith("_")]
globals().update({name: getattr(_implementation, name) for name in __all__})
