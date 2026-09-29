"""Static catalogue/dependency checks. Never connects to PostgreSQL or Docker.

Parser checks are not PostgreSQL 17 execution, catalogue certification or a
simulation of PL/pgSQL runtime. Stages B/D/E remain explicit gates.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from pglast import ast, get_postgresql_version, parse_sql, parser
from pglast.enums import ConstrType as CT

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from alembic_v2.resources import load_baseline


def norm(value):
    if isinstance(value, ast.Node):
        value = value()
    if isinstance(value, dict):
        return {
            k: norm(v)
            for k, v in value.items()
            if k
            not in (
                "location",
                "stmt_location",
                "stmt_len",
                "list_start",
                "list_end",
                "rexpr_list_start",
                "rexpr_list_end",
                "funcformat",
            )
        }
    if isinstance(value, (list, tuple)):
        return [norm(v) for v in value]
    return value


def strings(nodes):
    return tuple(n.sval for n in nodes or ())


def walk(value):
    if isinstance(value, ast.Node):
        value = value()
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, (tuple, list)):
        for v in value:
            yield from walk(v)


def catalogue(statements):
    tables, keys, functions, views, triggers, constraints, indexes = (
        {},
        collections.defaultdict(set),
        {},
        {},
        {},
        {},
        {},
    )
    primary = {}
    sequence = set()
    counts = collections.Counter()
    plpgsql = 0
    for sql in statements:
        parsed = parse_sql(sql)
        assert len(parsed) == 1, "One statement per resource entry required"
        s = parsed[0].stmt
        counts[type(s).__name__] += 1
        assert not isinstance(
            s,
            (
                ast.DropStmt,
                ast.TruncateStmt,
                ast.DeleteStmt,
                ast.UpdateStmt,
                ast.TransactionStmt,
            ),
        )
        if isinstance(s, ast.CreateStmt):
            t = s.relation.relname
            assert t not in tables and t != "alembic_version"
            assert not s.if_not_exists
            tables[t] = {c.colname: c for c in s.tableElts}
            assert len(tables[t]) == len(s.tableElts)
            assert all(isinstance(c, ast.ColumnDef) for c in s.tableElts)
            for column in s.tableElts:
                assert all(
                    co.contype
                    in (
                        CT.CONSTR_NOTNULL,
                        CT.CONSTR_NULL,
                        CT.CONSTR_DEFAULT,
                        CT.CONSTR_GENERATED,
                        CT.CONSTR_IDENTITY,
                    )
                    for co in column.constraints or ()
                ), ("Unextracted column constraint", t, column.colname)
        elif isinstance(s, ast.CreateSeqStmt):
            assert s.sequence.relname not in sequence
            sequence.add(s.sequence.relname)
        elif isinstance(s, ast.CreateFunctionStmt):
            name = ".".join(strings(s.funcname))
            assert name not in functions
            functions[name] = s
            options = {o.defname: o for o in s.options}
            if options["language"].arg.sval == "plpgsql":
                parser.parse_plpgsql_json(sql)
                plpgsql += 1
            body = options["as"].arg[0].sval
            # %ROWTYPE references must exist at function creation with checks ON.
            for t in re.findall(r"(?:public\.)?(\w+)%ROWTYPE", body, re.IGNORECASE):
                assert t in tables, ("Missing row type", name, t)
            if options["language"].arg.sval == "sql":
                parse_sql(body)
        elif isinstance(s, ast.AlterTableStmt):
            t = s.relation.relname
            assert t in tables, ("Unknown ALTER table", t)
            for cmd in s.cmds:
                c = cmd.def_
                assert isinstance(c, ast.Constraint), (
                    "Final shapes must precede constraints/views"
                )
                ident = (t, c.conname)
                assert ident not in constraints
                constraints[ident] = c
                if c.contype in (CT.CONSTR_PRIMARY, CT.CONSTR_UNIQUE):
                    cols = strings(c.keys)
                    assert set(cols) <= tables[t].keys()
                    keys[t].add(cols)
                    if c.contype == CT.CONSTR_PRIMARY:
                        assert t not in primary
                        primary[t] = cols
                elif c.contype == CT.CONSTR_FOREIGN:
                    parent = c.pktable.relname
                    assert parent in tables, ("Missing FK parent", ident, parent)
                    assert set(strings(c.fk_attrs)) <= tables[t].keys()
                    pc = strings(c.pk_attrs) or primary.get(parent)
                    assert pc and set(pc) <= tables[parent].keys()
                    assert pc in keys[parent], (
                        "FK target not unique before creation",
                        ident,
                        parent,
                        pc,
                    )
                    assert not c.skip_validation, ("Unvalidated FK", ident)
                elif c.contype == CT.CONSTR_CHECK:
                    assert not c.skip_validation
                    for node in walk(c.raw_expr):
                        if node.get("@") == "ColumnRef":
                            fields = node["fields"]
                            assert fields[0]["sval"] in tables[t], (
                                "Unknown CHECK column",
                                ident,
                                fields,
                            )
                else:
                    raise AssertionError(("Unreviewed constraint", ident, c.contype))
        elif isinstance(s, ast.IndexStmt):
            assert s.relation.relname in tables
            assert not s.concurrent and not s.if_not_exists
            assert s.idxname not in indexes
            indexes[s.idxname] = s
            for item in s.indexParams:
                if item.name:
                    assert item.name in tables[s.relation.relname]
            if (
                s.unique
                and s.whereClause is None
                and all(i.name for i in s.indexParams)
            ):
                keys[s.relation.relname].add(tuple(i.name for i in s.indexParams))
        elif isinstance(s, ast.ViewStmt):
            name = s.view.relname
            assert name not in views and name not in tables
            ctes = {
                n["ctename"] for n in walk(s.query) if n.get("@") == "CommonTableExpr"
            }
            for n in walk(s.query):
                if n.get("@") == "RangeVar":
                    assert n["relname"] in tables.keys() | views.keys() | ctes, (
                        "View dependency",
                        name,
                        n["relname"],
                    )
            views[name] = s
        elif isinstance(s, ast.CreateTrigStmt):
            name = (s.relation.relname, s.trigname)
            assert name not in triggers and s.relation.relname in tables
            fn = ".".join(strings(s.funcname))
            assert (fn if "." in fn else "public." + fn) in functions
            assert not s.trigname.startswith("RI_ConstraintTrigger")
            triggers[name] = s
        elif isinstance(s, ast.InsertStmt):
            assert s.relation.relname == "experiment_execution_gate", (
                "Scientific seed forbidden"
            )
    assert len(tables) == 102 and set(primary) == set(tables)
    return {
        "tables": tables,
        "functions": functions,
        "views": views,
        "triggers": triggers,
        "constraints": constraints,
        "indexes": indexes,
        "primary": primary,
        "sequence": sequence,
        "statements": counts,
        "plpgsql": plpgsql,
    }


def validate():
    manifest, statements = load_baseline()
    c = catalogue(statements)
    baseline = json.loads((ROOT / "docs/audits/e10_10_1_baseline.json").read_text())
    with (ROOT / "docs/audits/e10_10_4_schema_matrix.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 97
    assert {r["Objeto actual"] for r in rows} == {t["name"] for t in baseline["tables"]}
    expected_tables = {r["Objeto actual"] for r in rows if r["Acción"] != "MERGE"} - {
        "alembic_version"
    }
    expected_tables |= {
        "run_configurations",
        "evaluations",
        "evaluation_ensemble_members",
        "xai_evidence",
        "xai_artifacts",
        "xai_quantitative_evaluations",
        "xai_interpretations",
        "xai_specialist_reviews",
    }
    assert c["tables"].keys() == expected_tables

    # Independently compare inherited catalogue definitions with E10.10.1 evidence.
    inherited_functions = [f for f in baseline["functions"] if not f["extension_owned"]]
    for f in inherited_functions:
        target = c["functions"]["public." + f["name"]]
        original = parse_sql(f["definition"])[0].stmt
        assert norm(target) == norm(original), ("Legacy function changed", f["name"])
    inherited_triggers = [t for t in baseline["triggers"] if not t["internal"]]
    for tr in inherited_triggers:
        assert tr["enabled"] == "O"
        assert norm(c["triggers"][(tr["table_name"], tr["name"])]) == norm(
            parse_sql(tr["definition"])[0].stmt
        ), tr["name"]
    merges = {"confusion_matrices", "classification_reports"}
    preserved_constraints = 0
    for old in baseline["constraints"]:
        if old["table_name"] in merges | {"alembic_version"} or old["type"] not in (
            "p",
            "u",
            "c",
            "f",
        ):
            continue
        original = (
            parse_sql(
                f"ALTER TABLE public.{old['table_name']} ADD CONSTRAINT {old['name']} {old['definition']}"
            )[0]
            .stmt.cmds[0]
            .def_
        )
        assert norm(c["constraints"][(old["table_name"], old["name"])]) == norm(
            original
        ), ("Legacy constraint changed", old["name"])
        preserved_constraints += 1
    preserved_indexes = 0
    constraint_index_names = {
        x["name"] for x in baseline["constraints"] if x["type"] in ("p", "u")
    }
    for old in baseline["indexes"]:
        if (
            old["name"] in constraint_index_names
            or old["table_name"] in merges
            or old["name"] == "idx_training_history_run_phase_epoch"
        ):
            continue
        assert norm(c["indexes"][old["name"]]) == norm(
            parse_sql(old["definition"])[0].stmt
        ), ("Legacy index changed", old["name"])
        preserved_indexes += 1
    for old in baseline["views"]:
        assert norm(c["views"][old["name"]].query) == norm(
            parse_sql(old["definition"])[0].stmt
        ), ("Legacy view changed", old["name"])

    # Event guard bytes and event column types remain exact; head change does not bypass runtime guards.
    guard = c["functions"]["public.train_event_guard"]
    body = next(o.arg[0].sval for o in guard.options if o.defname == "as")
    assert hashlib.md5(body.encode()).hexdigest() == "d72ebe0d596f864bd42fcac85a91f9b1"
    for col in ("event_sequence", "event_id"):
        assert c["tables"]["train_execution_records"][col].typeName.typmods is None
    assert (
        "train_event_id_unique" in c["indexes"]
        and "train_event_sequence_unique" in c["indexes"]
    )

    history = json.loads(
        (ROOT / "docs/audits/e10_10_5a_history_manifest.json").read_text()
    )
    for name, sha in history["files"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, (
            "Historical bytes changed",
            name,
        )
    assert (
        len(history["captured_ledger"]) == 22
        and history["excluded_seed"] not in history["captured_ledger"]
    )
    for name, sha in history["captured_ledger"].items():
        assert (
            hashlib.sha256(
                (ROOT / "malaria_dl_local_project/db/init" / name).read_bytes()
            ).hexdigest()
            == sha
        )
    protected = baseline["table_policy"]["PROTECTED_TABLES"]
    source_tables = {
        s.stmt.relation.relname: s.stmt
        for s in parse_sql(
            (ROOT / "docs/audits/e10_10_4_target_schema.sql").read_text()
        )
        if isinstance(s.stmt, ast.CreateStmt)
    }
    for t in protected:
        assert [norm(col) for col in c["tables"][t].values()] == [
            norm(col) for col in source_tables[t].tableElts
        ], ("Protected shape changed", t)

    return {
        "stage": "E10.10.5A",
        "status": "STATIC_CHECKS_PASSED_PENDING_REVIEW",
        "parser_postgresql_version": list(get_postgresql_version()),
        "postgresql_17_executed": False,
        "database_connections": 0,
        "revision": manifest["revision"],
        "application_tables": len(c["tables"]),
        "physical_tables_including_alembic": len(c["tables"]) + 1,
        "views": len(c["views"]),
        "functions": len(c["functions"]),
        "triggers": len(c["triggers"]),
        "constraints": len(c["constraints"]),
        "constraint_types": dict(
            collections.Counter(v.contype.name for v in c["constraints"].values())
        ),
        "independent_indexes": len(c["indexes"]),
        "sequences": len(c["sequence"]),
        "plpgsql_bodies_parsed": c["plpgsql"],
        "statements": len(statements),
        "legacy_functions_preserved": len(inherited_functions),
        "legacy_triggers_preserved": len(inherited_triggers),
        "legacy_constraints_preserved": preserved_constraints,
        "legacy_independent_indexes_preserved": preserved_indexes,
        "legacy_views_preserved": len(baseline["views"]),
        "protected_tables_checked": len(protected),
        "historical_files_unchanged": len(history["files"]),
        "accredited_legacy_checksums": 22,
        "limits": [
            "No PostgreSQL 17 catalogue resolution or execution",
            "No runtime trigger/concurrency tests",
            "No installation, adoption, backup/restore or application contract certification",
        ],
    }


def main():
    parser_args = argparse.ArgumentParser(description=__doc__)
    parser_args.add_argument("--report", type=Path)
    args = parser_args.parse_args()
    result = validate()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
