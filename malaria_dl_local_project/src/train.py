"""Legacy training CLI and import compatibility adapter."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.training.trainer")
__all__ = [name for name in vars(_implementation) if not name.startswith("__")]
if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
