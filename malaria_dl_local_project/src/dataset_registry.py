"""Legacy adapter for the canonical dataset registry."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.data.registry")
sys.modules[__name__] = _implementation
