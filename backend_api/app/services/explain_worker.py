"""Fixed executable, closed JSON input, durable reservations before calculation."""
import json
import os
import re
import signal
import sys
from typing import Any, TextIO
from app.repositories.explain_generation import ExplainRepository
from app.schemas.explain_generation import ExplainRequest
from app.services.explain_generation import ExplainService
from app.services.artifacts import MALARIA_PROJECT_ROOT
from src.malaria_dl.assessment.service import reserve_execution, execute_reserved
from src.malaria_dl.execution.global_gate import GlobalGate
from src.malaria_dl.campaigns.contracts import CampaignError


def safe_code(exc: BaseException) -> str:
    code = str(exc)
    return code if isinstance(exc, CampaignError) and re.fullmatch('[A-Z][A-Z0-9_]+', code) else 'EXPLAIN_EXECUTOR_FAILED'


def stop(signum: int, frame: Any) -> None:
    raise InterruptedError('EXPLAIN_EXECUTOR_INTERRUPTED')


def execute(request: ExplainRequest, service: ExplainService, result: TextIO, actor: str) -> None:
    repository = service.repository
    owned: list[tuple[dict, dict]] = []
    with GlobalGate('assessment-explain-http') as gate:
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
            root = str(MALARIA_PROJECT_ROOT / 'artifacts/assessments')
            if prepared:
                method, value = prepared[0]
                value, attempt, created = reserve_execution(repository, value, root)
                if created:
                    owned.append((value, attempt))
                next(item for item in response if item['method'] == method).update(attempt_id=str(attempt['id']), state='running')
                # The first attempt durably records the complete requested batch.
                for item in response:
                    item['operation_id'] = str(attempt['id'])
            gate.event('http_explain_reserved', actor=actor, sample_id=str(request.sample_id), operations=response)
            result.write(json.dumps({'operations': response}) + '\n')
            result.flush()
            if sys.stdin.readline().strip() != 'START':
                raise InterruptedError('EXPLAIN_START_NOT_ACKNOWLEDGED')
            for index, (method, prepared_value) in enumerate(prepared):
                try:
                    gate.require_healthy()
                    if index:
                        value, attempt, created = reserve_execution(repository, prepared_value, root)
                        if created:
                            owned.append((value, attempt))
                    else:
                        value, attempt = owned[0]
                    execute_reserved(repository, value, attempt)
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


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    with os.fdopen(int(os.environ['CAPSTONE_EXPLAIN_RESULT_FD']), 'w') as result:
        try:
            envelope = json.loads(sys.stdin.readline())
            request = ExplainRequest.model_validate(envelope['request'])
            execute(request, ExplainService(ExplainRepository()), result, envelope['actor'])
        except BaseException as exc:
            try:
                result.write(json.dumps({'error': safe_code(exc)}) + '\n')
                result.flush()
            except BrokenPipeError:
                pass


if __name__ == '__main__':
    main()
