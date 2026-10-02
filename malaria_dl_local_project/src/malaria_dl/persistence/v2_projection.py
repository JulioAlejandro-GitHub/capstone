"""Atomic v2 projections; historical event bytes are never rewritten.

The evaluation provenance must be supplied explicitly in the run's immutable
execution snapshot (e10_v2_evaluation_context_v1). Missing evidence is an error.
The database enforces checkpoint, calibration, event and dataset relationships.
"""
import hashlib
import json
import re
from uuid import uuid5
import math

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


EVALUATION_CONTEXT_KEY = 'e10_v2_evaluation_context_v1'


def training_evaluation_context(*, checkpoint_artifact_id, protocol, dataset_version_id,
                                population, input_contract):
    """Producer side of e10_v2_evaluation_context_v1, from persisted evidence only.

    protocol: the campaign's frozen protocol (its own 'version').
    population: VAL sample paths actually predicted for the selected checkpoint.
    comparison_contract_hash is identical for every member of a campaign (same
    dataset, VAL population and protocol), so rows sharing it are comparable;
    input_contract_hash differs per architecture and stays outside it.
    """
    from ..campaigns.contracts import digest
    if not isinstance(protocol, dict) or not protocol.get('version') or not population:
        raise ResultPersistenceError()
    population_hash = digest({'dataset_version_id': str(dataset_version_id), 'split': 'val',
                              'samples': sorted(population)})
    protocol_hash = digest(protocol)
    return {
        'checkpoint_artifact_id': str(checkpoint_artifact_id),
        'protocol_version': str(protocol['version']),
        'protocol_hash': protocol_hash,
        'protocol_snapshot': protocol,
        'population_hash': population_hash,
        'input_contract_hash': digest(input_contract),
        'comparison_contract_hash': digest({
            'dataset_version_id': str(dataset_version_id), 'population_hash': population_hash,
            'protocol_hash': protocol_hash, 'metric_definition': 'binary_nullable_v2'}),
    }


def _evaluation_context(connection, event):
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
    return run, dict(context)


def _evaluation_row(run, context, event, role, threshold, source):
    return dict(context, id=uuid5(event.event_id, role), run_id=event.run_id,
               training_run_id=event.run_id, dataset_version_id=run['dataset_version_id'], split='val',
               evaluation_role=role, purpose='development', subject_kind='single', source_kind='e10',
               source_record_key=f'{event.event_id}:{role}', source_record_phase=event.schema_version,
               source_event_id=event.event_id, event_kind='e10_event', event_phase=event.schema_version,
               event_key=str(event.event_id), threshold_used=threshold, threshold_source=source,
               created_at=event.occurred_at)


def project_evaluation(connection, event, result):
    run, context = _evaluation_context(connection, event)
    evaluation = result.validation
    if evaluation.threshold.source == 'validation_calibration':
        match = connection.execute(text('''SELECT c.run_threshold_calibration_id FROM
            run_threshold_calibration c JOIN evaluations s ON s.id=c.selected_evaluation_id
            WHERE s.run_id=:run AND s.checkpoint_artifact_id=:checkpoint
              AND s.protocol_hash=:protocol AND s.population_hash=:population
              AND s.input_contract_hash=:input AND s.threshold_used=:threshold
              AND s.source_kind='e10' AND s.evaluation_role='calibration_selected' '''),
            dict(run=event.run_id, checkpoint=context['checkpoint_artifact_id'],
                 protocol=context['protocol_hash'], population=context['population_hash'],
                 input=context['input_contract_hash'], threshold=evaluation.threshold.value)).scalar_one()
        context['calibration_id'] = match
    row = _evaluation_row(run, context, event, 'training_validation_final',
                          evaluation.threshold.value, evaluation.threshold.source)
    identity = row['id']
    _insert(connection, 'evaluations', row)
    cm, metrics = evaluation.confusion_matrix, evaluation.metrics
    _insert(connection, 'run_clinical_metrics', dict(
        evaluation_id=identity, run_id=event.run_id, split_name='val',
        tn=cm.tn, fp=cm.fp, fn=cm.fn, tp=cm.tp,
        roc_auc_parasitized=metrics.roc_auc, pr_auc_parasitized=metrics.pr_auc,
        auc_unavailability_reason='single_class' if metrics.roc_auc is None or metrics.pr_auc is None else None,
        metadata={'source_event_id': str(event.event_id), 'original_metric_definition': 'validation_evaluation_v1'},
    ))


def project_calibration(connection, event):
    """Called inside ResultService's root ledger transaction, never commits itself.

    Consume the producer's existing canonical payload; no metrics or source
    labels are manufactured. SQL rechecks the pair against this same event.
    """
    run, context = _evaluation_context(connection, event)
    try:
        payload = event.to_dict()['payload']['result']
        calibration = payload['result']
        if (payload['split'] != 'val' or calibration['calibration_split'] != 'val'
                or calibration['threshold_source'] != 'validation_calibration'):
            raise ValueError()
        for key in ('threshold_selected', 'threshold_used', 'default_threshold', 'target_recall'):
            value = calibration[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError()
        if calibration['threshold_selected'] != calibration['threshold_used']:
            raise ValueError()
        metrics = [calibration['default_threshold_metrics'], calibration['selected_metrics']]
        for metric in metrics:
            if any(type(metric[k]) is not int or metric[k] < 0 for k in ('tn','fp','fn','tp')):
                raise ValueError()
            if sum(metric[k] for k in ('tn','fp','fn','tp')) <= 0:
                raise ValueError()
            for k in ('roc_auc_parasitized', 'pr_auc_parasitized'):
                v = metric[k]  # Absent is not equivalent to an evidenced NULL.
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1):
                    raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ResultPersistenceError() from None
    context.pop('calibration_id', None)
    calibration_id = uuid5(event.event_id, 'calibration')
    default = _evaluation_row(run, context, event, 'calibration_default',
                              calibration['default_threshold'], 'default')
    selected = _evaluation_row(run, context, event, 'calibration_selected',
                               calibration['threshold_selected'], 'validation_calibration')
    selected['calibration_id'] = calibration_id
    _insert(connection, 'evaluations', default)
    _insert(connection, 'run_threshold_calibration', dict(
        run_threshold_calibration_id=calibration_id, run_id=event.run_id,
        model_version_id=context.get('model_version_id'),
        default_evaluation_id=default['id'], selected_evaluation_id=selected['id'],
        default_threshold=calibration['default_threshold'], threshold_selected=calibration['threshold_selected'],
        target_recall=calibration['target_recall'], calibration_split='val',
        created_at=event.occurred_at))
    _insert(connection, 'evaluations', selected)
    for evaluation, metric in zip((default, selected), metrics, strict=True):
        single_class = metric['tp'] + metric['fn'] == 0 or metric['tn'] + metric['fp'] == 0
        unavailable = metric['roc_auc_parasitized'] is None or metric['pr_auc_parasitized'] is None
        _insert(connection, 'run_clinical_metrics', dict(
            evaluation_id=evaluation['id'], run_id=event.run_id, split_name='val',
            **{k: metric[k] for k in ('tn','fp','fn','tp','roc_auc_parasitized','pr_auc_parasitized')},
            auc_unavailability_reason=('single_class' if single_class else 'not_computed') if unavailable else None,
            metadata={'source_event_id': str(event.event_id)}))
