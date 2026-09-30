"""DBV2.3 authorization envelope: persistent stage never changes baseline SQL."""

import json
import tempfile
import unittest
from pathlib import Path

from alembic_v2.safety import UnsafeTarget, read_authorization


class PersistentAuthorizationTests(unittest.TestCase):
    def test_explicit_persistent_gate_required(self):
        target = {
            "authorized_stage": "DBV2.3",
            "gate_dbv22_approved": True,
            "persistent": True,
            "isolation_id": "b7994a3d-b7f7-4c87-91c4-64f001738a57",
            "database": "capstone_v2_isolated_persistent",
            "container_id": "a" * 64,
            "volume": "capstone_v2_isolated_persistent_data",
            "postgres_system_identifier": "123456789",
            "database_oid": 123,
            "host_port": 56440,
        }
        url = "postgresql+psycopg://capstone_v2_migrator@127.0.0.1:56440/capstone_v2_isolated_persistent"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "target.json"
            p.write_text(json.dumps(target))
            self.assertEqual(read_authorization(p, url), target)
            for changes in (
                {"persistent": False},
                {"gate_dbv22_approved": False},
                {"authorized_stage": "DBV2.4"},
            ):
                p.write_text(json.dumps(dict(target, **changes)))
                with self.subTest(changes=changes), self.assertRaises(UnsafeTarget):
                    read_authorization(p, url)


if __name__ == "__main__":
    unittest.main()
