"""Repeat the complete R1 scientific and receipt matrix on the R2 candidate."""
import json
from pathlib import Path
import subprocess
import sys
from campaign import HERE, OLD, seal, run
sys.path.insert(0, str(HERE))

commands=[[sys.executable,str(HERE/script)] for script in
          ['suite.py','test_ledger.py','storage_stress.py','capacity_allocation.py']]
commands += [[sys.executable,str(Path(__file__)),'diagnostics_and_controls']]

if len(sys.argv)==1:
    seal('regression_v1', list(HERE.glob('*.py'))+[OLD/'compare.py',OLD/'compare_reference.py'], commands)
    for command in commands:
        run(command,'regression_'+Path(command[1]).stem)
else:
    from extended import diagnostic
    from suite import run as experiment, check
    for arch in ['custom_cnn','vgg16','densenet121']:
        diagnostic(arch,[] if arch=='custom_cnn' else ['--two-phases'])
    a=experiment('no-augment_a','custom_cnn','--no-augment','--reference')
    b=experiment('no-augment_b','custom_cnn','--no-augment','--reference','--observer')
    assert check(a,b,'no-augment_comparison')
    subprocess.run([sys.executable,str(HERE/'resume_controls.py')],check=True)
    # The R1 retained-allocation probe is additional to its capacity/RSS probe.
    subprocess.run([sys.executable,str(HERE/'allocation_probe.py')],check=True)
