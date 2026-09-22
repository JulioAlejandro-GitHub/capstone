"""Contract tests only: no training, transport, database or artifact writes."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from src.malaria_dl.execution.contracts import (
    ExecutionContext, ExecutionMode, RunEvent, RunEventType, RunReporter,
)


def context(**changes):
    values = dict(run_id=UUID(int=1), owner=UUID(int=2),
                  execution_mode=ExecutionMode.DOCKER, dataset_version_id=UUID(int=3),
                  model_id="custom_cnn", adapter_version="1")
    return ExecutionContext(**(values | changes))


def event(**changes):
    values = dict(event_id=UUID(int=4), run_id=UUID(int=1), sequence=1,
                  event_type=RunEventType.EPOCH_COMPLETED,
                  occurred_at=datetime(2026, 9, 22, 10, tzinfo=timezone(timedelta(hours=-3))),
                  payload={"epoch": 1, "metrics": {"loss": 0.25}, "labels": ["α", None, True, 1.0]})
    return RunEvent(**(values | changes))


class InMemoryRunReporter(RunReporter):
    def __init__(self):
        self.events: list[RunEvent] = []

    def report(self, event: RunEvent) -> None:
        self.events.append(event)


def test_mode_exact_values_and_json():
    assert {mode.name: mode.value for mode in ExecutionMode} == {
        "DOCKER": "docker", "LOCAL_PYTHON": "local_python"}
    assert json.loads(json.dumps(list(ExecutionMode))) == ["docker", "local_python"]
    with pytest.raises(ValueError):
        ExecutionMode("remote")


def test_event_type_exact_values():
    expected = "heartbeat epoch_completed phase_started phase_completed artifact_prepared artifact_created predictions_completed selection_completed calibration_completed evaluation_completed training_completed training_failed".split()
    assert [kind.value for kind in RunEventType] == expected
    assert [kind.name for kind in RunEventType] == [name.upper() for name in expected]


def test_context_identity_immutability_and_optional_metadata():
    assert context() == context()
    assert context().attempt_id is None
    local = context(execution_mode=ExecutionMode.LOCAL_PYTHON, attempt_id=uuid4())
    assert local.campaign_id is None
    full = context(attempt_id=uuid4(), campaign_id=uuid4(), member_id=uuid4(),
                   configuration_hash="a" * 64, contract_hash="0" * 64)
    assert isinstance(full.member_id, UUID)
    with pytest.raises(FrozenInstanceError):
        full.run_id = uuid4()
    assert not hasattr(full, "__dict__")


@pytest.mark.parametrize("name", ["run_id", "owner", "dataset_version_id", "attempt_id", "campaign_id", "member_id"])
def test_context_requires_uuid_objects(name):
    with pytest.raises(TypeError):
        context(**{name: str(uuid4())})


@pytest.mark.parametrize("changes", [
    {"execution_mode": "docker"}, {"model_id": " "}, {"adapter_version": None},
    {"configuration_hash": "bad"}, {"contract_hash": "A" * 64},
])
def test_context_invalid_values(changes):
    with pytest.raises((TypeError, ValueError)):
        context(**changes)


@pytest.mark.parametrize("kind", list(RunEventType))
@pytest.mark.parametrize("attempt", [None, UUID(int=8)])
def test_event_json_round_trip(kind, attempt):
    original = event(event_type=kind, attempt_id=attempt)
    wire = json.loads(json.dumps(original.to_dict(), allow_nan=False))
    restored = RunEvent.from_dict(wire)
    assert restored == original
    assert restored.event_id == UUID(int=4)
    assert restored.event_type is kind
    assert restored.schema_version == "run_event_v1"
    assert restored.occurred_at == datetime(2026, 9, 22, 13, tzinfo=timezone.utc)
    assert restored.occurred_at.tzinfo is timezone.utc
    assert type(restored.payload["labels"][3]) is float


def test_deep_immutability_and_detached_serialization():
    source = {"nested": {"values": [1, {"x": 2}]}}
    original = event(payload=source)
    source["nested"]["values"][1]["x"] = 99
    assert original.payload["nested"]["values"][1]["x"] == 2
    with pytest.raises(FrozenInstanceError):
        original.sequence = 2
    with pytest.raises(TypeError):
        original.payload["new"] = 1
    with pytest.raises(TypeError):
        original.payload["nested"]["values"][1]["x"] = 3
    with pytest.raises(TypeError):
        original.payload["nested"]["values"][0] = 3
    wire = original.to_dict()
    wire["payload"]["nested"]["values"][1]["x"] = 88
    assert original.payload["nested"]["values"][1]["x"] == 2
    assert replace(original) == original
    assert not hasattr(original, "__dict__")


@pytest.mark.parametrize("changes", [
    {"event_id": "invalid"}, {"run_id": str(UUID(int=1))}, {"attempt_id": 1},
    {"sequence": 0}, {"sequence": -1}, {"sequence": True}, {"sequence": 1.5},
    {"event_type": "epoch_completed"}, {"schema_version": "run_event_v2"},
    {"occurred_at": datetime(2026, 1, 1)}, {"occurred_at": "2026-01-01"},
    {"payload": []},
])
def test_event_rejects_invalid_envelope_values(changes):
    with pytest.raises((TypeError, ValueError)):
        event(**changes)


class TensorLike:
    def item(self):
        raise AssertionError("normalization must be explicit, never call item()")


@pytest.mark.parametrize("value", [
    object(), Path("checkpoint"), RuntimeError("failure"), b"bytes", {1, 2},
    uuid4(), datetime.now(timezone.utc), TensorLike(), float("nan"),
    float("inf"), float("-inf"), {1: "non-string key"},
])
def test_payload_rejects_non_json_values(value):
    with pytest.raises((TypeError, ValueError)):
        event(payload={"nested": [value]})


def test_payload_cycles_rejected_but_shared_values_supported():
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match="cycle"):
        event(payload={"cycle": cyclic})
    shared = [1, 2]
    assert event(payload={"a": shared, "b": shared}).to_dict()["payload"] == {"a": [1, 2], "b": [1, 2]}


@pytest.mark.parametrize("name,value", [
    ("event_id", "bad"), ("event_id", UUID(int=4)), ("run_id", 1),
    ("attempt_id", 1), ("attempt_id", "bad"), ("event_type", "unknown"),
    ("schema_version", "v2"), ("schema_version", None),
    ("occurred_at", "bad"), ("occurred_at", "2026-01-01T00:00:00"),
    ("sequence", True), ("payload", {"value": float("nan")}),
])
def test_deserialization_rejects_invalid_values(name, value):
    wire = event().to_dict()
    wire[name] = value
    with pytest.raises((TypeError, ValueError)):
        RunEvent.from_dict(wire)


@pytest.mark.parametrize("name", list(event().to_dict()))
def test_deserialization_requires_all_fields(name):
    wire = event().to_dict()
    del wire[name]
    with pytest.raises(ValueError):
        RunEvent.from_dict(wire)


def test_deserialization_rejects_unknown_fields():
    with pytest.raises(ValueError):
        RunEvent.from_dict(event().to_dict() | {"future": 1})


def test_abstract_port_and_order_identity_content():
    with pytest.raises(TypeError):
        RunReporter()

    class Incomplete(RunReporter):
        pass

    with pytest.raises(TypeError):
        Incomplete()
    reporter = InMemoryRunReporter()
    first, second = event(), event(event_id=uuid4(), sequence=2)
    for item in (first, second, first):
        reporter.report(item)
    assert reporter.events == [first, second, first]
    assert reporter.events[0] is first
    assert reporter.events[0].event_id == reporter.events[2].event_id
    assert sorted([second, first], key=lambda item: item.sequence) == [first, second]
    assert [RunEvent.from_dict(item.to_dict()) for item in reporter.events] == reporter.events
