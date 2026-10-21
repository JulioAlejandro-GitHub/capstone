"""Final retained artifacts; exclude self-referential output and its console log."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

files=[]
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or path.name in ('inventory.json','inventory.log'):
        continue
    files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
report=ROOT.parent/'capstone_image_trace_1b_2_r2_metal.md'
result=dict(created_at=datetime.now(timezone.utc).isoformat(),files=files,
    total_bytes=sum(r['bytes'] for r in files),report=dict(path=str(report),bytes=report.stat().st_size,sha256=sha(report)),
    note='Final artifacts; premeasurement source/command hashes are recorded separately in campaign seals. No retrospective source-timestamp claims.')
with (ROOT/'inventory.json').open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True)
print('files',len(files),'bytes',result['total_bytes'],'report_sha256',result['report']['sha256'])
