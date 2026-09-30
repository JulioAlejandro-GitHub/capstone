"""Offline compiler of the reviewed E10.10.4 specification, never a DB runner.

Freezes final table shapes before functions/constraints/views, extracts inline
constraints, orders dependencies, and gives the Alembic ledger to Alembic alone.
Run --check after changes; --write is an explicit development-only regeneration.
The migration does NOT import this module or read the conceptual SQL.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pglast import ast, parse_sql
from pglast.enums import AlterTableType as AT
from pglast.enums import ConstrType as CT
from pglast.stream import RawStream

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/audits/e10_10_4_target_schema.sql"
DEST = ROOT / "alembic_v2/baseline"
REVISION = "pg_v2_baseline"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render(node):
    return RawStream()(node)


def strings(nodes):
    return tuple(n.sval for n in nodes or ())


def ordered(items, dependencies):
    pending = dict(items)
    result = []
    while pending:
        ready = sorted(n for n in pending if not (dependencies[n] & pending.keys()))
        if not ready:
            raise ValueError(f"Unresolved dependency cycle: {sorted(pending)}")
        for name in ready:
            result.append((name, pending.pop(name)))
    return result


def d03_columns():
    decision = json.loads((ROOT / "alembic_v2/d03_contract.json").read_text())
    columns = {tuple(x) for x in decision["uuid_core_defaults"]}
    assert len(columns) == 39
    assert not any(
        t in {"classification_reports", "confusion_matrices"} for t, _ in columns
    )
    return columns


def d03_column(table, col):
    """Exact approved AST changes only; no global function-name replacement."""
    if (table, col.colname) in d03_columns():
        defaults = [
            co for co in col.constraints or () if co.contype == CT.CONSTR_DEFAULT
        ]
        assert (
            len(defaults) == 1 and render(defaults[0].raw_expr) == "gen_random_uuid()"
        )
        defaults[0].raw_expr = (
            parse_sql("SELECT pg_catalog.gen_random_uuid()")[0].stmt.targetList[0].val
        )
    if (table, col.colname) == ("experiment_execution_events", "id"):
        assert render(col) == "id bigint NOT NULL"
        return parse_sql(
            "CREATE TABLE x (id bigint GENERATED ALWAYS AS IDENTITY NOT NULL)"
        )[0].stmt.tableElts[0]
    if (table, col.colname) == ("assessment_identities", "structural_hash"):
        assert render(col) == "structural_hash text"
        return parse_sql(
            "CREATE TABLE x (structural_hash text GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED)"
        )[0].stmt.tableElts[0]
    return col


def compile_spec(source):
    tables, functions, views = {}, {}, {}
    constraints, indexes, triggers, sequence = [], [], [], []
    ownership = []
    function_sql = {}
    for raw in parse_sql(source):
        s = copy.deepcopy(raw.stmt)
        if isinstance(s, ast.CreateStmt):
            assert s.relation.relname not in tables
            tables[s.relation.relname] = s
        elif isinstance(s, ast.AlterTableStmt):
            t = s.relation.relname
            for cmd in s.cmds:
                if cmd.subtype == AT.AT_AddConstraint:
                    constraints.append((t, cmd.def_))
                elif cmd.subtype == AT.AT_AddColumn:
                    tables[t].tableElts += (cmd.def_,)
                elif cmd.subtype in (AT.AT_AlterColumnType, AT.AT_SetNotNull):
                    col = next(
                        c
                        for c in tables[t].tableElts
                        if isinstance(c, ast.ColumnDef) and c.colname == cmd.name
                    )
                    if cmd.subtype == AT.AT_AlterColumnType:
                        col.typeName = cmd.def_.typeName
                    elif not any(
                        c.contype == CT.CONSTR_NOTNULL for c in col.constraints or ()
                    ):
                        col.constraints = (col.constraints or ()) + (
                            ast.Constraint(contype=CT.CONSTR_NOTNULL),
                        )
                else:
                    raise ValueError(f"Unreviewed ALTER: {cmd.subtype}")
        elif isinstance(s, ast.CreateFunctionStmt):
            name = ".".join(strings(s.funcname))
            assert name not in functions, "Overload requires a signature-aware compiler"
            functions[name] = s
            # Preserve the exact procedural body and proconfig of inherited guards.
            piece = (
                source[raw.stmt_location : raw.stmt_location + raw.stmt_len]
                if raw.stmt_len
                else source[raw.stmt_location :]
            )
            function_sql[name] = (
                piece[piece.upper().index("CREATE ") :].strip().rstrip(";")
            )
        elif isinstance(s, ast.ViewStmt):
            views[s.view.relname] = s
        elif isinstance(s, ast.IndexStmt):
            indexes.append(s)
        elif isinstance(s, ast.CreateTrigStmt):
            triggers.append(s)
        elif isinstance(s, ast.CreateSeqStmt):
            sequence.append(s)
        elif isinstance(s, ast.AlterSeqStmt):
            ownership.append(s)
        elif isinstance(s, (ast.CreateExtensionStmt, ast.VariableSetStmt)):
            pass  # Replaced with explicit, transaction-local prerequisites below.
        else:
            raise TypeError(f"Unreviewed statement: {type(s).__name__}")

    # D-03 restores the native legacy identity. PostgreSQL alone creates its sequence.
    assert len(sequence) == len(ownership) == 1
    assert (
        sequence[0].sequence.relname
        == ownership[0].sequence.relname
        == "experiment_execution_events_id_seq"
    )
    sequence.clear()
    ownership.clear()
    for name, column in d03_columns():
        assert name in tables and any(
            isinstance(c, ast.ColumnDef) and c.colname == column
            for c in tables[name].tableElts
        )

    for t, table in tables.items():
        columns = []
        for elt in table.tableElts:
            if isinstance(elt, ast.Constraint):
                constraints.append((t, elt))
                continue
            assert isinstance(elt, ast.ColumnDef)
            elt = d03_column(t, elt)
            retained = []
            previous = None
            for c in elt.constraints or ():
                # Raw PostgreSQL grammar exposes inline FK attributes as separate
                # nodes. They must travel with the extracted FK, not NOT NULL.
                if c.contype in (
                    CT.CONSTR_ATTR_DEFERRABLE,
                    CT.CONSTR_ATTR_NOT_DEFERRABLE,
                    CT.CONSTR_ATTR_DEFERRED,
                    CT.CONSTR_ATTR_IMMEDIATE,
                ):
                    assert previous is not None and previous.contype in (
                        CT.CONSTR_FOREIGN,
                        CT.CONSTR_PRIMARY,
                        CT.CONSTR_UNIQUE,
                    ), "Constraint attribute without eligible parent"
                    if c.contype in (
                        CT.CONSTR_ATTR_DEFERRABLE,
                        CT.CONSTR_ATTR_NOT_DEFERRABLE,
                    ):
                        previous.deferrable = c.contype == CT.CONSTR_ATTR_DEFERRABLE
                    else:
                        previous.initdeferred = c.contype == CT.CONSTR_ATTR_DEFERRED
                    continue
                previous = c
                if c.contype in (
                    CT.CONSTR_PRIMARY,
                    CT.CONSTR_UNIQUE,
                    CT.CONSTR_FOREIGN,
                    CT.CONSTR_CHECK,
                ):
                    if c.contype in (CT.CONSTR_PRIMARY, CT.CONSTR_UNIQUE):
                        c.keys = (ast.String(sval=elt.colname),)
                    if c.contype == CT.CONSTR_FOREIGN:
                        c.fk_attrs = (ast.String(sval=elt.colname),)
                    constraints.append((t, c))
                else:
                    retained.append(c)
            elt.constraints = tuple(retained)
            columns.append(elt)
        table.tableElts = tuple(columns)

    # The documentary 103 includes alembic_version. It is never application DDL.
    del tables["alembic_version"]
    constraints = [(t, c) for t, c in constraints if t != "alembic_version"]
    names = set()
    for t, c in constraints:
        if not c.conname:
            identity = render(c)
            c.conname = (
                "v2_"
                + t[:30]
                + "_"
                + c.contype.name.removeprefix("CONSTR_").lower()
                + "_"
                + digest(identity.encode())[:12]
            )
        assert len(c.conname.encode()) <= 63
        assert (t, c.conname) not in names, (t, c.conname)
        names.add((t, c.conname))

    output = []

    def emit(phase, kind, name, sql, **metadata):
        output.append(
            dict(
                phase=phase, kind=kind, name=name, sql=sql.rstrip(";") + ";", **metadata
            )
        )

    emit(
        "01_prerequisites",
        "setting",
        "search_path",
        "SET LOCAL search_path = public, pg_catalog",
    )
    emit(
        "01_prerequisites",
        "setting",
        "check_function_bodies",
        "SET LOCAL check_function_bodies = true",
    )
    emit(
        "01_prerequisites",
        "extension",
        "pgcrypto",
        "CREATE EXTENSION pgcrypto WITH SCHEMA public",
    )
    emit(
        "01_prerequisites",
        "acl",
        "public_schema",
        "REVOKE ALL ON SCHEMA public FROM PUBLIC",
    )
    deps = {}
    for name, function in functions.items():
        body = next(o.arg[0].sval for o in function.options if o.defname == "as")
        deps[name] = {
            n
            for n in functions
            if n != name
            and re.search(r"\b" + re.escape(n.split(".")[-1]) + r"\s*\(", body)
        }

    def emit_function(name, f, phase):
        options = {o.defname: o for o in f.options}
        body = options["as"].arg[0].sval
        emit(
            phase,
            "function",
            name,
            function_sql[name],
            arguments=[render(p) for p in f.parameters or ()],
            body_sha256=digest(body.encode()),
            dependencies=sorted(deps[name]),
        )

    early_functions = json.loads((ROOT / "alembic_v2/d05_contract.json").read_text())[
        "functions_before_tables"
    ]
    for name in early_functions:
        assert deps[name] <= set(early_functions[: early_functions.index(name)])
        emit_function(name, functions[name], "02_generated_functions")

    for seq in sequence:
        emit("02_sequences", "sequence", seq.sequence.relname, render(seq))
    for t in sorted(tables):
        table = tables[t]
        pk = {
            v.sval
            for owner, co in constraints
            if owner == t and co.contype == CT.CONSTR_PRIMARY
            for v in co.keys
        }
        column_manifest = {}
        for col in table.tableElts:
            cs = col.constraints or ()
            default = next(
                (render(co.raw_expr) for co in cs if co.contype == CT.CONSTR_DEFAULT),
                None,
            )
            generated = next(
                (render(co.raw_expr) for co in cs if co.contype == CT.CONSTR_GENERATED),
                None,
            )
            column_manifest[col.colname] = {
                "declaration": render(col),
                "identity": next(
                    (
                        co.generated_when
                        for co in cs
                        if co.contype == CT.CONSTR_IDENTITY
                    ),
                    "",
                ),
                "type": render(col.typeName),
                "nullable": not (
                    col.colname in pk
                    or any(co.contype == CT.CONSTR_NOTNULL for co in cs)
                ),
                "default": default,
                "generated": generated,
                "attgenerated": "s" if generated is not None else "",
                "collation": render(col.collClause) if col.collClause else None,
            }
        emit("03_tables", "table", t, render(table), columns=column_manifest)

    for name, f in ordered(functions, deps):
        if name not in early_functions:
            emit_function(name, f, "04_functions")

    for t, c in constraints:
        if c.contype in (CT.CONSTR_PRIMARY, CT.CONSTR_UNIQUE):
            emit(
                "05_keys",
                "constraint",
                t + "." + c.conname,
                f"ALTER TABLE public.{t} ADD {render(c)}",
                table=t,
                constraint_type=c.contype.name,
                keys=list(strings(c.keys)),
            )
    # Full unique indexes can also be FK targets, so precede foreign keys.
    for ix in indexes:
        if ix.unique and ix.whereClause is None:
            emit("05_keys", "index", ix.idxname, render(ix), table=ix.relation.relname)
    for t, c in constraints:
        if c.contype not in (CT.CONSTR_PRIMARY, CT.CONSTR_UNIQUE):
            meta = {
                "table": t,
                "constraint_type": c.contype.name,
                "deferrable": c.deferrable,
                "initially_deferred": c.initdeferred,
            }
            if c.contype == CT.CONSTR_FOREIGN:
                meta.update(
                    columns=list(strings(c.fk_attrs)),
                    parent=c.pktable.relname,
                    parent_columns=list(strings(c.pk_attrs)),
                )
            emit(
                "06_constraints",
                "constraint",
                t + "." + c.conname,
                f"ALTER TABLE public.{t} ADD {render(c)}",
                **meta,
            )
    for ix in indexes:
        if not (ix.unique and ix.whereClause is None):
            emit(
                "07_indexes", "index", ix.idxname, render(ix), table=ix.relation.relname
            )
    view_deps = {
        name: set(
            re.findall(
                r"\b(?:FROM|JOIN)\s+(?:public\.)?(\w+)", render(v), re.IGNORECASE
            )
        )
        & views.keys()
        for name, v in views.items()
    }
    for name, v in ordered(views, view_deps):
        emit("08_views", "view", name, render(v), dependencies=sorted(view_deps[name]))
    for tr in triggers:
        emit(
            "09_triggers",
            "trigger",
            tr.relation.relname + "." + tr.trigname,
            render(tr),
            table=tr.relation.relname,
            function=".".join(strings(tr.funcname)),
            constraint=tr.isconstraint,
            deferrable=tr.deferrable,
            initially_deferred=tr.initdeferred,
            enabled="O",
        )
    for seq in ownership:
        emit("10_privileges", "sequence_ownership", seq.sequence.relname, render(seq))
    emit(
        "10_privileges",
        "acl",
        "database",
        """DO $v2_acl$ BEGIN
 EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
 EXECUTE format('REVOKE ALL ON DATABASE %I FROM capstone_v2_runtime', current_database());
 EXECUTE format('GRANT CONNECT ON DATABASE %I TO capstone_v2_runtime', current_database());
