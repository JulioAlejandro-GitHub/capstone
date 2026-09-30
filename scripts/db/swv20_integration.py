"""SWV2.0: READ ONLY continuity checks of the certified BD-v2 across its Compose integration.

Reuses the DBV2.4/DBV2.5 derivations (structural snapshot, transfer hashes, scientific snapshot)
against a parametrized endpoint. Never prints or stores credentials or the application password hash.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psycopg
from psycopg.rows import dict_row
import dbv23_destination as persistent
from dbv23_source import DATASET, USER, DOCKER, OFFICIAL
from dbv24_transfer import FORMAT, science, hashes, integrity, absence, scalar
from dbv25_freeze import structure, baseline, FINGERPRINTS, XAI

E = ROOT / 'docs/audits/sw_v2/swv2_0'
PRIVATE = ROOT / 'var/maintenance/swv20'  # gitignored (/var/maintenance/)
SYSID = '7691366089693499436'
OID = 16386
MANIFEST = persistent.EXPECTED_MANIFEST
TRANSFER = json.loads((ROOT / 'docs/audits/db_v2/dbv2_4/dbv2_4_transfer_manifest.json').read_text())
DBV25 = json.loads((ROOT / 'docs/audits/db_v2/dbv2_5/dbv2_5_final_check.json').read_text())['result']


def save(name, obj):
    E.mkdir(parents=True, exist_ok=True)
    (E / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + '\n')


def normalize(obj):
    return json.loads(json.dumps(obj, sort_keys=True, default=str))


def dotenv(key):
    for line in (ROOT / '.env').read_text().splitlines():
        if line.startswith(key + '='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise KeyError(key)


@contextmanager
def session(port, database, role='capstone_v2_migrator'):
    """READ ONLY REPEATABLE READ session. `julio` uses the Compose .env credential (the DBeaver one)."""
    if role == 'julio':
        assert dotenv('POSTGRES_USER') == 'julio'
        password = dotenv('POSTGRES_PASSWORD')
    else:
        password = json.loads((persistent.PRIVATE / 'credentials.json').read_text())[role]
    c = psycopg.connect(host='127.0.0.1', port=port, dbname=database, user=role, password=password, autocommit=True,
                        row_factory=dict_row, options='-c default_transaction_read_only=on ' + FORMAT,
                        application_name='SWV2.0_READ_ONLY', connect_timeout=5)
    del password
    try:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        assert scalar(c, "SELECT current_setting('transaction_read_only')") == 'on'
        yield c
    finally:
        c.execute('ROLLBACK')
        c.close()


def identity(c):
    return c.execute("""SELECT current_database() AS database, current_user AS role,
        (SELECT oid::bigint FROM pg_database WHERE datname=current_database()) AS database_oid,
        (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) AS database_owner,
        (SELECT system_identifier::text FROM pg_control_system()) AS system_identifier,
        current_setting('server_version') AS server_version,
        current_setting('server_version_num')::int AS server_version_num, pg_is_in_recovery() AS recovery,
        inet_server_port() AS server_port""").fetchone()


def cluster(c):
    """Cluster-wide facts that are not part of the structural manifest (names/flags only, no secrets)."""
    return dict(
        databases=c.execute('SELECT datname, oid::bigint AS oid, pg_get_userbyid(datdba) AS owner, datallowconn, datistemplate, datacl::text FROM pg_database ORDER BY oid').fetchall(),
        roles=c.execute("SELECT rolname, rolsuper, rolcanlogin, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname !~ '^pg_' ORDER BY rolname").fetchall(),
        connections=c.execute("SELECT datname, usename, application_name, state FROM pg_stat_activity WHERE backend_type='client backend' AND pid<>pg_backend_pid() ORDER BY 1,2,3").fetchall())


def docker_identity(name):
    d = json.loads(subprocess.run(DOCKER + ['inspect', name], capture_output=True, text=True, check=True).stdout)[0]
    lab = d['Config']['Labels'] or {}
    return dict(container_id=d['Id'], container_name=d['Name'].lstrip('/'), image=d['Config']['Image'], running=d['State']['Running'],
                health=(d['State'].get('Health') or {}).get('Status'), restart_policy=d['HostConfig']['RestartPolicy']['Name'],
                port_bindings=d['HostConfig']['PortBindings'], networks=sorted(d['NetworkSettings']['Networks']),
                mounts=[dict(type=m['Type'], name=m.get('Name'), destination=m['Destination'], rw=m['RW']) for m in d['Mounts']],
                compose_project=lab.get('com.docker.compose.project'), compose_service=lab.get('com.docker.compose.service'),
                compose_config_files=lab.get('com.docker.compose.project.config_files'))


def password_digest(c):
    """Only a digest of the stored hash ever leaves memory, and only into the gitignored private dir."""
    rows = c.execute('SELECT password_hash FROM users ORDER BY id').fetchall()
    return hashlib.sha256('\n'.join(r['password_hash'] for r in rows).encode()).hexdigest()


def data(c):
    sci = science(c)
    assert normalize(sci) == normalize(DBV25['data']['scientific_snapshot']), 'SCIENTIFIC_SNAPSHOT_DRIFT_VS_DBV2_5'
    stored = c.execute("SELECT methodology_json->'freeze_contract'->'fingerprints' AS f, frozen_at, status FROM dataset_versions WHERE id=%s", (OFFICIAL,)).fetchone()
    fp = {k: stored['f'].get(k) for k in FINGERPRINTS}
    assert fp == FINGERPRINTS, 'FINGERPRINT_DRIFT'
    assert str(stored['frozen_at']) == str(DBV25['data']['frozen_at']) and stored['status'] == 'FROZEN', 'FROZEN_AT_DRIFT'
    expected = {r['table']: r for r in TRANSFER['dataset'] + TRANSFER['authentication']['tables']}
    tables = []
    for t in DATASET + USER:
        h = hashes(c, t)
        assert h['count'] == expected[t]['destination_count'] and h['transfer_hash'] == expected[t]['transfer_hash'], 'ROW_CONTENT_DRIFT:' + t
        if 'pk_hash' in expected[t]:
            assert h['pk_hash'] == expected[t]['pk_hash'], 'PK_DRIFT:' + t
        tables.append(dict(table=t, count=h['count'], transfer_hash=h['transfer_hash'], equals_dbv2_4=True))
    users = dict(users=scalar(c, 'SELECT count(*) FROM users'), roles=scalar(c, 'SELECT count(*) FROM roles'),
                 user_roles=scalar(c, 'SELECT count(*) FROM user_roles'),
                 active=scalar(c, "SELECT count(*) FROM users WHERE status='active'"))
    assert users == dict(users=1, roles=1, user_roles=1, active=1), users
    integ = integrity(c)
    return dict(dataset_version_id=OFFICIAL, status=stored['status'], frozen_at=stored['frozen_at'], scientific_snapshot=sci,
                scientific_snapshot_equals_dbv2_5=True, fingerprints=fp, fingerprints_match=True, tables=tables,
                application_users=users, absence=absence(c),
                integrity=dict((k, v) for k, v in integ.items() if k != 'queries'), integrity_checks=len(integ['queries']))


def check(label, port, database, container, expect_database):
    base = baseline()
    assert base['root_revision_sha256'] == persistent.EXPECTED_REVISION
    with session(port, database) as c:
        ident = identity(c)
        assert (ident['database'], ident['database_oid'], ident['system_identifier'], ident['server_version_num'], ident['recovery']) == \
            (expect_database, OID, SYSID, 170009, False), ident
        assert ident['server_version'].split()[0] == '17.9'
        st = structure(c)
        rev = c.execute('SELECT version_num FROM alembic_version').fetchall()
        assert [r['version_num'] for r in rev] == ['pg_v2_baseline']
        d = data(c)
        cl = cluster(c)
        digest = password_digest(c)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    ref = PRIVATE / 'password_hash_digest'
    if not ref.exists():
        ref.write_text(digest)
        ref.chmod(0o600)
    pw_unchanged = ref.read_text() == digest
    del digest
    assert pw_unchanged, 'APPLICATION_PASSWORD_HASH_CHANGED'
    r = dict(label=label, endpoint=dict(host='127.0.0.1', port=port, database=database), identity=ident,
             docker=docker_identity(container), alembic=dict(alembic_version=rev[0]['version_num'], rows=len(rev), static=base['alembic_static']),
             baseline=dict(root_revision_sha256=base['root_revision_sha256'], resource_manifest_sha256=base['resource_manifest_sha256'],
                           structural_manifest_file_sha256=base['structural_manifest_file_sha256'], resources_verified=base['resources_verified'],
                           diff_vs_gate_dbv24_commit=base['diff_vs_gate_dbv24_commit'], untracked=base['untracked']),
             structure=st, data=d, application_password_hash_unchanged=pw_unchanged, cluster=cl)
    save(f'swv2_0_check_{label}.json', r)
    return r


def dbeaver(port, database):
    """Same contract DBeaver uses: 127.0.0.1:<port>/<database>, role julio, .env credential."""
    with session(port, database, role='julio') as c:
        ident = identity(c)
        role = c.execute("SELECT rolname, rolsuper, rolcanlogin FROM pg_roles WHERE rolname=current_user").fetchone()
        tables = [r['t'] for r in c.execute("SELECT table_name AS t FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1")]
        views = scalar(c, "SELECT count(*) FROM information_schema.views WHERE table_schema='public'")
        xai = [t for t in tables if t.startswith('xai_')]
        readable = scalar(c, 'SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=%s', (OFFICIAL,))
        alembic = [x['version_num'] for x in c.execute('SELECT version_num FROM alembic_version')]
        sci = science(c)
    r = dict(contract=dict(host='127.0.0.1', port=port, database=database, role='julio',
                           jdbc=f'jdbc:postgresql://127.0.0.1:{port}/{database}', credential='Compose .env POSTGRES_PASSWORD (not stored)'),
             authenticated=True, session=dict(database=ident['database'], role=ident['role'], database_oid=ident['database_oid'],
                                              system_identifier=ident['system_identifier'], server_version=ident['server_version']),
             role_flags=role, visible_base_tables=len(tables), application_tables=len(tables) - ('alembic_version' in tables),
             views=views, xai_tables=xai, xai_explanations_present='xai_explanations' in tables, split_assignments_readable=readable,
             alembic_version=alembic, dataset=dict(status=sci['status'], train=sci['train'], validation=sci['validation'], test=sci['test'],
                                                   total=sci['total'], patients=sci['patients'], overlaps=sci['overlaps'],
                                                   equals_dbv2_5=normalize(sci) == normalize(DBV25['data']['scientific_snapshot'])))
    assert r['session']['system_identifier'] == SYSID and r['session']['database_oid'] == OID and r['session']['database'] == database
    assert ident['server_version'].split()[0] == '17.9' and ident['role'] == 'julio' and role['rolsuper'] and role['rolcanlogin']
    assert alembic == ['pg_v2_baseline'] and r['dataset']['equals_dbv2_5'] and r['dataset']['status'] == 'FROZEN'
    assert r['application_tables'] == 104 and views == 33 and xai == XAI and not r['xai_explanations_present'] and readable == 27558
    save('swv2_0_dbeaver_contract.json', r)
    return r


def secret_scan(port, database):
    """Counts only. Live application hash + v2 credentials + Compose .env password in SWV2.0 artefacts."""
    creds = json.loads((persistent.PRIVATE / 'credentials.json').read_text())
    with session(port, database) as c:
        live = [r['password_hash'] for r in c.execute('SELECT password_hash FROM users')]
    env_pw, jwt = dotenv('POSTGRES_PASSWORD'), dotenv('JWT_SECRET')
    strong = live + list(creds.values()) + [x for x in (env_pw, jwt) if len(x) >= 8]
    weak = [re.compile(r'(?i)(pass(word)?|pwd|secret)["\']?\s*[:=]\s*["\']?' + re.escape(env_pw) + r'\b|:' + re.escape(env_pw) + '@')] if 0 < len(env_pw) < 8 else []
    del creds, live, env_pw, jwt
    tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--cached', '--others', '--exclude-standard', 'docs/audits/sw_v2',
                              'scripts/db/swv20_integration.py', 'docker-compose.yml', 'docker-compose.override.yml',
                              'backend_api/tests/test_scientific_storage_docker_contract.py'], capture_output=True, text=True, check=True).stdout.split()
    texts = {p: (ROOT / p).read_bytes().decode('utf-8', 'replace') for p in tracked}
    hits = sorted(p for p, t in texts.items() if any(n in t for n in strong) or any(w.search(t) for w in weak))
    del strong, weak
    url = re.compile(r'postgres(?:ql)?(?:\+\w+)?://[^:/@\s"]+:([^@\s"$]+)@')
    url_hits = sorted(p for p, t in texts.items() if any(not m.group(1).startswith(('{', '$')) for m in url.finditer(t)))
    r = dict(files_scanned=len(texts), secret_hit_files=hits, url_with_inline_password_files=url_hits,
             checked=['users.password_hash (live, in memory)', 'capstone_v2 credentials (postgres, migrator, runtime)',
                      'Compose .env POSTGRES_PASSWORD (credential-context match when short)', 'JWT_SECRET', 'URLs with inline password'],
             result='PASS' if not hits and not url_hits else 'FAIL')
    save('swv2_0_secret_scan.json', r)
    assert r['result'] == 'PASS', 'SECRETS_IN_EVIDENCE'
    return r


def main():
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['check', 'dbeaver', 'secrets'])
    a.add_argument('--label')
    a.add_argument('--port', type=int, default=5432)
    a.add_argument('--database', default='malaria_experiments')
    a.add_argument('--container', default='capstone_db')
    x = a.parse_args()
    if x.action == 'check':
        check(x.label, x.port, x.database, x.container, x.database)
    elif x.action == 'dbeaver':
        dbeaver(x.port, x.database)
    else:
        secret_scan(x.port, x.database)
    print(x.action.upper(), x.label or '', 'PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = dict(status='BLOCKED', error_type=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None),
                    at=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)])
        if isinstance(error, AssertionError) and error.args and isinstance(error.args[0], str):
            safe['invariant'] = error.args[0]
        save('blocked.json', safe)
        print(json.dumps(safe, default=str))
        sys.exit(1)
