"""Run after suite.py, not concurrently with measured pairs."""
import json
from pathlib import Path
import subprocess
import sys
from compare import compare
BASE=Path(__file__).resolve().parent
for fault in ['before','during','after']:
    for arm in ['a','b']:
        name=f'fault_verified_{fault}_{arm}'
        cmd=[sys.executable,str(BASE/'experiment.py'),str(BASE/name),'--deterministic','--interrupt',fault]
        if arm=='b':cmd.append('--observer')
        with (BASE/(name+'.log')).open('w') as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        print(name,result.returncode,flush=True)
        outcome=json.loads((BASE/name/'outcome.json').read_text())
        if result.returncode==0 or 'INJECTED_' not in outcome.get('error',''): raise RuntimeError('Unexpected fault result')
