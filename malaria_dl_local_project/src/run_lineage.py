"""Legacy adapter for canonical run lineage."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.persistence.lineage")
sys.modules[__name__] = _implementation
