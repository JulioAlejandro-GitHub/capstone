"""Guarantee at most one direct TRAIN parent for each EVALUATE.

Revision ID: 20260901_01
Revises: 20260829_01
"""

import sqlalchemy as sa
from alembic import op


revision = "20260901_01"
down_revision = "20260829_01"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_run_lineage_single_evaluation_training_parent"
RELATIONSHIP_TYPE = "evaluates_checkpoint_from"


_DUPLICATE_CHILDREN = sa.text(
    """
    SELECT child_run_id::text AS evaluation_run_id, COUNT(*) AS parent_count
    FROM run_lineage
    WHERE relationship_type = 'evaluates_checkpoint_from'
    GROUP BY child_run_id
    HAVING COUNT(*) > 1
    ORDER BY child_run_id
    """
)


def upgrade():
    duplicates = op.get_bind().execute(_DUPLICATE_CHILDREN).mappings().all()
    if duplicates:
        details = ", ".join(
            f"{row['evaluation_run_id']} ({row['parent_count']} parents)"
            for row in duplicates
        )
        raise RuntimeError(
            "Cannot enforce one TRAIN parent per EVALUATE; duplicate direct "
            f"lineages exist: {details}"
        )

    op.create_index(
        INDEX_NAME,
        "run_lineage",
        ["child_run_id"],
        unique=True,
        postgresql_where=sa.text(
            "relationship_type = 'evaluates_checkpoint_from'"
        ),
    )


def downgrade():
    op.drop_index(INDEX_NAME, table_name="run_lineage")

