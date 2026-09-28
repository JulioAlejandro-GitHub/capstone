"""Read-only evidence and fail-closed identities for the isolated RESET.1B rehearsal."""
import hashlib
import json
import re
from pathlib import Path
from sqlalchemy import text


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode()).hexdigest()


def qi(name):
    require(bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name)), 'INVALID_IDENTIFIER')
    return '"' + name + '"'


def fingerprint(c, schema, tables=None):
    tables = tables or c.execute(text('SELECT tablename FROM pg_tables WHERE schemaname=:s ORDER BY tablename'), {'s': schema}).scalars().all()
    result = {}
    for table in tables:
        rows = c.execute(text(f'SELECT to_jsonb(t)::text FROM {qi(schema)}.{qi(table)} t ORDER BY to_jsonb(t)::text')).scalars().all()
        result[table] = {'count': len(rows), 'sha256': sha(rows)}
    return result


def catalog(c, schema):
    return {key: [dict(r) for r in c.execute(text(sql), {'s': schema}).mappings()] for key, sql in {
        'functions': "SELECT p.oid,p.proname,pg_get_functiondef(p.oid) AS definition,p.proowner::regrole::text AS owner,p.proacl::text AS acl FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=:s AND p.prokind='f' ORDER BY p.oid",
        'triggers': "SELECT t.oid,t.tgname,t.tgenabled,t.tgisinternal,t.tgrelid::regclass::text AS relation,pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname=:s ORDER BY t.oid",
        'constraints': "SELECT k.oid,k.conname,k.convalidated,pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname=:s ORDER BY k.oid",
        'owners_acl': "SELECT r.relname,r.relowner::regrole::text AS owner,r.relacl::text AS acl FROM pg_class r JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname=:s ORDER BY r.relname",
    }.items()}


def assert_clone(c, cfg):
    require(cfg['container'].startswith('capstone-reset1b-'), 'CLONE_HOST_REQUIRED')
    require(cfg['database']=='reset1b_rehearsal' and cfg['schema'].startswith('capstone_test_reset1b_'), 'PRODUCTION_EXECUTION_BLOCKED')
    actual=c.execute(text("SELECT current_database(),current_schema(),session_user,(SELECT system_identifier::text FROM pg_control_system()),current_setting('session_replication_role')")).one()
    require(tuple(actual)==(cfg['database'],cfg['schema'],cfg['user'],cfg['system_identifier'],'origin'), 'CLONE_IDENTITY_MISMATCH')
    require(cfg['system_identifier']!='7668020338728398886', 'OPERATIONAL_CLUSTER_FORBIDDEN')


def orphan_checks(c, manifest, schema):
    result=[]
    for fk in manifest['foreign_keys']:
        parent_schema=schema if fk['parent_schema']=='public' else fk['parent_schema']
        nonnull=' AND '.join('c.'+qi(a)+' IS NOT NULL' for a in fk['child_columns'])
        join=' AND '.join('c.'+qi(a)+'=p.'+qi(b) for a,b in zip(fk['child_columns'],fk['parent_columns']))
        n=c.execute(text(f'SELECT count(*) FROM {qi(schema)}.{qi(fk["child"])} c WHERE {nonnull} AND NOT EXISTS (SELECT 1 FROM {qi(parent_schema)}.{qi(fk["parent"])} p WHERE {join})')).scalar_one()
        require(n==0, 'ORPHANS:'+fk['conname'])
        result.append({'constraint':fk['conname'],'orphans':n})
    return result
