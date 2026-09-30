"""Complete independent PostgreSQL v2 root, including approved amendment A-01."""

from alembic import op
from alembic_v2.resources import load_baseline
from alembic_v2.safety import require

revision = "pg_v2_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    require(connection.info.get("pg_v2_verified_target"), "V2_UNVERIFIED_CONNECTION")
    require(connection.in_transaction(), "V2_TRANSACTION_REQUIRED")
    _, statements = load_baseline()
    for sql in statements:
        # Raw driver SQL avoids treating PL/pgSQL colon/percent characters as binds.
        connection.exec_driver_sql(sql, execution_options={"no_parameters": True})


def downgrade():
    raise RuntimeError("V2_DESTRUCTIVE_DOWNGRADE_DISABLED_RESTORE_ISOLATED_BACKUP")
