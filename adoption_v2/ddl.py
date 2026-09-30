"""Static in-place delta from audited legacy shape to certified Route A.

Existing guards are never disabled. The two reviewed MERGE tables are removed
only after their complete private archive and reconciliation are durable.
"""

import re

from pglast import parse_sql
from pglast.stream import RawStream

from .core import contract, require, target


def qi(name):
    return '"' + name.replace('"', '""') + '"'


def qtable(name):
    return "public." + qi(name)


def same_type(a, b):
    return RawStream()(parse_sql("SELECT NULL::" + a)) == RawStream()(
        parse_sql("SELECT NULL::" + b)
    )


def delta():
    spec = contract()
    manifest, statements = target()
    pairs = list(zip(manifest["statements"], statements, strict=True))
    source_tables = set(spec["tables"])
    target_tables = {e["name"] for e, _ in pairs if e["kind"] == "table"} | {
        "alembic_version"
    }
    require(
        source_tables - target_tables
        == {"confusion_matrices", "classification_reports"},
        "UNAPPROVED_TABLE_REMOVAL",
    )
    before = []
    after = []
    acl = []
    legacy_views = {r["name"] for r in spec["expected_schema"]["views"]}
    for e, _ in reversed(pairs):
        if e["kind"] == "view" and e["name"] in legacy_views:
            before.append("DROP VIEW " + qtable(e["name"]))
    legacy_indexes = {
        r["name"]: r
        for r in spec["expected_schema"]["indexes"]
        if not r["indisprimary"]
    }
    {e["name"] for e, _ in pairs if e["kind"] == "index"}
    # Only the approved redundant epoch index is removed outside MERGE tables.
    require(
        "idx_training_history_run_phase_epoch" in legacy_indexes,
        "LEGACY_EPOCH_INDEX_MISSING",
    )
    before.append("DROP INDEX public.idx_training_history_run_phase_epoch")
    for e, statement in pairs:
        if e["kind"] != "table":
            continue
        t = e["name"]
        if t not in source_tables:
            before.append(statement)
            continue
        oldcols = {
            r["column_name"]: r
            for r in spec["expected_schema"]["columns"]
            if r["table_name"] == t
        }
        require(set(oldcols) <= set(e["columns"]), "UNAPPROVED_COLUMN_REMOVAL", t)
        for name, col in e["columns"].items():
            column = qi(name)
            tbl = qtable(t)
            if name not in oldcols:
                declaration = column + " " + col["type"]
                if col["generated"]:
                    declaration += (
                        " GENERATED ALWAYS AS (" + col["generated"] + ") STORED"
                    )
                elif col["default"] is not None:
                    declaration += " DEFAULT " + col["default"]
                before.append("ALTER TABLE " + tbl + " ADD COLUMN " + declaration)
                if not col["nullable"]:
                    after.append(
                        "ALTER TABLE "
                        + tbl
                        + " ALTER COLUMN "
                        + column
                        + " SET NOT NULL"
                    )
            else:
                oldtype = spec["column_types"][t][name]
                if not same_type(oldtype, col["type"]):
                    require(
                        spec["tables"][t]["action"] == "REFACTOR",
                        "PROTECTED_TYPE_CHANGE",
                        t,
                    )
                    before.append(
                        f"ALTER TABLE {tbl} ALTER COLUMN {column} TYPE {col['type']} USING {column}::{col['type']}"
                    )
                if oldcols[name]["is_nullable"] == "YES" and not col["nullable"]:
                    after.append(
                        "ALTER TABLE "
                        + tbl
                        + " ALTER COLUMN "
                        + column
                        + " SET NOT NULL"
                    )
    functions = {
        r["schema"] + "." + r["name"] for r in spec["expected_schema"]["functions"]
    }
    for e, statement in pairs:
        if e["kind"] == "function" and e["name"] not in functions:
            before.append(statement)
    for t in sorted(source_tables - target_tables):
        after.append("DROP TABLE " + qtable(t))
    constraints = {
        r["table_name"] + "." + r["name"]
        for r in spec["expected_schema"]["constraints"]
    }
    triggers = {
        r["table_name"] + "." + r["name"] for r in spec["expected_schema"]["triggers"]
    }
    final_triggers = []
    for e, statement in pairs:
        kind = e["kind"]
        if (
            kind == "constraint"
            and e["name"] not in constraints
            or kind == "index"
            and e["name"] not in legacy_indexes
            or kind == "view"
        ):
            after.append(statement)
        elif kind == "trigger" and e["name"] not in triggers:
            final_triggers.append(statement)
        elif kind in ("acl", "sequence_ownership"):
            acl.append(statement)
    # Revalidate trigger-only invariants on adopted rows before installing immutable guards.
    validation = []
    probes = {
        "run_configurations": ["v2_configuration_guard"],
        "run_clinical_metrics": ["v2_binary_metric_guard"],
        "evaluations": ["v2_evaluation_complete", "e04_calibration_complete"],
        "evaluation_ensemble_members": ["v2_evaluation_complete"],
        "run_threshold_calibration": ["v2_calibration_pair_guard", "e04_calibration_complete"],
        "xai_evidence": ["v2_xai_lineage_guard"],
        "xai_artifacts": ["v2_xai_artifact_source_guard"],
    }
    table_specs = {e["name"]: e for e, _ in pairs if e["kind"] == "table"}
    for table, functions in probes.items():
        for fn in functions:
            trigger = "adoption_validate_" + fn
            validation.append(
                f"CREATE TRIGGER {qi(trigger)} BEFORE UPDATE ON {qtable(table)} FOR EACH ROW EXECUTE FUNCTION public.{qi(fn)}()"
                if fn not in ("v2_evaluation_complete", "v2_calibration_pair_guard", "e04_calibration_complete")
                else f"CREATE TRIGGER {qi(trigger)} AFTER UPDATE ON {qtable(table)} FOR EACH ROW EXECUTE FUNCTION public.{qi(fn)}()"
            )
            col = next(iter(table_specs[table]["columns"]))
            validation.append(f"UPDATE {qtable(table)} SET {qi(col)}={qi(col)}")
            validation.append(f"DROP TRIGGER {qi(trigger)} ON {qtable(table)}")
    result = {
        "prepare": before,
        "finalize": after,
        "validate": validation,
        "triggers": final_triggers,
        "acl": acl,
    }
    for group in result.values():
        for statement in group:
            require(
                "DISABLE TRIGGER" not in statement
                and "CASCADE" not in statement.upper().split("REFERENCES")[0]
                and not re.search(
                    r"CREATE\s+(?:TABLE|INDEX|EXTENSION)\s+IF\s+NOT\s+EXISTS",
                    statement,
                    re.IGNORECASE,
                ),
                "UNSAFE_DDL",
            )
            parse_sql(statement)
    return result
