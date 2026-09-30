"""Versioned, read-only runtime capabilities pinned to the E.1 catalog (D.4 scientific functions unchanged).

No Alembic imports, stamp, DDL, settings lookup or secondary datasource.
"""
import json
from pathlib import Path

from sqlalchemy import text


def require_v2_capabilities(connection):
    from ..execution.schema import E10SchemaNotReady

    contract = json.loads(Path(__file__).with_name('v2_runtime_contract.json').read_text())
    # pg_get_functiondef qualifies names relative to search_path. The certified
    # baseline owns public; reject a shadow schema instead of checking another DB.
    if connection.execute(text('SELECT current_schema()')).scalar_one() != 'public':
        raise E10SchemaNotReady(['v2_public_schema_required'])
    function_rows = connection.execute(text("""
        SELECT p.proname, md5(pg_get_functiondef(p.oid))
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND p.proname LIKE 'v2_%'
    """)).all()
    functions = dict(function_rows)
    if len(function_rows) != len(contract['functions']) or functions != contract['functions']:
        raise E10SchemaNotReady(['v2_function_contract'])
    triggers = [dict(r) for r in connection.execute(text("""
        SELECT r.relname AS relation, t.tgname AS name,
               pg_get_triggerdef(t.oid) AS definition, t.tgenabled,
               t.tgdeferrable, t.tginitdeferred
        FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=r.relnamespace
        WHERE n.nspname='public' AND t.tgname LIKE 'v2_%'
    """)).mappings()]
    if sorted(triggers, key=lambda r: r['name']) != sorted(contract['triggers'], key=lambda r: r['name']):
        raise E10SchemaNotReady(['v2_trigger_contract'])
