"""Replay only on a fresh auxiliary copy; force rollback after final catalog observation."""

import hashlib
from unittest.mock import patch

from certify_v2_d04_adoption import (
    BACKUP,
    apply_traced,
    connect,
    save,
)
from test_v2_d04_operations import data, dump, new_database, restore

from adoption_v2.core import digest, require
from adoption_v2.execute import catalog_snapshot, certified_catalog


class DiagnosticRollback(RuntimeError):
    pass


child = new_database("_d04_diagnostic")
restore(child, BACKUP, True)
backup = dump(child, "diagnostic_backup.dump")
child["backup_sha256"] = hashlib.sha256(backup.read_bytes()).hexdigest()
save("diagnostic_target.json", child)
with connect(child) as c, c.transaction():
    c.execute("SET TRANSACTION READ ONLY")
    before = data(c)
count = 0


def observe(c):
    global count
    actual = catalog_snapshot(c)
    count += 1
    if count == 2:
        expected = certified_catalog()
        save("attempted_catalog.json", actual)
        differences = {
            k: {
                "actual_only": [r for r in actual[k] if r not in expected[k]],
                "expected_only": [r for r in expected[k] if r not in actual[k]],
            }
            for k in expected
            if actual[k] != expected[k]
        }
        save("attempted_catalog_diff.json", differences)
        raise DiagnosticRollback(
            "Diagnostic final-catalog observation; mandatory rollback"
        )
    return actual


try:
    with patch("adoption_v2.execute.catalog_snapshot", side_effect=observe):
        apply_traced(child, "catalog_diagnostic", backup=backup)
except DiagnosticRollback:
    pass
else:
    raise AssertionError("Diagnostic did not reach final catalog; no certification")
with connect(child) as c, c.transaction():
    c.execute("SET TRANSACTION READ ONLY")
    after = data(c)
    head = c.execute("SELECT version_num FROM alembic_version").fetchall()
require(
    before == after and head == [{"version_num": "20260922_01"}],
    "DIAGNOSTIC_ROLLBACK_FAILED",
)
save(
    "diagnostic_rollback.json",
    {
        "passed": True,
        "catalog_unchanged": True,
        "all_tables_unchanged": True,
        "tables": len(after["tables"]),
        "before_sha256": digest(before),
        "after_sha256": digest(after),
        "head": head,
        "sequence": after["sequence"],
        "purpose": "diagnostic only; not adoption certification",
    },
)
print("Diagnostic catalog captured; exact rollback verified")
