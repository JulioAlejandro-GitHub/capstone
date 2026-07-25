"""Canonical single-image inference command-line entry point."""
from src.malaria_dl.inference.predictor import main, parse_args, run_clinical_inference
__all__ = ["main", "parse_args", "run_clinical_inference"]
if __name__ == "__main__":
    main()

