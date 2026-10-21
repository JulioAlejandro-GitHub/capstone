"""Identify retained Python allocation beyond the bounded aggregator objects."""
import gc
import json
from pathlib import Path
import tracemalloc
from ledger import Store, Aggregator, deep_size

ROOT = Path(__file__).resolve().parent
store = Store(ROOT/'allocation_journal')
agg = Aggregator(store)
tracemalloc.start()
for epoch in range(1000):
    agg.open(dict(run_id='allocation', epoch_local=epoch+1))
    for batch in range(8):
        agg.add(list(range(batch*8,(batch+1)*8)))
    agg.close()
    if epoch % 25 == 24:
        gc.collect()
current, peak = tracemalloc.get_traced_memory()
snapshot = tracemalloc.take_snapshot()
rows = [dict(location=str(stat.traceback), bytes=stat.size, allocations=stat.count)
        for stat in snapshot.statistics('lineno')[:20]]
(ROOT/'allocation_probe.json').write_text(json.dumps(dict(current=current, peak=peak,
    aggregator_objects=deep_size(agg.__dict__), top=rows), indent=2))
print(json.dumps(rows[:5], indent=2))
