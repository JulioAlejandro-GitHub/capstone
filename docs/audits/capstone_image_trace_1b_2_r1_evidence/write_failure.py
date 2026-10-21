"""Inject rename failure after fsync during an actual synthetic Metal TRAIN."""
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch
from ledger import Store
from observer import Observer
from recover_pending import recover

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'write_failure'
original_put = Store.put
original_save = Observer.save
injected = False
report = {}


def put(self, payload):
    global injected
    if payload['record_type'] == 'consumption_block' and not injected:
        injected = True
        with patch('ledger.os.rename', side_effect=OSError('INJECTED_RECEIPT_RENAME_FAILURE')):
            return original_put(self, payload)
    return original_put(self, payload)


def save(self):
    report['before_recovery'] = self.store.verify()
    report['recovery'] = recover(self.store)
    original_save(self)
    report['after_recovery'] = self.store.verify()
    (OUT/'write_failure_verification.json').write_text(json.dumps(report, indent=2))


sys.argv = ['experiment.py', str(OUT), '--observer', '--deterministic']
try:
    with patch.object(Store, 'put', put), patch.object(Observer, 'save', save):
        runpy.run_path(str(ROOT/'experiment.py'), run_name='__main__')
except OSError as error:
    if str(error) != 'INJECTED_RECEIPT_RENAME_FAILURE':
        raise
    assert report['before_recovery']['pending'] == 1
    assert report['before_recovery']['blocks'] == 0
    assert report['after_recovery']['batches'] == 5
    assert report['after_recovery']['partial'] == 1
    print('EXPECTED_RECEIPT_WRITE_FAILURE_EXACT_REPLAY_NO_SCIENCE_RETRY')
else:
    raise RuntimeError('Injection did not fire')
