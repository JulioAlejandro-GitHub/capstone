"""Legacy adapter for image quality control."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.data.quality_control")
sys.modules[__name__] = _implementation
