"""Project current scientific results without selecting a historical schema."""
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from src.malaria_dl.persistence.result_repository import _PostgresScope
from src.malaria_dl.results import ResultService
from src.malaria_dl.results.models import AcceptanceState
from src.malaria_dl.results.training import TrainingResultsV1, ThresholdResult
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.execution.contracts import RunEventType
from test_result_service import context, event


def test_service_projects_current_results_without_revision(monkeypatch):
    connection = Mock()
    result = TrainingResultsV1(evaluate_validation_predictions(
        [0, 1], [.1, .9], ThresholdResult(.5, 'default')))
    item = event(event_type=RunEventType.EVALUATION_COMPLETED, payload=result.validation.to_dict())
    project = Mock()
    monkeypatch.setattr('src.malaria_dl.persistence.v2_projection.project_evaluation', project)

    class Repository:
        @contextmanager
        def acceptance_scope(self, ctx, ev):
            scope = _PostgresScope(connection, ev, AcceptanceState(
                existing_event=None, sequence_event=None, last_sequence=0))
            yield scope

    assert ResultService(Repository()).accept_event(context(), item).status.value == 'accepted'
    statements = [str(call.args[0]) for call in connection.execute.call_args_list]
    assert 'INSERT INTO train_execution_records' in statements[0]
    updates = [s for s in statements if 'UPDATE runs' in s]
    assert updates == []
    project.assert_called_once_with(connection, item, result)
