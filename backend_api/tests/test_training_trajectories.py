from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.training_trajectories import TrainingTrajectories
from app.services.training_trajectories import TrainingTrajectoryService


def record(epoch, phase, samples):
    return {'phase': phase, 'record_key': str(epoch), 'payload': {'role': 'val', 'epoch': epoch, 'samples': samples}}


def cells(*scores):
    return [{'sample': 'val/Parasitized/a.png', 'label': 1, 'score': scores[0]},
            {'sample': 'val/Uninfected/b.png', 'label': 0, 'score': scores[1]}]


class Repository:
    def __init__(self, predictions, evaluation=None, run_type='training'):
        self.source = dict(run={'run_type': run_type}, predictions=predictions, evaluation=evaluation)

    def read(self, run_id, datasource):
        return self.source


def read(repository):
    return TrainingTrajectories.model_validate(TrainingTrajectoryService(repository).read(uuid4(), 'malaria'))


def test_every_cell_keeps_its_recorded_score_at_every_epoch_and_phase():
    sample = uuid4()
    evaluation = {'attempt_id': uuid4(), 'samples': [{'sample_id': str(sample), 'relative_path': 'val/Parasitized/a.png'}]}
    result = read(Repository([record(1, 'base', cells(0.2, 0.4)), record(2, 'fine_tuning', cells(0.9, 0.1))], evaluation))
    assert result.state == 'available' and not result.issues
    assert [(e.epoch, e.phase) for e in result.epochs] == [(1, 'base'), (2, 'fine_tuning')]
    assert [s.sample for s in result.samples] == ['val/Parasitized/a.png', 'val/Uninfected/b.png']
    assert result.scores == [[0.2, 0.9], [0.4, 0.1]]
    assert result.samples[0].sample_id == sample and result.samples[1].sample_id is None
    assert result.training_threshold == 0.5


def test_a_changing_population_is_reported_and_never_completed():
    changed = [{'sample': 'val/Parasitized/a.png', 'label': 1, 'score': 0.3}]
    result = read(Repository([record(1, 'base', cells(0.2, 0.4)), record(2, 'base', changed)]))
    assert result.state == 'inconsistent' and result.scores == [] and 'La población VAL cambia entre épocas.' in result.issues


def test_duplicated_or_skipped_epochs_and_invalid_scores_are_inconsistent():
    assert read(Repository([record(1, 'base', cells(0.2, 0.4)), record(1, 'fine_tuning', cells(0.2, 0.4))])).state == 'inconsistent'
    assert 'Las épocas registradas no son consecutivas desde 1.' in read(Repository([record(2, 'base', cells(0.2, 0.4))])).issues
    assert 'Score ausente o fuera de [0, 1].' in read(Repository([record(1, 'base', cells(1.5, 0.4))])).issues


def test_ambiguous_paths_are_not_linked_to_a_sample_id():
    evaluation = {'attempt_id': uuid4(), 'samples': [{'sample_id': str(uuid4()), 'relative_path': 'val/Parasitized/a.png'},
                                                      {'sample_id': str(uuid4()), 'relative_path': 'val/Parasitized/a.png'}]}
    result = read(Repository([record(1, 'base', cells(0.2, 0.4))], evaluation))
    assert result.state == 'available' and all(s.sample_id is None for s in result.samples)
    assert result.issues == ['Ninguna ruta coincide con la EVALUATE VAL verificada: células sin sample_id gobernado.']


def test_without_records_the_trajectory_is_missing_and_says_why():
    result = read(Repository([]))
    assert result.state == 'missing' and result.issues == ['Este TRAIN no registró predicciones VAL por época.']


def test_only_a_train_has_trajectories():
    with pytest.raises(HTTPException) as error:
        TrainingTrajectoryService(Repository([], run_type='evaluation')).read(uuid4(), 'malaria')
    assert error.value.status_code == 422


def test_route_is_registered_in_the_application():
    from app.main import app
    assert '/runs/{run_id}/training-trajectories' in app.openapi()['paths']
