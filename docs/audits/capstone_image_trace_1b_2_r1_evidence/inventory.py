"""Inventory only the synthetic audit; verify previous evidence without edits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent/'capstone_image_trace_1b_2_evidence'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


previous = json.loads((OLD/'inventory.json').read_text())
checks = []
for row in previous['files']:
    path = OLD/row['path']
    checks.append(dict(path=row['path'], passed=path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256']))
(ROOT/'original_integrity.json').write_text(json.dumps(dict(passed=all(c['passed'] for c in checks), total=len(checks), checks=checks), indent=2))
bench = json.loads((ROOT/'benchmark_source_hashes.json').read_text())
source_checks = {name: sha(ROOT/name) == value for name, value in bench['files'].items()}
archived_experiment_verified = sha(ROOT/'experiment_benchmarked.py') == bench['files']['experiment.py']
files = []
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or path.name in ('inventory.json', 'inventory.log'):
        continue
    files.append(dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=sha(path)))
result = dict(created_at=datetime.now(timezone.utc).isoformat(), files=files,
              total_bytes=sum(row['bytes'] for row in files), benchmark_sources_unchanged=source_checks, archived_benchmark_experiment_verified=archived_experiment_verified,
              source_change_note='Only the optional no-shuffle adapter signature was corrected after all 15 benchmark pairs. The exact measured experiment.py is archived as experiment_benchmarked.py.',
              original_evidence_unchanged=all(c['passed'] for c in checks),
              note='Final retained source/artifact hashes; not a retrospective claim of source hashes at earlier process launch.')
(ROOT/'inventory.json').write_text(json.dumps(result, indent=2, sort_keys=True))
print(json.dumps({k: v for k,v in result.items() if k != 'files'}, indent=2))
print('files', len(files))
