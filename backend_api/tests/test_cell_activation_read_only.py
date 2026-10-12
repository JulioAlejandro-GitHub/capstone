"""Read-only verification of the actual checkpoint; no publications or scientific runs."""
from uuid import UUID
import hashlib
from types import SimpleNamespace
from sqlalchemy import text
from app.db import read_only_transaction
from app.services.cell_activation import CellActivationService
from app.services.productive_model import ProductiveModelResolver
from src.malaria_dl.governance.services.deployment_service import _project_path


def test_real_selected_checkpoint_loads_without_registering_or_activating():
    with read_only_transaction('malaria') as c:
        binding = c.execute(text("""SELECT i.identity->'model' FROM assessment_attempts a
          JOIN assessment_identities i ON i.id=a.identity_id
          WHERE a.id=:id AND a.state='verified'"""),
          {'id': UUID('dded6222-12ae-407a-82c6-601e265e3f7d')}).scalar_one()
    path = _project_path(binding['path'])
    assert path.stat().st_size == binding['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == binding['sha256']
    resolver = ProductiveModelResolver()
    contract = binding['input_contract']
    shape = contract['shape']
    resolved = SimpleNamespace(checkpoint_path=path, checkpoint_size_bytes=binding['bytes'],
        checkpoint_sha256=binding['sha256'], input_height=shape[1], input_width=shape[2],
        input_channels=shape[3], output_signature=contract['output'])
    model = resolver._load_verified_copy(resolved)
    CellActivationService._smoke(model, resolved)
