from app.services.scientific_results import metric_dto


def test_undefined_metrics_are_not_zero_and_counts_keep_orientation():
    row = dict(tn=2, fp=0, fn=0, tp=0, recall_parasitized=None,
               specificity=1, precision_parasitized=None, f1_parasitized=None,
               f2_parasitized=None, roc_auc_parasitized=None, pr_auc_parasitized=None,
               accuracy=1, balanced_accuracy=None, auc_unavailability_reason='single_class')
    result = metric_dto(row)
    assert result['metrics']['recall'] == {'value': None, 'undefined_reason': 'zero_denominator'}
    assert result['metrics']['roc_auc'] == {'value': None, 'undefined_reason': 'single_class'}
    assert result['metrics']['specificity'] == {'value': 1, 'undefined_reason': None}
    assert [result[k] for k in ('tn', 'fp', 'fn', 'tp')] == [2, 0, 0, 0]
    assert result['confusion_matrix_orientation'] == {
        'rows': ['uninfected', 'parasitized'], 'columns': ['uninfected', 'parasitized']}


def test_defined_zero_is_preserved():
    row = {k: 0 for k in ('recall_parasitized', 'specificity', 'precision_parasitized',
                         'f1_parasitized', 'f2_parasitized', 'roc_auc_parasitized',
                         'pr_auc_parasitized', 'balanced_accuracy', 'accuracy')}
    row['auc_unavailability_reason'] = None
    assert all(m == {'value': 0, 'undefined_reason': None} for m in metric_dto(row)['metrics'].values())
