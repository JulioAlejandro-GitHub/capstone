"""Read-only final reconciliation and raw/justified catalog report for D.4."""

import hashlib
import json

from certify_v2_d04_adoption import connect, directory, guard, save

from adoption_v2.check_catalog import compare
from adoption_v2.core import MANIFEST_HASH, decode
from adoption_v2.execute import catalog_snapshot, certified_catalog, reconcile

guard()
plan = decode(json.loads((directory() / "apply/plan.json").read_text()))
with connect() as c, c.transaction():
    c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    actual = catalog_snapshot(c)
    comparison = compare(c, actual, certified_catalog())
    assert not comparison["unjustified"]
    assert len(comparison["justified"]) == 4
    inventory = reconcile(c, plan)
    head = c.execute("SELECT version_num FROM alembic_version").fetchall()
    assert head == [{"version_num": "pg_v2_baseline"}]
    sequence = c.execute(
        "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
    ).fetchone()
    invalid = c.execute(
        "SELECT conname FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated"
    ).fetchall()
    assert not invalid
save("adopted_catalog.json", actual)
save(
    "final_catalog_comparison.json",
    dict(
        comparison,
        manifest_sha256=MANIFEST_HASH,
        adopted_raw_sha256=hashlib.sha256(
            json.dumps(actual, sort_keys=True, default=str).encode()
        ).hexdigest(),
        certified_raw_sha256=hashlib.sha256(
            json.dumps(certified_catalog(), sort_keys=True, default=str).encode()
        ).hexdigest(),
    ),
)
save(
    "final_reconciliation.json",
    {
        "passed": True,
        "tables": inventory,
        "head": head,
        "sequence": sequence,
        "unvalidated_constraints": invalid,
        "plan_sha256": plan["plan_sha256"],
    },
)
# Counts and checksums only; source rows and identifier mappings stay private.
save(
    "transformation_summary.json",
    {
        "preserved_tables": plan["preserved_tables"],
        "source_inventory_sha256": plan["source_inventory_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "private_mapping_file_sha256": hashlib.sha256(
            (directory() / "apply/plan.json").read_bytes()
        ).hexdigest(),
        "destination_table_counts": {k: len(v) for k, v in plan["rows"].items()},
    },
)
print("final catalog and data reconciliation passed")
