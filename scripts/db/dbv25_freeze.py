"""DBV2.5: READ ONLY freeze verification of BD-v2; legacy SELECT-only; no secret output."""
import argparse
import os
import hashlib
import json
import re
import subprocess
import sys
import time
from contextlib import contextmanager
import traceback
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row
import dbv23_destination as persistent
from dbv23_source import DOCKER, OFFICIAL, metadata
from v2_catalog_probe import snapshot
from dbv24_transfer import FORMAT, TARGET, science, compare, absence, integrity, all_counts, scalar
from alembic_v2.safety import IDENTITY_SQL, ROLES_SQL, inspect_isolation, validate_server_snapshot

# DBV25_OUT lets the post-commit re-check write outside the committed evidence tree.
E = Path(os.environ.get('DBV25_OUT', ROOT / 'docs/audits/db_v2/dbv2_5'))
FREEZE_BASE_COMMIT = 'd8369f67be9a03166c3601356916529bb587b269'
TRANSFER_MANIFEST = '295ad3737e92d0e64333062f459a527026a4eacf6e9d36179ce31fbb89c33cf9'
DBV24_HASHSET = 'eaecc880b60230c281c989857db2aea8b686b914fa492847e8b31aa3845e5f4e'
FINGERPRINTS = dict(
    record_assignment_sha256='9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2',
    patient_assignment_sha256='cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f',
    clinical_identity_sha256='d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59',
    source_population_sha256='eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0')
XAI = sorted(['xai_method_configurations', 'xai_evidence', 'xai_artifacts', 'xai_region_attributions',
              'xai_evaluation_protocols', 'xai_quantitative_evaluations', 'xai_evaluation_members',
              'xai_interpretations', 'xai_specialist_reviews'])
COUNTS = dict(tables=104, views=33, FK=251, CHECK=518, UNIQUE=77, PK=104, indexes=413, indexes_physical=414, functions=79, triggers=105)
E10 = re.compile(r'^(experiment|run_|campaign|training|evaluation|prediction|calibration|deployment|publication|smear|clinical_workflow|model_)')


def save(name, obj):
    (E / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, check=True).stdout


@contextmanager
def v2():
    creds = json.loads((persistent.PRIVATE / 'credentials.json').read_text())
    c = psycopg.connect(host='127.0.0.1', port=TARGET['host_port'], dbname=TARGET['database'], user='capstone_v2_migrator',
                        password=creds['capstone_v2_migrator'], autocommit=True, row_factory=dict_row,
                        options='-c default_transaction_read_only=on ' + FORMAT, application_name='DBV2.5_READ_ONLY')
    del creds
    try:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        assert scalar(c, "SELECT current_setting('transaction_read_only')") == 'on'
        yield c
    finally:
        c.execute('ROLLBACK')
        c.close()


@contextmanager
def legacy():
    m = metadata()
    old = json.loads((ROOT / 'docs/audits/db_v2/dbv2_3/source_identity.json').read_text())
    assert m == old['environment'], 'SOURCE_IDENTITY_DRIFT'
    proc = subprocess.run(DOCKER + ['inspect', m['container_id']], capture_output=True, text=True, check=True)
    env = dict(s.split('=', 1) for s in json.loads(proc.stdout)[0]['Config']['Env'])
    c = psycopg.connect(host='127.0.0.1', port=m['host_port'], dbname=m['database'], user=m['role'], password=env.get('POSTGRES_PASSWORD'),
                        autocommit=True, row_factory=dict_row, options='-c default_transaction_read_only=on ' + FORMAT,
                        application_name='DBV2.5_LEGACY_READ_ONLY')
    del env, proc
    try:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        i = c.execute("SELECT current_database() AS database,current_setting('server_version_num') AS version,system_identifier::text AS system_identifier,current_setting('transaction_read_only') AS transaction_read_only,current_setting('default_transaction_read_only') AS default_transaction_read_only,current_setting('transaction_isolation') AS isolation FROM pg_control_system()").fetchone()
        assert i['database'] == old['server']['database'] and i['system_identifier'] == old['server']['system_identifier']
        assert i['transaction_read_only'] == i['default_transaction_read_only'] == 'on' and i['isolation'] == 'repeatable read'
        yield c, i
    finally:
        c.execute('ROLLBACK')
        c.close()


