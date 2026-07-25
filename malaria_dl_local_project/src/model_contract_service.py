"""Legacy adapter for the canonical model contract service."""
from importlib import import_module
_implementation = import_module("src.malaria_dl.governance.services.contract_service")
__all__ = [name for name in vars(_implementation) if not name.startswith("__")]
globals().update({name: getattr(_implementation, name) for name in __all__})
