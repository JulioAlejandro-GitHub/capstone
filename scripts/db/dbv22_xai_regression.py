"""Static regression guard for the approved DBV2.2-R1 trigger dispatch."""

import re

from pglast import ast, parse_sql


def validate_xai_dispatch(source):
    functions = [
        r.stmt
        for r in parse_sql(source)
        if isinstance(r.stmt, ast.CreateFunctionStmt)
        and r.stmt.funcname[-1].sval == "dbv21_xai_evaluation_complete"
    ]
    assert len(functions) == 1, "R1: exactly one XAI completion function required"
    body = next(o.arg[0].sval for o in functions[0].options if o.defname == "as")
    # Match separate PL/pgSQL statements, not expressions accessing both row shapes.
    pattern = r"""IF\s+TG_TABLE_NAME\s*=\s*'xai_quantitative_evaluations'\s+THEN
        \s*eid\s*:=\s*NEW\.id\s*;
        \s*ELSIF\s+TG_TABLE_NAME\s*=\s*'xai_evaluation_members'\s+THEN
        \s*eid\s*:=\s*NEW\.evaluation_id\s*;
        \s*ELSE\s+RAISE\s+EXCEPTION\s*
        'dbv21_xai_evaluation_complete\s+invoked\s+from\s+unsupported\s+table:\s*%'
        \s*,\s*TG_TABLE_NAME\s*;\s*END\s+IF\s*;"""
    assert re.search(pattern, body, re.IGNORECASE | re.VERBOSE), (
        "R1: explicit guarded row dispatch required"
    )
    for case in re.findall(r"\bCASE\b.*?\bEND\b", body, re.IGNORECASE | re.DOTALL):
        assert not (
            re.search(r"NEW\.id\b", case, re.IGNORECASE)
            and re.search(r"NEW\.evaluation_id\b", case, re.IGNORECASE)
        ), "R1: incompatible RECORD fields in CASE"
