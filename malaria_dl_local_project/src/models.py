"""Legacy adapter for canonical model architectures."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.models.architectures")
sys.modules[__name__] = _implementation
