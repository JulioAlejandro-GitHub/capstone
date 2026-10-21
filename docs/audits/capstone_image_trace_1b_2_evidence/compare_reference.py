"""Compare actual step arrays, including original gradients; no extra inference."""
import json
from pathlib import Path
import sys
import numpy as np
from compare import ATOL, RTOL
left,right,out=map(Path,sys.argv[1:])
checks=[]
lf=sorted(left.glob('reference_*.npz')); rf=sorted(right.glob('reference_*.npz'))
checks.append(dict(name='batch_sequence',passed=[p.name for p in lf]==[p.name for p in rf] and bool(lf)))
for a,b in zip(lf,rf):
    with np.load(a) as x,np.load(b) as y:
        checks.append(dict(name=a.name+'/keys',passed=x.files==y.files))
        for k in x.files:
            v,w=x[k],y[k]
            exact=k in ['x','y']
            passed=v.shape==w.shape and bool(np.all(np.isfinite(v)) and np.all(np.isfinite(w)))
            if passed: passed=bool(np.array_equal(v,w) if exact else np.all(np.abs(v-w)<=ATOL+RTOL*np.abs(v)))
            checks.append(dict(name=a.name+'/'+k,exact=exact,passed=passed,max_abs=float(np.max(np.abs(v-w)))))
result=dict(passed=all(c['passed'] for c in checks),total=len(checks),failed=sum(not c['passed'] for c in checks),checks=checks)
out.write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k!='checks'})

raise SystemExit(0 if result['passed'] else 1)
