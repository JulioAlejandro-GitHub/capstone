"""Summarize measured evidence; never promote missing dimensions to PASS."""
import json
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent

def read(path): return json.loads(path.read_text())
pairs=[]
for i in range(5):
    arms={}
    for arm in ['a','b']:
        root=BASE/f'perf_{i}_{arm}'
        result=read(root/'outcome.json')
        timings=read(root/'timings.json')
        # First train and first validation step include graph compilation.
        # Initial harness labelled bound A methods using `is`, which is false
        # for freshly accessed bound methods. Raw durations remain valid. Recover
        # purpose boundaries from the verified two-epoch finite 5 TRAIN/3 VAL schedule.
        assert len(timings) == 16
        epochs=[r for r in read(root/'records.json') if r['kind']=='epoch']
        assert len(epochs) == 2
        warm=[t['seconds'] for index,t in enumerate(timings) if index not in (0,5)]
        arms[arm]=dict(total_seconds=result['elapsed'],
                       batch_median_seconds=float(np.median(warm)), batch_p95_seconds=float(np.percentile(warm,95)),
                       rss_peak_bytes=result['rss_peak_bytes'],
                       throughput_images_per_second=112/result['elapsed'],
                       confirmed_step_count=len(timings),
                       measured_boundary='Keras train/test function return, synchronized metrics; excludes callbacks')
    pairs.append(dict(pair=i,order='AB' if i%2==0 else 'BA',arms=arms,
                      total_overhead_percent=100*(arms['b']['total_seconds']/arms['a']['total_seconds']-1),
                      batch_p95_overhead_percent=100*(arms['b']['batch_p95_seconds']/arms['a']['batch_p95_seconds']-1),
                      rss_peak_difference_bytes=arms['b']['rss_peak_bytes']-arms['a']['rss_peak_bytes']))
summary=dict(pairs=pairs,
             median_total_overhead_percent=float(np.median([p['total_overhead_percent'] for p in pairs])),
             median_batch_p95_overhead_percent=float(np.median([p['batch_p95_overhead_percent'] for p in pairs])),
             total_overhead_threshold_percent=5.0,
             total_overhead_passed=bool(np.median([p['total_overhead_percent'] for p in pairs]) <= 5),
             batch_p95_threshold_percent=10.0,
             every_pair_batch_p95_passed=all(p['batch_p95_overhead_percent'] <= 10 for p in pairs),
             gpu_memory='not measured reliably',
             aggregator_memory='not isolated from TensorFlow / map / reference tensor copies',
             throughput_basis='37 TRAIN + 19 internal VAL, twice; excludes existing additional prediction passes',
             warmup='first TRAIN and VAL indices 0/5 excluded using verified 5+3 batches per epoch; initial A purpose labels were wrong, raw durations unaffected; total includes compilation and flush')
(BASE/'performance.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='pairs'},indent=2))
