from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import text

from src.malaria_dl.governance.services.training_release_eligibility_service import (
    ELIGIBILITY_ACTOR,
    ELIGIBLE_REASON,
    reconcile_training_release_eligibility,
)
from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.persistence.training_release import (
    NotTrainingRunError,
    ProductiveStage2ConflictError,
    TrainingReleaseConflictError,
    TrainingReleaseStatus,
    get_training_release_state,
    list_training_release_states,
    set_training_release_status,
)


pytestmark = pytest.mark.requires_docker_postgres

PRODUCTIVE_TRAIN = UUID("623ad00c-0b03-4cf0-8f2c-bb9496efb496")


def _distribution(connection):
    return dict(
        connection.execute(
            text(
                """
                SELECT release_status, count(*)
                FROM runs
                WHERE run_type = 'training'
                GROUP BY release_status
                """
            )
        ).all()
    )


def _runs_fingerprint(connection):
    return connection.execute(
        text(
            """
            SELECT md5(COALESCE(string_agg(row_hash, '' ORDER BY id), ''))
            FROM (
                SELECT id, md5(row_to_json(run)::text) AS row_hash
                FROM runs AS run
            ) AS rows
            """
        )
    ).scalar_one()


def test_training_release_contract_rolls_back_every_write():
    engine = get_engine()
    with engine.connect() as connection:
        outer_transaction = connection.begin()
        initial_fingerprint = _runs_fingerprint(connection)
        initial_distribution = _distribution(connection)
        initial_count = connection.execute(text("SELECT count(*) FROM runs")).scalar_one()
        try:
            productive = get_training_release_state(
                PRODUCTIVE_TRAIN, connection=connection
            )
            assert productive.release_status is TrainingReleaseStatus.PRODUCTIVE_STAGE2

            training_ids = tuple(
                connection.execute(
                    text("SELECT id FROM runs WHERE run_type='training' ORDER BY id")
                ).scalars()
            )
            states = list_training_release_states(training_ids, connection=connection)
            assert len(states) == 24
            assert initial_distribution == {
                "productive_stage2": 1,
                "available_to_publish": 23,
            }

            available_id = next(
                run_id
                for run_id in training_ids
                if states[run_id].release_status
                is TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
            )
            changed = set_training_release_status(
                available_id,
                TrainingReleaseStatus.NOT_AVAILABLE,
                expected_current_status=TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
                changed_by="training-release-postgres-test",
                reason="rollback-only contract validation",
                connection=connection,
            )
            assert changed.changed
            assert get_training_release_state(
                available_id, connection=connection
            ).release_status is TrainingReleaseStatus.NOT_AVAILABLE

            with pytest.raises(TrainingReleaseConflictError):
                set_training_release_status(
                    available_id,
                    TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
                    expected_current_status=TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
                    changed_by=None,
                    reason=None,
                    connection=connection,
                )

            before_idempotent = get_training_release_state(
                available_id, connection=connection
            )
            unchanged = set_training_release_status(
                available_id,
                TrainingReleaseStatus.NOT_AVAILABLE,
                changed_by="must-not-replace-actor",
                reason="must-not-replace-reason",
                connection=connection,
            )
            assert not unchanged.changed
            assert unchanged.state.release_updated_at == before_idempotent.release_updated_at
            assert unchanged.state.release_changed_by == before_idempotent.release_changed_by
            assert unchanged.state.release_reason == before_idempotent.release_reason

            nontraining_id = connection.execute(
                text("SELECT id FROM runs WHERE run_type<>'training' ORDER BY id LIMIT 1")
            ).scalar_one()
            with pytest.raises(NotTrainingRunError):
                get_training_release_state(nontraining_id, connection=connection)

            with pytest.raises(ProductiveStage2ConflictError):
                set_training_release_status(
                    available_id,
                    TrainingReleaseStatus.PRODUCTIVE_STAGE2,
                    changed_by="training-release-postgres-test",
                    reason="expected unique-index rejection",
                    connection=connection,
                )
            assert connection.in_transaction()
            assert outer_transaction.is_active
            assert _distribution(connection) == {
                "productive_stage2": 1,
                "available_to_publish": 22,
                "not_available": 1,
            }
            assert connection.execute(text("SELECT count(*) FROM runs")).scalar_one() == initial_count
        finally:
            if outer_transaction.is_active:
                outer_transaction.rollback()

    with engine.connect() as independent:
        assert independent.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "20260901_01"
        assert _distribution(independent) == initial_distribution
        assert _runs_fingerprint(independent) == initial_fingerprint
        assert independent.execute(text("SELECT count(*) FROM runs")).scalar_one() == initial_count


