"""Score of every VAL cell at every TRAIN epoch, exactly as TRAIN recorded it.

The population is never repaired: a missing, duplicated or changing epoch makes the
trajectory «inconsistent» with its reasons, instead of a silently completed matrix.
A cell gets its governed sample_id only by an exact, unique relative-path match with the
latest verified VAL EVALUATE of the same TRAIN; otherwise it stays without one.
"""
import math
from typing import Annotated, Any
from uuid import UUID
from fastapi import Depends, HTTPException
from app.repositories.training_trajectories import TrainingTrajectoryRepository

# collect_predictions(..., threshold=0.5) in TRAIN: the operating threshold of these records.
TRAINING_THRESHOLD = 0.5


def score(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return round(value, 5) if math.isfinite(value) and 0 <= value <= 1 else None


def governed_ids(evaluation: dict[str, Any] | None) -> dict[str, str]:
    """relative_path → sample_id, only for paths that occur exactly once."""
    paths: dict[str, list[str]] = {}
    for sample in (evaluation or {}).get('samples') or []:
        if isinstance(sample, dict) and sample.get('relative_path') and sample.get('sample_id'):
            paths.setdefault(str(sample['relative_path']), []).append(str(sample['sample_id']))
    return {path: ids[0] for path, ids in paths.items() if len(ids) == 1}


class TrainingTrajectoryService:
    def __init__(self, repository: TrainingTrajectoryRepository) -> None:
        self.repository = repository

    def read(self, run_id: UUID, datasource: str | None) -> dict[str, Any]:
        source = self.repository.read(run_id, datasource)
        if source is None:
            raise HTTPException(404, 'Run no encontrado')
        if source['run']['run_type'] != 'training':
            raise HTTPException(422, 'run_id debe identificar un TRAIN')
        evaluation = source['evaluation']
        result: dict[str, Any] = dict(training_run_id=str(run_id), state='missing', issues=[], epochs=[], samples=[], scores=[],
                                      training_threshold=TRAINING_THRESHOLD,
                                      evaluation_attempt_id=str(evaluation['attempt_id']) if evaluation else None)
        records = source['predictions']
        if not records:
            result['issues'] = ['Este TRAIN no registró predicciones VAL por época.']
            return result
        issues: set[str] = set()
        epochs: list[dict[str, Any]] = []
        columns: list[dict[str, float | None]] = []
        labels: dict[str, int] = {}
        population: set[str] | None = None
        for record in records:
            payload = record['payload']
            epoch = payload.get('epoch')
            if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1 or any(e['epoch'] == epoch for e in epochs):
                issues.add('Época inválida o duplicada en las predicciones VAL.')
                continue
            column: dict[str, float | None] = {}
            for item in payload.get('samples') if isinstance(payload.get('samples'), list) else []:
                sample, label = (item.get('sample'), item.get('label')) if isinstance(item, dict) else (None, None)
                if not isinstance(sample, str) or not sample or label not in (0, 1) or isinstance(label, bool) or sample in column:
                    issues.add('Muestra, etiqueta o duplicado inválido en una época.')
                    continue
                if labels.setdefault(sample, label) != label:
                    issues.add('Una muestra cambia de etiqueta entre épocas.')
                value = score(item.get('score'))
                if value is None:
                    issues.add('Score ausente o fuera de [0, 1].')
                column[sample] = value
            if population is None:
                population = set(column)
            elif set(column) != population:
                issues.add('La población VAL cambia entre épocas.')
            epochs.append({'epoch': epoch, 'phase': record['phase']})
            columns.append(column)
        expected = list(range(1, len(epochs) + 1))
        if [e['epoch'] for e in epochs] != expected:
            issues.add('Las épocas registradas no son consecutivas desde 1.')
        if issues or not population:
            result.update(state='inconsistent', issues=sorted(issues or {'Predicciones VAL sin muestras.'}))
            return result
        ids = governed_ids(evaluation)
        ordered = sorted(population)
        result.update(state='available', epochs=epochs,
                      samples=[{'sample': path, 'label': labels[path], 'sample_id': ids.get(path)} for path in ordered],
                      scores=[[column[path] for column in columns] for path in ordered])
        if evaluation is None:
            result['issues'] = ['Sin EVALUATE VAL verificada: las células no se enlazan con su sample_id gobernado.']
        elif not any(sample['sample_id'] for sample in result['samples']):
            result['issues'] = ['Ninguna ruta coincide con la EVALUATE VAL verificada: células sin sample_id gobernado.']
        return result


def get_training_trajectory_service(repository: Annotated[TrainingTrajectoryRepository, Depends()]) -> TrainingTrajectoryService:
    return TrainingTrajectoryService(repository)
