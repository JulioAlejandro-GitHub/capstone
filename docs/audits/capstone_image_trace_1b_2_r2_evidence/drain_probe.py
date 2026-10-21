"""Separate timing diagnostic: age starts only when a completed batch is added."""
import json
from pathlib import Path
import runpy
import sys
import time
from unittest.mock import patch
from ledger import Aggregator

ROOT = Path(__file__).resolve().parent
arch = sys.argv[1]
OUT = ROOT/f'{arch}_drain_probe'
original_add, original_flush = Aggregator.add, Aggregator.flush
max_age = 0.
blocks = 0
first_confirmed = {}


def add(self, tokens):
    if not self.batches:
        first_confirmed[id(self)] = time.perf_counter()
    return original_add(self, tokens)


def flush(self):
    global max_age, blocks
    active = bool(self.batches)
    start = first_confirmed.get(id(self), time.perf_counter())
    result = original_flush(self)
    if active:
        max_age = max(max_age, time.perf_counter() - start)
        blocks += 1
    return result


sys.argv = ['experiment.py', str(OUT), '--observer', '--deterministic', '--architecture', arch]
if arch != 'custom_cnn':
    sys.argv += ['--two-phases']
with patch.object(Aggregator, 'add', add), patch.object(Aggregator, 'flush', flush):
    runpy.run_path(str(ROOT/'experiment.py'), run_name='__main__')
(OUT/'drain_measurement.json').write_text(json.dumps(dict(max_confirmed_to_durable_seconds=max_age,
    blocks=blocks, limit_seconds=5, passed=max_age <= 5), indent=2))
