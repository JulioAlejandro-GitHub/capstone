"""No concurrent training. Five alternating pairs per architecture plus controls."""
import json
from pathlib import Path
import subprocess
import sys
from suite import HERE, OLD, run, check


def diagnostic(arch, flags):
    a = run(f'{arch}_reference_a', arch, *flags, '--reference')
    b = run(f'{arch}_reference_b', arch, *flags, '--reference', '--observer')
    for side, directory, original in [('a', a, HERE/f'{arch}_aa1'), ('b', b, HERE/f'{arch}_b')]:
        check(original, directory, f'{arch}_reference_{side}_interference')
    subprocess.run([sys.executable, str(OLD/'compare_reference.py'), str(a), str(b),
                    str(HERE/f'{arch}_reference_comparison.json')], check=True)


if __name__ == '__main__':
    for arch in ['custom_cnn', 'vgg16', 'densenet121']:
        flags = [] if arch == 'custom_cnn' else ['--two-phases']
        diagnostic(arch, flags)
        for pair in range(5):
            for arm in ('ab' if pair % 2 == 0 else 'ba'):
                run(f'{arch}_perf_{pair}_{arm}', arch, *flags, *(['--observer'] if arm == 'b' else []))
            check(HERE/f'{arch}_perf_{pair}_a', HERE/f'{arch}_perf_{pair}_b', f'{arch}_perf_{pair}_comparison')
    for control in ['no-augment', 'no-shuffle']:
        a = run(f'{control}_a', 'custom_cnn', f'--{control}', '--reference')
        b = run(f'{control}_b', 'custom_cnn', f'--{control}', '--reference', '--observer')
        check(a, b, f'{control}_comparison')
        subprocess.run([sys.executable, str(OLD/'compare_reference.py'), str(a), str(b), str(HERE/f'{control}_reference.json')], check=True)
    a = run('duplicate_a', 'custom_cnn', '--duplicate-bytes', '--reference')
    b = run('duplicate_b', 'custom_cnn', '--duplicate-bytes', '--reference', '--observer')
    check(a, b, 'duplicate_comparison')
    subprocess.run([sys.executable, str(OLD/'compare_reference.py'), str(a), str(b), str(HERE/'duplicate_reference.json')], check=True)
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
