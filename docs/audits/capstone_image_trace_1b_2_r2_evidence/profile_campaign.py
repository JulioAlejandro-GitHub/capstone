"""Run diagnostic isolation after clean R1 reproduction; never concurrently."""
import json
from pathlib import Path
import sys
from campaign import HERE, R1, OLD, seal, run, compare

commands = [[sys.executable,str(HERE/'profile_run.py'),arch,mode]
            for arch in ['custom_cnn','vgg16','densenet121']
            for mode in ['baseline','tokens','memory','serialization','full']]
seal('diagnostics_v1', [HERE/'profile_run.py',Path(__file__),R1/'experiment_benchmarked.py',
     R1/'observer.py',R1/'ledger.py',OLD/'compare.py'], commands)
for cmd in commands:
    arch,mode = cmd[-2:]
    name = f'diagnostic_{arch}_{mode}'
    run(cmd,name)
    result = compare(HERE/f'reproduction_{arch}_perf_0_a',HERE/name)
    (HERE/(name+'_science.json')).write_text(json.dumps(result,indent=2))
    if not result['passed']: raise RuntimeError('DIAGNOSTIC_INTERFERENCE')
