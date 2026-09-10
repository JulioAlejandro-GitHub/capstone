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


def test_evidence_round_trip_and_write_failure_rolled_back(monkeypatch):
    engine = get_engine()
    event_id = str(uuid4())
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            try:

                @contextmanager
                def nested():
                    with connection.begin_nested():
                        yield connection

                # The writer may commit a SAVEPOINT, never the outer transaction.
                proxy = SimpleNamespace(begin=nested, dispose=lambda: None)
                monkeypatch.setattr(ev, "get_engine", lambda: proxy)
                monkeypatch.setattr(
                    ev, "dataset_read_connection", lambda: nullcontext(connection)
                )
                payload = dict(
                    consumer="stage1_isolated_integration",
                    dataset_version_id=str(uuid4()),
                    snapshot={"synthetic": True},
                    verifier_version="fixture",
                    integrity_status="verified",
                )
                ev.persist_dataset_evidence(payload, success=True, evidence_id=event_id)
                assert ev.read_dataset_evidence(event_id)["after_state"] == payload
                # Duplicate PK fails without any fallback; savepoint contains failure.
                with pytest.raises(ev.GovernedDatasetError, match="PERSISTENCE_FAILED"):
                    ev.persist_dataset_evidence(
                        payload, success=True, evidence_id=event_id
                    )
                assert (
                    connection.execute(
                        text("SELECT count(*) FROM audit_events WHERE id=:id"),
                        {"id": event_id},
                    ).scalar_one()
                    == 1
                )
            finally:
                outer.rollback()
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                assert (
                    connection.execute(
                        text("SELECT count(*) FROM audit_events WHERE id=:id"),
                        {"id": event_id},
                    ).scalar_one()
                    == 0
                )
    finally:
        engine.dispose()
