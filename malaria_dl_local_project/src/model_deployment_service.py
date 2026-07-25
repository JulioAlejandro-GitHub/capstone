"""Legacy adapter for the canonical deployment service."""
from importlib import import_module
_implementation = import_module("src.malaria_dl.governance.services.deployment_service")
__all__ = [name for name in vars(_implementation) if not name.startswith("__")]
globals().update({name: getattr(_implementation, name) for name in __all__})