END $v2_acl$""",
    )
    emit(
        "10_privileges",
        "acl",
        "clear_runtime_schema",
        "REVOKE ALL ON SCHEMA public FROM capstone_v2_runtime",
    )
    emit(
        "10_privileges",
        "acl",
        "clear_table_defaults",
        "REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, capstone_v2_runtime",
    )
    emit(
        "10_privileges",
        "acl",
        "clear_sequence_defaults",
        "REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, capstone_v2_runtime",
    )
    emit(
        "10_privileges",
        "acl",
        "runtime_schema",
        "GRANT USAGE ON SCHEMA public TO capstone_v2_runtime",
    )
    # No DDL, role membership, TRUNCATE, REFERENCES, TRIGGER or ledger writes for runtime.
    for t in sorted(tables):
        privileges = (
            "SELECT" if t == "schema_migrations" else "SELECT, INSERT, UPDATE, DELETE"
        )
        emit(
            "10_privileges",
            "acl",
            "runtime_" + t,
            f"GRANT {privileges} ON TABLE public.{t} TO capstone_v2_runtime",
        )
    for v in sorted(views):
        emit(
            "10_privileges",
            "acl",
            "runtime_" + v,
            f"GRANT SELECT ON TABLE public.{v} TO capstone_v2_runtime",
        )
    emit(
        "10_privileges",
        "acl",
        "runtime_sequence",
        "GRANT USAGE, SELECT ON SEQUENCE public.experiment_execution_events_id_seq TO capstone_v2_runtime",
    )
    for name, f in functions.items():
        signature = (
            name + "(" + ", ".join(render(p.argType) for p in f.parameters or ()) + ")"
        )
        emit(
            "10_privileges",
            "acl",
            "revoke_" + name,
            f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC",
        )
        emit(
            "10_privileges",
            "acl",
            "execute_" + name,
            f"GRANT EXECUTE ON FUNCTION {signature} TO capstone_v2_runtime",
        )
    emit(
        "10_privileges",
        "acl",
        "alembic_version",
        "REVOKE ALL ON TABLE public.alembic_version FROM PUBLIC, capstone_v2_runtime",
    )
    emit(
        "10_privileges",
        "acl",
        "alembic_version_read",
        "GRANT SELECT ON TABLE public.alembic_version TO capstone_v2_runtime",
    )
    emit(
        "11_technical_state",
        "seed",
        "free_gate",
        "INSERT INTO public.experiment_execution_gate (singleton, owner, db_pid, process_evidence, blocked_reason) VALUES (true, NULL, NULL, '{}'::jsonb, NULL)",
    )
    return output


def artifacts():
    source = SOURCE.read_text()
    entries = compile_spec(source)
    files, records = {}, []
    for e in entries:
        e = dict(e)
        sql = e.pop("sql").encode()
        filename = e["phase"] + ".sql"
        if filename not in files:
            files[filename] = (
                b"-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.\n"
            )
        start = len(files[filename])
        files[filename] += sql + b"\n\n"
        records.append(
            dict(
                e, file=filename, start=start, end=start + len(sql), sha256=digest(sql)
            )
        )
    manifest = {
        "format_version": 1,
        "revision": REVISION,
        "source_sha256": digest(source.encode()),
        "d03_contract_sha256": digest(
            (ROOT / "alembic_v2/d03_contract.json").read_bytes()
        ),
        "d05_contract_sha256": digest(
            (ROOT / "alembic_v2/d05_contract.json").read_bytes()
        ),
        "generated_column_contracts": [
            json.loads((ROOT / "alembic_v2/d05_contract.json").read_text())
        ],
        "identity_sequences": [
            json.loads((ROOT / "alembic_v2/d03_contract.json").read_text())["identity"]
        ],
        "managed_by_alembic": {
            "table": "alembic_version",
            "column": "version_num varchar(32) NOT NULL",
            "primary_key": "alembic_version_pkc",
        },
        "counts": dict(Counter(e["kind"] for e in entries)),
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "statements": records,
    }
    files["catalog_manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("Select exactly one of --write or --check")
    files = artifacts()
    if args.write:
        DEST.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (DEST / name).write_bytes(data)
    else:
        for name, data in files.items():
            if not (DEST / name).exists() or (DEST / name).read_bytes() != data:
                raise SystemExit("Frozen baseline differs: " + name)
        if {p.name for p in DEST.iterdir() if p.is_file()} != set(files):
            raise SystemExit("Unexpected baseline resource")
    print(
        f"{len(files)} resources {'written' if args.write else 'verified'}; no database access"
    )


if __name__ == "__main__":
    main()
