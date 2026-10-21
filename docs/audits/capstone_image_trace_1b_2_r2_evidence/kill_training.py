"""SIGKILL only this synthetic child, after its first durable consumed block."""
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
from unittest.mock import patch
from ledger import Store

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'killed_training'
if len(sys.argv) > 1:
    put = Store.put
    def kill_after_durable(self, payload):
        result = put(self, payload)
        if payload['record_type'] == 'consumption_block':
            os.kill(os.getpid(), signal.SIGKILL)
        return result
    sys.argv = ['experiment.py', str(OUT), '--observer', '--deterministic']
    with patch.object(Store, 'put', kill_after_durable):
        runpy.run_path(str(ROOT/'experiment.py'), run_name='__main__')
else:
    child = subprocess.run([sys.executable, __file__, 'child'])
    result = dict(returncode=child.returncode, recovery=Store(OUT/'journal').verify())
    assert result['returncode'] == -9
    assert result['recovery']['partial'] == 1
    assert result['recovery']['batches'] == 5
    (OUT/'kill_verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
