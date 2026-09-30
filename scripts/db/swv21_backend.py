"""SWV2.1: evidence that capstone_backend runs against PostgreSQL v2 as capstone_v2_runtime.

check    READ ONLY continuity (SWV2.0 derivation: identity, structural manifest, dataset, users, absence).
runtime  inside capstone_backend, through the backend's own engine: session role, flags, E10 guard.
auth     inside capstone_backend: route login query + argon2 verify in a rolled-back transaction, then a
         backend-issued token over real HTTP (/api/v1/auth/me, dataset endpoints). No committed writes.
smoke    unauthenticated infrastructure/read endpoints over real HTTP.
secrets  counts-only scan of SWV2.1 files for live credentials, hashes and inline-password URLs.

Never prints or stores passwords, password hashes, tokens or credentialed URLs.
"""
import argparse
import json
import re
import subprocess
import sys
import traceback
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/db'))
import swv20_integration as swv20  # noqa: E402

E = ROOT / 'docs/audits/sw_v2/swv2_1'
BASE = 'http://127.0.0.1:8000'
OFFICIAL = swv20.OFFICIAL
FILES = ['docker-compose.yml', '.env.example', 'docs/engineering/configuration.md',
         'scripts/db/build_v2_runtime_contract.py', 'scripts/db/swv21_backend.py',
         'malaria_dl_local_project/src/malaria_dl/persistence/schema_contract.py',
         'malaria_dl_local_project/src/malaria_dl/persistence/v2_runtime_contract.json',
         'malaria_dl_local_project/tests/test_v2_runtime_contract_guard.py',
         'tests/db_v2/test_v2_runtime_contract.py', 'backend_api/tests/test_backend_runtime_role_contract.py']


def save(name, obj):
    E.mkdir(parents=True, exist_ok=True)
    (E / name).write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + '\n')


# Operational delta found at SWV2.1 entry (not produced by SWV2.1): one real application login through
# POST /api/v1/auth/login at 2026-09-30 21:17:40Z, after the SWV2.0 commit (21:15:18Z) and before SWV2.1.
# The route updates only users.last_login_at and records USER_LOGIN_SUCCEEDED. last_login_at certified by
# DBV2.4 was read from the verified SWV2.0 dump (sha256 353759cf...59358b). Any other drift still fails.
ENTRY_DELTA = dict(
    users_last_login_at_certified='2026-09-29 21:18:19.690154+00',
    users_last_login_at_entry='2026-09-30 21:17:40.913955+00',
    audit_event=dict(id='9aa233c1-6f8b-4c7a-8a1b-13a0db3340c7', event_type='USER_LOGIN_SUCCEEDED', action='login',
                     request_method='POST', request_path='/api/v1/auth/login', success=True,
                     created_at='2026-09-30 21:17:40.916421+00'),
)
RESTORED = ("jsonb_set(to_jsonb(t)-'password_hash','{last_login_at}',"
            "to_jsonb(%s::timestamptz))::text AS body FROM public.users t WHERE t.last_login_at=%s::timestamptz ORDER BY t.id")


def users_hashes(c, t, original=swv20.hashes):
    """users: DBV2.4 transfer hash with only last_login_at restored; entry value must match exactly."""
    if t != 'users':
        return original(c, t)
    h = dict(original(c, t))
    rh, n = swv20.hashlib.sha256(), 0
    for r in c.execute('SELECT ' + RESTORED, (ENTRY_DELTA['users_last_login_at_certified'], ENTRY_DELTA['users_last_login_at_entry'])):
        b = r['body'].encode()
        rh.update(len(b).to_bytes(8, 'big'))
        rh.update(b)
        n += 1
    assert n == h['count'] == 1, 'USERS_LAST_LOGIN_CHANGED_SINCE_SWV2_1_ENTRY'
    h['transfer_hash'] = rh.hexdigest()
    return h


