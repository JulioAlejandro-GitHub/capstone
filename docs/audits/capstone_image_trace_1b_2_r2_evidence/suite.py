"""Serial GPU runs; immutable outputs, A/A gate before A/B interpretation."""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'capstone_image_trace_1b_2_evidence'
sys.path.insert(0, str(OLD))
from compare import compare


def run(name, architecture, *flags):
    output = HERE / name
    if output.exists():
        raise RuntimeError(f'REFUSE_OVERWRITE: {output}')
    command = [sys.executable, str(HERE/'experiment.py'), str(output), '--architecture', architecture, '--deterministic', *flags]
    with (HERE/f'{name}.log').open('x') as log:
        status = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
    print(name, status, flush=True)
    if status:
        raise RuntimeError(f'RUN_FAILED: {name}')
    return output


def check(a, b, name):
    result = compare(a, b)
    (HERE/f'{name}.json').write_text(json.dumps(result, indent=2))
    print(name, result['passed'], result['failed'], flush=True)
    return result['passed']


if __name__ == '__main__':
    for arch in ['custom_cnn', 'vgg16', 'densenet121']:
        flags = [] if arch == 'custom_cnn' else ['--two-phases']
        a1 = run(f'{arch}_aa1', arch, *flags)
        a2 = run(f'{arch}_aa2', arch, *flags)
        if not check(a1, a2, f'{arch}_aa'):
            raise RuntimeError('AA_GATE_FAILED')
        b = run(f'{arch}_b', arch, *flags, '--observer')
        check(a1, b, f'{arch}_ab')
