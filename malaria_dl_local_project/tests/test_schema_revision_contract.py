"""Exact revision recognition independent of any database settings."""
from unittest.mock import patch

import pytest
from src.malaria_dl.execution.schema import require_e10_schema, E10SchemaNotReady


class Result:
    def __init__(self, value): self.value = value
    def scalar_one(self): return self.value
    def scalars(self): return self
    def mappings(self): return self
    def all(self): return self.value
    def one(self): return self.value


@pytest.mark.parametrize('revision', ['20260922_01', 'pg_v2_baseline'])
def test_only_explicit_revisions_are_recognized(revision):
    with patch('src.malaria_dl.execution.schema.execute', side_effect=[Result(True), Result([revision]), Result({'event_guard': True})]), \
         patch('src.malaria_dl.persistence.schema_contract.require_v2_capabilities') as v2:
        assert require_e10_schema(object())['revision'] == revision
        assert v2.call_count == int(revision == 'pg_v2_baseline')


@pytest.mark.parametrize('versions', [[], ['future'], ['pg_v2_baseline', '20260922_01']])
def test_unknown_empty_and_multiple_heads_fail_closed_before_capabilities(versions):
    with patch('src.malaria_dl.execution.schema.execute', side_effect=[Result(True), Result(versions)]) as execute:
        with pytest.raises(E10SchemaNotReady, match='unsupported_alembic_revision'):
            require_e10_schema(object())
        assert execute.call_count == 2
