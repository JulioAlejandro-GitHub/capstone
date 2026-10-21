"""Synthetic-only immutable receipt files; no E10 or SQL integration."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from collections import Counter

MAX_BYTES = 256 * 1024
MAX_PAIRS = 8192
MAX_BATCHES = 128


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def deep_size(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set)):
        size += sum(deep_size(v, seen) for v in value)
    return size


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)
        self.write_seconds = 0.
        self.max_bytes = 0
        self.events = 0

    def put(self, payload):
        event = dict(payload, receipt_sha256=digest(payload))
        data = canonical(event)
        if len(data) > MAX_BYTES:
            raise ValueError('EVENT_CAPACITY')
        scope = event['scope']
        key = digest({k: v for k, v in scope.items() if k not in ('manifest_sha256', 'manifest_ref')})
        folder = self.root / key
        folder.mkdir(exist_ok=True)
        root_fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(root_fd)
        finally:
            os.close(root_fd)
        path = folder / f"{event['sequence']:08d}.json"
        start = time.perf_counter()
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError('CONTRADICTORY_REPLAY')
            return False
        if event['sequence']:
            prior_path = folder / f"{event['sequence'] - 1:08d}.json"
            if not prior_path.exists():
                raise ValueError('SEQUENCE_GAP')
            prior = json.loads(prior_path.read_bytes())
            if prior['record_type'] == 'scope_close' or prior['receipt_sha256'] != event['previous_sha256'] or prior['scope'] != scope:
                raise ValueError('CLOSED_OR_CHAIN_CONFLICT')
        elif event['record_type'] != 'scope_open' or event['previous_sha256'] is not None:
            raise ValueError('INVALID_OPEN')
        pending = path.with_suffix('.pending')
        # A failed pending write is retained and requires explicit recovery.
        with pending.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(pending, path)
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.write_seconds += time.perf_counter() - start
        self.max_bytes = max(self.max_bytes, len(data))
        self.events += 1
        return True

    def verify(self):
        start = time.perf_counter()
        result = dict(scopes=0, events=0, blocks=0, partial=0, pending=0, batches=0)
        for folder in self.root.iterdir():
            if not folder.is_dir():
                continue
            result['scopes'] += 1
            previous = None
            sequence = 0
            batches = total = 0
            closed = False
            scope = None
            def sequential_paths():
                index = 0
                while (folder / f'{index:08d}.json').exists():
                    yield folder / f'{index:08d}.json'
                    index += 1
                # Streaming check detects unexpected files beyond a gap.
                actual = sum(1 for entry in folder.iterdir() if entry.suffix == '.json')
                if actual != index:
                    raise ValueError('SEQUENCE_GAP')
            for path in sequential_paths():
                event = json.loads(path.read_bytes())
                sha = event.pop('receipt_sha256')
                if digest(event) != sha or event['sequence'] != sequence or event['previous_sha256'] != previous or closed:
                    raise ValueError('INTEGRITY_CHAIN')
                if scope is not None and scope != event['scope']:
                    raise ValueError('SCOPE_CONFLICT')
                scope = event['scope']
                kind = event['record_type']
                if sequence == 0 and kind != 'scope_open':
                    raise ValueError('MISSING_OPEN')
                if kind == 'consumption_block':
                    orders = event['batches']
                    counts = sorted(Counter(t for batch in orders for t in batch).items())
                    if [list(x) for x in counts] != event['counts'] or event['batch_first'] != batches + 1:
                        raise ValueError('COUNTS_OR_OVERLAP')
                    if len(orders) > MAX_BATCHES or len(counts) > MAX_PAIRS or len(canonical(dict(event, receipt_sha256=sha))) > MAX_BYTES:
                        raise ValueError('CAPACITY')
                    batches += len(orders)
                    total += sum(v for _, v in counts)
                    result['blocks'] += 1
                elif kind == 'scope_close':
                    if event['confirmed_batches'] != batches or event['total_processings'] != total:
                        raise ValueError('CLOSE_TOTALS')
                    closed = True
                    result['partial'] += not event['exhaustive']
                elif kind != 'scope_open' or sequence != 0:
                    raise ValueError('REOPEN')
                previous = sha
                sequence += 1
                result['events'] += 1
            result['partial'] += not closed
            result['pending'] += sum(1 for entry in folder.iterdir() if entry.suffix == '.pending')
            result['batches'] += batches
        result['recovery_seconds'] = time.perf_counter() - start
        return result


class Aggregator:
    def __init__(self, store):
        self.store = store
        self.scope = None
        self.batches = []
        self.counts = Counter()
        self.peak_bytes = 0
        self.close_seconds = 0.
        self.max_drain_seconds = 0.
        self.last_flush = time.monotonic()

    def emit(self, kind, **fields):
        payload = dict(contract_version='image_trace_v1_r1_experimental', record_type=kind,
                       scope=self.scope, sequence=self.sequence, previous_sha256=self.previous, **fields)
        self.store.put(payload)
        self.previous = digest(payload)
        self.sequence += 1

    def open(self, scope):
        if self.scope is not None:
            raise ValueError('SCOPE_ALREADY_ACTIVE')
        scope_key = digest({k: v for k, v in scope.items() if k not in ('manifest_sha256', 'manifest_ref')})
        if (self.store.root / scope_key).exists():
            raise ValueError('SCOPE_REOPEN_REQUIRES_NEW_SCIENTIFIC_PASS')
        self.scope = scope
        self.sequence = self.completed = self.total = self.blocks = 0
        self.previous = None
        self.emit('scope_open')
        self.last_flush = time.monotonic()

    def add(self, tokens):
        if self.scope is None:
            raise ValueError('NO_ACTIVE_SCOPE')
        if any(type(t) is not int or t < 0 for t in tokens):
            raise ValueError('UNRESOLVED_TOKEN')
        incoming = Counter(tokens)
        # Conservative envelope reserve; never split a scientific batch.
        if len(incoming) > MAX_PAIRS or len(canonical(tokens)) + len(canonical(sorted(incoming.items()))) > MAX_BYTES - 8192:
            raise ValueError('BATCH_CAPACITY_NO_MULTIPART')
        prospective = self.counts + incoming
        if self.batches and (len(self.batches) >= MAX_BATCHES or len(prospective) > MAX_PAIRS or
            len(canonical(self.batches + [tokens])) + len(canonical(sorted(prospective.items()))) > MAX_BYTES - 8192):
            self.flush()
        self.batches.append(tokens)
        self.counts.update(incoming)
        # Bound includes serialization copies and temporary prospective counters.
        self.peak_bytes = max(self.peak_bytes, deep_size(self.batches) + deep_size(self.counts) +
                              deep_size(prospective) + 4 * MAX_BYTES + deep_size(self.scope))
        if len(self.batches) >= MAX_BATCHES or time.monotonic() - self.last_flush >= 5:
            self.flush()

    def flush(self):
        if not self.batches:
            return
        self.max_drain_seconds = max(self.max_drain_seconds, time.monotonic() - self.last_flush)
        self.emit('consumption_block', block_sequence=self.blocks + 1,
                  batch_first=self.completed + 1, batch_last=self.completed + len(self.batches),
                  counts=sorted(self.counts.items()), batches=self.batches,
                  confirmation_basis='completed_original_step')
        self.completed += len(self.batches)
        self.total += sum(self.counts.values())
        self.blocks += 1
        self.batches = []
        self.counts = Counter()
        self.last_flush = time.monotonic()

    def close(self, exhaustive=True):
        if self.scope is None:
            return
        started = time.perf_counter()
        self.flush()
        self.emit('scope_close', confirmed_batches=self.completed, total_processings=self.total,
                  blocks=self.blocks, exhaustive=exhaustive,
                  unknown_window=None if exhaustive else 'after_last_durable_batch_upper_bound_unknown')
        self.scope = None
        self.close_seconds += time.perf_counter() - started
