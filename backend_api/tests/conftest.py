import os

# Unit-test collection needs configuration because application modules intentionally have
# no operational secrets or database defaults. PostgreSQL-marked tests override this with
# the real local values supplied by the operator.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@127.0.0.1:9/capstone")
os.environ.setdefault("JWT_SECRET", "unit-test-secret-at-least-thirty-two-characters")
