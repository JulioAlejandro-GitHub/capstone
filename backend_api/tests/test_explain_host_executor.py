"""Host GPU queue: blocking without heartbeat, idempotent keys and agent bookkeeping."""
from uuid import uuid4

import pytest
from app.schemas.explain_generation import ExplainRequest
from app.services import explain_agent
from app.services.explain_host import HostQueueLauncher, executor_status, request_key
from src.malaria_dl.campaigns.contracts import CampaignError


class Queue:
    def __init__(self, age=None):
        self.age, self.enqueued = age, []

    def heartbeat(self):
        return None if self.age is None else {'host': 'mac', 'age_seconds': self.age, 'last_seen': 'now',
                                              'device': {'gpu_devices': ['/physical_device:GPU:0']}}

    def enqueue(self, request, key, actor):
        self.enqueued.append((request, key, actor))
        return 'operation'


def request(methods=('lime', 'shap')):
    return ExplainRequest(source_attempt_id=uuid4(), sample_id=uuid4(), methods=list(methods))


@pytest.mark.parametrize('age', [None, 31.0])
def test_without_recent_heartbeat_generation_is_blocked(age):
    queue = Queue(age)
    with pytest.raises(CampaignError, match='EXPLAIN_HOST_EXECUTOR_UNAVAILABLE'):
        HostQueueLauncher(queue).launch(request(), 'actor')
    assert queue.enqueued == []
    assert executor_status(queue)['available'] is False


def test_recent_heartbeat_queues_once_per_method_set():
    queue = Queue(4.0)
    first = request(('shap', 'lime'))
    result = HostQueueLauncher(queue).launch(first, 'actor')
    assert [op['method'] for op in result['operations']] == ['shap', 'lime']
    assert all(op['state'] == 'pending' and op['operation_id'] == 'operation' for op in result['operations'])
    same = first.model_copy(update={'methods': ['lime', 'shap', 'lime']})
    assert request_key(same) == request_key(first)
    assert request_key(first.model_copy(update={'class_id': 0})) != request_key(first)
    assert executor_status(queue)['gpu_devices'] == ['/physical_device:GPU:0']


class AgentQueue:
    def __init__(self, claimed=(), state='claimed'):
        self.finished, self.acknowledged, self.claimed = [], [], list(claimed)
        self.state, self.children = state, []

    def attach_child(self, request_id, child):
        self.children.append((request_id, child))

    def job(self, request_id):
        return {'id': request_id, 'state': self.finished[-1][1] if self.finished else self.state}

    def acknowledge(self, request_id, operations):
        self.acknowledged.append((request_id, operations))

    def finish(self, request_id, state, cause=None):
        self.finished.append((request_id, state, cause))

    def claimed_on(self, host):
        return self.claimed


def test_serve_one_always_closes_the_request():
    queue = AgentQueue()
    job = {'id': 'job', 'actor': 'actor', 'request': request().model_dump(mode='json')}
    def ok(req, actor, acknowledge):
        acknowledge([{'method': 'lime', 'state': 'running'}])
    assert explain_agent.serve_one(queue, job, ok, lambda exc: 'X') == 'completed'
    assert queue.acknowledged == [('job', [{'method': 'lime', 'state': 'running'}])]
    def broken(req, actor, acknowledge):
        raise CampaignError('LOCAL_GPU_REQUIRED')
    assert explain_agent.serve_one(queue, job, broken, lambda exc: str(exc)) == 'failed'
    assert queue.finished == [('job', 'completed', None), ('job', 'failed', 'LOCAL_GPU_REQUIRED')]
    def stopped(req, actor, acknowledge):
        raise InterruptedError()
    with pytest.raises(InterruptedError):
        explain_agent.serve_one(queue, job, stopped, str)
    assert queue.finished[-1] == ('job', 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')


def test_recovery_closes_only_proven_absent_processes():
    alive, gone, foreign = ({'pid': 1}, {'pid': 2}, {'pid': 3})
    child_alive = {'pid': 2, 'child': {'pid': 1}}
    queue = AgentQueue([{'id': 'a', 'claimed_by': alive}, {'id': 'b', 'claimed_by': gone},
                        {'id': 'c', 'claimed_by': foreign}, {'id': 'd', 'claimed_by': child_alive}])
    def absent(identity):
        if identity is foreign:
            raise CampaignError('REMOTE_PROCESS_ABSENCE_UNPROVEN')
        return identity['pid'] == 2
    assert explain_agent.recover(queue, 'mac', absent) == 1
    assert queue.finished == [('b', 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')]


class Child:
    def __init__(self, code, queue=None, finish=None):
        self.pid, self.code, self.queue, self.finish, self.terminated = 99, code, queue, finish, False

    def wait(self, timeout=None):
        if self.finish:
            self.queue.finish('job', *self.finish)
        return self.code

    def terminate(self):
        self.terminated = True


def test_each_request_runs_in_its_own_child_so_the_gate_never_sees_a_live_coordinator():
    queue = AgentQueue()
    spawned = []
    def spawn(request_id):
        spawned.append(request_id)
        return Child(0, queue, ('completed',))
    for _ in range(2):
        assert explain_agent.dispatch(queue, {'id': 'job'}, spawn, lambda pid: {'pid': pid}) == 'completed'
    assert spawned == ['job', 'job'] and queue.children == [('job', {'pid': 99})] * 2


def test_a_child_that_dies_without_closing_its_request_is_failed():
    queue = AgentQueue()
    assert explain_agent.dispatch(queue, {'id': 'job'}, lambda _: Child(-9), lambda pid: {'pid': pid}) == 'failed'
    assert queue.finished == [('job', 'failed', 'EXPLAIN_HOST_EXECUTOR_INTERRUPTED')]


@pytest.mark.requires_docker_postgres
def test_real_queue_is_idempotent_and_heartbeat_marks_availability():
    from sqlalchemy import text
    from app.db import get_primary_engine
    from app.repositories.explain_queue import ExplainQueueRepository
    repository, agent = ExplainQueueRepository(), explain_agent.ExplainQueue(get_primary_engine())
    payload = request().model_dump(mode='json')
    key = request_key(ExplainRequest.model_validate(payload))
    first = repository.enqueue(payload, key, 'pytest')
    try:
        assert repository.enqueue(payload, key, 'pytest') == first
        agent.beat('pytest-host', {'pid': 1}, {'gpu_devices': ['GPU:0']})
        assert executor_status(repository)['available'] is True
    finally:
        agent.retire('pytest-host')
        with get_primary_engine().begin() as c:
            c.execute(text("UPDATE explain_requests SET state='cancelled', finished_at=clock_timestamp() WHERE id=:id"), {'id': first})
