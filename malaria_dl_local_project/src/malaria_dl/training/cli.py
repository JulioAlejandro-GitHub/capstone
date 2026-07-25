"""Canonical training command-line entry point."""
from src.malaria_dl.training.trainer import main, parse_args
__all__ = ["main", "parse_args"]
if __name__ == "__main__":
    main()

