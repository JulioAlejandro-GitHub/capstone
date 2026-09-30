"""SWV2.1: derive v2_runtime_contract.json from the frozen pg_v2_baseline structural manifest.

Source of truth: docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json, the certified
catalog snapshot (scripts/db/v2_catalog_probe.py) whose SHA-256 is the GATE DB-V2 structural manifest.
The projection is the one schema_contract.require_v2_capabilities reads from pg_catalog: md5 of
pg_get_functiondef for public v2_*/e04_* functions, v2_*/e04_* triggers, evaluations constraints and
uq_e04_* calibration indexes. Stdlib only; never connects to PostgreSQL.

    python scripts/db/build_v2_runtime_contract.py          # write the contract
    python scripts/db/build_v2_runtime_contract.py --check  # fail unless the committed file is identical
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'pg_v2_baseline'
SOURCE = 'docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json'
SOURCE_SHA256 = '15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb'
TARGET = ROOT / 'malaria_dl_local_project/src/malaria_dl/persistence/v2_runtime_contract.json'
PREFIXES = ('v2_', 'e04_')
TRIGGER_KEYS = ('relation', 'name', 'definition', 'tgenabled', 'tgdeferrable', 'tginitdeferred')
CONSTRAINT_KEYS = ('name', 'definition', 'condeferrable', 'condeferred', 'convalidated')
INDEX_KEYS = ('name', 'definition', 'indisvalid', 'indisready', 'indisunique', 'indnullsnotdistinct')


def build(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise SystemExit('STRUCTURAL_MANIFEST_MISMATCH: source is not the certified pg_v2_baseline manifest')
    catalog = json.loads(raw)
    functions = [f for f in catalog['functions'] if f['name'].startswith(PREFIXES)]
    if len({f['name'] for f in functions}) != len(functions):
        raise SystemExit('OVERLOADED_CONTRACT_FUNCTION: the runtime contract is keyed by function name')
    by_name = lambda row: row['name']
    contract = dict(
        revision=REVISION,
        source=dict(path=SOURCE, sha256=SOURCE_SHA256, generator='scripts/db/build_v2_runtime_contract.py'),
        functions={f['name']: hashlib.md5(f['definition'].encode()).hexdigest() for f in functions},
        triggers=sorted(({k: t[k] for k in TRIGGER_KEYS} for t in catalog['triggers'] if t['name'].startswith(PREFIXES)),
                        key=by_name),
        evaluation_constraints=sorted(({k: c[k] for k in CONSTRAINT_KEYS} for c in catalog['constraints']
                                       if c['relation'] == 'evaluations'), key=by_name),
        calibration_indexes=sorted(({k: i[k] for k in INDEX_KEYS} for i in catalog['indexes']
                                    if i['relation'] == 'evaluations' and i['name'].startswith('uq_e04_')), key=by_name),
    )
    return (json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    rendered = build((ROOT / SOURCE).read_bytes())
    if args.check:
        if not TARGET.exists() or TARGET.read_bytes() != rendered:
            sys.exit('V2_RUNTIME_CONTRACT_DRIFT: committed contract differs from the certified baseline derivation')
    else:
        TARGET.write_bytes(rendered)
    print(('CHECK PASS ' if args.check else 'WROTE ') + hashlib.sha256(rendered).hexdigest())


if __name__ == '__main__':
    main()
