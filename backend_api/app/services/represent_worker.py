"""Docker CPU executor for REPRESENT: fixed executable, closed JSON input, durable reservation before calculation."""
import json
import os
import signal
import sys
from typing import Any, TextIO
from app.repositories.representation_generation import RepresentRepository
from app.schemas.representation_generation import RepresentRequest
from app.services.artifacts import MALARIA_PROJECT_ROOT
from app.services.explain_codes import safe_code
from app.services.representation_generation import RepresentService, run_represent


def stop(signum: int, frame: Any) -> None:
    raise InterruptedError('EXPLAIN_EXECUTOR_INTERRUPTED')


def execute(request: RepresentRequest, service: RepresentService, result: TextIO, actor: str) -> None:
    def acknowledge(response: list[dict]) -> None:
        result.write(json.dumps(response[0]) + '\n')
        result.flush()
        if sys.stdin.readline().strip() != 'START':
            raise InterruptedError('EXPLAIN_START_NOT_ACKNOWLEDGED')
    run_represent(request, service, actor, acknowledge, str(MALARIA_PROJECT_ROOT / 'artifacts/assessments'))


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    with os.fdopen(int(os.environ['CAPSTONE_EXPLAIN_RESULT_FD']), 'w') as result:
        try:
            envelope = json.loads(sys.stdin.readline())
            request = RepresentRequest.model_validate(envelope['request'])
            execute(request, RepresentService(RepresentRepository()), result, envelope['actor'])
        except BaseException as exc:
            try:
                result.write(json.dumps({'error': safe_code(exc)}) + '\n')
                result.flush()
            except BrokenPipeError:
                pass


if __name__ == '__main__':
    main()
