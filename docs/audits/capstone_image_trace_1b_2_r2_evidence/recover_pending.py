"""Explicit recovery of exact, fully written experimental pending receipts."""
import json
import os
from ledger import canonical, digest, MAX_BYTES


def recover(store):
    outcomes = []
    for folder in store.root.iterdir():
        if not folder.is_dir():
            continue
        for pending in folder.glob('*.pending'):
            if pending.stat().st_size > MAX_BYTES:
                outcomes.append(dict(path=str(pending), status='oversize_unknown'))
                continue
            data = pending.read_bytes()
            try:
                event = json.loads(data)
                sha = event.pop('receipt_sha256')
                if digest(event) != sha or canonical(dict(event, receipt_sha256=sha)) != data:
                    raise ValueError('HASH_OR_CANONICAL')
                scope = event['scope']
                key = digest({k: v for k,v in scope.items() if k not in ('manifest_sha256','manifest_ref')})
                if key != folder.name or pending.stem != f"{event['sequence']:08d}":
                    raise ValueError('LOGICAL_KEY')
                if event['sequence']:
                    prior = json.loads((folder/f"{event['sequence']-1:08d}.json").read_bytes())
                    if prior['receipt_sha256'] != event['previous_sha256'] or prior['scope'] != scope or prior['record_type'] == 'scope_close':
                        raise ValueError('CHAIN')
                elif event['record_type'] != 'scope_open' or event['previous_sha256'] is not None:
                    raise ValueError('OPEN')
            except (ValueError, KeyError, OSError):
                outcomes.append(dict(path=str(pending), status='truncated_or_invalid_unknown'))
                continue
            final = pending.with_suffix('.json')
            if final.exists():
                if final.read_bytes() != data:
                    raise ValueError('CONTRADICTORY_PENDING')
                outcomes.append(dict(path=str(pending), status='identical_duplicate'))
                continue
            os.rename(pending, final)
            fd = os.open(folder, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            outcomes.append(dict(path=str(final), status='recovered_exact_bytes'))
    return outcomes
