"""Lazy command line and historical import compatibility."""
if __name__ == '__main__':
    from src.malaria_dl.training.cli import main
    main()
else:
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module('src.malaria_dl.training.trainer')
