"""Persist the release status of training runs.

Revision ID: 20260829_01
Revises: 20260812_02
"""

import sqlalchemy as sa
from alembic import op


revision = "20260829_01"
down_revision = "20260812_02"
branch_labels = None
depends_on = None


ACTIVE_PUBLICATION_COUNT_SQL = sa.text(
    """
    SELECT count(*)
    FROM stage2_model_publications
    WHERE datasource = 'malaria'
      AND scope = 'stage2'
      AND status = 'active'
      AND is_active = true
    """
)

ACTIVE_DEPLOYMENT_COUNT_SQL = sa.text(
    """
    SELECT count(*)
    FROM deployed_model_versions
    WHERE environment = 'stage2'
      AND alias = 'default'
      AND status = 'active'
    """
)

CONSISTENT_SELECTION_COUNT_SQL = sa.text(
    """
    SELECT count(*)
    FROM stage2_model_publications AS publication
    JOIN deployed_model_versions AS deployment
      ON deployment.model_version_id = publication.model_version_id
     AND deployment.checkpoint_artifact_id = publication.checkpoint_artifact_id
     AND deployment.environment = 'stage2'
     AND deployment.alias = 'default'
     AND deployment.status = 'active'
     AND deployment.metadata->>'production_scope' = 'stage2_experimental'
    JOIN model_versions AS model_version
      ON model_version.id = publication.model_version_id
     AND model_version.training_run_id = publication.training_run_id
     AND model_version.checkpoint_artifact_id = publication.checkpoint_artifact_id
    JOIN artifacts AS checkpoint
      ON checkpoint.id = publication.checkpoint_artifact_id
     AND checkpoint.run_id = publication.training_run_id
    JOIN runs AS training
      ON training.id = publication.training_run_id
     AND training.run_type = 'training'
     AND training.status = 'completed'
    JOIN runs AS evaluation
      ON evaluation.id = publication.evaluation_run_id
     AND evaluation.run_type = 'evaluation'
     AND evaluation.status = 'completed'
    JOIN run_lineage AS lineage
      ON lineage.parent_run_id = publication.training_run_id
     AND lineage.child_run_id = publication.evaluation_run_id
     AND lineage.relationship_type = 'evaluates_checkpoint_from'
     AND lineage.model_version_id = publication.model_version_id
     AND lineage.checkpoint_artifact_id = publication.checkpoint_artifact_id
    WHERE publication.datasource = 'malaria'
      AND publication.scope = 'stage2'
      AND publication.status = 'active'
      AND publication.is_active = true
    """
)


def _validate_productive_selection(bind):
    publication_count = bind.execute(ACTIVE_PUBLICATION_COUNT_SQL).scalar_one()
    deployment_count = bind.execute(ACTIVE_DEPLOYMENT_COUNT_SQL).scalar_one()

    if publication_count > 1:
        raise RuntimeError(
            "Release backfill aborted: multiple active malaria/stage2 publications"
        )
    if deployment_count > 1:
        raise RuntimeError(
            "Release backfill aborted: multiple active stage2/default deployments"
        )

    # A database without an active publication has no initial productive TRAIN.
    if publication_count == 0:
        return

    consistent_count = bind.execute(CONSISTENT_SELECTION_COUNT_SQL).scalar_one()
    if consistent_count != 1:
        raise RuntimeError(
            "Release backfill aborted: active Stage 2 selection is incomplete, "
            "ambiguous, or inconsistent"
        )


