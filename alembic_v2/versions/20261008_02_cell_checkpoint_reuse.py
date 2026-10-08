"""Bind assessment checkpoints to existing physical artifacts by verified identity and bytes."""
from alembic import op
from sqlalchemy import text

revision = 'cell_checkpoint_reuse_v2'
down_revision = 'cell_activation_v1'
branch_labels = None
depends_on = None

OLD = "OR evidence#>>'{model,checkpoint_artifact_id}' IS DISTINCT FROM NEW.checkpoint_artifact_id::text"
NEW = """OR NOT EXISTS(SELECT 1 FROM public.artifacts physical
      WHERE physical.id=NEW.checkpoint_artifact_id AND physical.run_id=train
        AND physical.checksum=evidence#>>'{model,sha256}'
        AND physical.file_size_bytes=(evidence#>>'{model,bytes}')::bigint)"""


def upgrade():
    source = op.get_bind().execute(text("SELECT pg_get_functiondef('public.validate_cell_assessment_reference()'::regprocedure)")).scalar_one()
    if OLD not in source:
        raise RuntimeError('CELL_REFERENCE_FUNCTION_VERSION_MISMATCH')
    op.execute(source.replace(OLD, NEW))


def downgrade():
    if op.get_bind().execute(text("""SELECT EXISTS(SELECT 1 FROM stage2_model_publications p
      JOIN assessment_attempts a ON a.id=p.evaluation_attempt_id
      JOIN assessment_identities i ON i.id=a.identity_id
      WHERE p.checkpoint_artifact_id::text IS DISTINCT FROM i.identity#>>'{model,checkpoint_artifact_id}')""")).scalar_one():
        raise RuntimeError('CELL_CHECKPOINT_ALIAS_IN_USE')
    source = op.get_bind().execute(text("SELECT pg_get_functiondef('public.validate_cell_assessment_reference()'::regprocedure)")).scalar_one()
    if NEW not in source:
        raise RuntimeError('CELL_REFERENCE_FUNCTION_VERSION_MISMATCH')
    op.execute(source.replace(NEW, OLD))
