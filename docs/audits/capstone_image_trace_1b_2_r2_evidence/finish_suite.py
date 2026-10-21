"""Sequential post-benchmark controls; no concurrent model execution."""
from pathlib import Path
import subprocess
import sys
from suite import check

ROOT = Path(__file__).resolve().parent
for name, arguments in [('final_controls', []), ('write_failure', []), ('kill_training', [])] + [
        ('drain_probe', [arch]) for arch in ['custom_cnn', 'vgg16', 'densenet121']]:
    label = '_'.join([name, *arguments])
    with (ROOT/f'{label}.log').open('x') as log:
        subprocess.run([sys.executable, str(ROOT/f'{name}.py'), *arguments], stdout=log, stderr=subprocess.STDOUT, check=True)
    print(label, 'completed', flush=True)
    if name == 'drain_probe':
        arch = arguments[0]
        check(ROOT/f'{arch}_aa1', ROOT/f'{arch}_drain_probe', f'{arch}_drain_interference')
subprocess.run([sys.executable, str(ROOT/'verify_results.py')], check=True)
subprocess.run([sys.executable, str(ROOT/'summarize.py')], check=True)

for arch in ['custom_cnn', 'vgg16', 'densenet121']:
    for arm in 'ab':
        with (ROOT/f'{arch}_state_{arm}.log').open('x') as log:
            subprocess.run([sys.executable, str(ROOT/'state_probe.py'), arch, arm], stdout=log, stderr=subprocess.STDOUT, check=True)
        check(ROOT/f'{arch}_{'aa1' if arm == 'a' else 'b'}', ROOT/f'{arch}_state_{arm}', f'{arch}_state_{arm}_interference')
    subprocess.run([sys.executable, str(ROOT/'compare_reference.py'), str(ROOT/f'{arch}_state_a'), str(ROOT/f'{arch}_state_b'), str(ROOT/f'{arch}_state_reference.json')], check=True)
subprocess.run([sys.executable, str(ROOT/'compare_states.py')], check=True)
subprocess.run([sys.executable, str(ROOT/'verify_results.py')], check=True)

with (ROOT/'no-shuffle_fixed_smoke.log').open('x') as log:
    subprocess.run([sys.executable, str(ROOT/'experiment.py'), str(ROOT/'no-shuffle_fixed_smoke'), '--deterministic', '--observer', '--reference', '--no-shuffle'], stdout=log, stderr=subprocess.STDOUT, check=True)
check(ROOT/'no-shuffle_verified_a', ROOT/'no-shuffle_fixed_smoke', 'no-shuffle_fixed_smoke_comparison')
subprocess.run([sys.executable, str(ROOT/'verify_results.py')], check=True)
