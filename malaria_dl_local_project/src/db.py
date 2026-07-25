"""Legacy adapter for canonical database access."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.persistence.database")
sys.modules[__name__] = _implementation
