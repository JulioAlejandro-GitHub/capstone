"""D-05 generated expression behavior on disposable native-column fixtures."""

import psycopg
from verify_v2_route_a import connect, guard, save

t = guard()
results = []


def record(name, passed, **extra):
    results.append(dict(name=name, passed=passed, **extra))
    save("d05_server_tests.json", results)
    assert passed, name


with connect(t) as c:
    col = c.execute(
        "SELECT a.attgenerated,a.attnotnull,format_type(a.atttypid,a.atttypmod) type,pg_get_expr(d.adbin,d.adrelid) expression FROM pg_attribute a JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE a.attrelid='assessment_identities'::regclass AND a.attname='structural_hash'"
    ).fetchone()
    record(
        "native_generated_contract",
        col
        == {
            "attgenerated": "s",
            "attnotnull": False,
            "type": "text",
            "expression": "assessment_structural_hash(identity)",
        },
        metadata=col,
    )
    # LIKE copies the actual generated expression, types and NOT NULL constraints.
    # No application rows or triggers are altered; other columns removed in TEMP only.
    c.execute(
        "CREATE TEMP TABLE d05_generated_probe (LIKE public.assessment_identities INCLUDING GENERATED)"
    )
    names = c.execute(
        "SELECT attname FROM pg_attribute WHERE attrelid='pg_temp.d05_generated_probe'::regclass AND attnum>0 AND NOT attisdropped"
    ).fetchall()
    from psycopg import sql

    for row in names:
        if row["attname"] not in ["identity", "structural_hash"]:
            c.execute(
                sql.SQL("ALTER TABLE d05_generated_probe DROP COLUMN {}").format(
                    sql.Identifier(row["attname"])
                )
            )
    a = c.execute(
        "INSERT INTO d05_generated_probe(identity) VALUES ('{\"a\":1}') RETURNING structural_hash,assessment_structural_hash(identity) expected"
    ).fetchone()
    record(
        "omitted_auto_calculation",
        a["structural_hash"] == a["expected"] and a["expected"] is not None,
    )
    try:
        with c.transaction():
            c.execute(
                "INSERT INTO d05_generated_probe(identity,structural_hash) VALUES ('{}','invented')"
            )
    except psycopg.Error as e:
        record("explicit_write_rejected", e.sqlstate == "428C9", sqlstate=e.sqlstate)
    else:
        record("explicit_write_rejected", False)
    b = c.execute(
        "UPDATE d05_generated_probe SET identity='{\"a\":2}' RETURNING structural_hash,assessment_structural_hash(identity) expected"
    ).fetchone()
    record(
        "identity_update_regenerates",
        b["structural_hash"] == b["expected"]
        and b["structural_hash"] != a["structural_hash"],
    )
    # Exhaustive SQL three-valued associativity underlying D-06 tree flattening.
    rows = c.execute(
        "WITH v(x) AS (VALUES (true),(false),(NULL::boolean)) SELECT a.x a,b.x b,c.x c, ((a.x AND b.x) AND c.x) IS NOT DISTINCT FROM (a.x AND (b.x AND c.x)) same_and, ((a.x OR b.x) OR c.x) IS NOT DISTINCT FROM (a.x OR (b.x OR c.x)) same_or FROM v a CROSS JOIN v b CROSS JOIN v c"
    ).fetchall()
    record(
        "d06_three_valued_associativity",
        len(rows) == 27 and all(r["same_and"] and r["same_or"] for r in rows),
        cases=rows,
    )
    c.rollback()
print(str(len(results)) + " D-05/D-06 checks passed")
