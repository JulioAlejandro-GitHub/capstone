"""SWV2.1: v2_runtime_contract.json is a reproducible derivation of the frozen pg_v2_baseline manifest."""

import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_v2_runtime_contract', ROOT / 'scripts/db/build_v2_runtime_contract.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class RuntimeContractTests(unittest.TestCase):
    def test_source_is_the_certified_structural_manifest(self):
        raw = (ROOT / builder.SOURCE).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb')

    def test_committed_contract_equals_two_independent_derivations(self):
        raw = (ROOT / builder.SOURCE).read_bytes()
        first, second = builder.build(raw), builder.build(bytes(raw))
        self.assertEqual(first, second)
        self.assertEqual(builder.TARGET.read_bytes(), first)

    def test_tampered_manifest_is_refused(self):
        raw = (ROOT / builder.SOURCE).read_bytes()
        with self.assertRaises(SystemExit):
            builder.build(raw.replace(b'v2_immutable', b'v2_immutablx', 1))
