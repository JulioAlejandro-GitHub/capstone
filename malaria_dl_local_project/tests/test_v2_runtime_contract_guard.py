"""SWV2.1: require_v2_capabilities stays fail-closed against the certified pg_v2_baseline contract.

The catalog is a fake built from the committed contract, so no PostgreSQL is read or damaged.
"""
import copy
import json
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from src.malaria_dl.execution.schema import E10SchemaNotReady, require_e10_schema
from src.malaria_dl.persistence import schema_contract
from src.malaria_dl.persistence.schema_contract import CONTRACT_PATH, load_contract, require_v2_capabilities

CONTRACT = json.loads(CONTRACT_PATH.read_text())


class Result:
    def __init__(self, value): self.value = value
    def scalar_one(self): return self.value
    def scalars(self): return self
    def mappings(self): return self
    def all(self): return self.value
    def one(self): return self.value
    def __iter__(self): return iter(self.value)


class Catalog:
    """Answers the guard's pg_catalog projections; rejects anything that is not a SELECT."""
    def __init__(self, schema='public', **changes):
        self.schema = schema
        self.view = copy.deepcopy({k: CONTRACT[k] for k in
                                   ('functions', 'triggers', 'evaluation_constraints', 'calibration_indexes')})
        self.view.update(changes)
        self.statements = []

    def execute(self, statement, *args):
        sql = str(statement)
        self.statements.append(sql)
        assert sql.lstrip().upper().startswith('SELECT')
        if 'current_schema()' in sql:
            return Result(self.schema)
        if 'pg_proc' in sql:
            return Result(list(self.view['functions'].items()))
        if 'pg_trigger' in sql:
            return Result(self.view['triggers'])
        if 'pg_constraint' in sql:
            return Result(list(reversed(self.view['evaluation_constraints'])))  # order must not matter
        if 'pg_index' in sql:
            return Result(self.view['calibration_indexes'])
        raise AssertionError(sql)


def reject(catalog, reason):
    with pytest.raises(E10SchemaNotReady, match=reason):
        require_v2_capabilities(catalog)


def test_committed_contract_is_the_certified_v2_baseline():
    assert CONTRACT['revision'] == 'pg_v2_baseline'
    assert CONTRACT['source']['sha256'] == '15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb'
    assert (len(CONTRACT['functions']), len(CONTRACT['triggers']),
            len(CONTRACT['evaluation_constraints']), len(CONTRACT['calibration_indexes'])) == (13, 21, 40, 2)
    # Removed by the DB-V2 XAI redesign; its presence would mean a stale E.4 contract.
    assert 'v2_xai_comparison_guard' not in CONTRACT['functions']


def test_exact_catalog_passes_with_only_selects():
    catalog = Catalog()
    assert require_v2_capabilities(catalog) is None
    assert len(catalog.statements) == 5


def test_v2_baseline_plus_exact_contract_passes_full_guard():
    catalog = Catalog()
    with patch('src.malaria_dl.execution.schema.execute',
               side_effect=[Result(True), Result(['pg_v2_baseline']), Result({'event_guard': True})]):
        assert require_e10_schema(catalog)['revision'] == 'pg_v2_baseline'
    assert len(catalog.statements) == 5


@pytest.mark.parametrize('versions', [['pg_v2_baseline_next'], [''], [], ['pg_v2_baseline', 'pg_v2_baseline']])
def test_unknown_empty_or_multiple_revisions_are_rejected_before_contract(versions):
    catalog = Catalog()
    with patch('src.malaria_dl.execution.schema.execute', side_effect=[Result(True), Result(versions)]):
        with pytest.raises(E10SchemaNotReady, match='unsupported_alembic_revision'):
            require_e10_schema(catalog)
    assert catalog.statements == []


def test_wrong_function_hash_is_rejected():
    name = sorted(CONTRACT['functions'])[0]
    reject(Catalog(functions={**CONTRACT['functions'], name: '0' * 32}), 'v2_function_contract')


def test_missing_function_is_rejected():
    functions = dict(CONTRACT['functions'])
    functions.pop('v2_immutable')
    reject(Catalog(functions=functions), 'v2_function_contract')


def test_unexpected_function_is_rejected():
    reject(Catalog(functions={**CONTRACT['functions'], 'v2_xai_comparison_guard': '0' * 32}), 'v2_function_contract')


def test_missing_trigger_is_rejected():
    reject(Catalog(triggers=CONTRACT['triggers'][1:]), 'v2_trigger_contract')


def test_altered_trigger_is_rejected():
    triggers = copy.deepcopy(CONTRACT['triggers'])
    triggers[0]['tgenabled'] = 'D'
    reject(Catalog(triggers=triggers), 'v2_trigger_contract')


def test_altered_evaluation_constraint_is_rejected():
    constraints = copy.deepcopy(CONTRACT['evaluation_constraints'])
    constraints[0]['convalidated'] = not constraints[0]['convalidated']
    reject(Catalog(evaluation_constraints=constraints), 'v2_evaluation_contract')


def test_missing_calibration_index_is_rejected():
    reject(Catalog(calibration_indexes=CONTRACT['calibration_indexes'][:1]), 'v2_calibration_uniqueness_contract')


def test_shadow_schema_is_rejected():
    reject(Catalog(schema='capstone_test_shadow'), 'v2_public_schema_required')


def test_catalog_error_fails_closed():
    catalog = Catalog()
    catalog.execute = lambda *a: (_ for _ in ()).throw(OperationalError('SELECT', {}, Exception()))
    with patch('src.malaria_dl.execution.schema.execute',
               side_effect=[Result(True), Result(['pg_v2_baseline']), Result({'event_guard': True})]):
        with pytest.raises(E10SchemaNotReady, match='schema_inspection_failed'):
            require_e10_schema(catalog)


def _incomplete(contract):
    for key in ('revision', 'functions', 'triggers', 'evaluation_constraints', 'calibration_indexes'):
        missing = dict(contract)
        missing.pop(key)
        yield missing
        if key != 'revision':
            yield {**contract, key: type(contract[key])()}
    yield {**contract, 'revision': '20260922_01'}
    yield {**contract, 'functions': list(contract['functions'])}


@pytest.mark.parametrize('broken', list(_incomplete(CONTRACT)) + ['{not json', None])
def test_incomplete_or_foreign_contract_is_rejected_before_catalog(tmp_path, broken):
    path = tmp_path / 'v2_runtime_contract.json'
    if broken is not None:
        path.write_text(broken if isinstance(broken, str) else json.dumps(broken))
    catalog = Catalog()
    with patch.object(schema_contract, 'CONTRACT_PATH', path):
        with pytest.raises(E10SchemaNotReady, match='v2_contract_incomplete'):
            load_contract()
        reject(catalog, 'v2_contract_incomplete')
    assert catalog.statements == []
