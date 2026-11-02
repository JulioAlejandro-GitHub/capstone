import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException

from app.schemas.activation_traces import ActivationTraceCatalog
from app.services import activation_traces
from app.services.activation_trace_compute import VERSION, block_of, statistics, write_atomic
from app.services.activation_traces import ActivationTraceService


class Architecture:
    def __init__(self, architecture='vgg16', run_type='training'):
        self.source = dict(run={'run_type': run_type}, configuration={'architecture': architecture})

    def read(self, run_id, datasource):
        return self.source


class Evaluations:
    def evaluation(self, run_id, datasource):
        return {'id': uuid4(), 'split': 'val'}

    def result(self, attempt, sample, datasource):
        return {'raw_score': 0.5}


def saved(root, run, sample, **values):
    write_atomic(root / str(run) / f'{sample}.json', dict(created_at='2026-11-01T10:00:00', label=1, predicted=0, score=0.03, persisted_score=0.03,
                                                         consistent=True, split='val', checkpoint_sha256='abc', version=VERSION, **values))


def test_saved_traces_are_listed_when_the_run_is_reopened(tmp_path):
    run, sample = uuid4(), uuid4()
    saved(tmp_path, run, sample)
    result = ActivationTraceCatalog.model_validate(ActivationTraceService(Evaluations(), Architecture(), tmp_path).catalog(run, 'malaria'))
    assert result.available and [item.sample_id for item in result.items] == [sample]
    assert result.used_bytes == result.items[0].bytes > 0


def test_only_vgg16_is_supported_and_other_models_say_why(tmp_path):
    result = ActivationTraceService(Evaluations(), Architecture('custom_cnn'), tmp_path).catalog(uuid4(), 'malaria')
    assert not result['available'] and 'VGG16' in result['reason']
    with pytest.raises(HTTPException) as error:
        ActivationTraceService(Evaluations(), Architecture('custom_cnn'), tmp_path).create(uuid4(), uuid4(), 'malaria')
    assert error.value.status_code == 409


def representing(monkeypatch, sha='abc'):
    class Repository:
        def source(self, attempt):
            return {'identity': {'model': {'sha256': sha}, 'samples': []}}
    monkeypatch.setattr(activation_traces, 'RepresentRepository', Repository)


def test_existing_trace_is_reused_without_running_the_model(tmp_path, monkeypatch):
    run, sample = uuid4(), uuid4()
    saved(tmp_path, run, sample)
    representing(monkeypatch)
    monkeypatch.setattr(activation_traces.subprocess, 'run', lambda *args, **kwargs: pytest.fail('no debe recalcular'))
    assert ActivationTraceService(Evaluations(), Architecture(), tmp_path).create(run, sample, 'malaria')['sample_id'] == str(sample)


def test_limit_blocks_new_traces_and_never_deletes_saved_ones(tmp_path, monkeypatch):
    run, sample = uuid4(), uuid4()
    saved(tmp_path, run, sample)
    representing(monkeypatch)
    monkeypatch.setattr(activation_traces, 'MAX_BYTES', 1)
    with pytest.raises(HTTPException) as error:
        ActivationTraceService(Evaluations(), Architecture(), tmp_path).create(run, uuid4(), 'malaria')
    assert error.value.status_code == 409 and '500 MB' in error.value.detail
    assert (tmp_path / str(run) / f'{sample}.json').is_file()


def test_delete_removes_only_the_requested_trace(tmp_path):
    run, first, second = uuid4(), uuid4(), uuid4()
    saved(tmp_path, run, first), saved(tmp_path, run, second)
    service = ActivationTraceService(Evaluations(), Architecture(), tmp_path)
    service.delete(run, first)
    assert [Path(item).stem for item in map(str, (tmp_path / str(run)).glob('*.json'))] == [str(second)]
    with pytest.raises(HTTPException) as error:
        service.read(run, first)
    assert error.value.status_code == 404


def test_step_blocks_and_statistics_follow_the_architecture():
    assert [block_of(name) for name in ('block3_pool', 'global_avg_pool', 'binary_output')] == ['block3', 'head', 'output']
    assert statistics(np.array([0.0, 2.0])) == {'min': 0.0, 'max': 2.0, 'mean': 1.0, 'std': 1.0, 'active': 0.5}


def test_atomic_write_leaves_no_partial_file(tmp_path):
    write_atomic(tmp_path / 'run' / 'cell.json', {'score': 1})
    assert [path.name for path in (tmp_path / 'run').iterdir()] == ['cell.json']
    assert json.loads((tmp_path / 'run' / 'cell.json').read_text()) == {'score': 1}


def test_routes_are_registered_in_the_application():
    from app.main import app
    assert {'/runs/{run_id}/activation-traces', '/runs/{run_id}/activation-traces/candidates',
            '/runs/{run_id}/activation-traces/{sample_id}'} <= set(app.openapi()['paths'])
