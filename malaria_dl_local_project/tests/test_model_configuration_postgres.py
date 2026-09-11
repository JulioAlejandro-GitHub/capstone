"""Compose-only E2 round-trip in a temporary runs table; outer rollback mandatory."""

import os
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import text
from src.malaria_dl.persistence import model_configuration as target
from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.models.configuration import resolve_config
from test_dataset_evidence_postgres import sanitized_failure

pytestmark = [
    pytest.mark.requires_docker_postgres,
    pytest.mark.skipif(
        os.environ.get("RUN_STAGE2_POSTGRES_TESTS") != "1",
        reason="Authorized Compose opt-in required",
    ),
]


def configuration_roundtrip_and_rollback(monkeypatch, model_name="custom_cnn"):
    engine = None
    errors = []
    run_id, dataset_id = str(uuid4()), str(uuid4())
    phase = "connection"
    try:
        engine = get_engine()
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                phase = "isolated_temp_table"
                # No public schema changes or operational rows. Session-local shadow.
                assert (
                    connection.execute(
                        text(
                            "SELECT count(*) FROM public.runs WHERE id=CAST(:id AS uuid)"
                        ),
                        {"id": run_id},
                    ).scalar_one()
                    == 0
                )
                connection.execute(
                    text(
                        "CREATE TEMP TABLE runs (id uuid PRIMARY KEY, run_type text, dataset_version_id uuid, execution_parameters jsonb) ON COMMIT DROP"
                    )
                )
                assert connection.execute(
                    text(
                        "SELECT pg_my_temp_schema() = (SELECT relnamespace FROM pg_class WHERE oid='runs'::regclass)"
                    )
                ).scalar_one()
                connection.execute(
                    text(
                        "INSERT INTO runs VALUES(CAST(:id AS uuid),'training',CAST(:dataset AS uuid),'{}'::jsonb)"
                    ),
                    dict(id=run_id, dataset=dataset_id),
                )

                @contextmanager
                def nested():
                    with connection.begin_nested():
                        yield connection

                monkeypatch.setattr(
                    target,
                    "get_engine",
                    lambda: SimpleNamespace(begin=nested, dispose=lambda: None),
                )
                monkeypatch.setattr(
                    target, "dataset_read_connection", lambda: nullcontext(connection)
                )
                monkeypatch.setattr(
                    target, "environment_identity", lambda: {"synthetic": True}
                )
                config = resolve_config(model_name)
                phase = "roundtrip"
                snapshot = target.persist_model_configuration(
                    run_id,
                    config,
                    {"base": {"synthetic": True}},
                    {"dataset_version_id": dataset_id},
                    {"synthetic": True},
                )
                stored = connection.execute(
                    text(
                        "SELECT execution_parameters->'model_configuration_e2' FROM runs WHERE id=CAST(:id AS uuid)"
                    ),
                    {"id": run_id},
                ).scalar_one()
                assert snapshot == stored
                phase = "failed_identity_write"
                with pytest.raises(target.ModelConfigurationPersistenceError):
                    target.persist_model_configuration(
                        run_id, config, {}, {"dataset_version_id": str(uuid4())}, {}
                    )
                assert connection.execute(text("SELECT 1")).scalar_one() == 1
                assert (
                    connection.execute(text("SELECT count(*) FROM runs")).scalar_one()
                    == 1
                )
            except BaseException as exc:
                errors.append(sanitized_failure(exc, phase))
            finally:
                try:
                    outer.rollback()
                except BaseException as exc:
                    errors.append(sanitized_failure(exc, "rollback"))
    except BaseException as exc:
        errors.append(sanitized_failure(exc, phase))
    finally:
        if engine is not None:
            try:
                with engine.connect() as subsequent:
                    with subsequent.begin():
                        subsequent.execute(text("SET TRANSACTION READ ONLY"))
                        assert (
                            subsequent.execute(
                                text(
                                    "SELECT count(*) FROM public.runs WHERE id=CAST(:id AS uuid)"
                                ),
                                {"id": run_id},
                            ).scalar_one()
                            == 0
                        )
                        assert (
                            subsequent.execute(
                                text(
                                    "SELECT count(*) FROM pg_class WHERE relnamespace=pg_my_temp_schema() AND relname='runs'"
                                )
                            ).scalar_one()
                            == 0
                        )
            except BaseException as exc:
                errors.append(sanitized_failure(exc, "absence_after_rollback"))
            finally:
                try:
                    engine.dispose()
                except BaseException as exc:
                    errors.append(sanitized_failure(exc, "dispose"))
    if errors:
        pytest.fail(f"Synthetic configuration failure: {errors}", pytrace=False)
    return snapshot


def test_configuration_roundtrip_and_rollback(monkeypatch):
    configuration_roundtrip_and_rollback(monkeypatch)
