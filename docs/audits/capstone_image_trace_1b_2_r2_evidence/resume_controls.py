"""Resume remaining controls after preserving the invalid positional adapter trial."""
import json
from pathlib import Path
import subprocess
import sys
from suite import HERE, OLD, run, check

for arm in 'ab':
    with (HERE/f'no-shuffle_verified_{arm}.log').open('x') as log:
        subprocess.run([sys.executable, str(HERE/'no_shuffle_control.py'), arm], stdout=log, stderr=subprocess.STDOUT, check=True)
check(HERE/'no-shuffle_verified_a', HERE/'no-shuffle_verified_b', 'no-shuffle_verified_comparison')
a = run('duplicate_a', 'custom_cnn', '--duplicate-bytes', '--reference')
b = run('duplicate_b', 'custom_cnn', '--duplicate-bytes', '--reference', '--observer')
check(a, b, 'duplicate_comparison')
run('duration_30_epochs', 'custom_cnn', '--duration-epochs', '30', '--observer')
with (HERE/'unresolved.log').open('x') as log:
    code = subprocess.run([sys.executable, str(HERE/'experiment.py'), str(HERE/'unresolved'),
        '--deterministic', '--observer', '--unresolved'], stdout=log, stderr=subprocess.STDOUT).returncode
if not code:
    raise RuntimeError('Unresolved identity was not rejected')
for fault in ['before', 'during', 'after']:
    for arm in 'ab':
        name = f'fault_{fault}_{arm}'
        with (HERE/f'{name}.log').open('x') as log:
            code = subprocess.run([sys.executable, str(HERE/'experiment.py'), str(HERE/name), '--deterministic',
                '--interrupt', fault, *(['--observer'] if arm == 'b' else [])], stdout=log, stderr=subprocess.STDOUT).returncode
        outcome = json.loads((HERE/name/'outcome.json').read_text())
        if code == 0 or 'INJECTED_' not in outcome['error']:
            raise RuntimeError(f'Invalid injection {name}')
        print(name, 'expected_error', flush=True)
subprocess.run([sys.executable, str(HERE/'finish_suite.py')], check=True)