def absence_with_entry_login(c):
    rows = c.execute("""SELECT id::text, event_type, action, request_method, request_path, success, created_at::text
                        FROM audit_events ORDER BY created_at""").fetchall()
    assert [dict(r) for r in rows] == [ENTRY_DELTA['audit_event']], 'AUDIT_EVENTS_CHANGED_SINCE_SWV2_1_ENTRY'
    # Same rule as dbv24_transfer.absence, allowing only the one entry login audit row.
    from dbv24_transfer import TABLES, all_counts
    outside = {t: n for t, n in all_counts(c).items() if t not in TABLES}
    assert outside.pop('alembic_version') == 1 and outside.pop('experiment_execution_gate') == 1
    assert outside.pop('audit_events') == 1
    assert not any(outside.values()), 'UNAUTHORIZED_ROWS'
    return dict(unauthorized_transferred_rows=0, baseline_empty_tables=outside,
                technical_rows={'alembic_version': 1, 'experiment_execution_gate': 1},
                operational_rows_at_entry={'audit_events': 1}, entry_delta=ENTRY_DELTA)


def check(label):
    swv20.save = lambda name, obj: save(name.replace('swv2_0_', 'swv2_1_'), obj)
    swv20.hashes = users_hashes
    swv20.absence = absence_with_entry_login
    r = swv20.check(label, 5432, 'malaria_experiments', 'capstone_db', 'malaria_experiments')
    volume = [m['name'] for m in r['docker']['mounts'] if m['destination'] == '/var/lib/postgresql/data']
    assert volume == ['capstone_v2_isolated_persistent_data'], volume
    return r


def in_backend(code, name):
    p = subprocess.run(['docker', 'exec', '-i', '-w', '/app', 'capstone_backend', 'python', '-'],
                       input=code, capture_output=True, text=True)
    if p.returncode:
        # stderr of our own probe; it never contains credentials (URL is never printed).
        raise RuntimeError(f'{name} probe failed: ' + p.stderr.strip().splitlines()[-1])
    return json.loads(p.stdout)


RUNTIME = r'''
import json
from sqlalchemy import text
from app.db import get_primary_engine
from app.config import get_settings
from app.database_safety import redacted_database_target
from src.malaria_dl.execution.schema import require_e10_schema
with get_primary_engine().connect() as c:
    s = dict(c.execute(text("""SELECT current_user, session_user, current_database() AS database,
        current_schema() AS schema, r.rolsuper, r.rolcreatedb, r.rolcreaterole, r.rolbypassrls,
        r.rolreplication, r.rolcanlogin, r.rolinherit,
        has_schema_privilege(current_user,'public','CREATE') AS public_create,
        has_database_privilege(current_user,current_database(),'CREATE') AS database_create,
        has_table_privilege(current_user,'alembic_version','INSERT,UPDATE,DELETE,TRUNCATE') AS alembic_write,
        pg_has_role(current_user,'capstone_v2_migrator','MEMBER') AS migrator_member,
        EXISTS(SELECT 1 FROM pg_roles WHERE rolname='julio' AND pg_has_role(current_user,oid,'MEMBER')) AS julio_member
        FROM pg_roles r WHERE r.rolname=current_user""")).mappings().one())
    guard = require_e10_schema(c)
    c.rollback()
print(json.dumps(dict(session=s, target=redacted_database_target(get_settings().database_url),
                      require_e10_schema=dict(result='PASS', **guard)), default=str))
'''

