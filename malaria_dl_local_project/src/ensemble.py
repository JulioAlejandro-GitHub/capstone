"""Legacy adapter for ensemble inference CLI."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.inference.ensemble")
if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
