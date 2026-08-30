"""Static contract for the expand-compatible TRAIN release migration."""

from __future__ import annotations

import ast
import re
from pathlib import Path


TEST_FILE = Path(__file__).resolve()
ROOT = next(
    candidate
    for candidate in (TEST_FILE.parents[1], TEST_FILE.parents[2])
    if (candidate / "alembic" / "versions").is_dir()
)
VERSIONS = ROOT / "alembic" / "versions"
MIGRATION = VERSIONS / "20260829_01_persist_training_release_status.py"
SOURCE = MIGRATION.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

EXPECTED_COLUMNS = {
    "release_status",
    "release_updated_at",
    "release_changed_by",
    "release_reason",
}
EXPECTED_STATES = {
    "not_available",
    "available_to_publish",
    "productive_stage2",
}
PREFLIGHT_UUIDS = {
    "623ad00c-0b03-4cf0-8f2c-bb9496efb496",
    "243b1d73-8bae-4a23-a92d-ae2d4b15de31",
    "172b7031-9f79-44e3-a7ad-2dc10a9ffd08",
    "44577ce0-1a80-4971-9f3d-bd78d2a63bf4",
    "81d69942-17eb-4999-a6bd-2b05779a65a4",
    "cf2f20d3-a1e0-499c-b5ab-501b7c1ae198",
}


def _assignment(name: str):
    for node in TREE.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment: {name}")


def _calls(attribute: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(TREE)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
    ]


def test_revision_is_the_only_new_linear_head():
    matching = sorted(VERSIONS.glob("20260829_*.py"))
    assert matching == [MIGRATION]
    assert _assignment("revision") == "20260829_01"
    assert _assignment("down_revision") == "20260812_02"


def test_adds_exactly_four_nullable_release_columns_without_touching_run_status():
    calls = _calls("add_column")
    assert len(calls) == 4
    columns = {}
    for call in calls:
        assert ast.literal_eval(call.args[0]) == "runs"
        column = call.args[1]
        assert isinstance(column, ast.Call)
        name = ast.literal_eval(column.args[0])
        nullable = next(
            ast.literal_eval(keyword.value)
            for keyword in column.keywords
            if keyword.arg == "nullable"
        )
        columns[name] = nullable
    assert set(columns) == EXPECTED_COLUMNS
    assert all(value is True for value in columns.values())
    assert not _calls("alter_column")
    assert 'UPDATE runs AS training' in SOURCE
    assert not re.search(r"SET\s+status\s*=", SOURCE, re.IGNORECASE)


def test_constraints_are_expand_compatible_and_use_exact_vocabulary():
    states = {
        value
        for value in EXPECTED_STATES
        if re.search(rf"['\"]{value}['\"]", SOURCE)
    }
    assert states == EXPECTED_STATES
    assert "release_status IS NULL" in SOURCE
    assert "run_type = 'training'" in SOURCE
    assert "release_status IS NULL OR release_updated_at IS NOT NULL" in SOURCE
    assert "ck_runs_release_status_training_vocabulary" in SOURCE
    assert "ck_runs_release_status_requires_timestamp" in SOURCE


def test_defines_query_and_single_productive_partial_indexes():
    assert "idx_runs_training_release_status" in SOURCE
    assert "uq_runs_single_productive_stage2" in SOURCE
    assert "postgresql_where" in SOURCE
    assert "run_type = 'training' AND release_status = 'productive_stage2'" in SOURCE
    assert "unique=True" in SOURCE


def test_backfill_eligibility_only_requires_completed_train_and_evaluation_lineage():
    assert "training.status = 'completed'" in SOURCE
    assert "evaluation.status = 'completed'" in SOURCE
    assert "eligibility_lineage.relationship_type" in SOURCE
    assert "'evaluates_checkpoint_from'" in SOURCE
    eligibility = SOURCE.split("WHEN training.status = 'completed'", 1)[1].split(
        "THEN 'available_to_publish'", 1
    )[0]
    eligibility = eligibility.replace("evaluates_checkpoint_from", "")
    for forbidden in ("model_version", "checkpoint", "artifact", "threshold", "metric"):
        assert forbidden not in eligibility.lower()


def test_productive_selection_is_complete_and_zero_is_valid():
    assert "publication_count == 0" in SOURCE
    assert "publication_count > 1" in SOURCE
    assert "deployment_count > 1" in SOURCE
    assert "consistent_count != 1" in SOURCE
    assert "publication.status = 'active'" in SOURCE
    assert "publication.is_active = true" in SOURCE
    assert "deployment.status = 'active'" in SOURCE
    assert "deployment.environment = 'stage2'" in SOURCE
    assert "deployment.alias = 'default'" in SOURCE
    assert "production_scope' = 'stage2_experimental'" in SOURCE
    assert "deployment.model_version_id = publication.model_version_id" in SOURCE
    assert "deployment.checkpoint_artifact_id = publication.checkpoint_artifact_id" in SOURCE
    assert "lineage.model_version_id = publication.model_version_id" in SOURCE
    assert "lineage.checkpoint_artifact_id = publication.checkpoint_artifact_id" in SOURCE


def test_migration_has_no_forbidden_resolution_or_external_execution():
    lowered = SOURCE.lower()
    assert "order by created_at desc limit 1" not in lowered
    assert not PREFLIGHT_UUIDS.intersection(lowered)
    for command in ("alembic upgrade", "alembic downgrade", "alembic stamp"):
        assert command not in lowered
    for library in ("tensorflow", "keras"):
        assert library not in lowered
    assert "sha256" not in lowered


def test_migration_only_alters_runs_and_creates_no_schema_objects():
    assert not _calls("create_table")
    assert not _calls("drop_table")
    assert not _calls("execute") or "UPDATE runs AS training" in SOURCE
    for statement in ("UPDATE stage2_model_publications", "UPDATE deployed_model_versions", "UPDATE run_lineage", "UPDATE model_versions"):
        assert statement not in SOURCE
    assert "CREATE TYPE" not in SOURCE.upper()
    assert "CREATE TABLE" not in SOURCE.upper()


def test_downgrade_is_explicitly_forward_only():
    function = next(
        node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
    )
    assert any(isinstance(node, ast.Raise) for node in ast.walk(function))