AUTH = r'''
import inspect, json, secrets, urllib.request
from sqlalchemy import text
from app.db import get_primary_engine
from app.routes import auth
from app.security import create_access_token, verify_password
LOGIN = """
            SELECT u.id::text, u.username, u.password_hash, u.status,
                   COALESCE(array_agg(r.name) FILTER (WHERE r.name IS NOT NULL), '{}') roles
            FROM users u LEFT JOIN user_roles ur ON ur.user_id=u.id
            LEFT JOIN roles r ON r.id=ur.role_id WHERE lower(u.username)=lower(:username)
            GROUP BY u.id
        """
UPDATE = "UPDATE users SET last_login_at=:now WHERE id=CAST(:id AS uuid)"
source = inspect.getsource(auth.login)
assert LOGIN in source and UPDATE in source, 'LOGIN_ROUTE_SQL_CHANGED'
out = {}
with get_primary_engine().connect() as c:
    t = c.begin()
    try:
        user = c.execute(text("SELECT username FROM users WHERE status='active'")).scalar_one()
        row = c.execute(text(LOGIN), {"username": user.upper()}).mappings().one()
        out['login_query'] = dict(user_found=True, status=row['status'], roles=sorted(row['roles']),
                                  case_insensitive_lookup=True)
        out['wrong_password_rejected'] = verify_password(secrets.token_urlsafe(24), row['password_hash']) is False
        out['stored_hash_scheme'] = row['password_hash'].split('$')[1]
        n = c.execute(text(UPDATE), {"now": __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
                                     "id": row['id']}).rowcount
        out['last_login_update_permitted_rows'] = n
    finally:
        t.rollback()
    out['transaction'] = 'ROLLED_BACK'
token = create_access_token(row['id'], row['username'], list(row['roles']))
def get(path):
    q = urllib.request.Request('http://127.0.0.1:8000' + path, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(q, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')
status, me = get('/api/v1/auth/me')
out['me'] = dict(status=status, same_user=me.get('id') == row['id'] and me.get('username') == row['username'],
                 roles=me.get('roles'), permissions=len(me.get('permissions', [])), insecure_local=me.get('insecure_local'))
status, versions = get('/api/datasets')
FIELDS = ('dataset_version_id', 'status', 'source_record_count', 'train_records', 'val_records', 'test_records',
          'patient_count', 'trainable')
out['datasets'] = dict(status=status, items=[{k: v.get(k) for k in FIELDS} for v in versions.get('items', [])])
status, detail = get('/api/datasets/%s')
out['dataset_detail'] = dict(status=status, body=detail)
print(json.dumps(out, default=str))
'''


def auth():
    r = in_backend(AUTH % OFFICIAL, 'auth')
    detail = r.pop('dataset_detail')
    body = detail['body']
    r['dataset_detail'] = dict(status=detail['status'], keys=sorted(body) if isinstance(body, dict) else None)
    assert r['login_query']['user_found'] and r['login_query']['status'] == 'active'
    assert r['wrong_password_rejected'] and r['last_login_update_permitted_rows'] == 1
    assert r['me']['status'] == 200 and r['me']['same_user'] and not r['me']['insecure_local']
    assert r['datasets']['status'] == 200 and len(r['datasets']['items']) == 1
    item = r['datasets']['items'][0]
    assert (str(item['dataset_version_id']), item['status'], item['source_record_count'], item['train_records'],
            item['val_records'], item['test_records'], item['patient_count']) == \
        (OFFICIAL, 'FROZEN', 27558, 22180, 2693, 2685, 201), item
    assert detail['status'] == 200
    save('swv2_1_auth.json', r)
    return r, body


