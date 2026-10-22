"""preflight_population reads the identity scalars once.

Regression for Comparación Científica consensus over 3 TEST attempts (2.685 samples each):
joining dataset_split_assignments on identity->>'split' re-parsed the ~1 MB identity per
assignment row (~7.5 s per attempt, 22 s per request) and the 15 s client timeout reported a
query error for a valid answer. No database: the SQL text is captured.
"""
import re
from uuid import uuid4

from app.repositories.assessments import AssessmentReadRepository


class Capture:
    def __init__(self):
        self.sql, self.params = None, None

    def execute(self, statement, params):
        self.sql, self.params = str(statement), params
        return type("R", (), {"mappings": lambda self: []})()


def captured():
    connection = Capture()
    ids = [uuid4(), uuid4(), uuid4()]
    assert AssessmentReadRepository().preflight_population(connection, ids) == []
    return connection, ids


def cte(sql, name):
    match = re.search(rf"\b{name} AS (?:MATERIALIZED )?\((.*?)\n            \),", sql, re.S)
    assert match, name
    return match.group(1)


def test_selected_extracts_dataset_version_and_split_once():
    connection, _ = captured()
    assert "selected AS MATERIALIZED (" in connection.sql
    selected = cte(connection.sql, "selected")
    assert "CAST(i.identity#>>'{dataset,dataset_version_id}' AS uuid) AS dataset_version_id" in selected
    assert "i.identity->>'split' AS split" in selected


def test_governed_join_uses_scalars_not_the_identity_jsonb():
    connection, _ = captured()
    governed = connection.sql[connection.sql.index("governed AS ("):connection.sql.index("SELECT s.id AS attempt_id")]
    assert "a.dataset_version_id=s.dataset_version_id" in governed and "a.split_name=s.split" in governed
    assert "identity" not in governed


def test_parameters_are_unchanged():
    connection, ids = captured()
    assert connection.params == {"ids": [str(i) for i in ids], "participants": 3}
