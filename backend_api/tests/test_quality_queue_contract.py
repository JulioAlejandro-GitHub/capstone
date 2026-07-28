import pytest
from pydantic import ValidationError

from app.schemas.analysis import QualityQueueCreate, QualityQueueRetry
from app.security import Permission, ROLE_PERMISSIONS


RUN_ID = "00000000-0000-4000-8000-000000000001"


@pytest.mark.parametrize("priority", [1, 50, 100])
def test_queue_accepts_only_documented_priorities(priority):
    assert QualityQueueCreate(analysis_run_id=RUN_ID, priority=priority).priority == priority


def test_queue_defaults_to_normal_priority():
    assert QualityQueueCreate(analysis_run_id=RUN_ID).priority == 50


@pytest.mark.parametrize("priority", [0, 2, 49, 51, 99, 101])
def test_queue_rejects_intermediate_priorities(priority):
    with pytest.raises(ValidationError):
        QualityQueueCreate(analysis_run_id=RUN_ID, priority=priority)


def test_retry_defaults_to_normal_priority_and_validates_values():
    assert QualityQueueRetry().priority == 50
    with pytest.raises(ValidationError):
        QualityQueueRetry(priority=75)


def test_queue_rbac_matches_role_policy():
    read = Permission.SCIENTIFIC_ANALYSIS_QUEUE_READ
    mutations = {
        Permission.SCIENTIFIC_ANALYSIS_QUEUE_CREATE,
        Permission.SCIENTIFIC_ANALYSIS_QUEUE_EXECUTE,
        Permission.SCIENTIFIC_ANALYSIS_QUEUE_RETRY,
    }
    for role in ("administrator", "researcher", "operator"):
        assert {read, *mutations} <= ROLE_PERMISSIONS[role]
    for role in ("reviewer", "read_only"):
        assert read in ROLE_PERMISSIONS[role]
        assert ROLE_PERMISSIONS[role].isdisjoint(mutations)


def test_queue_migration_has_priority_fifo_and_active_uniqueness():
    source = open("alembic/versions/20260727_04_quality_assessment_queue.py", encoding="utf-8").read()
    assert "priority IN (1, 50, 100)" in source
    assert "attempt_count >= 0" in source
    assert "WHERE status IN ('queued', 'running')" in source
    assert "priority DESC, requested_at ASC" in source


def test_queue_service_contains_no_automatic_processing_primitives():
    source = open("backend_api/app/services/quality_queue.py", encoding="utf-8").read().lower()
    for forbidden in ("celery", "redis", "rabbitmq", "scheduler", "backoff", "websocket"):
        assert forbidden not in source


def test_manual_retry_clears_previous_error_without_executing():
    source = open("backend_api/app/services/quality_queue.py", encoding="utf-8").read()
    retry_body = source.split("def retry(", 1)[1]
    assert "status='queued'" in retry_body
    assert "last_error_code=NULL" in retry_body
    assert "last_error_message=NULL" in retry_body
    assert "self.execute(" not in retry_body
