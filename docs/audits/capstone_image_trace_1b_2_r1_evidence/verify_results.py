"""Read-only verification of actual receipts, fixture identities and diagnostics."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from ledger import Store, digest

ROOT = Path(__file__).resolve().parent
checks = []


def check(name, passed, **details):
    checks.append(dict(name=name, passed=bool(passed), **details))


for output in sorted(ROOT.iterdir()):
    if not output.is_dir() or not (output/'observer_summary.json').exists():
        continue
    manifest = json.loads((output/'token_manifest.json').read_text())
    expected_hash = digest(manifest)
    seen = set()
    for token, row in enumerate(manifest):
        identity = (row['dataset_version'], row['materialization'], row['split'], row['path'], row['source_record'])
        check(f'{output.name}/identity/{token}', identity not in seen and
              hashlib.sha256((output/'fixture'/row['path']).read_bytes()).hexdigest() == row['sha256'])
        seen.add(identity)
    verified = Store(output/'journal').verify()
    check(f'{output.name}/integrity', verified['events'] == json.loads((output/'observer_summary.json').read_text())['events'])
    scopes = {}
    for folder in (output/'journal').iterdir():
        if not folder.is_dir():
            continue
        events = [json.loads(p.read_text()) for p in sorted(folder.glob('*.json'))]
        if not events:
            continue
        scope = events[0]['scope']
        batches = [batch for event in events if event['record_type'] == 'consumption_block' for batch in event['batches']]
        split = 'train' if scope['usage_purpose'] == 'weight_optimization' else 'val'
        tokens = [t for batch in batches for t in batch]
        check(f'{output.name}/{folder.name}/manifest', scope['manifest_sha256'] == expected_hash)
        check(f'{output.name}/{folder.name}/split', all(0 <= t < len(manifest) and manifest[t]['split'] == split for t in tokens))
        if events[-1]['record_type'] == 'scope_close' and events[-1]['exhaustive']:
            check(f'{output.name}/{folder.name}/population', Counter(tokens) == Counter(i for i, row in enumerate(manifest) if row['split'] == split))
            check(f'{output.name}/{folder.name}/tail', [len(batch) for batch in batches] == ([8,8,8,8,5] if split == 'train' else [8,8,3]))
        scopes[(scope['phase'], scope['epoch_local'], split)] = batches
        if scope['phase'] == 'fine_tuning':
            check(f'{output.name}/{folder.name}/epoch_offset', scope['epoch_global'] == scope['epoch_local'] + 2)
    for phase in ('base', 'fine_tuning'):
        a, b = scopes.get((phase, 1, 'train')), scopes.get((phase, 2, 'train'))
        if a and b:
            if output.name.startswith('no-shuffle'):
                check(f'{output.name}/{phase}/no_shuffle', a == b)
            else:
                check(f'{output.name}/{phase}/shuffle_changes', a != b)
    diagnostic = sorted(output.glob('reference_*.npz'))
    if diagnostic:
        for phase in ('base', 'fine_tuning'):
            for split, purpose in [('train', 'weight_optimization'), ('val', 'keras_validation')]:
                npzs = sorted(output.glob(f'reference_{phase}_*_{split}.npz'))
                receipt_batches = [batch for epoch in range(1, 4) for batch in scopes.get((phase, epoch, split), [])]
                if npzs:
                    check(f'{output.name}/{phase}/{split}/diagnostic_count', len(npzs) == len(receipt_batches))
                    for path, batch in zip(npzs, receipt_batches):
                        with np.load(path) as arrays:
                            check(f'{output.name}/{path.name}/tokens', arrays['tokens'].tolist() == batch)
                            check(f'{output.name}/{path.name}/labels', arrays['y'].tolist() == [manifest[t]['label'] for t in batch])
    if output.name == 'duplicate_b':
        hashes = Counter(row['sha256'] for row in manifest)
        check('duplicate_bytes_distinct_records', max(hashes.values()) == 2 and len(seen) == 56)

for fault, expected in [('before', 0), ('during', 0), ('after', 1)]:
    path = ROOT/f'fault_{fault}_b'/'observer_summary.json'
    if path.exists():
        result = json.loads(path.read_text())
        check(f'fault/{fault}', result['batches'] == expected and result['partial'] == 1)
unresolved = ROOT/'unresolved'/'outcome.json'
if unresolved.exists():
    failure = json.loads(unresolved.read_text())
    check('unresolved_identity_rejected', failure['status'] == 'ERROR' and
          any(marker in failure['error'] for marker in ['assert_greater_equal', 'GreaterEqual', 'Condition x >= y']))
result = dict(passed=all(row['passed'] for row in checks), checks=checks,
              total=len(checks), failed=sum(not row['passed'] for row in checks))
(ROOT/'receipt_verification.json').write_text(json.dumps(result, indent=2))
print({k: v for k, v in result.items() if k != 'checks'})

raise SystemExit(0 if result['passed'] else 1)
