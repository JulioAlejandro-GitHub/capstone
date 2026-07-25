"""Legacy adapter for SVM feature extraction."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.feature_engineering.svm_features")
if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
