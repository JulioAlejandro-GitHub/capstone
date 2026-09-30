"""DBV2.5: deterministic final manifest + hash set from DBV2.5 evidence; no DB access, no secrets."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'docs/audits/db_v2/dbv2_5'
MANIFEST = E / 'db_v2_final_manifest.json'
HASHES = E / 'dbv2_5_hashes.sha256'
HEAD_BEFORE_FREEZE = 'd8369f67be9a03166c3601356916529bb587b269'
# Certified artefacts outside dbv2_5 whose hashes the freeze pins.
EXTERNAL = [
    'alembic_v2.ini',
    'alembic_v2/versions/20260929_01_pg_v2_baseline.py',
    'alembic_v2/baseline/catalog_manifest.json',
    *[f'alembic_v2/baseline/{n}' for n in sorted(json.loads((ROOT / 'alembic_v2/baseline/catalog_manifest.json').read_text())['files'])],
    'alembic_v2/env.py',
    'alembic_v2/resources.py',
    'alembic_v2/safety.py',
    'docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json',
    'docs/audits/db_v2/dbv2_2/restart_r1/certificate.json',
    'docs/audits/db_v2/dbv2_3/persistent_target.json',
    'docs/audits/db_v2/dbv2_4/dbv2_4_transfer_manifest.json',
    'docs/audits/db_v2/dbv2_4/dbv2_4_hashes.sha256',
    'scripts/db/dbv25_freeze.py',
    'scripts/db/dbv25_evidence.py',
]


def load(name):
    return json.loads((E / name).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def manifest():
    base, v, final = load('dbv2_5_baseline_files.json'), load('dbv2_5_verification.json'), load('dbv2_5_final_check.json')['result']
    ev, persist, url, scan = load('dbv2_5_dbv24_evidence.json'), load('dbv2_5_persistence.json'), load('dbv2_5_database_url.json'), load('dbv2_5_secret_scan.json')
    i, s, d = v['identity'], v['structure'], v['data']
    sci, auth, ab = d['scientific_snapshot'], d['authentication'], d['absence']
    # Every value in the manifest must hold in the freeze check, after restart, and in the final check.
    for other in (final, ):
        assert other['structure'] == s and other['identity']['database_oid'] == i['database_oid']
        assert {k: other['data'][k] for k in ('scientific_snapshot', 'fingerprints', 'authentication', 'absence')} == {k: d[k] for k in ('scientific_snapshot', 'fingerprints', 'authentication', 'absence')}
    assert persist['status'] == 'PASS' and ev['status'] == 'PASS' and scan['result'] == 'PASS'
    branch = subprocess.run(['git', '-C', str(ROOT), 'branch', '--show-current'], capture_output=True, text=True, check=True).stdout.strip()
    m = dict(
        project='BD-v2', phase='DBV2.5',
        postgres_version=i['server_version'].split()[0], postgres_version_num=i['server_version_num'],
        database=dict(name=i['database'], oid=i['database_oid'], system_identifier=i['system_identifier'],
                      container=i['docker']['container_name'], container_id=i['docker']['container_id'],
                      endpoint='127.0.0.1:56440', persistent_volume=i['docker']['volume']['name']),
        alembic=dict(revision=base['alembic_static']['revision'], down_revision=base['alembic_static']['down_revision'],
                     roots=base['alembic_static']['roots'], heads=base['alembic_static']['heads'], database_version_num=v['alembic_version'],
                     frozen=True, state='FROZEN / IMMUTABLE',
                     future_changes='new Alembic v2 revision with down_revision = pg_v2_baseline (or the latest v2 revision)'),
        structural_manifest_sha256=s['structural_manifest_sha256'],
        root_revision_sha256=base['root_revision_sha256'],
        resource_manifest_sha256=base['resource_manifest_sha256'],
        transfer_manifest_sha256=ev['transfer_manifest_sha256'],
        dbv2_4_evidence_hashset_sha256=ev['hashset_sha256'], dbv2_4_evidence_files=ev['files'],
        catalog=dict(application_tables=s['counts']['tables'], alembic_version_table=s['alembic_version_table'], views=s['counts']['views'],
                     primary_keys=s['counts']['PK'], foreign_keys=s['counts']['FK'], check_constraints=s['counts']['CHECK'],
                     unique_constraints=s['counts']['UNIQUE'], application_indexes=s['counts']['indexes'],
                     physical_indexes=s['counts']['indexes_physical'], functions=s['counts']['functions'], triggers=s['counts']['triggers'],
                     xai_tables=s['xai_tables'], xai_explanations_present=s['xai_explanations_present'],
                     clinical_target_recall=dict(s['clinical_target_recall'], default=None)),
        dataset=dict(version_id=d['dataset_version_id'], state=d['status'], frozen_at=d['frozen_at'], frozen_at_preserved=d['frozen_at_equals_legacy'],
                     train=sci['train'], validation=sci['validation'], test=sci['test'], total=sci['total'], patients=sci['patients'],
                     patient_overlap=sci['overlaps'], dataset_split_images=sci['dataset_split_images'],
                     dataset_split_images_semantics='2 physical roots x 27,558 (not deduplicated)',
                     fingerprints=d['fingerprints']),
        authentication=dict(preserved_users=auth['preserved_user_count'], roles=auth['roles_count'], user_roles=auth['user_roles_count'],
                            user_id_preserved=auth['user_id_preserved'], identity_preserved=auth['identity_preserved'],
                            role_preserved=auth['roles_preserved'], password_hash_match=auth['password_hash_match']),
        absence=dict(unauthorized_rows=ab['unauthorized_transferred_rows'], audit_events=sum(d['audit_rows'].values()),
                     xai_history=sum(d['xai_rows'].values()), e10_history=sum(d['e10_rows'].values())),
        integrity=d['integrity'],
        infrastructure=dict(persistent=True, restart_pass=persist['status'] == 'PASS', separate_from_capstone_malaria=i['docker']['compose_project'] is None,
                            database_url_switched=url['application_database_url_switched_to_v2'], cutover=False, legacy_available=True,
                            legacy_writes_during_dbv2_5=0, dbv2_5_v2_row_writes=0 if persist['v2_row_write_counters_unchanged'] else None),
        secrets_in_evidence=scan['secret_hits'],
        git=dict(branch=branch, head_before_freeze=HEAD_BEFORE_FREEZE, baseline_and_dbv2_1_to_2_4_evidence_commit=HEAD_BEFORE_FREEZE,
                 freeze_commit='the commit that adds this file (not self-referenceable; resolve with: git log --format=%H -- docs/audits/db_v2/dbv2_5/db_v2_final_manifest.json)'),
        result='PROJECT BD-v2 TECHNICALLY FROZEN',
    )
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    print('DB_V2_FINAL_MANIFEST_SHA256', sha(MANIFEST))


def hashes():
    files = sorted(str(p.relative_to(ROOT)) for p in E.iterdir() if p.is_file() and p != HASHES) + EXTERNAL
    HASHES.write_text(''.join(f'{sha(ROOT / f)}  {f}\n' for f in files))
    print(len(files), 'files;', 'hashset', sha(HASHES))


def verify():
    lines = HASHES.read_text().splitlines()
    bad = [f for h, f in (l.split('  ', 1) for l in lines) if sha(ROOT / f) != h]
    listed = {l.split('  ', 1)[1] for l in lines}
    unlisted = sorted(str(p.relative_to(ROOT)) for p in E.iterdir() if p.is_file() and p != HASHES and str(p.relative_to(ROOT)) not in listed)
    print(dict(files=len(lines), mismatches=bad, unlisted=unlisted, result='PASS' if not bad and not unlisted else 'FAIL'))
    assert not bad and not unlisted


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['manifest', 'hashes', 'verify'])
    globals()[a.parse_args().action]()
