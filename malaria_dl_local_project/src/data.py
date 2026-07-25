"""Legacy adapter for canonical data loaders."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.data.loaders")
sys.modules[__name__] = _implementation
