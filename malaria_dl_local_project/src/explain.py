"""Public EXEC.1 CLI, with historical import compatibility."""
if __name__ == "__main__":
    from src.malaria_dl.assessment.cli import main
    raise SystemExit(main("explain"))
else:
    from importlib import import_module
    _implementation = import_module("src.malaria_dl.explainability.pipeline")
    __all__ = [name for name in vars(_implementation) if not name.startswith("__")]
    globals().update({name: getattr(_implementation, name) for name in __all__})
