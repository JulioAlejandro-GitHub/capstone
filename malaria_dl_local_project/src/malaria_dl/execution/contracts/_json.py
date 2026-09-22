"""Strict JSON values, copied and deeply frozen at the contract boundary."""
from collections.abc import Mapping
import math
from types import MappingProxyType
from typing import TypeAlias

JSONValue: TypeAlias = (
    None | bool | int | float | str | list["JSONValue"]
    | tuple["JSONValue", ...] | Mapping[str, "JSONValue"]
)
JSONObject: TypeAlias = Mapping[str, JSONValue]


def freeze_object(value: JSONObject) -> JSONObject:
    if type(value) not in (dict, MappingProxyType):
        raise TypeError("payload must be a JSON object")
    return _freeze(value, set())


def _freeze(value: JSONValue, visiting: set[int]) -> JSONValue:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
        return value
    if type(value) not in (dict, MappingProxyType, list, tuple):
        raise TypeError("payload contains a non-JSON value")
    identity = id(value)
    if identity in visiting:
        raise ValueError("payload contains a cycle")
    visiting.add(identity)
    try:
        if type(value) in (dict, MappingProxyType):
            if any(type(key) is not str for key in value):
                raise TypeError("JSON object keys must be strings")
            return MappingProxyType({key: _freeze(item, visiting) for key, item in value.items()})
        return tuple(_freeze(item, visiting) for item in value)
    finally:
        visiting.remove(identity)


def thaw(value: JSONValue) -> JSONValue:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value
