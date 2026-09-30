"""Offline materialization of approved DBV2.1 + R1. Never executes design SQL.

The archived candidate is read ONLY for reviewed retained ACLs and historical
comparison. Installed Alembic resources are self-contained and hash-verified.
"""

import argparse
import hashlib
import json
import re
from collections import Counter

from pglast import ast, parse_sql
from pglast.enums import ConstrType as CT

try:
    from .build_v2_baseline import render, strings
    from .dbv22_xai_regression import validate_xai_dispatch
    from .validate_dbv2_1 import ROOT, SQL, build, catalogue, norm, read_sql
except ImportError:  # Direct CLI invocation.
    from build_v2_baseline import render, strings
    from dbv22_xai_regression import validate_xai_dispatch
    from validate_dbv2_1 import ROOT, SQL, build, catalogue, norm, read_sql

REFERENCE = ROOT / "docs/audits/db_v2/dbv2_2/restart_r1/reference_candidate"
DEST = ROOT / "alembic_v2/baseline"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def artifacts():
    build(False, REFERENCE)
    validate_xai_dispatch(SQL.read_text())
    statements = read_sql(SQL)
    c = catalogue(statements)
    groups = {
        f"{i:02}_{n}": []
        for i, n in enumerate(
            [
                "prerequisites",
                "generated_functions",
                "tables",
                "functions",
                "keys",
                "constraints",
                "indexes",
                "views",
                "triggers",
                "privileges",
                "technical_state",
            ],
            1,
        )
    }

    def add(phase, kind, name, sql, **meta):
        groups[phase].append(
            dict(kind=kind, name=name, sql=sql.strip().rstrip(";") + ";", **meta)
        )

    for raw in statements:
        s = parse_sql(raw)[0].stmt
        sql = render(s)
        if isinstance(s, ast.CreateStmt):
            name = s.relation.relname
            columns = {}
            for col in s.tableElts:
                cs = col.constraints or ()
                val = lambda typ, cs=cs: next(
                    (render(x.raw_expr) for x in cs if x.contype == typ), None
                )
                columns[col.colname] = {
                    "declaration": render(col),
                    "type": render(col.typeName),
                    "nullable": col.colname not in c["primary"][name]
                    and not any(x.contype == CT.CONSTR_NOTNULL for x in cs),
                    "default": val(CT.CONSTR_DEFAULT),
                    "generated": val(CT.CONSTR_GENERATED),
                    "identity": next(
                        (
                            x.generated_when
                            for x in cs
                            if x.contype == CT.CONSTR_IDENTITY
                        ),
                        "",
                    ),
                }
            add("03_tables", "table", name, sql, columns=columns)
        elif isinstance(s, ast.CreateFunctionStmt):
            name = ".".join(strings(s.funcname))
            phase = (
                "02_generated_functions"
                if name
                in ("public.assessment_canonical", "public.assessment_structural_hash")
                else "04_functions"
            )
            add(phase, "function", name, sql)
        elif isinstance(s, ast.AlterTableStmt):
            co = s.cmds[0].def_
            t = s.relation.relname
            phase = (
                "05_keys"
                if co.contype in (CT.CONSTR_PRIMARY, CT.CONSTR_UNIQUE)
                else "06_constraints"
            )
            add(
                phase,
                "constraint",
                t + "." + co.conname,
                sql,
                table=t,
                constraint_type=co.contype.name,
            )
        elif isinstance(s, ast.IndexStmt):
            phase = "05_keys" if s.unique and s.whereClause is None else "07_indexes"
            add(phase, "index", s.idxname, sql, table=s.relation.relname)
        elif isinstance(s, ast.ViewStmt):
            add("08_views", "view", s.view.relname, sql)
        elif isinstance(s, ast.CreateTrigStmt):
            add("09_triggers", "trigger", s.relation.relname + "." + s.trigname, sql)
        elif isinstance(s, ast.VariableSetStmt):
            add("01_prerequisites", "setting", s.name, sql)
        elif isinstance(s, ast.CreateExtensionStmt):
            add("01_prerequisites", "extension", s.extname, sql)
        elif isinstance(s, ast.GrantStmt):
            add("01_prerequisites", "acl", "public_schema", sql)
        else:
            raise TypeError(type(s))
    # PK/UNIQUE precede explicit UNIQUE indexes and all FKs.
    groups["05_keys"].sort(key=lambda x: x["kind"] == "index")
    removed = (
        "schema_migrations",
        "model_governance_backfill_audit",
        "prevent_model_governance_audit_mutation",
        "v2_xai_comparison_guard",
    )
    for raw in read_sql(REFERENCE / "alembic_v2/baseline/10_privileges.sql"):
        sql = render(parse_sql(raw)[0].stmt)
        if any(re.search(r"\b" + name + r"\b", sql) for name in removed):
            continue
        add("10_privileges", "acl", "retained_acl", sql)
    for t in (
        "xai_method_configurations",
        "xai_region_attributions",
        "xai_evaluation_protocols",
        "xai_evaluation_members",
    ):
        add(
            "10_privileges",
            "acl",
            t,
            f"GRANT SELECT, INSERT ON TABLE public.{t} TO capstone_v2_runtime",
        )
    for f in ("dbv21_xai_configuration_guard", "dbv21_xai_evaluation_complete"):
        add(
            "10_privileges",
            "acl",
            f,
            f"REVOKE ALL ON FUNCTION public.{f}() FROM PUBLIC",
        )
        add(
            "10_privileges",
            "acl",
            f,
            f"GRANT EXECUTE ON FUNCTION public.{f}() TO capstone_v2_runtime",
        )
    for raw in read_sql(REFERENCE / "alembic_v2/baseline/11_technical_state.sql"):
        add(
            "11_technical_state",
            "seed",
            "experiment_execution_gate",
            render(parse_sql(raw)[0].stmt),
        )
    files = {}
    entries = []
    for phase, rows in groups.items():
        data = b"-- DBV2.2 + approved R1. Install exclusively via guarded Alembic v2.\n"
        for row in rows:
            row = dict(row)
            sql = row.pop("sql").encode()
            start = len(data)
            data += sql + b"\n\n"
            entries.append(
                dict(
                    row,
                    phase=phase,
                    file=phase + ".sql",
                    start=start,
                    end=start + len(sql),
                    sha256=digest(sql),
                )
            )
        files[phase + ".sql"] = data
    # Independent AST identity check against the approved specification.
    actual = catalogue(
        [
            files[e["file"]][e["start"] : e["end"]].decode()
            for e in entries
            if e["phase"] < "10"
        ]
    )
    for key in (
        "tables",
        "constraints",
        "indexes",
        "functions",
        "triggers",
        "views",
        "primary",
        "sequence",
    ):
        assert norm(actual[key]) == norm(c[key]), key
    old = json.loads(
        (REFERENCE / "alembic_v2/baseline/catalog_manifest.json").read_text()
    )
    manifest = {
        k: old[k]
        for k in (
            "format_version",
            "revision",
            "identity_sequences",
            "generated_column_contracts",
            "managed_by_alembic",
            "e04_contract_sha256",
        )
    }
    manifest.update(
        source_sha256=digest(SQL.read_bytes()),
        contract="DBV2.1 + DBV2.2-R1",
        counts=dict(Counter(e["kind"] for e in entries)),
        files={n: digest(d) for n, d in files.items()},
        statements=entries,
    )
    files["catalog_manifest.json"] = (
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode()
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    for name, data in artifacts().items():
        if args.write:
            (DEST / name).write_bytes(data)
        else:
            assert (DEST / name).read_bytes() == data, "Baseline differs: " + name
    print(
        "PASS_STATIC_ONLY: baseline AST identities match corrected DBV2.1; deterministic resources verified"
    )
