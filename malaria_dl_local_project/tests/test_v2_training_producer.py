"""V2 producer of TRAIN/VAL evidence: evaluation context and projection-based completion.

No database: the PostgreSQL behaviour is covered end to end on an isolated clone.
"""
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.malaria_dl.campaigns.contracts import digest
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.execution.completion import TrainingResultsMismatch, _projection_matches
from src.malaria_dl.persistence.v2_projection import training_evaluation_context
from src.malaria_dl.results.errors import ResultPersistenceError
from src.malaria_dl.results.training import ThresholdResult

PROTOCOL = {"version": "campaign_configuration_v1:abc", "sensitivity_target": 0.98}
DATASET = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"


def context(**changes):
    values = dict(checkpoint_artifact_id=uuid4(), protocol=PROTOCOL, dataset_version_id=DATASET,
                  population=["val/b.png", "val/a.png"], input_contract={"model": "custom_cnn"})
    values.update(changes)
    return training_evaluation_context(**values)


def test_context_satisfies_the_v2_projection_contract():
    value = context()
    required = {"checkpoint_artifact_id", "protocol_version", "protocol_hash", "population_hash",
                "input_contract_hash", "comparison_contract_hash", "protocol_snapshot"}
    assert set(value) == required
    for key in ("protocol_hash", "population_hash", "input_contract_hash", "comparison_contract_hash"):
        assert re.fullmatch("[0-9a-f]{64}", value[key])
    assert value["protocol_version"] == PROTOCOL["version"] and value["protocol_snapshot"] == PROTOCOL
    assert value["protocol_hash"] == digest(PROTOCOL)


def test_population_is_order_independent_but_content_sensitive():
    assert context()["population_hash"] == context(population=["val/a.png", "val/b.png"])["population_hash"]
    assert context()["population_hash"] != context(population=["val/a.png"])["population_hash"]


def test_members_of_one_campaign_share_the_comparison_contract():
    # Different architecture (input contract) and checkpoint: still comparable.
    a = context(input_contract={"model": "custom_cnn"})
    b = context(input_contract={"model": "vgg16", "preprocessing": "vgg16_imagenet"})
    assert a["input_contract_hash"] != b["input_contract_hash"]
    assert a["comparison_contract_hash"] == b["comparison_contract_hash"]
    # Another protocol, dataset or VAL population is not comparable.
    assert context(protocol={"version": "other"})["comparison_contract_hash"] != a["comparison_contract_hash"]
    assert context(dataset_version_id=str(uuid4()))["comparison_contract_hash"] != a["comparison_contract_hash"]
    assert context(population=["val/a.png"])["comparison_contract_hash"] != a["comparison_contract_hash"]


@pytest.mark.parametrize("changes", [dict(protocol={}), dict(protocol=None), dict(population=[])])
def test_missing_provenance_is_an_error(changes):
    with pytest.raises(ResultPersistenceError):
        context(**changes)


def evaluation(threshold=ThresholdResult(0.5, "default")):
    return evaluate_validation_predictions([0, 0, 1, 1, 1], [0.1, 0.7, 0.6, 0.9, 0.2], threshold)


def projected(ev, event_id, **changes):
    cm = ev.confusion_matrix
    row = dict(source_event_id=event_id, threshold_used=ev.threshold.value,
               threshold_source=ev.threshold.source, tn=cm.tn, fp=cm.fp, fn=cm.fn, tp=cm.tp,
               roc_auc_parasitized=ev.metrics.roc_auc, pr_auc_parasitized=ev.metrics.pr_auc)
    row.update(changes)
    return row


def test_projection_of_the_same_event_is_accepted():
    from decimal import Decimal
    ev, event = evaluation(), SimpleNamespace(event_id=uuid4())
    # NUMERIC columns come back as Decimal.
    row = projected(ev, event.event_id, threshold_used=Decimal("0.5"),
                    roc_auc_parasitized=Decimal(str(ev.metrics.roc_auc)))
    _projection_matches(row, event, ev)


@pytest.mark.parametrize("changes", [
    dict(tp=0), dict(threshold_source="validation_calibration"), dict(threshold_used=0.4),
    dict(roc_auc_parasitized=None), dict(pr_auc_parasitized=0.01),
])
def test_projection_disagreeing_with_the_event_is_rejected(changes):
    ev, event = evaluation(), SimpleNamespace(event_id=uuid4())
    with pytest.raises(TrainingResultsMismatch):
        _projection_matches(projected(ev, event.event_id, **changes), event, ev)


def test_projection_from_another_event_or_missing_is_rejected():
    ev, event = evaluation(), SimpleNamespace(event_id=uuid4())
    with pytest.raises(TrainingResultsMismatch):
        _projection_matches(projected(ev, uuid4()), event, ev)
    with pytest.raises(TrainingResultsMismatch):
        _projection_matches(None, event, ev)
