"""R2 immutable commands and source snapshots, sequential independent processes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'capstone_image_trace_1b_2_r1_evidence'
OLD = HERE.parent / 'capstone_image_trace_1b_2_evidence'
sys.path.insert(0, str(OLD))
from compare import compare

def seal(name, sources, commands):
    files = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    with (HERE / (name + '_seal.json')).open('x') as f:
        json.dump(dict(utc=datetime.now(timezone.utc).isoformat(), files=files,
                       commands=commands, environment={k:os.environ.get(k) for k in
                       ['PYTHONDONTWRITEBYTECODE','MPLCONFIGDIR']}), f, indent=2)

def run(command, name, expected=0):
    with (HERE / (name + '.log')).open('x') as f:
        code = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT).returncode
    print(name, code, flush=True)
    if code != expected:
        raise RuntimeError((name, code, expected))

def benchmark(stage):
    script = R1/'experiment_benchmarked.py' if stage == 'reproduction' else HERE/'experiment.py'
    directory = script.parent
    commands = []
    for arch in ['custom_cnn','vgg16','densenet121']:
        flags = [] if arch == 'custom_cnn' else ['--two-phases']
        for pair in range(5):
            for arm in ('ab' if pair % 2 == 0 else 'ba'):
                name = f'{stage}_{arch}_perf_{pair}_{arm}'
                commands.append([sys.executable,str(script),str(HERE/name),'--architecture',arch,
                                 '--deterministic',*flags,*(['--observer'] if arm=='b' else [])])
    seal(stage, [script,directory/'observer.py',directory/'ledger.py',OLD/'compare.py',Path(__file__)], commands)
    for i, command in enumerate(commands):
        run(command, Path(command[2]).name)
        if i % 2:
            name = Path(command[2]).name[:-1]
            result = compare(HERE/(name+'a'), HERE/(name+'b'))
            (HERE/(name+'comparison.json')).write_text(json.dumps(result,indent=2))
            if not result['passed']:
                raise RuntimeError('SCIENTIFIC_GATE_FAILED')

if __name__ == '__main__':
    benchmark(sys.argv[1])
