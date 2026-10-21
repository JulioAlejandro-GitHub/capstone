"""Calibration projection keeps the exact decimals of its E10 event.

Regression for pilot run a137c67c: a float bound as float8 is stored in a numeric column
with 15 significant digits, so e04_assert_calibration (which compares the columns with
the event JSON text) rejected a clinical threshold of 0.3062586486339569.
Fake connection only; no database.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.malaria_dl.execution.worker import failure_signature
from src.malaria_dl.persistence import v2_projection
from src.malaria_dl.results.errors import ResultPersistenceError

THRESHOLD = 0.3062586486339569  # selected by the pilot; float8 -> numeric gives 0.306258648633957
AUC, PR_AUC = 0.9385335981463092, 0.9446738204183319
HEX = 'a' * 64


class Connection:
    def __init__(self, run):
        self.run, self.inserts, self.queries = run, [], []

    def execute(self, statement, params=None):
        sql = str(statement)
        if sql.startswith('SELECT * FROM runs'):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(one=lambda: self.run))
        if sql.startswith('INSERT INTO'):
            self.inserts.append((sql.split()[2], params))
            return None
        self.queries.append(params)
        return SimpleNamespace(scalar_one=lambda: uuid4())

    def rows(self, table):
        return [params for name, params in self.inserts if name == table]


def run_row():
    context = dict(checkpoint_artifact_id=str(uuid4()), protocol_version='v', protocol_hash=HEX,
                   population_hash=HEX, input_contract_hash=HEX, comparison_contract_hash=HEX,
                   protocol_snapshot={'threshold': 0.5}, model_version_id=str(uuid4()))
    return {'id': uuid4(), 'dataset_version_id': uuid4(),
            'execution_parameters': {'e10_v2_evaluation_context_v1': context}}


def metrics(tn, fp, fn, tp):
    return dict(tn=tn, fp=fp, fn=fn, tp=tp, roc_auc_parasitized=AUC, pr_auc_parasitized=PR_AUC)


def calibration_event():
    calibration = dict(calibration_split='val', threshold_source='validation_calibration',
                       threshold_selected=THRESHOLD, threshold_used=THRESHOLD, default_threshold=0.5,
                       target_recall=0.98, default_threshold_metrics=metrics(875, 493, 70, 1255),
                       selected_metrics=metrics(460, 908, 26, 1299))
    payload = {'legacy_record': {'kind': 'calibration', 'phase': 'val', 'record_key': 'selected'},
               'result': {'split': 'val', 'checkpoint_epoch': 2, 'result': calibration}}
    return SimpleNamespace(event_id=uuid4(), run_id=uuid4(), schema_version='run_event_v1',
                           occurred_at=datetime.now(timezone.utc),
                           to_dict=lambda: {'payload': json.loads(json.dumps(payload))})


def as_json_text(value):
    return json.dumps(value)


@pytest.mark.parametrize('value', [THRESHOLD, AUC, 0.5, 0.98, 1e-05, 9.999999747378752e-05])
def test_float_binds_the_decimal_written_in_the_event_json(value):
    bound = v2_projection._exact(value)
    # Same numeric value PostgreSQL reads from the event text ((json->>'k')::numeric).
    assert isinstance(bound, Decimal) and bound == Decimal(as_json_text(value))
    assert float(bound) == value


@pytest.mark.parametrize('value', [None, 0, 3, True, 'text', Decimal('0.5')])
def test_non_float_values_are_bound_unchanged(value):
    assert v2_projection._exact(value) is value


def test_insert_never_binds_a_float_parameter():
    connection = Connection(run_row())
    v2_projection._insert(connection, 'evaluations', {'threshold_used': THRESHOLD, 'n': 2,
                                                      'metadata': {'score': THRESHOLD}})
    (_, params), = connection.inserts
    assert params['threshold_used'] == Decimal(as_json_text(THRESHOLD)) and params['n'] == 2
    assert json.loads(params['metadata']) == {'score': THRESHOLD}
    assert not any(isinstance(v, float) for v in params.values())


def test_calibration_projection_stores_threshold_and_metrics_exactly():
    connection = Connection(run_row())
    event = calibration_event()
    v2_projection.project_calibration(connection, event)
    exact = Decimal(as_json_text(THRESHOLD))
    calibration, = connection.rows('run_threshold_calibration')
    assert calibration['threshold_selected'] == exact and calibration['default_threshold'] == Decimal('0.5')
    assert calibration['target_recall'] == Decimal('0.98')
    default, selected = connection.rows('evaluations')
    assert selected['threshold_used'] == exact and selected['threshold_source'] == 'validation_calibration'
    assert default['threshold_used'] == Decimal('0.5') and default['threshold_source'] == 'default'
    for row in connection.rows('run_clinical_metrics'):
        assert row['roc_auc_parasitized'] == Decimal(as_json_text(AUC))
        assert row['pr_auc_parasitized'] == Decimal(as_json_text(PR_AUC))
    for _, params in connection.inserts:
        assert not any(isinstance(v, float) for v in params.values())


def test_calibration_projection_still_rejects_inconsistent_payloads():
    connection = Connection(run_row())
    event = calibration_event()
    payload = event.to_dict()
    payload['payload']['result']['result']['threshold_used'] = 0.5
    event.to_dict = lambda: payload
    with pytest.raises(ResultPersistenceError):
        v2_projection.project_calibration(connection, event)
    assert connection.inserts == []


def test_final_evaluation_lookup_uses_the_exact_calibrated_threshold():
    connection = Connection(run_row())
    evaluation = SimpleNamespace(
        threshold=SimpleNamespace(value=THRESHOLD, source='validation_calibration'),
        confusion_matrix=SimpleNamespace(tn=460, fp=908, fn=26, tp=1299),
        metrics=SimpleNamespace(roc_auc=AUC, pr_auc=PR_AUC))
    v2_projection.project_evaluation(connection, calibration_event(), SimpleNamespace(validation=evaluation))
    lookup, = connection.queries
    assert lookup['threshold'] == Decimal(as_json_text(THRESHOLD))
    final, = connection.rows('evaluations')
    assert final['threshold_used'] == Decimal(as_json_text(THRESHOLD)) and final['calibration_id'] is not None


class Diag:
    message_primary = 'E04_EVENT_PROVENANCE'


def test_worker_failure_signature_names_classes_and_guard_codes_only():
    class DatabaseError(Exception):
        orig = SimpleNamespace(diag=Diag())
    try:
        try:
            raise DatabaseError('patient 123 data must not leak')
        except DatabaseError:
            raise ResultPersistenceError() from None
    except ResultPersistenceError as exc:
        signature = failure_signature(exc)
    assert signature == 'ResultPersistenceError <- DatabaseError[E04_EVENT_PROVENANCE]'
    assert 'patient' not in signature


def test_worker_failure_signature_ignores_free_text_diagnostics():
    class DatabaseError(Exception):
        orig = SimpleNamespace(diag=SimpleNamespace(message_primary='duplicate key value for sample 42'))
    assert failure_signature(DatabaseError('x')) == 'DatabaseError'
