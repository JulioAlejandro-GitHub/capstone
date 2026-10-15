"""SQL extraction parity: one existing connection, exact query and parameters."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from src.malaria_dl.data.sample_repository import select_dataset_sample_ids
from src.malaria_dl.assessment.service import select_explanation_samples
from src.malaria_dl.assessment.contracts import AssessmentError

DATASET = 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
SAMPLE = '000f6007-9330-5085-972a-247631c541c6'
OLD_SQL = '''SELECT source_record_id FROM dataset_split_assignments
WHERE dataset_version_id=CAST(:dataset AS uuid) AND split_name=:split
AND (CAST(:sample AS uuid) IS NULL OR source_record_id=CAST(:sample AS uuid))
ORDER BY source_record_id LIMIT :limit'''


@pytest.mark.parametrize('sample,limit,returned', [(None, 1, [UUID(SAMPLE)]), (SAMPLE, None, [UUID(SAMPLE)]),
    (None, 5, [UUID(int=1), UUID(int=2)]), (None, None, []), (SAMPLE, 1, [])])
def test_selection_preserves_sql_order_filters_limits_and_output(sample, limit, returned):
    connection = Mock()
    connection.execute.return_value.scalars.return_value = returned
    result = select_dataset_sample_ids(connection, DATASET, 'val', sample, limit)
    assert result == returned
    statement, params = connection.execute.call_args.args
    assert ' '.join(str(statement).split()) == ' '.join(OLD_SQL.split())
    assert params == dict(dataset=DATASET, split='val', sample=sample, limit=limit)
    connection.begin.assert_not_called()
    connection.commit.assert_not_called()


@pytest.mark.parametrize('maximum,sample,ids', [(1, None, [SAMPLE]), ('all', SAMPLE, [SAMPLE]),
    (5, None, [SAMPLE]), ('all', None, [SAMPLE]), (1, None, [])])
def test_explain_behavior_unchanged(maximum, sample, ids):
    connection = Mock()
    connection.execute.return_value.scalars.return_value = ids
    calls = []
    @contextmanager
    def transaction(readonly=False):
        calls.append(readonly)
        yield connection
    repository = SimpleNamespace(transaction=transaction)
    samples = [{'sample_id': SAMPLE, 'split': 'val'}]
    if not ids:
        with pytest.raises(AssessmentError, match='EXPLANATION_SAMPLE_SELECTION_EMPTY'):
            select_explanation_samples(repository, {'dataset_version_id': DATASET}, 'val', samples, maximum, sample)
        return
    selected, metadata = select_explanation_samples(repository, {'dataset_version_id': DATASET}, 'val', samples, maximum, sample)
    assert selected == samples
    assert metadata['sample_ids'] == [SAMPLE]
    assert metadata['requested_sample_id'] == sample
    assert metadata['requested_max_images'] == maximum
    assert calls == ([] if maximum == 'all' and sample is None else [True])
