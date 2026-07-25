"""Canonical explainability command-line entry point."""
from src.malaria_dl.explainability.pipeline import main, parse_args
__all__ = ["main", "parse_args"]
if __name__ == "__main__":
    main()

