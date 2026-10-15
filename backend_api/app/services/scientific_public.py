"""Public projections never use storage locations as scientific identifiers."""
import re
from typing import Any

_PRIVATE_KEYS = {
    'owner', 'host', 'host_name', 'pid', 'command', 'canonical_identity',
    'canonical_configuration', 'filename', 'working_directory',
}
_LOCATION = re.compile(r'(?:^|[\s"\x27=])(?:/(?:[^ /]+/)|[A-Za-z]:[\\/]|file://)')


def public_evidence(value: Any) -> Any:
    """Remove storage locators recursively, including extension metadata."""
    if isinstance(value, dict):
        return {key: public_evidence(item) for key, item in value.items()
                if key not in _PRIVATE_KEYS
                and not any(part in key.lower().split('_') for part in ('path', 'paths', 'uri', 'root', 'directory'))}
    if isinstance(value, (list, tuple)):
        return [public_evidence(item) for item in value]
    if isinstance(value, str) and _LOCATION.search(value):
        return None
    return value


def assessment_projection(value: dict[str, Any]) -> dict[str, Any]:
    result = public_evidence(value)
    identity = value.get('identity') or {}
    split = value.get('split') or identity.get('split')
    kind = value['kind']
    result['assessment_type'] = 'TEST' if kind == 'evaluate' and split == 'test' else kind.upper()
    result['split'] = split
    result['identity_id'] = value.get('identity_id', value.get('id'))
    result['evidence_status'] = 'available' if value.get('verification') else 'not_persisted'
    result['generation_status'] = 'unknown' if not value.get('verification') else 'recorded'
    result['file_availability'] = 'not_checked'
    return result
