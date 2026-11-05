"""Saved forward passes of single cells, one JSON file per cell. Nothing is overwritten or evicted."""
import json
import subprocess
import sys
from pathlib import Path
from threading import Lock
from typing import Annotated, Any
from uuid import UUID
from fastapi import Depends, HTTPException
from app.config import get_settings
from app.repositories.activation_traces import CATEGORIES, ActivationTraceRepository
from app.repositories.model_architecture import ModelArchitectureRepository
from app.repositories.representation_generation import RepresentRepository
from app.services.activation_trace_compute import VERSION

MAX_BYTES = 500 * 1024 * 1024
# Keras CNNs whose layers the trace knows how to group into the architecture's blocks.
TRACEABLE = {'vgg16': 'VGG16', 'custom_cnn': 'CNN propia', 'densenet121': 'DenseNet121'}
TIMEOUT_SECONDS = 120
SUMMARY = ('sample_id', 'created_at', 'label', 'predicted', 'score', 'persisted_score', 'consistent', 'split', 'bytes')
# One model load at a time keeps the machine usable; the use is occasional.
computing = Lock()


class ActivationTraceService:
    def __init__(self, repository: ActivationTraceRepository, architecture: ModelArchitectureRepository, root: Path) -> None:
        self.repository = repository
        self.architecture = architecture
        self.root = root

    def _supported(self, run_id: UUID, datasource: str | None) -> tuple[dict[str, Any] | None, str | None]:
        source = self.architecture.read(run_id, datasource)
        if source is None:
            raise HTTPException(404, 'Run no encontrado')
        if source['run']['run_type'] != 'training':
            raise HTTPException(422, 'run_id debe identificar un TRAIN')
        family = (source['configuration'] or {}).get('architecture')
        if family not in TRACEABLE:
            return None, f"El recorrido por capas está disponible para {', '.join(list(TRACEABLE.values())[:-1])} y {list(TRACEABLE.values())[-1]}."
        self.family = family
        evaluation = self.repository.evaluation(run_id, datasource)
        return (evaluation, None) if evaluation else (None, 'Este TRAIN no tiene una EVALUATE verificada.')

    def _directory(self, run_id: UUID) -> Path:
        return self.root / str(run_id)

    def used_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.root.glob('*/*.json')) if self.root.exists() else 0

    def _read(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text()) | {'bytes': path.stat().st_size, 'sample_id': path.stem}

    def catalog(self, run_id: UUID, datasource: str | None) -> dict[str, Any]:
        evaluation, reason = self._supported(run_id, datasource)
        saved = [self._read(path) for path in self._directory(run_id).glob('*.json')]
        items = sorted(({key: item.get(key) for key in SUMMARY} for item in saved), key=lambda item: item['created_at'], reverse=True)
        return dict(available=evaluation is not None, reason=reason, split=evaluation['split'] if evaluation else None,
                    items=items, used_bytes=self.used_bytes(), max_bytes=MAX_BYTES)

    def candidates(self, run_id: UUID, category: str, limit: int, datasource: str | None,
                   explained_only: bool = False) -> list[dict[str, Any]]:
        if category not in CATEGORIES:
            raise HTTPException(422, 'Categoría no válida')
        evaluation, reason = self._supported(run_id, datasource)
        if evaluation is None:
            raise HTTPException(409, reason)
        return self.repository.candidates(evaluation['id'], category, limit, datasource, explained_only)

    def read(self, run_id: UUID, sample_id: UUID) -> dict[str, Any]:
        path = self._directory(run_id) / f'{sample_id}.json'
        if not path.is_file():
            raise HTTPException(404, 'Recorrido no calculado')
        return self._read(path)

    def delete(self, run_id: UUID, sample_id: UUID) -> None:
        path = self._directory(run_id) / f'{sample_id}.json'
        if not path.is_file():
            raise HTTPException(404, 'Recorrido no calculado')
        path.unlink()

    def create(self, run_id: UUID, sample_id: UUID, datasource: str | None) -> dict[str, Any]:
        path = self._directory(run_id) / f'{sample_id}.json'
        evaluation, reason = self._supported(run_id, datasource)
        if evaluation is None:
            raise HTTPException(409, reason)
        value = RepresentRepository().source(str(evaluation['id']))['identity']
        sha256 = value['model'].get('sha256') or value['model'].get('checkpoint_sha256')
        if path.is_file():
            saved = self._read(path)
            if saved.get('checkpoint_sha256') == sha256 and saved.get('version') == VERSION:
                return saved
        if self.used_bytes() >= MAX_BYTES:
            raise HTTPException(409, 'Se alcanzó el límite de 500 MB: elimina un recorrido antes de calcular otro.')
        sample = next((item for item in value['samples'] if str(item.get('sample_id')) == str(sample_id)), None)
        persisted = self.repository.result(evaluation['id'], sample_id, datasource)
        if sample is None or persisted is None:
            raise HTTPException(404, 'La célula no pertenece a la evaluación de este TRAIN')
        if not computing.acquire(blocking=False):
            raise HTTPException(409, 'Ya hay un recorrido en cálculo; inténtalo al terminar.')
        try:
            job = dict(value=value, sample=sample, persisted=persisted, path=str(path), family=self.family, identity=dict(
                training_run_id=str(run_id), attempt_id=str(evaluation['id']), split=evaluation['split'], checkpoint_sha256=sha256))
            try:
                subprocess.run([sys.executable, '-m', 'app.services.activation_trace_compute'], input=json.dumps(job, default=str), text=True,
                               check=True, timeout=TIMEOUT_SECONDS, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                raise HTTPException(502, 'No fue posible calcular el recorrido de esta célula.') from None
        finally:
            computing.release()
        return self._read(path)


def get_activation_trace_service(repository: Annotated[ActivationTraceRepository, Depends()],
                                 architecture: Annotated[ModelArchitectureRepository, Depends()]) -> ActivationTraceService:
    return ActivationTraceService(repository, architecture, get_settings().activation_trace_root)
