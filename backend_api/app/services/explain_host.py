"""Host GPU executor policy: queue for the agent, or block when its heartbeat is not recent."""
import hashlib
import json
from typing import Any
from app.schemas.explain_generation import ExplainRequest
from src.malaria_dl.campaigns.contracts import CampaignError

# Three missed heartbeats (agent beats every 10 s).
FRESH_SECONDS = 30
AGENT_COMMAND = 'scripts/host_services.sh start explain'


def request_key(request: ExplainRequest) -> str:
    payload = request.model_dump(mode='json')
    payload['methods'] = sorted(set(payload['methods']))
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def executor_status(queue: Any) -> dict[str, Any]:
    beat = queue.heartbeat()
    available = bool(beat and beat['age_seconds'] is not None and float(beat['age_seconds']) <= FRESH_SECONDS)
    device = (beat or {}).get('device') or {}
    return {'executor': 'host_gpu', 'available': available, 'host': (beat or {}).get('host'),
            'gpu_devices': device.get('gpu_devices', []), 'tensorflow_metal': device.get('tensorflow_metal'),
            'last_seen': (beat or {}).get('last_seen'),
            'age_seconds': None if not beat or beat['age_seconds'] is None else round(float(beat['age_seconds']), 1),
            'reason': None if available else 'EXPLAIN_HOST_EXECUTOR_UNAVAILABLE', 'start_command': AGENT_COMMAND}


class HostQueueLauncher:
    """Same contract as ExplainLauncher.launch, but the host agent computes the batch."""

    def __init__(self, queue: Any) -> None:
        self.queue = queue

    def launch(self, request: ExplainRequest, actor: str) -> dict[str, Any]:
        if not executor_status(self.queue)['available']:
            raise CampaignError('EXPLAIN_HOST_EXECUTOR_UNAVAILABLE')
        operation = self.queue.enqueue(request.model_dump(mode='json'), request_key(request), actor)
        return {'operations': [{'method': method, 'state': 'pending', 'operation_id': operation}
                               for method in dict.fromkeys(request.methods)]}
