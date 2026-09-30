"""Read-only E preflight. Never falls back to migrator for runtime operations."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'docs/audits/e10_10_5e_evidence/instance'
sys.path[:0] = [str(ROOT), str(ROOT / 'malaria_dl_local_project')]


def main():
    from sqlalchemy import create_engine, text
    from alembic_v2.safety import inspect_isolation, read_authorization, verify_connection
    from src.malaria_dl.execution.schema import require_e10_schema, E10SchemaNotReady

    target = json.loads((E / 'target.json').read_text())
    assert target['authorized_stage'] == 'E10.10.5E' and target['gate_d_approved'] is True
    os.environ['PGPASSFILE'] = json.loads((E / 'private_paths.json').read_text())['pgpass']
    url = f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{target['host_port']}/{target['database']}"
    read_authorization(E / 'target.json', url)
    inspect_isolation(target)
    result = {'scope': 'isolated E, SELECT only', 'operational_access': False}
    engine = create_engine(url)
    try:
        with engine.connect() as c:
            verify_connection(c, target)
            result['migrator_read_only_diagnostic'] = require_e10_schema(c)
            result['runtime_revision_select'] = c.execute(text(
                "SELECT has_table_privilege('capstone_v2_runtime','public.alembic_version','SELECT')"
            )).scalar_one()
            result['runtime_is_superuser'] = c.execute(text(
                "SELECT rolsuper FROM pg_roles WHERE rolname='capstone_v2_runtime'"
            )).scalar_one()
    finally:
        engine.dispose()
    engine = create_engine(url.replace('capstone_v2_migrator@', 'capstone_v2_runtime@'))
    try:
        with engine.connect() as c:
            try:
                result['runtime'] = require_e10_schema(c)
            except E10SchemaNotReady as exc:
                result['runtime_rejection'] = str(exc)
    finally:
        engine.dispose()
    result['manifest_sha256'] = hashlib.sha256((ROOT / 'alembic_v2/baseline/catalog_manifest.json').read_bytes()).hexdigest()
    result['integration_ready'] = 'runtime' in result
    (E.parent / 'runtime_preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['integration_ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
