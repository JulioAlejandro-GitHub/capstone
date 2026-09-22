"""Read the two ledger families explicitly; preserve the historical projection."""
from sqlalchemy import text

from ..campaigns.repository import identifier
from .result_repository import _decode


def read_legacy_execution_records(connection, run_id):
    # ->> maps SQL NULL to NULL and also works before the E10 metadata migration
    # (missing column in the row object). Never classify by kind/payload content.
    return [dict(row) for row in connection.execute(text('''
        SELECT kind,phase,record_key,payload FROM train_execution_records AS record
        WHERE run_id=CAST(:id AS uuid) AND (to_jsonb(record)->>'event_id') IS NULL
        ORDER BY kind,phase,record_key'''), {'id': identifier(run_id)}).mappings()]


def read_result_events(connection, run_id):
    """Return validated RunEvents in numeric sequence order, including after close.

    This is a trusted backend read, not a remote authorization or restart API.
    E10.3's decoder checks canonical text AND projected identity; corrupt evidence
    fails closed. A schema predating E10 contains no events and returns [].
    """
    rows = connection.execute(text('''
        SELECT record.* FROM train_execution_records AS record
        WHERE run_id=CAST(:id AS uuid) AND (to_jsonb(record)->>'event_id') IS NOT NULL
        ORDER BY (to_jsonb(record)->>'event_sequence')::numeric'''),
        {'id': identifier(run_id)}).mappings()
    return [_decode(row) for row in rows]
