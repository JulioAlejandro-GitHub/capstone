"""Sequential processes; alternate A/B order. Stop on subprocess failure."""
import json
from pathlib import Path
import subprocess
import sys
from compare import compare
BASE=Path(__file__).resolve().parent

def run(name, architecture='custom_cnn', observer=False):
    command=[sys.executable,str(BASE/'experiment.py'),str(BASE/name),'--architecture',architecture,'--deterministic']
    if observer: command.append('--observer')
    with (BASE/(name+'.log')).open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    print(name+' completed',flush=True)

def comparison(a,b,name):
    result=compare(BASE/a,BASE/b)
    (BASE/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(name+': '+str(result['passed']),flush=True)
    return result['passed']

for i in range(5):
    for arm in ('a','b') if i%2==0 else ('b','a'):
        run(f'perf_{i}_{arm}',observer=arm=='b')
    comparison(f'perf_{i}_a',f'perf_{i}_b',f'perf_{i}_comparison')
for architecture in ['vgg16','densenet121']:
    run(architecture+'_aa1',architecture)
    run(architecture+'_aa2',architecture)
    if comparison(architecture+'_aa1',architecture+'_aa2',architecture+'_aa_comparison'):
        run(architecture+'_b',architecture,True)
        comparison(architecture+'_aa1',architecture+'_b',architecture+'_ab_comparison')
