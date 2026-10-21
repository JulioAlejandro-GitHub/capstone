"""Inventory generated audit evidence only; never scans clinical datasets."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
files=[]
for path in sorted(BASE.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or path.name=='inventory.json': continue
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    files.append(dict(path=path.relative_to(BASE).as_posix(),bytes=path.stat().st_size,sha256=digest.hexdigest()))
outcomes={p.parent.name:json.loads(p.read_text())['status'] for p in BASE.glob('*/outcome.json')}
comparisons={p.name:{k:v for k,v in json.loads(p.read_text()).items() if k in ['passed','failed','total']}
             for p in BASE.glob('*comparison.json')}
result=dict(created_at=datetime.now(timezone.utc).isoformat(),files=files,total_bytes=sum(f['bytes'] for f in files),
            outcomes=outcomes,comparisons=comparisons,
            note='Hashes describe final retained artifacts and final harness, not a retrospective source hash at process launch.')
(BASE/'inventory.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(len(files),'files;',result['total_bytes'],'bytes;',len(outcomes),'process outcomes')
