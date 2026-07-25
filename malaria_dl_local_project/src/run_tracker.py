"""Legacy adapter for the canonical run repository."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.persistence.run_repository")
sys.modules[__name__] = _implementation
