"""Read-only catalog and cleanup of this probe's isolated synthetic sessions."""
import hashlib
import json
import subprocess
from pathlib import Path
import probe_v2_e2_projection as probe
from v2_catalog_probe import snapshot


def main():
    target = probe.guard()
    with probe.connect(target) as connection:
        catalog = snapshot(connection)
    digest = hashlib.sha256(json.dumps(catalog, sort_keys=True, default=str).encode()).hexdigest()
    # Compare the actual prior catalog, not a guessed certificate field.
    old = json.loads((probe.ROOT / 'docs/audits/e10_10_5e1_evidence/route_a/installed_catalog.json').read_text())
    assert catalog == old
    with probe.connect(target, role=probe.RUNTIME) as connection:
        gate = connection.execute('SELECT owner,db_pid FROM experiment_execution_gate').fetchone()
        assert gate == {'owner': None, 'db_pid': None}
        active = connection.execute("SELECT count(*) AS n FROM train_execution_sessions WHERE host='E2-synthetic' AND state='active'").fetchone()['n']
        assert active == 0
    protected = {}
    paths = subprocess.check_output(['git', 'ls-files', 'alembic_v2', 'adoption_v2', 'docs/audits/e10_10_5e1_evidence', 'docs/audits/e10_10_5d*_evidence', 'malaria_dl_local_project/src/malaria_dl/results/identity.py'], text=True).splitlines()
    for name in paths:
        before = subprocess.check_output(['git', 'show', 'HEAD:' + name])
        current = (probe.ROOT / name).read_bytes()
        assert before == current, name
        protected[name] = hashlib.sha256(current).hexdigest()
    (probe.E / 'preservation.json').write_text(json.dumps(dict(
        catalog_unchanged=True, catalog_sha256=digest, gate=gate,
        active_synthetic_sessions=active, protected_files=protected), indent=2) + '\n')
    print(json.dumps({'catalog_unchanged': True, 'catalog_sha256': digest,
                      'protected_files': len(protected), 'active_synthetic_sessions': active}))


if __name__ == '__main__':
    main()
