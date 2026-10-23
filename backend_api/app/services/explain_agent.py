"""Host GPU executor for EXPLAIN (and REPRESENT) requested from the report (launchd label cl.capstone.explain-agent).

Runs on macOS with `.venv-metal`: the same bootstrap as the local TRAIN launcher (PostgreSQL on loopback,
GPU required, accelerator canary), then claims `explain_requests` with SKIP LOCKED. Each request runs in a
short-lived child (`--job <id>`) that owns GlobalGate and exits, like the Docker worker: the gate records its
coordinator as the previous process, so a long-lived coordinator would block every later experiment.
It never talks HTTP and never decides a process died by time.
"""
import json
import signal
import socket
import subprocess
import sys
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

    def attach_child(self, request_id: str, child: dict) -> None:
        with self.engine.begin() as c:
            c.execute(text("""UPDATE explain_requests SET claimed_by=claimed_by || jsonb_build_object('child', CAST(:child AS jsonb))
                WHERE id=:id AND state='claimed'"""), dict(id=str(request_id), child=json.dumps(child)))

    def job(self, request_id: str) -> dict[str, Any] | None:
        with self.engine.begin() as c:
            row = c.execute(text("SELECT id, request, actor, state FROM explain_requests WHERE id=:id"),
                            dict(id=str(request_id))).mappings().one_or_none()
            return dict(row) if row else None

    def claimed_on(self, host: str) -> list[dict[str, Any]]:
        with self.engine.begin() as c:
            return [dict(row) for row in c.execute(text("""SELECT id, claimed_by FROM explain_requests
                WHERE state='claimed' AND claimed_by->>'host'=:host"""), dict(host=host)).mappings()]


def recover(queue: ExplainQueue, host: str, absent: Callable[[dict], bool]) -> int:
    """Close only requests whose claiming process on this host is proven absent."""
    closed = 0
    for row in queue.claimed_on(host):
        try:
            # Both the claiming agent and its job child (if recorded) must be proven absent.
            identities = [row['claimed_by'], *([row['claimed_by']['child']] if row['claimed_by'].get('child') else [])]
            gone = all(absent(identity) for identity in identities)
        except ValueError:
            continue  # REMOTE_PROCESS_ABSENCE_UNPROVEN: another boot or host; never guess.
        if gone:
            queue.finish(row['id'], 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')
            closed += 1
    return closed


def serve_one(queue: ExplainQueue, job: dict[str, Any], execute: Callable[..., None], safe_code: Callable[[BaseException], str]) -> str:
    """Execute one claimed request; the request row always ends completed or failed."""
    from app.schemas.explain_generation import ExplainRequest
    from app.schemas.representation_generation import RepresentRequest
    try:
        # REPRESENT rows share the queue; EXPLAIN requests forbid the extra 'operation' field.
        model = RepresentRequest if job['request'].get('operation') == 'represent' else ExplainRequest
        request = model.model_validate(job['request'])
        execute(request, job['actor'], lambda operations: queue.acknowledge(job['id'], operations))
    except InterruptedError:
        queue.finish(job['id'], 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')
        raise
    except Exception as exc:
        queue.finish(job['id'], 'failed', safe_code(exc))
        return 'failed'
    queue.finish(job['id'], 'completed')
    return 'completed'


def dispatch(queue: ExplainQueue, job: dict[str, Any], spawn: Callable[[str], Any], identity: Callable[[int], dict]) -> str:
    """Run one claimed request in a child process; the row is closed even if the child dies."""
    child = spawn(str(job['id']))
    try:
        queue.attach_child(job['id'], identity(child.pid))
        code = child.wait()
    except InterruptedError:
        child.terminate()
        try:
            child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        raise
    finally:
        current = queue.job(job['id'])
        if current and current['state'] == 'claimed':
            queue.finish(job['id'], 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')
    current = queue.job(job['id'])
    return current['state'] if current else ('completed' if code == 0 else 'failed')


def spawn_job(request_id: str) -> subprocess.Popen:
    # Own session, as GlobalGate expects for managed processes; environment (DATABASE_URL, flags) is inherited.
    return subprocess.Popen([sys.executable, '-m', 'app.services.explain_agent', '--job', request_id],
                            start_new_session=True)


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


def run_job(request_id: str) -> int:
    """Child: own GlobalGate for exactly one request, then exit."""
    from src.malaria_dl.execution.local_launch import bootstrap
    bootstrap()
    from src.malaria_dl.execution.storage_paths import PROJECT_ROOT
    from src.malaria_dl.persistence.database import get_engine
    from app.repositories.explain_queries import ExplainQueries
    from app.services.explain_codes import safe_code
    from app.services.explain_execution import run_batch
    from app.services.explain_generation import ExplainService
    from app.repositories.representation_queries import RepresentQueries
    from app.schemas.representation_generation import RepresentRequest
    from app.services.representation_generation import RepresentService, run_represent
    signal.signal(signal.SIGTERM, _stop)
    queue = ExplainQueue(get_engine())
    job = queue.job(request_id)
    if not job or job['state'] != 'claimed':
        return 0
    service = ExplainService(ExplainQueries())
    root = str(PROJECT_ROOT / 'artifacts/assessments')

    def execute(request: Any, actor: str, acknowledge: Callable[[list[dict]], None]) -> None:
        if isinstance(request, RepresentRequest):
            run_represent(request, RepresentService(RepresentQueries()), actor, acknowledge, root)
        else:
            run_batch(request, service, actor, acknowledge, root)
    result = serve_one(queue, job, execute, safe_code)
    return 0 if result == 'completed' else 1


def main() -> None:
    import os
    if len(sys.argv) == 3 and sys.argv[1] == '--job':
        sys.exit(run_job(sys.argv[2]))
    from src.malaria_dl.execution.local_launch import bootstrap
    bootstrap()  # .venv-metal, Python 3.12, DATABASE_URL on loopback, CAPSTONE_LOCAL_TRAIN=1 (GPU required)
    import tensorflow as tf
    from src.malaria_dl.execution.accelerator import configure
    from src.malaria_dl.execution.global_gate import process_absent, process_identity
    from src.malaria_dl.persistence.database import get_engine

    device = {**configure(tf, require_gpu=True), 'tensorflow': tf.__version__}
    host = socket.gethostname()
    process = process_identity(os.getpid())
    queue = ExplainQueue(get_engine())
    print(f'explain-agent: {host} · {", ".join(device["gpu_devices"])} · recovered {recover(queue, host, process_absent)}', flush=True)
    heartbeat = Heartbeat(queue, host, process, device)
    heartbeat.start()
    signal.signal(signal.SIGTERM, _stop)

    try:
        while True:
            job = queue.claim(process)
            if not job:
                time.sleep(POLL_SECONDS)
                continue
            print(f'explain-agent: {job["id"]} {dispatch(queue, job, spawn_job, process_identity)}', flush=True)
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
