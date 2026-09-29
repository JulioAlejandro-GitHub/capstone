import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row

from adoption_v2.core import CATALOG_HASH, MANIFEST_HASH
from adoption_v2.execute import catalog_snapshot, certified_catalog
from adoption_v2.function_guard import DEPENDENCY_SQL
from alembic_v2.safety import (
    IDENTITY_SQL,
    ROLES_SQL,
    inspect_isolation,
    validate_server_snapshot,
)

A = ROOT / "docs/audits/e10_10_5d2_evidence/route_a"
E = ROOT / "docs/audits/e10_10_5d3_evidence"
t = json.loads((A / "target.json").read_text())
inspect_isolation(t)
os.environ["PGPASSFILE"] = json.loads((A / "private_paths.json").read_text())["pgpass"]
with psycopg.connect(
    host="127.0.0.1",
    port=t["host_port"],
    dbname=t["database"],
    user="capstone_v2_migrator",
    row_factory=dict_row,
    autocommit=True,
) as c:
    identity = c.execute(IDENTITY_SQL).fetchone()
    validate_server_snapshot(t, identity, c.execute(ROLES_SQL).fetchall())
    with c.transaction():
        c.execute("SET TRANSACTION READ ONLY")
        assert catalog_snapshot(c) == certified_catalog()
        deps = c.execute(DEPENDENCY_SQL).fetchall()
v = {
    "manifest_sha256": MANIFEST_HASH,
    "catalog_sha256": CATALOG_HASH,
    "identity": identity,
    "query": DEPENDENCY_SQL,
    "dependencies": deps,
    "scope": "Read-only supplement; D-03 certificate unchanged",
}
p = E / "route_a_function_dependencies.json"
assert not p.exists()
p.write_text(json.dumps(v, indent=2) + "\n")
print(hashlib.sha256(p.read_bytes()).hexdigest())