def test_training_release_eligibility_rolls_back_every_write():
    engine = get_engine()
    with engine.connect() as connection:
        outer_transaction = connection.begin()
        initial_fingerprint = _runs_fingerprint(connection)
        initial_distribution = _distribution(connection)
        initial_count = connection.execute(text("SELECT count(*) FROM runs")).scalar_one()
        initial_statuses = dict(
            connection.execute(text("SELECT id, status FROM runs")).all()
        )
        try:
            eligible_training_id = connection.execute(
                text(
                    """
                    SELECT training.id
                    FROM runs AS training
                    WHERE training.run_type = 'training'
                      AND training.status = 'completed'
                      AND training.release_status = 'available_to_publish'
                      AND EXISTS (
                          SELECT 1
                          FROM run_lineage AS lineage
                          JOIN runs AS evaluation
                            ON evaluation.id = lineage.child_run_id
                           AND evaluation.run_type = 'evaluation'
                           AND evaluation.status = 'completed'
                          WHERE lineage.parent_run_id = training.id
                            AND lineage.relationship_type = 'evaluates_checkpoint_from'
                      )
                    ORDER BY training.id
                    LIMIT 1
                    """
                )
            ).scalar_one()

            before_idempotent = get_training_release_state(
                eligible_training_id, connection=connection
            )
            idempotent = reconcile_training_release_eligibility(
                eligible_training_id, connection=connection
            )
            assert idempotent.eligible
            assert not idempotent.changed
            assert idempotent.final_state == before_idempotent

            with connection.begin_nested():
                set_training_release_status(
                    eligible_training_id,
                    TrainingReleaseStatus.NOT_AVAILABLE,
                    expected_current_status=TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
                    changed_by="training-release-eligibility-postgres-test",
                    reason="rollback-only transition validation",
                    connection=connection,
                )
                restored = reconcile_training_release_eligibility(
                    eligible_training_id, connection=connection
                )
                assert restored.changed
                assert restored.eligible
                assert restored.previous_status is TrainingReleaseStatus.NOT_AVAILABLE
                assert restored.final_state.release_status is TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
                assert restored.final_state.release_changed_by == ELIGIBILITY_ACTOR
                assert restored.final_state.release_reason == ELIGIBLE_REASON

            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        UPDATE runs
                        SET release_status = NULL,
                            release_updated_at = NULL,
                            release_changed_by = NULL,
                            release_reason = NULL
                        WHERE id = :training_run_id
                        """
                    ),
                    {"training_run_id": eligible_training_id},
                )
                initialized = reconcile_training_release_eligibility(
                    eligible_training_id, connection=connection
                )
                assert initialized.changed
                assert initialized.previous_status is None
                assert initialized.final_state.release_status is TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
                assert initialized.final_state.release_updated_at is not None
                assert initialized.final_state.release_changed_by == ELIGIBILITY_ACTOR
                assert initialized.final_state.release_reason == ELIGIBLE_REASON

            productive_before = get_training_release_state(
                PRODUCTIVE_TRAIN, connection=connection
            )
            protected = reconcile_training_release_eligibility(
                PRODUCTIVE_TRAIN, connection=connection
            )
            assert protected.productive_protected
            assert not protected.changed
            assert protected.target_status is TrainingReleaseStatus.PRODUCTIVE_STAGE2
            assert protected.final_state == productive_before

            assert connection.in_transaction()
            assert outer_transaction.is_active
            assert connection.execute(text("SELECT count(*) FROM runs")).scalar_one() == initial_count
            assert dict(connection.execute(text("SELECT id, status FROM runs")).all()) == initial_statuses
            assert _distribution(connection) == initial_distribution
        finally:
            if outer_transaction.is_active:
                outer_transaction.rollback()

    with engine.connect() as independent:
        assert independent.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "20260901_01"
        assert _distribution(independent) == {
            "productive_stage2": 1,
            "available_to_publish": 23,
        }
        assert _runs_fingerprint(independent) == initial_fingerprint
        assert independent.execute(text("SELECT count(*) FROM runs")).scalar_one() == initial_count
        assert dict(independent.execute(text("SELECT id, status FROM runs")).all()) == initial_statuses
