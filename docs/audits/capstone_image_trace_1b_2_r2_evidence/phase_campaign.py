"""Native profiler has no GPU plane: supplemental synchronized diagnostics."""
import json
import sys
from pathlib import Path
from campaign import HERE,R1,OLD,seal,run,compare

commands=[[sys.executable,str(HERE/'phase_profile.py'),arch,arm]
          for arch in ['custom_cnn','vgg16','densenet121'] for arm in 'ab']
seal('phase_diagnostics_v1',[Path(__file__),HERE/'phase_profile.py',R1/'experiment_benchmarked.py',
     R1/'observer.py',R1/'ledger.py',OLD/'compare.py'],commands)
for command in commands:
    arch,arm=command[-2:]
    name=f'phase_profile_{arch}_{arm}'
    run(command,name)
    result=compare(HERE/f'reproduction_{arch}_perf_0_{arm}',HERE/name)
    (HERE/(name+'_science.json')).write_text(json.dumps(result,indent=2))
    if not result['passed']:raise RuntimeError('PROFILE_INTERFERENCE')