def http(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


def smoke(label):
    out = {}
    for path in ('/health', '/ready', '/datasources', '/api/dataset/summary', '/api/dataset/split', '/api/v1/auth/me'):
        status, body = http(path)
        out[path] = dict(status=status, body=body if path in ('/health', '/ready', '/datasources', '/api/v1/auth/me') else
                         dict(keys=sorted(body), counts=body.get('counts')))
    assert out['/health']['status'] == 200 and out['/ready']['status'] == 200
    assert out['/ready']['body']['components'] == dict(database='ready', migrations='ready', storage='ready')
    assert out['/api/v1/auth/me']['status'] == 401  # authentication stays enforced
    save(f'swv2_1_smoke_{label}.json', out)
    return out


def runtime(label):
    r = in_backend(RUNTIME, 'runtime')
    s = r['session']
    assert s['current_user'] == s['session_user'] == 'capstone_v2_runtime', s
    assert s['current_user'] not in ('julio', 'capstone_v2_migrator', 'postgres')
    assert not any(s[k] for k in ('rolsuper', 'rolcreatedb', 'rolcreaterole', 'rolbypassrls', 'rolreplication'))
    assert not any(s[k] for k in ('public_create', 'database_create', 'alembic_write', 'migrator_member', 'julio_member'))
    assert s['database'] == 'malaria_experiments' and s['schema'] == 'public'
    assert r['require_e10_schema']['revision'] == 'pg_v2_baseline'
    assert r['target'] == 'db:5432/malaria_experiments'
    save(f'swv2_1_runtime_{label}.json', r)
    return r


def secret_scan():
    creds = json.loads((swv20.persistent.PRIVATE / 'credentials.json').read_text())
    with swv20.session(5432, 'malaria_experiments') as c:
        live = [r['password_hash'] for r in c.execute('SELECT password_hash FROM users')]
    env_pw, jwt = swv20.dotenv('POSTGRES_PASSWORD'), swv20.dotenv('JWT_SECRET')
    strong = live + list(creds.values()) + [x for x in (env_pw, jwt) if len(x) >= 8]
    weak = [re.compile(r'(?i)(pass(word)?|pwd|secret)["\']?\s*[:=]\s*["\']?' + re.escape(env_pw) + r'\b|:' + re.escape(env_pw) + '@')] if 0 < len(env_pw) < 8 else []
    del creds, live, env_pw, jwt
    paths = sorted(set(FILES) | {str(p.relative_to(ROOT)) for p in E.rglob('*') if p.is_file()})
    texts = {p: (ROOT / p).read_bytes().decode('utf-8', 'replace') for p in paths}
    hits = sorted(p for p, t in texts.items() if any(n in t for n in strong) or any(w.search(t) for w in weak))
    token = re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.')
    token_hits = sorted(p for p, t in texts.items() if token.search(t))
    argon2 = re.compile(r'\$argon2(?:id|i|d)\$v=\d+\$m=\d+')
    argon = sorted(p for p, t in texts.items() if argon2.search(t))
    del strong, weak
    url = re.compile(r'postgres(?:ql)?(?:\+\w+)?://[^:/@\s"]+:([^@\s"$]+)@')
    url_hits = sorted(p for p, t in texts.items() if any(not m.group(1).startswith(('{', '$', '<')) for m in url.finditer(t)))
    r = dict(files_scanned=len(texts), files=paths, secret_hit_files=hits, jwt_token_files=token_hits,
             argon2_hash_files=argon, url_with_inline_password_files=url_hits,
             checked=['users.password_hash (live, in memory)', 'capstone_v2 credentials (postgres, migrator, runtime)',
                      'Compose .env POSTGRES_PASSWORD (credential-context match when short)', 'JWT_SECRET',
                      'JWT-shaped tokens', 'argon2 hashes', 'URLs with inline password'],
             result='PASS' if not (hits or token_hits or argon or url_hits) else 'FAIL')
    save('swv2_1_secret_scan.json', r)
    assert r['result'] == 'PASS', 'SECRETS_IN_EVIDENCE'
    return r


def main():
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['check', 'runtime', 'auth', 'smoke', 'secrets'])
    a.add_argument('--label', default='final')
    x = a.parse_args()
    if x.action == 'check':
        check(x.label)
    elif x.action == 'runtime':
        runtime(x.label)
    elif x.action == 'auth':
        auth()
    elif x.action == 'smoke':
        smoke(x.label)
    else:
        secret_scan()
    print(x.action.upper(), x.label, 'PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = dict(status='BLOCKED', error_type=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None),
                    at=[f'{Path(f.filename).name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)])
        if isinstance(error, (AssertionError, RuntimeError)) and error.args and isinstance(error.args[0], str):
            safe['invariant'] = error.args[0]
        save('blocked.json', safe)
        print(json.dumps(safe, default=str))
        sys.exit(1)
