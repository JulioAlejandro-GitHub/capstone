"""Correct positional loader adapter; failed initial control remains preserved."""
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2]/'malaria_dl_local_project'))
from src.malaria_dl.data import loaders
arm = sys.argv[1]
OUT = ROOT/f'no-shuffle_verified_{arm}'
original = loaders.make_image_dataset_from_directory


def load(directory, img_size, batch_size, shuffle, seed=42):
    return original(directory, img_size, batch_size, False, seed=seed)


sys.argv = ['experiment.py', str(OUT), '--deterministic', '--reference']
if arm == 'b':
    sys.argv += ['--observer']
with patch.object(loaders, 'make_image_dataset_from_directory', load):
    runpy.run_path(str(ROOT/'experiment.py'), run_name='__main__')
(OUT/'control.json').write_text(json.dumps(dict(shuffle=False, adapter='no_shuffle_control.py'), indent=2))
