"""Compose stdin: metadata and terminal checkpoint bytes only; no TRAIN or writes."""
import datetime
import json
from pathlib import Path
from contextlib import contextmanager
from src.malaria_dl.data.governed_dataset import dataset_read_connection
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.execution.artifacts import file_identity

out = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
out["resources"] = {}
for name in ("memory.events", "memory.current", "memory.max", "memory.swap.current"):
    out["resources"][name] = (Path('/sys/fs/cgroup') / name).read_text()
out["attempts"] = []
with dataset_read_connection() as connection:
    @contextmanager
    def scope(readonly=False):
        assert readonly
        yield connection
    repo = ExecutionRepository(scope)
    campaign = repo.get('3acf89b7-dc42-4b7a-8e2a-ca6ea024c344')
    for attempt in campaign['attempts']:
        session = repo.session(attempt['training_run_id'])
        entry = {"run_id": str(session['run_id']), "state": session['state']}
        if session['state'] == 'active':
            entry['checkpoints'] = 'deferred: active writer'
            entry['processes'] = []
            for role in ('parent_pid', 'child_pid'):
                pid = session[role]
                process = {"role": role, "pid": pid}
                try:
                    root = Path('/proc') / str(pid)
                    stat = (root / 'stat').read_text().rsplit(')', 1)[1].split()
                    process.update(state=stat[0], utime=stat[11], stime=stat[12], start_ticks=stat[19])
                    process['memory'] = [x for x in (root/'status').read_text().splitlines() if x.startswith(('VmRSS:', 'VmHWM:', 'VmSwap:', 'Threads:'))]
                except OSError as exc:
                    process['error_type'] = type(exc).__name__
                entry['processes'].append(process)
        elif session['state'] in ('failed', 'interrupted'):
            entry['checkpoints'] = []
            for record in repo.records(session['run_id']):
                if record['kind'] != 'artifact':
                    continue
                payload = record['payload']
                proof = {"path": payload['path'], "epoch": payload['epoch']}
                try:
                    root = Path(session['artifact_root']).resolve()
                    assert Path(payload['path']).resolve().is_relative_to(root)
                    assert str(payload['run_id']) == str(session['run_id'])
                    identity = file_identity(payload['path'])
                    proof.update(identity)
                    proof['matches'] = all(identity[k] == payload[k] for k in ('bytes', 'sha256'))
                except Exception as exc:
                    proof['error_type'] = type(exc).__name__
                entry['checkpoints'].append(proof)
            entry['full_train_verified'] = False
        out['attempts'].append(entry)
print(json.dumps(out, indent=2))
