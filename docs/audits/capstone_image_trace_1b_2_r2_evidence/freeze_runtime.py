"""Record operational and installed implementation hashes before later campaigns."""
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
project=ROOT/'malaria_dl_local_project'
paths=list((project/'src').rglob('*.py'))
site=project/'.venv-metal/lib/python3.12/site-packages'
paths += [site/p for p in [
    'keras/src/backend/tensorflow/trainer.py','keras/src/utils/image_dataset_utils.py',
    'tensorflow/python/eager/polymorphic_function/polymorphic_function.py']]
result=dict(utc=datetime.now(timezone.utc).isoformat(),files={str(p.relative_to(ROOT)):
    hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})
with (HERE/(sys.argv[1]+'_runtime_sources.json')).open('x') as stream:
    json.dump(result,stream,indent=2)
print('runtime source hashes',len(paths))
