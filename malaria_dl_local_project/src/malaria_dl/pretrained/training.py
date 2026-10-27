"""Operational skip; never registers a pretrained model or creates a session."""
import json
from ..models.registry import MODEL_REGISTRY

def omit_training(model):
    descriptor = MODEL_REGISTRY.get(model)
    if descriptor is None or descriptor.trainable:
        return False
    print(json.dumps({"model": model, "state": "omitted",
                      "reason": "No requiere entrenamiento local"}, ensure_ascii=False))
    return True
