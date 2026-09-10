"""Opt-in integration: existing Compose PostgreSQL, all writes rolled back.

Does not touch a dataset, run, user, image or checkpoint. Uses synthetic audit
UUIDs. Run only through the project's Docker test environment with explicit
RUN_STAGE1_POSTGRES_TESTS=1; never creates another database or starts a service.
"""

from contextlib import contextmanager, nullcontext
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.malaria_dl.persistence import dataset_evidence as ev
from src.malaria_dl.persistence.database import get_engine

pytestmark = [
    pytest.mark.requires_docker_postgres,
    pytest.mark.skipif(
        os.environ.get("RUN_STAGE1_POSTGRES_TESTS") != "1",
        reason="Requires explicit opt-in inside the authorized Compose environment",
    ),
]


def sanitized_failure(exc, phase):
    """Never stringify a driver exception (it may contain SQL and parameters)."""
    original = getattr(exc, "orig", None) or exc
    state = getattr(original, "sqlstate", None)
    if not isinstance(state, str) or len(state) != 5 or not state.isalnum():
        state = None
    return {"phase": phase, "type": type(original).__name__, "sqlstate": state}


def test_evidence_round_trip_and_write_failure_rolled_back(monkeypatch):
    event_id = str(uuid4())
    engine = None
    failures = []
    diagnostics = []
    phase = "connection"
    payload = dict(
        consumer="stage1_isolated_integration",
        dataset_version_id=str(uuid4()),
        snapshot={"synthetic": True},
        verifier_version="fixture",
        integrity_status="verified",
    )
    expected = dict(after_state=payload, success=True, error_code=None)
    original_read = ev.read_dataset_evidence

    try:
        engine = get_engine()
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                class WriterConnection:
                    def execute(self, statement, params):
                        nonlocal phase
                        phase = "INSERT"
                        try:
                            return connection.execute(statement, params)
                        except Exception as exc:
                            diagnostics.append(sanitized_failure(exc, phase))
                            raise

                @contextmanager
                def nested():
                    nonlocal phase
                    phase = "savepoint_open"
                    try:
                        with connection.begin_nested():
                            yield WriterConnection()
                            phase = "savepoint_release"
                    except Exception as exc:
                        if phase != "INSERT":
                            diagnostics.append(sanitized_failure(exc, phase))
                        raise

                class ReadConnection:
                    def execute(self, statement, params):
                        nonlocal phase
                        phase = "read"
                        result = connection.execute(statement, params)
                        phase = "result_normalization"
                        return result

                def read(evidence_id):
                    nonlocal phase
                    phase = "read_or_normalization"
                    try:
                        stored = original_read(evidence_id)
                    except Exception as exc:
                        diagnostics.append(sanitized_failure(exc, phase))
                        raise
                    phase = "round_trip_comparison"
                    if stored != expected:
                        # Only this test's synthetic object is inspected; no values.
                        diagnostics.append({
                            "phase": phase,
                            "different_fields": [
                                key for key in expected if stored.get(key) != expected[key]
                            ],
                            "keys_equal": set(stored) == set(expected),
                        })
                    return stored

                proxy = SimpleNamespace(begin=nested, dispose=lambda: None)
                monkeypatch.setattr(ev, "get_engine", lambda: proxy)
                monkeypatch.setattr(
                    ev, "dataset_read_connection", lambda: nullcontext(ReadConnection())
                )
                monkeypatch.setattr(ev, "read_dataset_evidence", read)
                ev.persist_dataset_evidence(payload, success=True, evidence_id=event_id)
                assert ev.read_dataset_evidence(event_id) == expected
                phase = "correlation_identity"
                assert connection.execute(
                    text("SELECT correlation_id FROM audit_events WHERE id=CAST(:id AS uuid)"),
                    {"id": event_id},
                ).scalar_one() == event_id
                diagnostics.clear()
                with pytest.raises(ev.GovernedDatasetError, match="PERSISTENCE_FAILED"):
                    ev.persist_dataset_evidence(payload, success=True, evidence_id=event_id)
                assert diagnostics == [
                    {"phase": "INSERT", "type": "UniqueViolation", "sqlstate": "23505"}
                ]
                phase = "outer_transaction_after_duplicate"
                assert connection.execute(text("SELECT 1")).scalar_one() == 1
                assert connection.execute(
                    text("SELECT count(*) FROM audit_events WHERE id=CAST(:id AS uuid)"),
                    {"id": event_id},
                ).scalar_one() == 1
            except BaseException as exc:
                # Capture before cleanup; never let a rollback error replace it.
                failures.append(sanitized_failure(exc, phase))
            finally:
                try:
                    outer.rollback()
                except BaseException as exc:
                    failures.append(sanitized_failure(exc, "outer_rollback"))
    except BaseException as exc:
        failures.append(sanitized_failure(exc, phase))
    finally:
        if engine is not None:
            try:
                # Run even when INSERT, comparison or rollback itself failed.
                with engine.connect() as subsequent:
                    with subsequent.begin():
                        subsequent.execute(text("SET TRANSACTION READ ONLY"))
                        assert subsequent.execute(
                            text("SELECT count(*) FROM audit_events WHERE id=CAST(:id AS uuid)"),
                            {"id": event_id},
                        ).scalar_one() == 0
            except BaseException as exc:
                failures.append(sanitized_failure(exc, "absence_after_rollback"))
            finally:
                try:
                    engine.dispose()
                except BaseException as exc:
                    failures.append(sanitized_failure(exc, "dispose"))
    if failures:
        pytest.fail(f"Synthetic evidence failure: {failures}; diagnostics: {diagnostics}",
                    pytrace=False)
