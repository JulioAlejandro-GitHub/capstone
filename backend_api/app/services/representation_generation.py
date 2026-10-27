"""Application REPRESENT operations shared by HTTP and its isolated executors (Docker worker, host GPU agent)."""
import hashlib
import json
import re
from typing import Any, Callable
from app.schemas.representation_generation import RepresentRequest
from app.services.explain_codes import safe_code
from app.services.explain_generation import owner_absent, scientific_context
from app.services.explain_host import executor_status
from src.malaria_dl.assessment.contracts import require
from src.malaria_dl.assessment.representation import representation_spec
from src.malaria_dl.assessment.service import execute_reserved, prepare, reserve_execution, verify
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.global_gate import GlobalGate


class RepresentService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def context(self, request: RepresentRequest) -> dict[str, Any]:
        source = self.repository.source(str(request.source_attempt_id))
        require(source is not None, 'REPRESENT_SOURCE_NOT_FOUND')
        # The population, split, protocol and threshold come from one verified EVALUATE (VAL or TEST).
        require(source['state'] == 'verified' and source['identity'].get('kind') == 'evaluate', 'REPRESENT_SOURCE_NOT_EVALUATE')
        return source['identity']

    @staticmethod
    def compatible(row: dict[str, Any], source: dict[str, Any]) -> bool:
        identity = row['identity']
        return (scientific_context(identity) == scientific_context(source) and identity['samples'] == source['samples']
                and identity.get('representation') == representation_spec())

    def matching(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        return [row for row in self.repository.represent_candidates(source['model']['training_run_id'])
                if self.compatible(row, source)]

    def reusable(self, source: dict[str, Any]) -> dict[str, Any] | None:
        for row in self.matching(source):
            if row['state'] == 'active' and not owner_absent(row):
                return row
            if row['state'] == 'verified':
                try:
                    verify(self.repository, row, row['identity'])
                except (ValueError, OSError):
                    continue
                return row
        return None

    def prepare(self, source: dict[str, Any]) -> dict[str, Any]:
        value = prepare(self.repository, training_run_id=source['model']['training_run_id'],
                        dataset_version_id=source['dataset']['dataset_version_id'],
                        split=source['split'], purpose=source['purpose'], protocol=source['protocol'],
                        requested_threshold=source['decision']['requested'], seed=source['seed'],
                        batch_size=source['batch_size'], representation=representation_spec())
        require(scientific_context(value) == scientific_context(source) and value['samples'] == source['samples'],
                'REPRESENT_SOURCE_CONTEXT_CHANGED')
        return value

    def submit(self, request: RepresentRequest, launcher: Any, actor: str) -> dict[str, Any]:
        existing = self.reusable(self.context(request))
        if existing:
            return {'state': 'completed' if existing['state'] == 'verified' else 'running', 'attempt_id': str(existing['id'])}
        return launcher.launch(request, actor)

    def state(self, request: RepresentRequest, authorized: bool) -> dict[str, Any]:
        """Cheap status for polling: never hashes the checkpoint (reuse and the report read verify)."""
        source = self.context(request)
        result: dict[str, Any] = {'source_attempt_id': str(request.source_attempt_id), 'authorized': authorized,
                                  'training_run_id': source['model']['training_run_id'], 'state': 'not_executed'}
        rows = self.matching(source)
        row = next((item for item in rows if item['state'] in ('verified', 'active')), None) or next(iter(rows), None)
        if row:
            result['attempt_id'] = str(row['id'])
            if row['state'] == 'verified':
                return {**result, 'state': 'completed'}
            if row['state'] == 'active':
                return {**result, 'state': 'failed', 'error': 'ASSESSMENT_OWNER_PROCESS_ABSENT'} if owner_absent(row) \
                    else {**result, 'state': 'running'}
            cause = row.get('cause')
            result.update(state='failed', error=cause if isinstance(cause, str) and re.fullmatch('[A-Z][A-Z0-9_]+', cause) else 'ASSESSMENT_EXECUTION_FAILED')
        latest = next(iter(self.repository.represent_requests(str(request.source_attempt_id))), None)
        if latest and latest['state'] in ('queued', 'claimed'):
            result.update(state='pending', operation_id=str(latest['id']), error=None)
        elif latest and latest['state'] == 'failed' and result['state'] == 'not_executed':
            cause = latest.get('cause')
            result.update(state='failed', operation_id=str(latest['id']),
                          error=cause if isinstance(cause, str) and re.fullmatch('[A-Z][A-Z0-9_]+', cause) else 'EXPLAIN_HOST_EXECUTION_FAILED')
        return result


def run_represent(request: RepresentRequest, service: RepresentService, actor: str, acknowledge: Callable[[list[dict]], None],
                  root: str, *, gate_factory: Callable[[str], Any] = GlobalGate,
                  reserve: Callable[..., Any] = reserve_execution, run: Callable[..., Any] = execute_reserved) -> None:
    """Reserve durably, acknowledge, then compute; same gate and fencing as EXPLAIN batches."""
    repository = service.repository
    owned = None
    with gate_factory('assessment-represent-http') as gate:
        try:
            source = service.context(request)
            for previous in service.matching(source):
                if previous['state'] == 'active':
                    repository.recover(previous['id'])
            existing = service.reusable(source)
            if existing:
                acknowledge([{'state': 'completed' if existing['state'] == 'verified' else 'running', 'attempt_id': str(existing['id'])}])
                return
            value = service.prepare(source)
            value['http_request'] = {'request': request.model_dump(mode='json'), 'actor': actor}
            value, attempt, created = reserve(repository, value, root)
            if created:
                owned = attempt
            gate.event('http_represent_reserved', actor=actor, attempt_id=str(attempt['id']))
            acknowledge([{'state': 'running', 'attempt_id': str(attempt['id'])}])
            if created:
                gate.require_healthy()
                try:
                    run(repository, value, attempt)
                except InterruptedError:
                    raise
                except Exception as exc:
                    # execute_reserved already closed the attempt as failed; keep the sanitized cause in the gate log.
                    gate.event('http_represent_failed', code=safe_code(exc))
                    raise
        finally:
            if owned is not None and repository.attempt(owned['id'])['state'] == 'active':
                repository.finish(owned['id'], owned['owner'], 'interrupted', cause='REPRESENT_EXECUTOR_INTERRUPTED')


def request_key(request: RepresentRequest) -> str:
    return hashlib.sha256(json.dumps(request.model_dump(mode='json'), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class RepresentHostLauncher:
    """Queues REPRESENT for the host GPU agent, in the same queue as EXPLAIN."""

    def __init__(self, queue: Any) -> None:
        self.queue = queue

    def launch(self, request: RepresentRequest, actor: str) -> dict[str, Any]:
        if not executor_status(self.queue)['available']:
            raise CampaignError('EXPLAIN_HOST_EXECUTOR_UNAVAILABLE')
        return {'state': 'pending', 'operation_id': self.queue.enqueue(request.model_dump(mode='json'), request_key(request), actor)}
