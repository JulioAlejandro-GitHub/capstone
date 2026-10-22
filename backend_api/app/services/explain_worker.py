"""Fixed executable, closed JSON input, durable reservations before calculation."""
import json
import os
import signal
import sys
from typing import Any, TextIO
from app.repositories.explain_generation import ExplainRepository
from app.schemas.explain_generation import ExplainRequest
from app.services.explain_generation import ExplainService
from app.services.artifacts import MALARIA_PROJECT_ROOT
from src.malaria_dl.assessment.service import reserve_execution, execute_reserved
from src.malaria_dl.execution.global_gate import GlobalGate
from app.services.explain_codes import safe_code
from app.services.explain_execution import run_batch


def stop(signum: int, frame: Any) -> None:
    raise InterruptedError('EXPLAIN_EXECUTOR_INTERRUPTED')


def execute(request: ExplainRequest, service: ExplainService, result: TextIO, actor: str) -> None:
    def acknowledge(response: list[dict]) -> None:
        result.write(json.dumps({'operations': response}) + '\n')
        result.flush()
        if sys.stdin.readline().strip() != 'START':
            raise InterruptedError('EXPLAIN_START_NOT_ACKNOWLEDGED')
    # Module globals are passed at call time so tests can replace them on this module.
    run_batch(request, service, actor, acknowledge, str(MALARIA_PROJECT_ROOT / 'artifacts/assessments'),
              gate_factory=GlobalGate, reserve=reserve_execution, run=execute_reserved)


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
