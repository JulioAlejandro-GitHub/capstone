"""Test-only candidate reference injection; never promotes production pins."""
import hashlib
import json
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'docs/audits/e10_10_5e4_evidence/route_a'


@contextmanager
def candidate():
    from adoption_v2 import core, execute, planner
    report = json.loads((E/'catalog_diff.json').read_text())
    assert report['status']=='passed'
    manifest = hashlib.sha256((ROOT/'alembic_v2/baseline/catalog_manifest.json').read_bytes()).hexdigest()
    catalogue = json.loads((E/'installed_catalog.json').read_text())
    catalog_hash = hashlib.sha256(json.dumps(catalogue,sort_keys=True,default=str).encode()).hexdigest()
    assert manifest == report['manifest_sha256']
    assert catalog_hash == report['installed_sha256'] == report['expected_sha256']
    with ExitStack() as stack:
        for module,key,value in [(core,'MANIFEST_HASH',manifest),(core,'CATALOG_HASH',catalog_hash),
                                 (planner,'MANIFEST_HASH',manifest),(execute,'CATALOG_HASH',catalog_hash),
                                 (execute,'CERTIFIED_CATALOG_PATH',E/'installed_catalog.json')]:
            stack.enter_context(patch.object(module,key,value))
        yield
