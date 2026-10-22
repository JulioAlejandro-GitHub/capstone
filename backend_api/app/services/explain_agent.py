"""Host GPU executor for EXPLAIN requested from the report (launchd label cl.capstone.explain-agent).

Runs on macOS with `.venv-metal`: the same bootstrap as the local TRAIN launcher (PostgreSQL on loopback,
GPU required, accelerator canary), then claims `explain_requests` with SKIP LOCKED and executes them with
the batch logic shared with the Docker worker. It never talks HTTP and never decides a process died by time.
"""
import json
import signal
import socket
import threading
import time
from typing import Any, Callable

from sqlalchemy import text

EXECUTOR = 'host_gpu'
HEARTBEAT_SECONDS = 10
POLL_SECONDS = 2


class ExplainQueue:
    """Rows of explain_requests and executor_heartbeats; one short transaction per call."""

    def __init__(self, engine) -> None:
        self.engine = engine

    def beat(self, host: str, process: dict, device: dict) -> None:
        # Database time only: the host clock and the Docker VM clock may differ.
        with self.engine.begin() as c:
            c.execute(text("""INSERT INTO executor_heartbeats(executor,host,process,device,started_at)
                VALUES(:executor,:host,CAST(:process AS jsonb),CAST(:device AS jsonb),clock_timestamp())
                ON CONFLICT (executor,host) DO UPDATE SET process=EXCLUDED.process, device=EXCLUDED.device,
                  started_at=CASE WHEN executor_heartbeats.process IS DISTINCT FROM EXCLUDED.process
                                  THEN clock_timestamp() ELSE executor_heartbeats.started_at END,
                  last_seen=clock_timestamp()"""),
                dict(executor=EXECUTOR, host=host, process=json.dumps(process), device=json.dumps(device)))

    def retire(self, host: str) -> None:
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM executor_heartbeats WHERE executor=:executor AND host=:host"),
                      dict(executor=EXECUTOR, host=host))

    def claim(self, process: dict) -> dict[str, Any] | None:
        with self.engine.begin() as c:
            row = c.execute(text("""UPDATE explain_requests SET state='claimed', claimed_by=CAST(:who AS jsonb),
                  claimed_at=clock_timestamp()
                WHERE id=(SELECT id FROM explain_requests WHERE state='queued' AND executor=:executor
                          ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
                RETURNING id, request, actor"""), dict(who=json.dumps(process), executor=EXECUTOR)).mappings().one_or_none()
            return dict(row) if row else None

    def acknowledge(self, request_id: str, operations: list[dict]) -> None:
        with self.engine.begin() as c:
            c.execute(text("UPDATE explain_requests SET operations=CAST(:ops AS jsonb) WHERE id=:id AND state='claimed'"),
                      dict(id=str(request_id), ops=json.dumps(operations)))

    def finish(self, request_id: str, state: str, cause: str | None = None) -> None:
        with self.engine.begin() as c:
            c.execute(text("""UPDATE explain_requests SET state=:state, cause=:cause, finished_at=clock_timestamp()
                WHERE id=:id AND state='claimed'"""), dict(id=str(request_id), state=state, cause=cause))

    def claimed_on(self, host: str) -> list[dict[str, Any]]:
        with self.engine.begin() as c:
            return [dict(row) for row in c.execute(text("""SELECT id, claimed_by FROM explain_requests
                WHERE state='claimed' AND claimed_by->>'host'=:host"""), dict(host=host)).mappings()]


def recover(queue: ExplainQueue, host: str, absent: Callable[[dict], bool]) -> int:
    """Close only requests whose claiming process on this host is proven absent."""
    closed = 0
    for row in queue.claimed_on(host):
        try:
            gone = absent(row['claimed_by'])
        except ValueError:
            continue  # REMOTE_PROCESS_ABSENCE_UNPROVEN: another boot or host; never guess.
        if gone:
            queue.finish(row['id'], 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')
            closed += 1
    return closed


def serve_one(queue: ExplainQueue, job: dict[str, Any], execute: Callable[..., None], safe_code: Callable[[BaseException], str]) -> str:
    """Execute one claimed request; the request row always ends completed or failed."""
    from app.schemas.explain_generation import ExplainRequest
    try:
        request = ExplainRequest.model_validate(job['request'])
        execute(request, job['actor'], lambda operations: queue.acknowledge(job['id'], operations))
    except InterruptedError:
        queue.finish(job['id'], 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')
        raise
    except Exception as exc:
        queue.finish(job['id'], 'failed', safe_code(exc))
        return 'failed'
    queue.finish(job['id'], 'completed')
    return 'completed'


class Heartbeat(threading.Thread):
    def __init__(self, queue: ExplainQueue, host: str, process: dict, device: dict) -> None:
        super().__init__(name='explain-heartbeat', daemon=True)
        self.queue, self.host, self.process, self.device = queue, host, process, device
        self.stopped = threading.Event()

    def run(self) -> None:
        while not self.stopped.is_set():
            try:
                self.queue.beat(self.host, self.process, self.device)
            except Exception as exc:  # The database may restart; keep trying without crashing the agent.
                print(f'heartbeat: {type(exc).__name__}', flush=True)
            self.stopped.wait(HEARTBEAT_SECONDS)


def _stop(signum: int, frame: Any) -> None:
    raise InterruptedError('EXPLAIN_HOST_EXECUTOR_INTERRUPTED')


def main() -> None:
    import os
    from src.malaria_dl.execution.local_launch import bootstrap
    bootstrap()  # .venv-metal, Python 3.12, DATABASE_URL on loopback, CAPSTONE_LOCAL_TRAIN=1 (GPU required)
    import tensorflow as tf
    from src.malaria_dl.execution.accelerator import configure
    from src.malaria_dl.execution.global_gate import process_absent, process_identity
    from src.malaria_dl.execution.storage_paths import PROJECT_ROOT
    from src.malaria_dl.persistence.database import get_engine
    from app.repositories.explain_queries import ExplainQueries
    from app.services.explain_codes import safe_code
    from app.services.explain_execution import run_batch
    from app.services.explain_generation import ExplainService

    device = {**configure(tf, require_gpu=True), 'tensorflow': tf.__version__}
    host = socket.gethostname()
    process = process_identity(os.getpid())
    queue = ExplainQueue(get_engine())
    service = ExplainService(ExplainQueries())
    root = str(PROJECT_ROOT / 'artifacts/assessments')
    print(f'explain-agent: {host} · {", ".join(device["gpu_devices"])} · recovered {recover(queue, host, process_absent)}', flush=True)
    heartbeat = Heartbeat(queue, host, process, device)
    heartbeat.start()
    signal.signal(signal.SIGTERM, _stop)

    def execute(request, actor, acknowledge):
        run_batch(request, service, actor, acknowledge, root)

    try:
        while True:
            job = queue.claim(process)
            if not job:
                time.sleep(POLL_SECONDS)
                continue
            print(f'explain-agent: {job["id"]} {serve_one(queue, job, execute, safe_code)}', flush=True)
    except (InterruptedError, KeyboardInterrupt):
        pass
    finally:
        heartbeat.stopped.set()
        try:
            queue.retire(host)
        except Exception:
            pass


if __name__ == '__main__':
    main()