def upgrade():
    op.add_column("runs", sa.Column("release_status", sa.Text(), nullable=True))
    op.add_column(
        "runs", sa.Column("release_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("runs", sa.Column("release_changed_by", sa.Text(), nullable=True))
    op.add_column("runs", sa.Column("release_reason", sa.Text(), nullable=True))

    bind = op.get_bind()
    _validate_productive_selection(bind)

    op.execute(
        """
        WITH productive_selection AS (
            SELECT
                publication.training_run_id,
                COALESCE(publication.updated_at, publication.published_at) AS changed_at,
                publication.published_by AS changed_by
            FROM stage2_model_publications AS publication
            JOIN deployed_model_versions AS deployment
              ON deployment.model_version_id = publication.model_version_id
             AND deployment.checkpoint_artifact_id = publication.checkpoint_artifact_id
             AND deployment.environment = 'stage2'
             AND deployment.alias = 'default'
             AND deployment.status = 'active'
             AND deployment.metadata->>'production_scope' = 'stage2_experimental'
            JOIN model_versions AS model_version
              ON model_version.id = publication.model_version_id
             AND model_version.training_run_id = publication.training_run_id
             AND model_version.checkpoint_artifact_id = publication.checkpoint_artifact_id
            JOIN artifacts AS checkpoint
              ON checkpoint.id = publication.checkpoint_artifact_id
             AND checkpoint.run_id = publication.training_run_id
            JOIN runs AS selected_training
              ON selected_training.id = publication.training_run_id
             AND selected_training.run_type = 'training'
             AND selected_training.status = 'completed'
            JOIN runs AS selected_evaluation
              ON selected_evaluation.id = publication.evaluation_run_id
             AND selected_evaluation.run_type = 'evaluation'
             AND selected_evaluation.status = 'completed'
            JOIN run_lineage AS selected_lineage
              ON selected_lineage.parent_run_id = publication.training_run_id
             AND selected_lineage.child_run_id = publication.evaluation_run_id
             AND selected_lineage.relationship_type = 'evaluates_checkpoint_from'
             AND selected_lineage.model_version_id = publication.model_version_id
             AND selected_lineage.checkpoint_artifact_id = publication.checkpoint_artifact_id
            WHERE publication.datasource = 'malaria'
              AND publication.scope = 'stage2'
              AND publication.status = 'active'
              AND publication.is_active = true
        ), classified AS (
            SELECT
                training.id AS training_run_id,
                productive.changed_at,
                productive.changed_by,
                CASE
                    WHEN productive.training_run_id IS NOT NULL
                        THEN 'productive_stage2'
                    WHEN training.status = 'completed'
                     AND EXISTS (
                        SELECT 1
                        FROM run_lineage AS eligibility_lineage
                        JOIN runs AS evaluation
                          ON evaluation.id = eligibility_lineage.child_run_id
                         AND evaluation.run_type = 'evaluation'
                         AND evaluation.status = 'completed'
                        WHERE eligibility_lineage.parent_run_id = training.id
                          AND eligibility_lineage.relationship_type =
                              'evaluates_checkpoint_from'
                     ) THEN 'available_to_publish'
                    ELSE 'not_available'
                END AS release_status
            FROM runs AS training
            LEFT JOIN productive_selection AS productive
              ON productive.training_run_id = training.id
            WHERE training.run_type = 'training'
        )
        UPDATE runs AS training
        SET release_status = classified.release_status,
            release_updated_at = COALESCE(classified.changed_at, CURRENT_TIMESTAMP),
            release_changed_by = classified.changed_by,
            release_reason = CASE
                WHEN classified.release_status = 'productive_stage2'
                    THEN 'Initial backfill from the active Stage 2 publication'
                ELSE 'Initial backfill from TRAIN/EVALUATE eligibility'
            END
        FROM classified
        WHERE training.id = classified.training_run_id
          AND training.run_type = 'training'
        """
    )

    op.create_check_constraint(
        "ck_runs_release_status_training_vocabulary",
        "runs",
        """
        release_status IS NULL
        OR (
            run_type = 'training'
            AND release_status IN (
                'not_available',
                'available_to_publish',
                'productive_stage2'
            )
        )
        """,
    )
    op.create_check_constraint(
        "ck_runs_release_status_requires_timestamp",
        "runs",
        "release_status IS NULL OR release_updated_at IS NOT NULL",
    )
    op.create_index(
        "idx_runs_training_release_status",
        "runs",
        ["release_status"],
        unique=False,
        postgresql_where=sa.text("run_type = 'training'"),
    )
    op.create_index(
        "uq_runs_single_productive_stage2",
        "runs",
        ["release_status"],
        unique=True,
        postgresql_where=sa.text(
            "run_type = 'training' AND release_status = 'productive_stage2'"
        ),
    )


def downgrade():
    raise RuntimeError(
        "Downgrade is intentionally prohibited because persisted release states "
        "must not be discarded"
    )
