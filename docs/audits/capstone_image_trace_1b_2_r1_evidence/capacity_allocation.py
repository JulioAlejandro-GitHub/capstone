"""Isolated peak allocation of a maximum-pair block; no identity map or TF."""
import json
from pathlib import Path
import resource
import tracemalloc
from ledger import Aggregator, Store

ROOT = Path(__file__).resolve().parent
rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
tracemalloc.start()
store = Store(ROOT/'capacity_allocation_journal')
agg = Aggregator(store)
agg.open(dict(run_id='synthetic-capacity-allocation', epoch_local=1))
agg.add(list(range(8192)))
agg.add([8192])
agg.close()
current, peak = tracemalloc.get_traced_memory()
rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
tracemalloc.stop()
result = dict(tracemalloc_current_bytes=current, tracemalloc_peak_bytes=peak,
              process_rss_peak_before_bytes=rss_before, process_rss_peak_after_bytes=rss_after,
              process_rss_peak_increment_bytes=rss_after-rss_before,
              object_bound_bytes=agg.peak_bytes, max_event_bytes=store.max_bytes,
              verification=store.verify())
assert peak <= 32*1024*1024
(ROOT/'capacity_allocation.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
