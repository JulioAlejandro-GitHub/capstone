"""Canonical evaluation command-line entry point."""
from src.malaria_dl.evaluation.evaluator import main, parse_args
__all__ = ["main", "parse_args"]
if __name__ == "__main__":
    main()

