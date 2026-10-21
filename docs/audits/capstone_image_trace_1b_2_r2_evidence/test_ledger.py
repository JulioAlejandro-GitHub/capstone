"""Faults target experimental receipt storage, never production files."""
import json
from pathlib import Path
import tempfile
import tracemalloc
import unittest
from ledger import Aggregator, Store, canonical, digest, MAX_BYTES
from recover_pending import recover


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'journal'
        self.store = Store(self.root)
        self.agg = Aggregator(self.store)
        self.scope = dict(run_id='synthetic', epoch_local=1, manifest_sha256='a' * 64)
    def tearDown(self):
        self.temp.cleanup()
    def event(self, n=0):
        path = sorted(self.root.glob('*/*.json'))[n]
        value = json.loads(path.read_bytes())
        value.pop('receipt_sha256')
        return value
    def test_replay_conflict_and_recovery(self):
        self.agg.open(self.scope)
        self.agg.add([0, 0, 1])
        self.agg.close()
        self.assertFalse(self.store.put(self.event(1)))
        conflict = self.event(1)
        conflict['counts'] = [[0, 1], [1, 1]]
        with self.assertRaisesRegex(ValueError, 'CONTRADICTORY'):
            self.store.put(conflict)
        self.assertEqual(Store(self.root).verify()['batches'], 1)
        self.assertEqual(self.store.verify()['partial'], 0)
    def test_open_partial_and_pending(self):
        self.agg.open(self.scope)
        self.agg.add([1])
        self.agg.flush()
        folder = next(self.root.iterdir())
        (folder / '00000002.pending').write_bytes(b'{"truncated":')
        result = Store(self.root).verify()
        self.assertEqual((result['partial'], result['pending'], result['batches']), (1, 1, 1))
    def test_partial_close(self):
        self.agg.open(self.scope)
        self.agg.add([1, 2, 3])
        self.agg.close(False)
        self.assertEqual(self.store.verify()['partial'], 1)
    def test_full_block_and_no_split(self):
        self.agg.open(self.scope)
        for _ in range(129):
            self.agg.add([0, 1])
        self.agg.close()
        self.assertEqual(self.store.verify()['blocks'], 2)
        self.assertEqual(len(self.event(1)['batches']), 128)
        self.assertEqual(len(self.event(2)['batches']), 1)
    def test_oversize_unresolved(self):
        self.agg.open(self.scope)
        for tokens in (list(range(8193)), [-1], [True]):
            with self.assertRaises(ValueError):
                self.agg.add(tokens)
        self.assertEqual(self.agg.batches, [])
    def test_integrity_corruption(self):
        self.agg.open(self.scope)
        path = next(self.root.glob('*/*.json'))
        value = json.loads(path.read_bytes())
        value['scope']['run_id'] = 'changed'
        path.write_bytes(canonical(value))
        with self.assertRaisesRegex(ValueError, 'INTEGRITY'):
            self.store.verify()
    def test_storage_failure_does_not_clear_active_block(self):
        self.agg.open(self.scope)
        self.agg.add([1, 2])
        original = self.store.put
        def fail(payload):
            raise OSError('INJECTED_WRITE')
        self.store.put = fail
        with self.assertRaises(OSError):
            self.agg.flush()
        self.assertEqual(self.agg.batches, [[1, 2]])
        self.store.put = original
        self.agg.close(False)
        self.assertEqual(self.store.verify()['batches'], 1)
    def test_recovery_preserves_truncated_pending(self):
        self.agg.open(self.scope)
        folder = next(self.root.iterdir())
        path = folder/'00000001.pending'
        path.write_bytes(b'{"truncated":')
        before = path.read_bytes()
        result = recover(self.store)
        self.assertEqual(result[0]['status'], 'truncated_or_invalid_unknown')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.store.verify()['batches'], 0)
    def test_recovery_rejects_contradictory_final(self):
        self.agg.open(self.scope)
        folder = next(self.root.iterdir())
        event = self.event()
        event['padding'] = 'conflicting-content'
        pending = dict(event, receipt_sha256=digest(event))
        (folder/'00000000.pending').write_bytes(canonical(pending))
        with self.assertRaisesRegex(ValueError, 'CONTRADICTORY_PENDING'):
            recover(self.store)
        self.assertEqual(self.store.verify()['events'], 1)
    def test_serialized_event_and_batch_caps(self):
        self.agg.open(self.scope)
        with self.assertRaisesRegex(ValueError, 'BATCH_CAPACITY'):
            self.agg.add([10**4000 + i for i in range(40)])
        payload = self.event()
        payload['padding'] = 'x' * MAX_BYTES
        with self.assertRaisesRegex(ValueError, 'EVENT_CAPACITY'):
            self.store.put(payload)
        self.assertEqual(self.agg.batches, [])
    def test_manifest_contradiction_same_logical_key(self):
        self.agg.open(self.scope)
        payload = self.event()
        payload['scope']['manifest_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'CONTRADICTORY'):
            self.store.put(payload)
    def test_overlap_is_not_verified(self):
        self.agg.open(self.scope)
        self.agg.add([1])
        self.agg.flush()
        payload = self.event(1)
        payload.update(sequence=2, previous_sha256=digest(payload))
        self.store.put(payload)
        with self.assertRaisesRegex(ValueError, 'COUNTS_OR_OVERLAP'):
            self.store.verify()
    def test_closed_reopen_rejected(self):
        self.agg.open(self.scope)
        self.agg.close()
        with self.assertRaisesRegex(ValueError, 'SCOPE_REOPEN'):
            self.agg.open(self.scope)
    def test_gap_rejected(self):
        self.agg.open(self.scope)
        payload = self.event()
        payload.update(sequence=4, record_type='consumption_block')
        with self.assertRaisesRegex(ValueError, 'SEQUENCE_GAP'):
            self.store.put(payload)
    def test_reopen_active_rejected(self):
        self.agg.open(self.scope)
        with self.assertRaisesRegex(ValueError, 'SCOPE_ALREADY'):
            self.agg.open(self.scope)


if __name__ == '__main__':
    unittest.main(verbosity=2)
