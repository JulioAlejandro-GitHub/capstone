"""Framework-neutral runtime evidence; public integration writes always roll back."""
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from unittest.mock import patch

import pytest
from sqlalchemy import text

from src.malaria_dl.persistence import run_repository as runs
from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.governance.services.prepare_release_service import (
    PrepareModelReleaseService, observed_framework_version,
)


@pytest.mark.parametrize(('framework', 'runtime', 'expected'), [
    ('keras', {'tensorflow': '2.17.1', 'packages': {'keras': '3.15.1'}}, '3.15.1'),
    ('tensorflow', {'tensorflow': '2.17.1'}, '2.17.1'),
    ('pytorch', {'packages': {'torch': '2.8.0', 'keras': '3.15.1'}}, '2.8.0'),
    ('pytorch', {'packages': {'keras': '3.15.1'}}, None),
    ('openclip', {'packages': {'open-clip-torch': '3.2.0', 'keras': '3.15.1'}}, '3.2.0'),
    ('openclip', {'packages': {'torch': '2.8.0'}}, None),
    (None, {'packages': {'keras': '3.15.1'}}, None),
    ('keras', {}, None),
])
def test_version_requires_framework_evidence(framework, runtime, expected):
    assert observed_framework_version(framework, runtime) == expected


@pytest.mark.parametrize('provided', [None, {}, {'host_name': 'executor', 'packages': {'torch': '2.8.0'}}])
def test_start_preserves_parameters_and_explicit_executor(provided):
    env = {'host_name': 'caller', 'gpu_devices': [], 'tensorflow': None, 'packages': {'torch': '2.7.0'}}
    parameters = {'epochs': 5, 'runtime_environment': provided}
    before = deepcopy(parameters)
    with patch.object(runs, 'collect_runtime_environment', return_value=env), patch.object(runs, '_execute_returning_id', return_value='id') as execute:
        assert runs.start_run(execution_parameters=parameters) == 'id'
    sql, values = execute.call_args.args
    assert json.loads(values['execution_parameters']) == {'epochs': 5, 'runtime_environment': provided or env}
    assert parameters == before
    assert 'tensorflow_version' not in sql and 'keras_version' not in sql
    assert 'tensorflow' not in values and 'packages' not in values


def test_capture_without_tensorflow_records_installed_packages():
    absent = {'tensorflow_version': None, 'keras_version': None, 'gpu_available': None, 'gpu_devices': []}
    with patch.object(runs, '_tensorflow_environment', return_value=absent):
        env = runs.collect_runtime_environment()
    assert env['tensorflow'] is None
    assert env['packages']['sqlalchemy']
    assert 'tensorflow_version' not in env and 'keras_version' not in env


@pytest.mark.requires_docker_postgres
@pytest.mark.skipif(os.getenv('RUN_STAGE4_POSTGRES_TESTS') != '1', reason='PostgreSQL opt-in')
def test_real_start_and_release_context_rollback(monkeypatch):
    engine = get_engine()
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                @contextmanager
                def scope():
                    yield connection
                monkeypatch.setattr(runs, 'get_connection', scope)
                # Capture the actual process environment, then verify the actual INSERT.
                env = runs.collect_runtime_environment()
                monkeypatch.setattr(runs, 'collect_runtime_environment', lambda: env)
                run_id = runs.start_run(run_type='training', execution_parameters={'contract_test': True})
                assert run_id is not None
                row = connection.execute(text('SELECT execution_parameters FROM runs WHERE id=:id'), {'id': run_id}).scalar_one()
                assert row == {'contract_test': True, 'runtime_environment': env}
                ExecutionRepository.project_runtime(connection, run_id, {})
                assert connection.execute(text("SELECT execution_parameters FROM runs WHERE id=:id"), {"id": run_id}).scalar_one() == row
                service = PrepareModelReleaseService(connection_factory=scope)
                ids = connection.execute(text("SELECT id FROM runs WHERE run_type='training' AND id<>:id"), {'id': run_id}).scalars().all()
                assert ids
                for training_id in ids:
                    context = service._load_context(str(training_id), validate_model=False)
                    assert context.exists
                    if context.framework and ('keras' in context.framework.lower() or 'tensorflow' in context.framework.lower()):
                        assert context.framework_version == '3.15.1'
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
