"""EXPLAIN batch execution shared by the Docker worker and the host GPU agent."""
from typing import Any, Callable
from app.schemas.explain_generation import ExplainRequest
from app.services.explain_generation import ExplainService
from src.malaria_dl.assessment.service import execute_reserved, reserve_execution
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.global_gate import GlobalGate
from app.services.explain_codes import safe_code


def run_batch(request: ExplainRequest, service: ExplainService, actor: str, acknowledge: Callable[[list[dict]], None],
              root: str, *, gate_factory: Callable[[str], Any] = GlobalGate,
              reserve: Callable[..., Any] = reserve_execution, run: Callable[..., Any] = execute_reserved) -> None:
    """Reserve every missing method durably, acknowledge the batch, then compute it sequentially."""
    repository = service.repository
    owned: list[tuple[dict, dict]] = []
    with gate_factory('assessment-explain-http') as gate:
        try:
            source = service.context(request)
            response = []
            prepared = []
            batch = {'request': request.model_dump(mode='json'), 'actor': actor}
            for method in dict.fromkeys(request.methods):
                try:
                    for previous in service.matching(request, source, method):
                        if previous['state'] == 'active':
                            repository.recover(previous['id'])
                    existing = service.reusable(request, source, method)
                    if existing:
                        response.append({'method': method, 'attempt_id': str(existing['id'])})
                        continue
                    value = service.prepare(request, source, method)
                    value['http_request'] = batch
                    prepared.append((method, value))
                    response.append({'method': method, 'state': 'pending'})
                except InterruptedError:
                    raise
                except Exception as exc:
                    response.append({'method': method, 'error': safe_code(exc)})
            batch['preparation_errors'] = {item['method']: item['error'] for item in response if item.get('error')}
            if not prepared and not any(item.get('attempt_id') for item in response):
                raise CampaignError(next(iter(batch['preparation_errors'].values()), 'EXPLAIN_PREPARATION_FAILED'))
            if prepared:
                method, value = prepared[0]
                value, attempt, created = reserve(repository, value, root)
                if created:
                    owned.append((value, attempt))
                next(item for item in response if item['method'] == method).update(attempt_id=str(attempt['id']), state='running')
                # The first attempt durably records the complete requested batch.
                for item in response:
                    item['operation_id'] = str(attempt['id'])
            gate.event('http_explain_reserved', actor=actor, sample_id=str(request.sample_id), operations=response)
            acknowledge(response)
            for index, (method, prepared_value) in enumerate(prepared):
                try:
                    gate.require_healthy()
                    if index:
                        value, attempt, created = reserve(repository, prepared_value, root)
                        if created:
                            owned.append((value, attempt))
                    else:
                        value, attempt = owned[0]
                    run(repository, value, attempt)
                except InterruptedError:
                    raise
                except Exception as exc:
                    gate.event('http_explain_failed', method=method, code=safe_code(exc))
                    # Clear this reservation before the next method, while retaining
                    # partial results and the durable full request in the first identity.
                    for _, active in owned:
                        if repository.attempt(active['id'])['state'] == 'active':
                            repository.finish(active['id'], active['owner'], 'failed', cause=safe_code(exc))
        finally:
            # Cleanup while the execution token is still owned.
            for _, attempt in owned:
                current = repository.attempt(attempt['id'])
                if current['state'] == 'active':
                    repository.finish(attempt['id'], attempt['owner'], 'interrupted', cause='EXPLAIN_EXECUTOR_INTERRUPTED')
