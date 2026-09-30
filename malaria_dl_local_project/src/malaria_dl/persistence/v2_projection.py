"""Atomic v2 projections; historical event bytes are never rewritten.

The evaluation provenance must be supplied explicitly in the run's immutable
execution snapshot (e10_v2_evaluation_context_v1). Missing evidence is an error.
The database enforces checkpoint, calibration, event and dataset relationships.
"""
import hashlib
import json
import re
from uuid import uuid4

from sqlalchemy import text

from ..campaigns.contracts import canonical
from ..results.errors import ResultPersistenceError


def _insert(connection, table, row):
    # Callers below construct every identifier; values always remain parameters.
    columns = ','.join(row)
    values = ','.join(f'CAST(:{k} AS jsonb)' if isinstance(v, (dict, list)) else f':{k}'
                      for k, v in row.items())
    connection.execute(text(f'INSERT INTO {table} ({columns}) VALUES ({values})'),
                       {k: json.dumps(v, allow_nan=False) if isinstance(v, (dict, list)) else v
                        for k, v in row.items()})


def project_configuration(connection, run_id, config):
    """Only the effective configuration; no resolver/defaults and no invention."""
    try:
        r = config['resolved']
        ex, model, opt, selection = (r[k] for k in ('execution', 'model', 'optimizer', 'selection'))
        raw = canonical(r)
        row = dict(run_id=run_id, architecture=config['model_id'], adapter_version=config['adapter_version'],
                   optimizer=opt['name'], learning_rate=opt['parameters']['learning_rate'],
                   fine_tune_learning_rate=opt['fine_tune_learning_rate'], random_seed=ex['seed'],
                   checkpoint_monitor=selection['monitor'], checkpoint_mode=selection['mode'],
                   early_stopping_monitor=selection['early_stopping_monitor'],
                   early_stopping_mode=selection['early_stopping_mode'], normalization=model['preprocessing'],
                   internal_preprocessing=r['input_contract']['internal']['mode'],
                   input_height=model['input_shape'][0], input_width=model['input_shape'][1],
                   input_channels=model['input_shape'][2], loss_function=r['recipe']['loss'],
                   calibration_enabled=ex['calibrate_threshold'], default_threshold=selection['threshold'],
                   clinical_target_recall=ex['target_recall'], canonical_configuration=raw,
                   configuration_hash=hashlib.sha256(raw.encode()).hexdigest(),
                   optimizer_extensions={k: v for k, v in opt['parameters'].items() if k != 'learning_rate'},
                   extension_configuration=r, provenance_snapshot=config)
        row.update({k: ex[k] for k in ('batch_size', 'max_epochs', 'fine_tune_epochs', 'early_stopping',
                                     'early_stopping_patience', 'early_stopping_min_delta', 'restore_best_weights')})
        row.update({k: model[k] for k in ('dropout', 'l2', 'weights', 'fine_tune_layers')})
    except (KeyError, TypeError, IndexError):
        raise ResultPersistenceError() from None
    _insert(connection, 'run_configurations', row)


def project_evaluation(connection, event, result):
    run = connection.execute(text('SELECT * FROM runs WHERE id=:run'), {'run': event.run_id}).mappings().one()
    context = run['execution_parameters'].get('e10_v2_evaluation_context_v1')
    required = {'checkpoint_artifact_id', 'protocol_version', 'protocol_hash', 'population_hash',
                'input_contract_hash', 'comparison_contract_hash', 'protocol_snapshot'}
    optional = {'model_version_id', 'calibration_id'}
    if (not isinstance(context, dict) or not required <= context.keys()
            or context.keys() - required - optional
            or any(context[k] is None for k in required)
            or not isinstance(context['protocol_snapshot'], dict)):
        raise ResultPersistenceError()
    for key in ('protocol_hash', 'population_hash', 'input_contract_hash', 'comparison_contract_hash'):
        if not isinstance(context[key], str) or re.fullmatch('[0-9a-f]{64}', context[key]) is None:
            raise ResultPersistenceError()
    evaluation = result.validation
    identity = uuid4()
    row = dict(context, id=identity, run_id=event.run_id, training_run_id=event.run_id,
               dataset_version_id=run['dataset_version_id'], split='val',
               evaluation_role='training_validation_final', purpose='development', subject_kind='single',
               source_kind='e10', source_record_key=str(event.event_id), source_record_phase=event.schema_version,
               source_event_id=event.event_id, event_kind='e10_event', event_phase=event.schema_version,
               event_key=str(event.event_id), threshold_used=evaluation.threshold.value,
               threshold_source=evaluation.threshold.source, created_at=event.occurred_at)
    _insert(connection, 'evaluations', row)
    cm, metrics = evaluation.confusion_matrix, evaluation.metrics
    _insert(connection, 'run_clinical_metrics', dict(
        evaluation_id=identity, run_id=event.run_id, split_name='val',
        tn=cm.tn, fp=cm.fp, fn=cm.fn, tp=cm.tp,
        roc_auc_parasitized=metrics.roc_auc, pr_auc_parasitized=metrics.pr_auc,
        auc_unavailability_reason='single_class' if metrics.roc_auc is None or metrics.pr_auc is None else None,
        metadata={'source_event_id': str(event.event_id), 'original_metric_definition': 'validation_evaluation_v1'},
    ))