def baseline():
    """Baseline files: re-hash from disk and prove identical to the GATE DBV2.4 commit."""
    persistent.verify_baseline()
    rev = ROOT / 'alembic_v2/versions/20260929_01_pg_v2_baseline.py'
    res = json.loads((ROOT / 'alembic_v2/baseline/catalog_manifest.json').read_text())
    frozen = ['alembic_v2', 'alembic_v2.ini', 'docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json']
    drift = git('diff', '--name-only', FREEZE_BASE_COMMIT, '--', *frozen).split()
    untracked = git('ls-files', '--others', '--exclude-standard', '--', *frozen).split()
    assert not drift and not untracked, 'BASELINE_MODIFIED'
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    s = ScriptDirectory.from_config(Config(str(ROOT / 'alembic_v2.ini')))
    revs = list(s.walk_revisions())
    alembic = dict(revisions=[r.revision for r in revs], revision=revs[0].revision, down_revision=revs[0].down_revision,
                   roots=len(s.get_bases()), heads=len(s.get_heads()))
    assert alembic == dict(revisions=['pg_v2_baseline'], revision='pg_v2_baseline', down_revision=None, roots=1, heads=1)
    return dict(root_revision_file=str(rev.relative_to(ROOT)), root_revision_sha256=sha(rev),
                structural_manifest_file='docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json',
                structural_manifest_file_sha256=sha(ROOT / 'docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json'),
                resource_manifest_sha256=sha(ROOT / 'alembic_v2/baseline/catalog_manifest.json'),
                resources={k: v for k, v in sorted(res['files'].items())}, resources_verified=len(res['files']),
                diff_vs_gate_dbv24_commit=drift, untracked=untracked, alembic_static=alembic,
                safety_py_sha256=sha(ROOT / 'alembic_v2/safety.py'))


def dbv24_evidence():
    d = ROOT / 'docs/audits/db_v2/dbv2_4'
    lines = (d / 'dbv2_4_hashes.sha256').read_text().splitlines()
    bad = [p for h, p in (l.split('  ', 1) for l in lines) if sha(ROOT / p) != h]
    tracked = set(git('ls-files', 'docs/audits/db_v2/dbv2_4').split())
    r = dict(files=len(lines), mismatches=bad, all_tracked=all(l.split('  ', 1)[1] in tracked for l in lines),
             hashset_sha256=sha(d / 'dbv2_4_hashes.sha256'), transfer_manifest_sha256=sha(d / 'dbv2_4_transfer_manifest.json'))
    assert r['files'] == 67 and not bad and r['all_tracked'] and r['hashset_sha256'] == DBV24_HASHSET and r['transfer_manifest_sha256'] == TRANSFER_MANIFEST
    return dict(r, status='PASS')


