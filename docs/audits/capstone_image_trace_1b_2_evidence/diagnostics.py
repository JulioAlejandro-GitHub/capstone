"""Run after suite.py, not concurrently with measured pairs."""
import json
from pathlib import Path
import subprocess
import sys
from compare import compare
BASE=Path(__file__).resolve().parent
for arm in ['a','b']:
    name='reference_'+arm
    cmd=[sys.executable,str(BASE/'experiment.py'),str(BASE/name),'--deterministic','--reference']
    if arm=='b':cmd.append('--observer')
    with (BASE/(name+'.log')).open('w') as log:
        completed=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    print(name,completed.returncode,flush=True)
    if completed.returncode: raise SystemExit(completed.returncode)
    result=compare(BASE/('aa1' if arm=='a' else 'b1'),BASE/name)
    (BASE/(name+'_interference.json')).write_text(json.dumps(result,indent=2)+'\n')
subprocess.run([sys.executable,str(BASE/'compare_reference.py'),str(BASE/'reference_a'),str(BASE/'reference_b'),str(BASE/'reference_comparison.json')],check=True)
for fault in ['before','during','after']:
    for arm in ['a','b']:
        name=f'fault_{fault}_{arm}'
        cmd=[sys.executable,str(BASE/'experiment.py'),str(BASE/name),'--deterministic','--interrupt',fault]
        if arm=='b':cmd.append('--observer')
        with (BASE/(name+'.log')).open('w') as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        print(name,result.returncode,flush=True)
        outcome=json.loads((BASE/name/'outcome.json').read_text())
        if result.returncode==0 or 'INJECTED_' not in outcome.get('error',''): raise RuntimeError('Unexpected fault result')
