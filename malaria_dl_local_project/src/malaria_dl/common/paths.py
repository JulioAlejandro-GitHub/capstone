"""Stable project paths independent from the importing module depth."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RELEASES_DIR = PROJECT_ROOT / "releases"
DB_DIR = PROJECT_ROOT / "db"

__all__ = ["PROJECT_ROOT", "DATA_DIR", "OUTPUT_DIR", "RELEASES_DIR", "DB_DIR"]

