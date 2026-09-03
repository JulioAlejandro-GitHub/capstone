import os
import tempfile
from pathlib import Path

# Unit-test collection needs configuration because application modules intentionally have
# no operational secrets or database defaults. PostgreSQL-marked tests override this with
# the real local values supplied by the operator.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@db:5432/capstone")
os.environ.setdefault("JWT_SECRET", "unit-test-secret-at-least-thirty-two-characters")
os.environ["STORAGE_ROOT"] = str(
    Path(tempfile.gettempdir()) / f"capstone-pytest-{os.getpid()}"
)
