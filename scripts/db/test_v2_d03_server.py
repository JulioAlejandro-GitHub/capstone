"""D-03 real server behavior checks on the newly certified isolated baseline."""

import json

import psycopg
from verify_v2_route_a import ROOT, RUNTIME, connect, guard, save

t = guard()
results = []


def record(name, passed, **extra):
    results.append(dict(name=name, passed=passed, **extra))
    save("d03_server_tests.json", results)
    assert passed, name


with connect(t) as c:
    initial = c.execute(
        "SELECT last_value,is_called FROM experiment_execution_events_id_seq"
    ).fetchone()
    a = c.execute(
        "SELECT attidentity FROM pg_attribute WHERE attrelid='experiment_execution_events'::regclass AND attname='id'"
    ).fetchone()
    dep = c.execute(
        "SELECT deptype FROM pg_depend WHERE classid='pg_class'::regclass AND objid='experiment_execution_events_id_seq'::regclass AND refobjid='experiment_execution_events'::regclass"
    ).fetchall()
    record(
        "identity_native_contract",
        a["attidentity"] == "a"
        and dep == [{"deptype": "i"}]
        and initial == {"last_value": 1, "is_called": False},
        initial=initial,
        dependencies=dep,
    )
    approved = json.loads((ROOT / "alembic_v2/d03_contract.json").read_text())[
        "uuid_core_defaults"
    ]
    for table, col in approved:
        x = c.execute(
            "SELECT d.adbin::text tree,pg_get_expr(d.adbin,d.adrelid) expression FROM pg_attrdef d JOIN pg_attribute a ON a.attrelid=d.adrelid AND a.attnum=d.adnum WHERE d.adrelid=%s::regclass AND a.attname=%s",
            ("public." + table, col),
        ).fetchone()
        f = c.execute(
            "SELECT 'pg_catalog.gen_random_uuid()'::regprocedure::oid oid"
        ).fetchone()["oid"]
        record(
            "core_default:" + table + "." + col,
            (":funcid " + str(f) + " ") in x["tree"],
            expression=x["expression"],
        )
with connect(t, role=RUNTIME) as c:

    def probe(name, statement, expected):
        try:
            with c.transaction():
                row = c.execute(statement).fetchone()
                record(name, expected == "00000", sqlstate="00000", row=row)
                c.execute("ROLLBACK")
        except psycopg.Error as e:
            record(name, e.sqlstate == expected, sqlstate=e.sqlstate)

    values = "'00000000-0000-0000-0000-000000000001','D03_SYNTHETIC_PROBE','{}'"
    probe(
        "identity_omitted_id",
        "INSERT INTO experiment_execution_events(owner,event,payload) VALUES ("
        + values
        + ") RETURNING id",
        "00000",
    )
    probe(
        "identity_explicit_id",
        "INSERT INTO experiment_execution_events(id,owner,event,payload) VALUES (9000000,"
        + values
        + ") RETURNING id",
        "428C9",
    )
    probe(
        "identity_override",
        "INSERT INTO experiment_execution_events(id,owner,event,payload) OVERRIDING SYSTEM VALUE VALUES (9000001,"
        + values
        + ") RETURNING id",
        "00000",
    )
    # Immutable E10 global event guard stays active on generated IDs.
    with c.transaction():
        row = c.execute(
            "INSERT INTO experiment_execution_events(owner,event,payload) VALUES ("
            + values
            + ") RETURNING id"
        ).fetchone()
        try:
            with c.transaction():
                c.execute(
                    "UPDATE experiment_execution_events SET event=event WHERE id=%s",
                    (row["id"],),
                )
        except psycopg.Error as e:
            record("global_event_immutable", e.sqlstate == "P0001", sqlstate=e.sqlstate)
        else:
            record("global_event_immutable", False)
        c.execute("ROLLBACK")
# Privilege discriminator only in a rolled-back auxiliary table, no scientific rows.
with connect(t, role="postgres") as c, c.transaction():
    c.execute(
        "CREATE TABLE public.d03_uuid_probe(id uuid DEFAULT pg_catalog.gen_random_uuid())"
    )
    c.execute("GRANT INSERT,SELECT ON public.d03_uuid_probe TO capstone_v2_runtime")
    c.execute(
        "REVOKE EXECUTE ON FUNCTION public.gen_random_uuid() FROM PUBLIC,capstone_v2_runtime"
    )
    c.execute("SET LOCAL ROLE capstone_v2_runtime")
    row = c.execute(
        "INSERT INTO public.d03_uuid_probe DEFAULT VALUES RETURNING id"
    ).fetchone()
    record("core_default_independent_of_wrapper_privilege", row["id"].version == 4)
    c.execute("ROLLBACK")
print(str(len(results)) + " D-03 checks passed")
