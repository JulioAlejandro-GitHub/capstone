"""Compare observed initial and restored weights/optimizer, no inference."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
checks = []
for arch in ['custom_cnn', 'vgg16', 'densenet121']:
    left, right = ROOT/f'{arch}_state_a', ROOT/f'{arch}_state_b'
    files = sorted(left.glob('state_*.npz'))
    checks.append(dict(architecture=arch, name='states_present', passed=bool(files) and [p.name for p in files] == sorted(p.name for p in right.glob('state_*.npz'))))
    for path in files:
        with np.load(path) as a, np.load(right/path.name) as b:
            checks.append(dict(architecture=arch, name=path.name+'/keys', passed=a.files == b.files))
            for key in a.files:
                x, y = a[key], b[key]
                passed = x.shape == y.shape and np.isfinite(x).all() and np.isfinite(y).all()
                if passed:
                    passed = bool(np.all(np.abs(x-y) <= 1e-7 + 1e-6*np.abs(x)))
                checks.append(dict(architecture=arch, name=path.name+'/'+key, passed=bool(passed),
                                   max_abs=float(np.max(np.abs(x-y))) if x.shape == y.shape else None))
    for arm, folder in [('a',left), ('b',right)]:
        for phase in (['base'] if arch == 'custom_cnn' else ['base','fine_tuning']):
            best = folder/f'state_{phase}_early_stopping_best.npz'
            after = folder/f'state_{phase}_after_fit_and_restore.npz'
            checks.append(dict(architecture=arch, name=f'{arm}/{phase}/best_weights_present', passed=best.exists()))
            if best.exists():
                with np.load(best) as a, np.load(after) as b:
                    for key in a.files:
                        x,y=a[key],b[key]
                        checks.append(dict(architecture=arch, name=f'{arm}/{phase}/restored/{key}',
                            passed=bool(x.shape==y.shape and np.all(np.abs(x-y)<=1e-7+1e-6*np.abs(x))),
                            max_abs=float(np.max(np.abs(x-y)))))
result = dict(passed=all(c['passed'] for c in checks), total=len(checks), failed=sum(not c['passed'] for c in checks), checks=checks)
(ROOT/'state_comparison.json').write_text(json.dumps(result, indent=2))
print({k: v for k,v in result.items() if k != 'checks'})

raise SystemExit(0 if result['passed'] else 1)
