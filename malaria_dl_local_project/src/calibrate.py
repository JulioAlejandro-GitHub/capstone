"""Legacy probability/threshold calibration CLI adapter."""
from importlib import import_module
_implementation = import_module("src.malaria_dl.evaluation.calibration_cli")
__all__ = [name for name in vars(_implementation) if not name.startswith("__")]
globals().update({name: getattr(_implementation, name) for name in __all__})
if __name__ == "__main__":
    _implementation.main()
