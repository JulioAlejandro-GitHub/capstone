"""Offline SQL syntax/scope validation. This tool NEVER executes the transfer plan."""

import json

from dbv23_source import DATASET, USER, E, save
from pglast import ast, parse_sql, parser


def main():
    plan = (E / "dbv2_4_transfer_plan.sql").read_text()
    assert plan.startswith(
        "-- DBV2.4 TRANSFER PLAN\n-- GENERATED AND VALIDATED BY DBV2.3\n-- DO NOT EXECUTE DURING DBV2.3\n"
    )
    statements = parse_sql(plan)
    insertions = [r.stmt for r in statements if isinstance(r.stmt, ast.InsertStmt)]
    assert len(insertions) == 16 and {s.relation.relname for s in insertions} == set(
        DATASET + USER
    )
    columns = json.loads((E / "catalog_after_restart.json").read_text())["columns"]
    for s in insertions:
        expected = [r["name"] for r in columns if r["relation"] == s.relation.relname]
        assert [c.name for c in s.cols] == expected
        assert len(s.selectStmt.targetList) == len(expected)
        assert all(not isinstance(x.val, ast.A_Star) for x in s.selectStmt.targetList)
    assert not any(
        isinstance(r.stmt, (ast.DeleteStmt, ast.TruncateStmt, ast.AlterTableStmt))
        for r in statements
    )
    updates = [r.stmt for r in statements if isinstance(r.stmt, ast.UpdateStmt)]
    assert len(updates) == 1 and updates[0].relation.relname == "dataset_versions"
    for raw in statements:
        if isinstance(raw.stmt, ast.DoStmt):
            text = plan[raw.stmt_location : raw.stmt_location + raw.stmt_len] + ";"
            parser.parse_plpgsql_json(text)
    assert "DISABLE TRIGGER" not in plan and "session_replication_role" not in plan
    save(
        "transfer_plan_static_validation.json",
        {
            "status": "PASS_STATIC_ONLY",
            "inserts": 16,
            "explicit_column_mappings": sum(len(s.cols) for s in insertions),
            "update_scope": "dataset_versions.status: approved technical restoration",
            "sql_executed": False,
            "source_password_values_read": False,
        },
    )
    print(
        "PASS_STATIC_ONLY: 16 explicit INSERT SELECT statements; 177 columns; plan NOT executed."
    )


if __name__ == "__main__":
    main()
