"""Report all pairs, including startup, serializations and durable close."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
report = {}
for arch in ['custom_cnn', 'vgg16', 'densenet121']:
    rows = []
    for pair in range(5):
        arms = {}
        for arm in 'ab':
            folder = ROOT/f'{arch}_perf_{pair}_{arm}'
            if not (folder/'outcome.json').exists():
                continue
            outcome = json.loads((folder/'outcome.json').read_text())
            timings = json.loads((folder/'timings.json').read_text())
            values = [row['seconds'] for row in timings]
            # Same finite 5 TRAIN / 3 VAL fixture, two epochs per phase.
            # This boundary calculation is only timing warmup, never identity evidence.
            warm = [v for i, v in enumerate(values) if i not in ({0,5} if arch == 'custom_cnn' else {0,5,16,21})]
            arms[arm] = dict(total=outcome['elapsed'], rss_peak_bytes=outcome['rss_peak_bytes'],
                             batch_median=float(np.median(values)), batch_p95=float(np.percentile(values,95)),
                             warm_median=float(np.median(warm)), warm_p95=float(np.percentile(warm,95)),
                             throughput=(112 if arch == 'custom_cnn' else 224)/outcome['elapsed'])
            if arm == 'b':
                arms[arm]['observer'] = json.loads((folder/'observer_summary.json').read_text())
        if len(arms) == 2:
            rows.append(dict(pair=pair, order='AB' if pair % 2 == 0 else 'BA', arms=arms,
                overhead_total_percent=100*(arms['b']['total']/arms['a']['total']-1),
                overhead_p95_all_percent=100*(arms['b']['batch_p95']/arms['a']['batch_p95']-1),
                overhead_p95_warm_percent=100*(arms['b']['warm_p95']/arms['a']['warm_p95']-1)))
    if rows:
        report[arch] = dict(pairs=rows,
            total_median_overhead_percent=float(np.median([r['overhead_total_percent'] for r in rows])),
            p95_all_median_overhead_percent=float(np.median([r['overhead_p95_all_percent'] for r in rows])),
            p95_warm_median_overhead_percent=float(np.median([r['overhead_p95_warm_percent'] for r in rows])),
            p95_warm_worst_overhead_percent=max(r['overhead_p95_warm_percent'] for r in rows))
(ROOT/'performance.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: {key: value for key, value in v.items() if key != 'pairs'} for k,v in report.items()}, indent=2))
