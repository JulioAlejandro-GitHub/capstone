"""Long aggregation and isolated abrupt death, without TensorFlow training."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tracemalloc
from ledger import Aggregator, Store, deep_size

ROOT = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    store = Store(ROOT / 'crash_journal')
    agg = Aggregator(store)
    agg.open(dict(run_id='synthetic-crash', epoch_local=1))
    agg.add([0, 1, 2])
    agg.flush()
    agg.add([3, 4])  # Completed in-memory receipt simulation, not durable.
    folder = next(store.root.iterdir())
    with (folder / '00000002.pending').open('xb') as stream:
        stream.write(b'{"incomplete":')
        stream.flush()
        os.fsync(stream.fileno())
    os.kill(os.getpid(), signal.SIGKILL)
else:
    store = Store(ROOT / 'stress_journal_v2')
    agg = Aggregator(store)
    tracemalloc.start()
    memory = []
    started = time.perf_counter()
    for epoch in range(200):
        agg.open(dict(run_id='synthetic-stress', epoch_local=epoch + 1))
        for batch in range(8):
            agg.add(list(range(batch * 8, (batch + 1) * 8)))
        agg.close()
        current, peak = tracemalloc.get_traced_memory()
        memory.append(dict(epoch=epoch + 1, live_bytes=current, telemetry_bytes=deep_size(memory), peak_bytes=peak,
                           aggregator_bound_bytes=agg.peak_bytes))
    tracemalloc.stop()
    report = dict(epochs=memory, elapsed=time.perf_counter()-started, verification=store.verify())
    process = subprocess.run([sys.executable, __file__, 'crash'])
    report['abrupt_death'] = dict(returncode=process.returncode, verification=Store(ROOT/'crash_journal').verify())
    (ROOT/'storage_stress.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'epochs'}, indent=2))
