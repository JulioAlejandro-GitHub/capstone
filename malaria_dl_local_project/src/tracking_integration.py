"""Legacy adapter for canonical tracking integration."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.persistence.tracking")
sys.modules[__name__] = _implementation
