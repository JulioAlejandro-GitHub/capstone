"""Read-only analysis: preserve every pair and strict R1 warmup definition."""
import json
from pathlib import Path
import statistics
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
def stats(values):
    return dict(count=len(values),total=sum(values),median=float(np.median(values)),
                p95=float(np.percentile(values,95)),maximum=max(values)) if values else {}

def benchmark(stage):
    result = {}
    for arch in ['custom_cnn','vgg16','densenet121']:
        rows=[]
        for pair in range(5):
            arms={}
            for arm in 'ab':
                folder=ROOT/f'{stage}_{arch}_perf_{pair}_{arm}'
                if not (folder/'timings.json').exists(): continue
                outcome=json.loads((folder/'outcome.json').read_text())
                timing=json.loads((folder/'timings.json').read_text())
                assert len(timing)==(16 if arch=='custom_cnn' else 32)
                values=[r['seconds'] for r in timing]
                excluded={0,5} if arch=='custom_cnn' else {0,5,16,21}
                arms[arm]=dict(total=outcome['elapsed'],rss_peak_bytes=outcome['rss_peak_bytes'],
                    throughput=(112 if arch=='custom_cnn' else 224)/outcome['elapsed'],
                    all=stats(values),warm=stats([v for i,v in enumerate(values) if i not in excluded]),
                    slowest=sorted(enumerate(values),key=lambda x:x[1],reverse=True)[:5])
                if arm=='b': arms[arm]['observer']=json.loads((folder/'observer_summary.json').read_text())
            if len(arms)!=2: continue
            a,b=arms['a'],arms['b']
            row=dict(pair=pair+1,order='AB' if pair%2==0 else 'BA',arms=arms,
                     total_percent=100*(b['total']/a['total']-1),
                     full_p95_percent=100*(b['all']['p95']/a['all']['p95']-1),
                     warm_p95_percent=100*(b['warm']['p95']/a['warm']['p95']-1))
            row['p95_pass']=row['full_p95_percent']<=10 and row['warm_p95_percent']<=10
            rows.append(row)
        if rows:
            median=statistics.median(r['total_percent'] for r in rows)
            result[arch]=dict(pairs=rows,total_median_percent=median,
                worst_full_p95_percent=max(r['full_p95_percent'] for r in rows),
                worst_warm_p95_percent=max(r['warm_p95_percent'] for r in rows),
                passed=len(rows)==5 and median<=5 and all(r['p95_pass'] for r in rows))
    (ROOT/(stage+'_performance.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:{key:value for key,value in v.items() if key!='pairs'} for k,v in result.items()},indent=2))

def profiles():
    from collections import defaultdict
    result={}
    for folder in sorted(ROOT.glob('diagnostic_*')):
        if not (folder/'host_timeline.json').exists(): continue
        events=json.loads((folder/'host_timeline.json').read_text())
        groups=defaultdict(list)
        for e in events:
            label=e['name']+('/'+e['caller'] if e['name']=='numpy' else '')
            groups[label].append(e['seconds'])
        result[folder.name]=dict(components={k:stats(v) for k,v in groups.items()},
            tracing=[e for e in events if e['name']=='tf_function' and e['traces_before']!=e['traces_after']],
            tf_functions=[e for e in events if e['name']=='tf_function'],
            metadata=json.loads((folder/'diagnostic_metadata.json').read_text()))
    (ROOT/'profile_summary.json').write_text(json.dumps(result,indent=2))
    print('profiles',len(result))

if __name__=='__main__':
    if sys.argv[1]=='profiles': profiles()
    else: benchmark(sys.argv[1])
