"""Verify historical artifacts without changing their inventories or caches."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

stage=sys.argv[1]
results={}
for name in ['capstone_image_trace_1b_2_evidence','capstone_image_trace_1b_2_r1_evidence']:
    folder=ROOT.parent/name
    inventory=json.loads((folder/'inventory.json').read_text())
    checks=[]
    for row in inventory['files']:
        p=folder/row['path']
        checks.append(dict(path=row['path'],passed=p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']))
    results[name]=dict(passed=all(r['passed'] for r in checks),checks=checks,
        inventory_sha256=sha(folder/'inventory.json'),total=len(checks))
with (ROOT/f'historical_integrity_{stage}.json').open('x') as f:
    json.dump(dict(utc=datetime.now(timezone.utc).isoformat(),results=results),f,indent=2)
print({k:(v['passed'],v['total']) for k,v in results.items()})
assert all(v['passed'] for v in results.values())
