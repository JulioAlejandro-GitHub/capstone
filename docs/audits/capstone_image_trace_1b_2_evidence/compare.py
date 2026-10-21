"""Compare saved A/A evidence without inference. Tolerances fixed before B."""
import argparse
import io
import json
from pathlib import Path
import zipfile
import h5py
import numpy as np

ATOL, RTOL = 1e-7, 1e-6


def compare(left, right):
    checks = []
    def numeric(name, a, b):
        a, b = np.asarray(a), np.asarray(b)
        same_shape = a.shape == b.shape
        finite = bool(np.all(np.isfinite(a)) and np.all(np.isfinite(b)))
        passed = same_shape and finite and bool(np.all(np.abs(a-b) <= ATOL + RTOL*np.abs(a)))
        checks.append(dict(name=name, passed=passed,
                           max_abs=float(np.max(np.abs(a-b))) if same_shape and a.size else None))
    def tree(name, a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            checks.append(dict(name=name+'/keys', passed=a.keys()==b.keys()))
            for k in a.keys() & b.keys(): tree(name+'/'+k, a[k], b[k])
        elif isinstance(a, list) and isinstance(b, list):
            checks.append(dict(name=name+'/length', passed=len(a)==len(b)))
            for i, (x,y) in enumerate(zip(a,b)): tree(name+'/'+str(i), x,y)
        elif isinstance(a, (float,int)) and not isinstance(a,bool) and isinstance(b,(float,int)):
            if isinstance(a,int) and isinstance(b,int): checks.append(dict(name=name, passed=a==b))
            else: numeric(name,a,b)
        else: checks.append(dict(name=name, passed=a==b))
    for file in ['manifest.json','configuration.json']:
        checks.append(dict(name=file, passed=(left/file).read_bytes()==(right/file).read_bytes()))
    for kind in ['epoch','phase','selection','predictions','calibration']:
        rows=[]
        for folder in [left,right]:
            rows.append([r for r in json.loads((folder/'records.json').read_text()) if r['kind']==kind])
        tree(kind,*rows)
    def arrays(path):
        with zipfile.ZipFile(path) as z:
            with h5py.File(io.BytesIO(z.read('model.weights.h5'))) as f:
                result={}
                def visit(name,obj):
                    if isinstance(obj,h5py.Dataset): result[name]=obj[()]
                f.visititems(visit)
                return result
    files = sorted((left/'checkpoints').glob('*.keras'))
    checks.append(dict(name='checkpoint_names', passed=[p.name for p in files]==sorted(p.name for p in (right/'checkpoints').glob('*.keras'))))
    for p in files:
        if not (right/'checkpoints'/p.name).exists(): continue
        a,b=arrays(p),arrays(right/'checkpoints'/p.name)
        checks.append(dict(name=p.name+'/variables', passed=a.keys()==b.keys()))
        for key in a.keys() & b.keys(): numeric(p.name+'/'+key,a[key],b[key])
    return dict(atol=ATOL,rtol=RTOL,passed=all(c['passed'] for c in checks),checks=checks,
                failed=sum(not c['passed'] for c in checks), total=len(checks))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('left',type=Path); p.add_argument('right',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); result=compare(a.left,a.right)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))

    raise SystemExit(0 if result['passed'] else 1)
