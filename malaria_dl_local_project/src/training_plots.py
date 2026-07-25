"""Legacy adapter for canonical training plots."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.training.plots")
sys.modules[__name__] = _implementation
