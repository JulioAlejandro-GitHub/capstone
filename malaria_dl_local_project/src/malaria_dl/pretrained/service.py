"""Registration orchestration: scientific identity lock, global gate, SQL transaction."""
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import text

from ..campaigns.contracts import digest
from ..execution.artifacts import file_identity
from ..execution.global_gate import GlobalGate
from ..persistence.database import get_engine
from .contracts import COMPONENTS, configuration, framework_versions, require
from .repository import PretrainedRepository


def register_pretrained(*, dataset_version_id, biomedclip_directory, text_directory, engine_factory=get_engine):
    @contextmanager
    def scope(readonly=False):
        engine = engine_factory()
        try:
            with engine.begin() as connection:
                if readonly:
                    connection.execute(text("SET TRANSACTION READ ONLY"))
                yield connection
        finally:
            engine.dispose()

    repo = PretrainedRepository(scope)
    dataset = repo.resolve_dataset(dataset_version_id)
    config = configuration(dataset, framework_versions())
    for name, expected in COMPONENTS.items():
        source = Path(text_directory) / name[5:] if name.startswith("text/") else Path(biomedclip_directory) / name
        require(not any(p.is_symlink() for p in (source, *source.parents)), "PRETRAINED_SYMLINK_FORBIDDEN")
        require(file_identity(source) == expected, "PRETRAINED_COMPONENT_IDENTITY_MISMATCH:" + name)
    # Same-identity callers wait before acquiring the nonblocking global execution gate.
    # The unique SQL index also protects direct writers that do not cooperate with this lock.
    engine = engine_factory()
    key = int(digest(config)[:15], 16)
    try:
        with engine.connect() as lock:
            lock.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
            lock.commit()
            try:
                existing = repo.find(digest(config))
                if existing:
                    return {**repo.recover(existing), "reused": True}
                with GlobalGate("register-pretrained", engine_factory=engine_factory) as gate:
                    result = repo.register(config=config, biomedclip_directory=biomedclip_directory,
                                           text_directory=text_directory, owner=gate.owner)
                return {**result, "reused": False}
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                lock.commit()
    finally:
        engine.dispose()
