"""Verify observed synthetic tokens and fault evidence, not a durable ledger."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import numpy as np
BASE=Path(__file__).resolve().parent
checks=[]
for name in ['b1','reference_b','vgg16_b','densenet121_b','vgg16_phases_b','densenet121_phases_b']:
    root=BASE/name
    if not (root/'receipts.json').exists(): continue
    rows=json.loads((root/'receipts.json').read_text())
    manifest=json.loads((root/'manifest.json').read_text())
    epochs=sum(r['kind']=='epoch' for r in json.loads((root/'records.json').read_text()))
    expected=[]
    for epoch in range(epochs):
        expected += [('weight_optimization',n) for n in [8,8,8,8,5]]
        expected += [('keras_validation',n) for n in [8,8,3]]
    checks.append(dict(name=name+'/completed_batch_sizes',passed=[(r['purpose'],len(r['tokens'])) for r in rows]==expected))
    for epoch in range(epochs):
        for purpose,split in [('weight_optimization','train'),('keras_validation','val')]:
            selected=[r for r in rows[epoch*8:(epoch+1)*8] if r['purpose']==purpose]
            tokens=[t for r in selected for t in r['tokens']]
            target=[i for i,e in enumerate(manifest) if e['path'].startswith(split+'/')]
            checks.append(dict(name=f'{name}/{epoch}/{purpose}/multiplicity',passed=Counter(tokens)==Counter(target)))
            checks.append(dict(name=f'{name}/{epoch}/{purpose}/labels',passed=all(manifest[t]['label']==int(y) for r in selected for t,y in zip(r['tokens'],r['labels']))))
    first=[t for r in rows[:5] for t in r['tokens']]
    second=[t for r in rows[8:13] for t in r['tokens']]
    checks.append(dict(name=name+'/shuffle_changes_between_epochs',passed=first!=second))
    if name=='reference_b':
        for row,path in zip(rows, sorted(root.glob('reference_*.npz'))):
            with np.load(path) as data:
                checks.append(dict(name=path.name+'/same_tensor_as_reference',passed=row['tensor_sha256']==hashlib.sha256(data['x'].tobytes()).hexdigest()))
    started=time.perf_counter()
    encoded=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    (root/'receipt_cost.json').write_text(json.dumps(dict(bytes=len(encoded),serialization_seconds=time.perf_counter()-started,
        note='One post-run serialization sample; no durable ledger or isolated aggregator memory measurement'),indent=2)+'\n')
for fault,count in [('before',0),('during',0),('after',1)]:
    root=BASE/f'fault_verified_{fault}_b'
    rows=json.loads((root/'receipts.json').read_text())
    checks.append(dict(name=f'fault_{fault}/confirmed_batches',passed=len(rows)==count))
result=dict(passed=all(c['passed'] for c in checks),checks=checks,
            limitations=['Epoch partition validated against completed original epoch records; logs lack explicit scope keys.',
                         'No durable replay/idempotence protocol implemented.',
                         'Zero confirmed receipts during failure means unknown consumption, not zero processing.'])
(BASE/'receipt_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('receipt checks:',result['passed'],len(checks))

raise SystemExit(0 if result['passed'] else 1)
