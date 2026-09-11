"""E3 input snapshots through E2's reviewed temporary-table/rollback harness."""

import os

import pytest
import test_model_configuration_postgres as harness

pytestmark = [
    pytest.mark.requires_docker_postgres,
    pytest.mark.skipif(
        os.environ.get("RUN_STAGE3_POSTGRES_TESTS") != "1",
        reason="Authorized Compose E3 opt-in required",
    ),
]


@pytest.mark.parametrize("architecture", ["custom_cnn", "vgg16", "densenet121"])
def test_input_snapshot_roundtrip(monkeypatch, architecture):
    snapshot = harness.configuration_roundtrip_and_rollback(
        monkeypatch, model_name=architecture
    )
    contract = snapshot["configuration"]["resolved"]["input_contract"]
    assert contract["schema_version"] == "malaria_input_v1"
    assert contract["architecture"] == architecture
    assert contract["external"]["mode"] == (
        "vgg16_imagenet" if architecture == "vgg16" else "rescale_0_1"
    )
