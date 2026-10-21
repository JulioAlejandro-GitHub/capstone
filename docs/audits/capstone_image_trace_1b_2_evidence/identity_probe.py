"""Negative synthetic identity tests; no model or inference."""
import json
from pathlib import Path
import sys
import tensorflow as tf
from observer import Observer
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parents[2]/'malaria_dl_local_project'))
if not tf.config.list_physical_devices('GPU'): raise RuntimeError('METAL_UNAVAILABLE')
source=BASE/'b1'
manifest=json.loads((source/'manifest.json').read_text())
fixture=BASE/'identity_fixture'
fixture.mkdir(exist_ok=False)
original=manifest[0]
content=(source/'fixture'/original['path']).read_bytes()
entries=[]
for name in ['one.png','other.png']:
    (fixture/name).write_bytes(content)
    entries.append({**original,'path':name})
checks=[]
try:
    Observer(fixture,entries,BASE)
except ValueError as e:
    checks.append(dict(case='distinct_paths_identical_tensor',passed=str(e)=='AMBIGUOUS_SYNTHETIC_IDENTITY',error=str(e)))
else: checks.append(dict(case='distinct_paths_identical_tensor',passed=False))
observer=Observer(source/'fixture',manifest,BASE)
unknown=tf.data.Dataset.from_tensors((tf.zeros((1,32,32,3)),tf.zeros((1,))))
try:
    next(iter(observer.preprocess(unknown,'rescale_0_1')))
except tf.errors.InvalidArgumentError:
    checks.append(dict(case='unmapped_input',passed=not observer.rows))
else: checks.append(dict(case='unmapped_input',passed=False))
from src.malaria_dl.data import loaders
raw=loaders.make_image_dataset_from_directory(source/'fixture'/'train',32,8,True,42)
prepared=observer.preprocess(raw,'rescale_0_1',augment=False)
next(iter(prepared))  # Explicit preparation-only control; never passed to Keras.
checks.append(dict(case='prefetch_preparation_without_scientific_step',
                   passed=int(observer.prepared.size().numpy())>0 and not observer.rows,
                   prepared_entries=int(observer.prepared.size().numpy()),confirmed_batches=len(observer.rows)))
(BASE/'identity_verification.json').write_text(json.dumps(dict(passed=all(c['passed'] for c in checks),checks=checks),indent=2)+'\n')
print(checks)

raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
