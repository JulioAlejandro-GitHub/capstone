"""Academic authentication and RBAC foundation."""

from alembic import op

revision = "20260726_01"
down_revision = "20260726_00"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
      CREATE TABLE users (
        id UUID PRIMARY KEY, username TEXT NOT NULL UNIQUE, email TEXT UNIQUE,
        password_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active'
          CHECK (status IN ('active','disabled')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_login_at TIMESTAMPTZ, disabled_at TIMESTAMPTZ
      );
      CREATE TABLE roles (
        id UUID PRIMARY KEY, name TEXT NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE TABLE user_roles (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY(user_id, role_id)
      );
      INSERT INTO roles(id,name) VALUES
        (gen_random_uuid(),'administrator'),(gen_random_uuid(),'researcher'),
        (gen_random_uuid(),'operator'),(gen_random_uuid(),'reviewer'),(gen_random_uuid(),'read_only');
    """)


def downgrade():
    op.execute("DROP TABLE user_roles; DROP TABLE roles; DROP TABLE users;")
