"""Logical TRAIN is identified exclusively by public.models.metadata.training_mode."""
import json
from sqlalchemy import text
from ..persistence.database import get_connection


def omit_training(model, metadata=None):
    if metadata is None:
        with get_connection() as connection:
            rows = connection.execute(text('SELECT metadata FROM models WHERE name=:name'),
                                      {'name': model}).scalars().all()
        if len(rows) != 1:
            raise ValueError('MODEL_NOT_REGISTERED_OR_AMBIGUOUS:' + str(model))
        metadata = rows[0] or {}
    if metadata.get('training_mode') != 'logical':
        return False
    print(json.dumps({'model': model, 'state': 'omitted',
                      'reason': 'No requiere entrenamiento local'}, ensure_ascii=False))
    return True
