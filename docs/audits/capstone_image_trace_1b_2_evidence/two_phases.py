"""Two-phase A/A gate and A/B, using original freezing and optimizer resets."""
from pathlib import Path
import json
import subprocess
import sys
from compare import compare
BASE=Path(__file__).resolve().parent
for architecture in ['vgg16','densenet121']:
    for arm in ['aa1','aa2','b']:
        if arm=='b':
            result=compare(BASE/f'{architecture}_phases_aa1',BASE/f'{architecture}_phases_aa2')
            (BASE/f'{architecture}_phases_aa_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
            if not result['passed']:
                print(architecture,'A/A failed, B not executed',flush=True)
                break
        name=f'{architecture}_phases_{arm}'
        cmd=[sys.executable,str(BASE/'experiment.py'),str(BASE/name),'--architecture',architecture,'--deterministic','--two-phases']
        if arm=='b':cmd.append('--observer')
        with (BASE/(name+'.log')).open('w') as log:
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(name,'completed',flush=True)
        if arm=='b':
            result=compare(BASE/f'{architecture}_phases_aa1',BASE/name)
            (BASE/f'{architecture}_phases_ab_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
            print(architecture,'A/B',result['passed'],flush=True)
