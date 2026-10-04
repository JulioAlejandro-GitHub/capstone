"""C2.12 read-only prerequisite evidence; fail closed before synthetic writes."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.db import read_only_transaction
from src.malaria_dl.execution.schema import require_e10_schema


QUERIES = {
    "server": """SELECT current_setting('server_version') AS version,
        current_schema() AS schema,
        current_setting('transaction_read_only') AS read_only,
        has_database_privilege(current_user,current_database(),'CREATE') AS can_create_schema""",
    "revision": "SELECT version_num FROM alembic_version",
    "gate": "SELECT owner IS NOT NULL AS occupied FROM experiment_execution_gate",
    "ownership_function": """SELECT proname,prosecdef,proconfig FROM pg_proc
        WHERE oid=to_regprocedure('experiment_require_owner()')""",
    "tables": """SELECT tablename FROM pg_tables WHERE schemaname=current_schema()
        AND tablename IN ('experimental_campaigns','campaign_configurations','runs',
        'run_configurations','train_execution_records','evaluations',
        'run_threshold_calibration','run_clinical_metrics') ORDER BY tablename""",
    "temporary_schemas": """SELECT nspname FROM pg_namespace
        WHERE nspname LIKE 'capstone_test_%' ORDER BY nspname""",
}


def main() -> int:
    evidence: dict = {"observed_at": datetime.now(timezone.utc).isoformat()}
    with read_only_transaction("malaria") as connection:
        assert connection.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        evidence["queries"] = {
            name: [dict(row) for row in connection.execute(text(sql)).mappings()]
            for name, sql in QUERIES.items()
        }
        evidence["event_schema"] = require_e10_schema(connection)
    reasons = []
    if not evidence["queries"]["server"][0]["can_create_schema"]:
        reasons.append("Configured role cannot create an isolated schema")
    if any("search_path=public, pg_catalog" in (row["proconfig"] or [])
           for row in evidence["queries"]["ownership_function"]):
        reasons.append("Ownership guard is bound to public; search_path alone cannot isolate it")
    # A newly granted permission is not proof of an isolated v2 fixture. Never
    # silently fall through to operational writes or legacy schema migrations.
    reasons.append("No certified v2 isolation fixture for independent committed event transactions")
    evidence.update(status="BLOCKED", reasons=reasons, writes_performed=0,
                    integration_tests_executed=0, cleanup="No objects or rows created")
    print(json.dumps(evidence, indent=2, default=str))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
