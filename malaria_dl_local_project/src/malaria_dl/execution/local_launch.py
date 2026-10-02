"""Host bootstrap for `python run_train_all_models.py --campaign-id <UUID>`.

Inside Docker nothing changes. On the host (macOS) it checks the dedicated
virtualenv and points DATABASE_URL at the Docker Compose PostgreSQL published on
127.0.0.1:5432, with the same runtime role and root .env the backend uses.
The launcher talks to PostgreSQL directly: no HTTP API, no JWT, no agent config.
Stdlib only before the venv check, so a wrong interpreter fails readably.
"""
import importlib.util
import os
import sys
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VENV = ".venv-local-train"
REQUIRED = ("tensorflow", "keras", "numpy", "sqlalchemy", "psycopg", "psutil", "dotenv")
# Same role as docker-compose.yml backend.DATABASE_URL (certified non-superuser).
RUNTIME_ROLE = "capstone_v2_runtime"


class LocalLaunchError(RuntimeError):
    pass


def in_docker():
    return Path("/.dockerenv").exists()


def environment_problem(prefix=None, base=None, version=None, find=importlib.util.find_spec):
    prefix = sys.prefix if prefix is None else prefix
    base = sys.base_prefix if base is None else base
    version = sys.version_info if version is None else version
    if Path(prefix).name != VENV or prefix == base:
        return f"intérprete activo: {prefix}"
    if tuple(version[:2]) != (3, 12):
        return f"Python {version[0]}.{version[1]} (se requiere 3.12)"
    missing = [m for m in REQUIRED if find(m) is None]
    if missing:
        return "faltan paquetes: " + ", ".join(missing)
    return None


def database_url(env_file=None):
    """Built from the Compose .env; the password is never printed."""
    env_file = PROJECT_ROOT.parent / ".env" if env_file is None else Path(env_file)
    if not env_file.is_file():
        raise LocalLaunchError(f"LOCAL_DATABASE_CONFIG_MISSING: {env_file}")
    from dotenv import dotenv_values

    values = dotenv_values(env_file)
    password, database = values.get("CAPSTONE_V2_RUNTIME_PASSWORD"), values.get("POSTGRES_DB")
    if not password or not database:
        raise LocalLaunchError(
            f"LOCAL_DATABASE_CONFIG_MISSING: CAPSTONE_V2_RUNTIME_PASSWORD/POSTGRES_DB en {env_file}")
    return f"postgresql+psycopg://{RUNTIME_ROLE}:{quote(password, safe='')}@127.0.0.1:5432/{quote(database, safe='')}"


def bootstrap(environ=os.environ, docker=None):
    """Exit(2) with an actionable message before any attempt can be created."""
    if in_docker() if docker is None else docker:
        return
    problem = environment_problem()
    if problem:
        print(f"LOCAL_ENVIRONMENT_INVALID\n{problem}\n\nActive el entorno:\n\n"
              f"  cd {PROJECT_ROOT}\n  source {VENV}/bin/activate", file=sys.stderr)
        raise SystemExit(2)
    try:
        environ["DATABASE_URL"] = database_url()
    except LocalLaunchError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    # Opt-in for the loopback host in persistence.database; inherited by workers.
    environ["CAPSTONE_LOCAL_TRAIN"] = "1"