def identity():
    inspect_isolation(TARGET)
    with v2() as c:
        i = c.execute(IDENTITY_SQL).fetchone()
        # safety.py requires a writable session (migration semantics); DBV2.5 sessions are READ ONLY by design,
        # so the frozen guard receives the server-level mode, and the session read-only state is asserted separately.
        assert i['read_only'] == 'on' and i['recovery'] is False
        server_mode = scalar(c, "SELECT boot_val FROM pg_settings WHERE name='default_transaction_read_only'")
        validate_server_snapshot(TARGET, dict(i, read_only=server_mode), c.execute(ROLES_SQL).fetchall())
        i['server_version'] = scalar(c, 'SHOW server_version')
    d = json.loads(subprocess.run(DOCKER + ['inspect', TARGET['container_id']], capture_output=True, text=True, check=True).stdout)[0]
    v = json.loads(subprocess.run(DOCKER + ['volume', 'inspect', TARGET['volume']], capture_output=True, text=True, check=True).stdout)[0]
    docker = dict(container_id=d['Id'], container_name=d['Name'].lstrip('/'), running=d['State']['Running'], image=d['Config']['Image'],
                  labels=d['Config']['Labels'], port_bindings=d['HostConfig']['PortBindings'], restart_policy=d['HostConfig']['RestartPolicy']['Name'],
                  mounts=[dict(type=m['Type'], name=m.get('Name'), destination=m['Destination'], rw=m['RW']) for m in d['Mounts']],
                  volume=dict(name=v['Name'], driver=v['Driver'], labels=v['Labels'], created_at=v['CreatedAt']),
                  compose_project=d['Config']['Labels'].get('com.docker.compose.project'))
    r = dict(database=i['database'], database_oid=i['database_oid'], system_identifier=i['system_identifier'],
             server_version=i['server_version'], server_version_num=i['server_version_num'], recovery=i['recovery'], docker=docker)
    assert (r['database'], r['database_oid'], r['system_identifier'], r['server_version_num']) == ('capstone_v2_isolated_persistent', 16386, '7691366089693499436', 170009)
    assert r['server_version'].split()[0] == '17.9'
    assert docker['container_name'] == 'capstone_db_v2' and docker['port_bindings'] == {'5432/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '56440'}]}
    assert docker['mounts'] == [dict(type='volume', name='capstone_v2_isolated_persistent_data', destination='/var/lib/postgresql/data', rw=True)]
    assert docker['compose_project'] is None and docker['labels'].get('org.capstone.pgv2.lifecycle') == 'persistent'
    return r


def structure(c):
    obj = snapshot(c)
    digest = hashlib.sha256((json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()).hexdigest()
    # Same derivation as scripts/db/certify_dbv22.py catalog(); 413 = 414 physical indexes minus alembic_version PK.
    counts = dict(views=len(obj['views']), triggers=len(obj['triggers']), indexes_physical=len(obj['indexes']),
                  indexes=sum(r['relation'] != 'alembic_version' for r in obj['indexes']),
                  tables=sum(r['relkind'] == 'r' and r['name'] != 'alembic_version' for r in obj['relations']),
                  functions=sum(r['extension'] is None for r in obj['functions']))
    for k, n in [('p', 'PK'), ('f', 'FK'), ('c', 'CHECK'), ('u', 'UNIQUE')]:
        counts[n] = sum(r['contype'] == k and r['relation'] != 'alembic_version' for r in obj['constraints'])
    tables = sorted(r['name'] for r in obj['relations'] if r['relkind'] == 'r')
    xai = [t for t in tables if t.startswith('xai_')]
    col = [x for x in obj['columns'] if x['name'] == 'clinical_target_recall']
    chk = [x['definition'] for x in obj['constraints'] if x['contype'] == 'c' and 'clinical_target_recall' in x['definition']]
    default = c.execute("SELECT count(*) AS n FROM pg_attrdef d JOIN pg_attribute a ON a.attrelid=d.adrelid AND a.attnum=d.adnum WHERE a.attname='clinical_target_recall'").fetchone()['n']
    recall = dict(relation=col[0]['relation'], type=col[0]['type'], not_null=col[0]['attnotnull'], default_count=default, checks=chk)
    pk_missing = [t for t in tables if not any(r['relation'] == t and r['contype'] == 'p' for r in obj['constraints'])]
    r = dict(structural_manifest_sha256=digest, counts=counts, alembic_version_table=('alembic_version' in tables),
             application_tables=len(tables) - 1, pk_missing=pk_missing, xai_tables=xai, xai_explanations_present='xai_explanations' in tables,
             clinical_target_recall=recall, extensions=obj['extensions'], identity_or_generated_columns=[
                 dict(relation=x['relation'], name=x['name'], identity=x['attidentity'], generated=x['attgenerated'])
                 for x in obj['columns'] if x['attidentity'] or x['attgenerated']],
             owners=sorted({r.get('owner') for r in obj['relations']} - {None}), schema_acl=obj['schema_acl'], database_acl=obj['database_acl'],
             note='E-04 invariants, R1 correction, ownership, ACL, types and trigger bodies are all part of the hashed snapshot; identical digest => identical contract.')
    assert digest == persistent.EXPECTED_MANIFEST, 'STRUCTURAL_MANIFEST_DRIFT'
    assert all(counts[k] == v for k, v in COUNTS.items()), counts
    assert xai == XAI and not r['xai_explanations_present'] and not pk_missing
    assert recall == dict(relation='run_configurations', type='numeric', not_null=True, default_count=0,
                          checks=['CHECK (((clinical_target_recall > (0)::numeric) AND (clinical_target_recall <= (1)::numeric)))'])
    return r


def data(c, s):
    sci = science(c)
    assert sci == science(s), 'SCIENTIFIC_SNAPSHOT_DIVERGES_FROM_LEGACY'
    stored = c.execute("SELECT methodology_json->'freeze_contract'->'fingerprints' AS f, frozen_at, status FROM dataset_versions WHERE id=%s", (OFFICIAL,)).fetchone()
    fp = {k: stored['f'].get(k) for k in FINGERPRINTS}
    assert fp == FINGERPRINTS, 'FINGERPRINT_DRIFT'
    legacy_frozen_at = s.execute('SELECT frozen_at FROM dataset_versions WHERE id=%s', (OFFICIAL,)).fetchone()['frozen_at']
    assert stored['frozen_at'] is not None and stored['frozen_at'] == legacy_frozen_at, 'FROZEN_AT_DRIFT'
    tables, auth = compare(s, c)  # exact row equality incl. password_hash, compared in memory only
    absent = absence(c)
    counts = all_counts(c)
    xai_rows = {t: counts[t] for t in XAI}
    e10_rows = {t: n for t, n in counts.items() if E10.match(t) and t != 'experiment_execution_gate'}
    audit = {t: n for t, n in counts.items() if 'audit' in t}
    assert not any(xai_rows.values()) and not any(e10_rows.values()) and not any(audit.values())
    integ = integrity(c)
    return dict(dataset_version_id=OFFICIAL, status=stored['status'], frozen_at=stored['frozen_at'], frozen_at_equals_legacy=True,
                scientific_snapshot=sci, fingerprints=fp, fingerprints_match=True, tables=tables, authentication=auth,
                absence=absent, xai_rows=xai_rows, e10_rows=e10_rows, audit_rows=audit,
                integrity=dict((k, v) for k, v in integ.items() if k != 'queries'), integrity_checks=len(integ['queries']))


def stats(c):
    return c.execute("SELECT xact_commit,tup_inserted,tup_updated,tup_deleted FROM pg_stat_database WHERE datname=current_database()").fetchone()


def verify(label):
    ident = identity()
    with v2() as c, legacy() as (s, li):
        c.execute('SELECT pg_stat_clear_snapshot()')
        before = stats(c)
        st = structure(c)
        rev = scalar(c, 'SELECT version_num FROM alembic_version')
        assert rev == 'pg_v2_baseline' and scalar(c, 'SELECT count(*) FROM alembic_version') == 1
        d = data(c, s)
        secret = c.execute('SELECT password_hash FROM users').fetchone()['password_hash']
    r = dict(label=label, identity=ident, alembic_version=rev, structure=st, data=d, legacy_session=li, v2_stats=before,
             destination_session='REPEATABLE READ READ ONLY; default_transaction_read_only=on')
    return r, secret


def secret_scan(secret):
    """Look for the live password hash and DB credentials in all BD-v2 artefacts; report only counts.
    High-entropy secrets (password hash, 64-char v2 credentials) are matched as raw substrings; a short legacy
    password (<8 chars, a dictionary word that also occurs in schema text) only counts in a credential context."""
    creds = json.loads((persistent.PRIVATE / 'credentials.json').read_text())
    proc = subprocess.run(DOCKER + ['inspect', 'capstone_db'], capture_output=True, text=True, check=True)
    legacy_pw = dict(s.split('=', 1) for s in json.loads(proc.stdout)[0]['Config']['Env']).get('POSTGRES_PASSWORD') or ''
    strong = [secret] + list(creds.values()) + ([legacy_pw] if len(legacy_pw) >= 8 else [])
    assert all(len(n) >= 8 for n in strong)
    weak = [re.compile(r'(?i)(pass(word)?|pwd|secret)["\']?\s*[:=]\s*["\']?' + re.escape(legacy_pw) + r'\b|:' + re.escape(legacy_pw) + '@')] if 0 < len(legacy_pw) < 8 else []
    del creds, proc, legacy_pw
    paths = {ROOT / p for p in git('ls-files', 'docs/audits/db_v2', 'scripts/db', 'alembic_v2', 'alembic_v2.ini', 'tests/db_v2').split()}
    paths |= {p for p in E.iterdir() if p.is_file()}
    paths |= {ROOT / 'scripts/db/dbv25_freeze.py'}
    texts = {p: p.read_bytes().decode('utf-8', 'replace') for p in paths}
    hits = sorted(str(p.relative_to(ROOT)) for p, t in texts.items() if any(n in t for n in strong) or any(w.search(t) for w in weak))
    del strong, weak
    url = re.compile(r'postgres(?:ql)?(?:\+\w+)?://[^:/@\s"]+:([^@\s"$]+)@')
    url_hits = sorted(str(p.relative_to(ROOT)) for p, t in texts.items() if any(not m.group(1).startswith('{') for m in url.finditer(t)))
    return dict(files_scanned=len(paths), secret_hits=len(hits), secret_hit_files=hits, url_with_inline_password_files=url_hits,
                checked=['users.password_hash (live value, in memory)', 'capstone_v2 credentials (postgres, migrator, runtime)',
                         'legacy POSTGRES_PASSWORD (credential-context match: short dictionary word)', 'URLs with literal inline password'],
                result='PASS' if not hits and not url_hits else 'FAIL')


def app_database_url():
    """Only booleans: whether the application points to BD-v2. Never the URL itself."""
    d = json.loads(subprocess.run(DOCKER + ['inspect', 'capstone_backend'], capture_output=True, text=True, check=True).stdout)[0]
    url = next((v.split('=', 1)[1] for v in d['Config']['Env'] if v.startswith('DATABASE_URL=')), '')
    u = urlsplit(url)
    env_file = (ROOT / '.env').read_text()
    r = dict(backend_database_url_present=bool(url), backend_host_is_legacy_service=u.hostname == 'db', backend_port=u.port,
             backend_points_to_v2=('capstone_v2' in url or '56440' in url), dotenv_mentions_v2=('capstone_v2' in env_file or '56440' in env_file),
             compose_file_tracked_changes=git('status', '--short', '--', 'docker-compose.yml').strip(),
             backend_compose_project=d['Config']['Labels'].get('com.docker.compose.project'))
    del url, u, env_file
    assert not r['backend_points_to_v2'] and not r['dotenv_mentions_v2'] and r['backend_host_is_legacy_service']
    return dict(r, application_database_url_switched_to_v2=False)


def docker_state():
    rows = subprocess.run(DOCKER + ['ps', '-a', '--format', '{{json .}}'], capture_output=True, text=True, check=True).stdout.splitlines()
    out = []
    for line in rows:
        x = json.loads(line)
        out.append(dict(name=x['Names'], id=x['ID'], image=x['Image'], state=x['State'], ports=x['Ports'], labels_compose_project=next(
            (l.split('=', 1)[1] for l in x['Labels'].split(',') if l.startswith('com.docker.compose.project=')), None), mounts=x['Mounts']))
    tmp = []
    for name in ['capstone_v2_isolated_fafc32d0d3a3', 'capstone_v2_isolated_1621252d7ab4']:
        d = json.loads(subprocess.run(DOCKER + ['inspect', name], capture_output=True, text=True, check=True).stdout)[0]
        tmp.append(dict(name=name, id=d['Id'], running=d['State']['Running'], labels=d['Config']['Labels'],
                        mounts=[m.get('Name') for m in d['Mounts']], port=d['HostConfig']['PortBindings']))
    return dict(containers=sorted(out, key=lambda r: r['name']), dbv24_disposables=tmp)


def restart():
    before, _ = verify('before_restart')
    subprocess.run(DOCKER + ['stop', '--time', '30', TARGET['container_id']], capture_output=True, check=True)
    stopped = json.loads(subprocess.run(DOCKER + ['inspect', TARGET['container_id']], capture_output=True, text=True, check=True).stdout)[0]['State']['Running']
    subprocess.run(DOCKER + ['start', TARGET['container_id']], capture_output=True, check=True)
    for _ in range(60):
        if subprocess.run(DOCKER + ['exec', TARGET['container_id'], 'pg_isready', '-U', 'postgres'], capture_output=True).returncode == 0:
            break
        time.sleep(1)
    time.sleep(2)
    after, _ = verify('after_restart')
    strip = lambda r: {k: v for k, v in r.items() if k not in ('label', 'legacy_session', 'v2_stats')}
    same = strip(before) == strip(after)
    same_stats = {k: before['v2_stats'][k] for k in ('tup_inserted', 'tup_updated', 'tup_deleted')} == {k: after['v2_stats'][k] for k in ('tup_inserted', 'tup_updated', 'tup_deleted')}
    assert same and stopped is False, 'RESTART_CHANGED_STATE'
    r = dict(status='PASS', stopped_observed=True, same_container_id=True, volume_removed=False, recreated=False,
             identical_before_after=same, v2_row_write_counters_unchanged=same_stats,
             before=before['v2_stats'], after=after['v2_stats'], identity_after=after['identity'])
    save('dbv2_5_persistence.json', r)
    return r


def main():
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['verify', 'restart', 'final'])
    act = a.parse_args().action
    E.mkdir(exist_ok=True)
    if act == 'verify':
        base = baseline()
        ev = dbv24_evidence()
        r, secret = verify('freeze')
        assert base['root_revision_sha256'] == persistent.EXPECTED_REVISION
        save('dbv2_5_baseline_files.json', base)
        save('dbv2_5_dbv24_evidence.json', ev)
        save('dbv2_5_verification.json', r)
        save('dbv2_5_docker_state.json', docker_state())
        save('dbv2_5_database_url.json', app_database_url())
        scan = secret_scan(secret)
        del secret
        save('dbv2_5_secret_scan.json', scan)
        assert scan['result'] == 'PASS', 'SECRETS_IN_EVIDENCE'
    elif act == 'restart':
        restart()
    elif act == 'final':
        base = baseline()
        r, secret = verify('final')
        scan = secret_scan(secret)
        del secret
        assert scan['result'] == 'PASS'
        save('dbv2_5_final_check.json', dict(baseline_root_revision_sha256=base['root_revision_sha256'], result=r, secret_scan=scan))
    print(act.upper(), 'PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never serialize PostgreSQL DETAIL, query parameters or user rows.
        safe = dict(status='BLOCKED', error_type=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None),
                    at=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)])
        if isinstance(error, AssertionError) and error.args and isinstance(error.args[0], (str, dict)):
            safe['invariant'] = error.args[0]
        E.mkdir(exist_ok=True)
        save('blocked.json', safe)
        print(json.dumps(safe, default=str))
        sys.exit(1)
