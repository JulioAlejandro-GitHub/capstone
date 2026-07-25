"""Legacy adapter for test-time augmentation CLI."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.inference.tta")
if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
