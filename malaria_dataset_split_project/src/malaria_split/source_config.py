"""SOURCE is provenance; ROOT is local storage. No database or ML imports."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
CELL_SOURCE = 'https://data.lhncbc.nlm.nih.gov/public/Malaria/cell_images.zip'
SMEAR_SOURCE = 'https://data.lhncbc.nlm.nih.gov/public/Malaria/NIH-NLM-ThinBloodSmearsPf/index.html'
SMEAR_ROOT = 'malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf'
CURRENT_SPLIT_ROOT = 'malaria_dl_local_project/data/malaria_physical_split'


@dataclass(frozen=True)
class SourceConfig:
    cell_source: str
    smear_source: str
    smear_root: Path
    current_split_root: Path


def resolve_source_config(
    root: str | Path | None = None, *, capstone_root: Path = CAPSTONE_ROOT,
    environ: Mapping[str, str] | None = None,
    current_split_default: str = CURRENT_SPLIT_ROOT,
) -> SourceConfig:
    """CLI root > process environment > optional existing .env > official defaults."""
    values: dict[str, str] = {}
    env_file = capstone_root / 'malaria_dataset_split_project/.env'
    if env_file.is_file():
        from dotenv import dotenv_values
        values.update({k: v for k, v in dotenv_values(env_file, interpolate=False).items() if v})
    values.update({k: v for k, v in (os.environ if environ is None else environ).items() if v})

    def local_path(value: str | Path) -> Path:
        path = Path(value).expanduser()
        return (path if path.is_absolute() else capstone_root / path).absolute()

    return SourceConfig(
        cell_source=values.get('MALARIA_CELL_DATASET_SOURCE', CELL_SOURCE),
        smear_source=values.get('THIN_BLOOD_SMEARS_PF_SOURCE', SMEAR_SOURCE),
        smear_root=local_path(root or values.get('THIN_BLOOD_SMEARS_PF_ROOT', SMEAR_ROOT)),
        current_split_root=local_path(values.get('MALARIA_CURRENT_SPLIT_ROOT', current_split_default)),
    )
