"""Locate latency without equating host intervals with unobserved Metal kernels."""
from collections import defaultdict
import json
from pathlib import Path
import pstats
import numpy as np
from analyze import ROOT,stats

report={}
for folder in sorted(ROOT.glob('diagnostic_*')):
    if not (folder/'host_timeline.json').exists():continue
    timeline=json.loads((folder/'host_timeline.json').read_text())
    functions=[e for e in timeline if e['name']=='scientific_function']
    timing=json.loads((folder/'timings.json').read_text())
    assert len(functions)==len(timing)
    traces=[e for e in timeline if e['name']=='tf_function' and e['traces_before']!=e['traces_after']]
    rows=[]
    for i,(step,measured) in enumerate(zip(functions,timing)):
        start,end=step['start'],step['start']+step['seconds']
        active=[e for e in traces if start<=e['start']<=end and e.get('function') in ('one_step_on_data','multi_step_on_iterator')]
        rows.append(dict(index=i,purpose=step['purpose'],function_number=step['function_number'],
            function_batch=step['batch'],function_seconds=step['seconds'],
            measured_seconds=measured['seconds'],outside_function_seconds=measured['seconds']-step['seconds'],
            trace_increments=[dict(function=e['function'],before=e['traces_before'],after=e['traces_after']) for e in active]))
    groups=defaultdict(list)
    for e in timeline:
        if e['name']=='numpy' and e['caller'].startswith('observer.py:'):
            groups[e['caller']].append(e['seconds'])
    cpu=pstats.Stats(str(folder/'cpu_profile.pstats'))
    host_costs=[]
    for (file,line,name),(primitive,total,own,cumulative,callers) in cpu.stats.items():
        if Path(file).name=='ledger.py':
            host_costs.append(dict(file=file,line=line,function=name,primitive_calls=primitive,
                total_calls=total,own_seconds=own,cumulative_seconds=cumulative))
    report[folder.name]=dict(steps=rows,observer_numpy={k:stats(v) for k,v in groups.items()},
        outside_function=stats([r['outside_function_seconds'] for r in rows]),ledger_cpu=host_costs,
        note='Function interval includes iterator delivery, graph/runtime execution and synchronization; no isolated GPU kernel attribution.')
with (ROOT/'causal_analysis.json').open('x') as stream:json.dump(report,stream,indent=2)
for key,value in report.items():
    if key.endswith('_full'):
        print(key,'outside function ms', {k:round(v*1000,3) for k,v in value['outside_function'].items() if k!='count'})
