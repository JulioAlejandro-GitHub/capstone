"""Strict pre-fit configuration snapshot in existing runs JSONB; no sidecars."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess

from sqlalchemy import text
from .database import get_engine
from ..data.governed_dataset import (
    dataset_read_connection,
    normalize_dataset_version_id,
)


class ModelConfigurationPersistenceError(RuntimeError):
    pass


def environment_identity():
    import tensorflow as tf

    root = Path(__file__).resolve().parents[3]

    def git(*args):
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None

    files = {}
    # Fingerprint effective implementation and development configs, never .env/data.
    for directory in (root / "src", root / "configs"):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.suffix in (".py", ".json"):
                files[str(path.relative_to(root))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    for path in sorted(root.glob("run_*.py")):
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(
        git_commit=git("rev-parse", "HEAD"),
        git_dirty=bool(git("status", "--porcelain")),
        source_sha256=hashlib.sha256(
            json.dumps(files, sort_keys=True).encode()
        ).hexdigest(),
        python=platform.python_version(),
        tensorflow=tf.__version__,
        packages={
            name: importlib.metadata.version(name)
            for name in ("keras", "numpy", "SQLAlchemy", "psycopg")
        },
        devices=[
            dict(type=d.device_type, name=d.name)
            for d in tf.config.list_logical_devices()
        ],
        determinism_environment={
            key: os.environ.get(key)
            for key in ("TF_DETERMINISTIC_OPS", "PYTHONHASHSEED")
        },
    )


def persist_model_configuration(run_id, configuration, runtime, dataset, execution):
    """Update only the requested TRAIN/dataset, then compare a fresh read in full."""
    engine = None
    try:
        run_id = normalize_dataset_version_id(run_id)
        version = normalize_dataset_version_id(dataset["dataset_version_id"])
        snapshot = dict(
            configuration=configuration,
            runtime=runtime,
            dataset=dataset,
            execution=execution,
            environment=environment_identity(),
        )
        serialized = json.dumps(snapshot, allow_nan=False)
        engine = get_engine()
        with engine.begin() as connection:
            changed = connection.execute(
                text("""
                UPDATE runs SET execution_parameters =
                  COALESCE(execution_parameters, '{}'::jsonb) ||
                  jsonb_build_object('model_configuration_e2', CAST(:snapshot AS jsonb))
                WHERE id=CAST(:id AS uuid) AND run_type='training'
                  AND dataset_version_id=CAST(:dataset AS uuid)
                RETURNING id
            """),
                dict(id=run_id, dataset=version, snapshot=serialized),
            ).scalar_one_or_none()
            if changed is None:
                raise ValueError("RUN_IDENTITY_MISMATCH")
        with dataset_read_connection() as connection:
            stored = connection.execute(
                text("""
                SELECT execution_parameters->'model_configuration_e2'
                FROM runs WHERE id=CAST(:id AS uuid) AND run_type='training'
                  AND dataset_version_id=CAST(:dataset AS uuid)
            """),
                dict(id=run_id, dataset=version),
            ).scalar_one_or_none()
        if stored != json.loads(serialized):
            raise ValueError("MODEL_CONFIGURATION_ROUND_TRIP_MISMATCH")
    except Exception:
        raise ModelConfigurationPersistenceError(
            "MODEL_CONFIGURATION_PERSISTENCE_FAILED"
        ) from None
    finally:
        if engine is not None:
            engine.dispose()
    return snapshot
