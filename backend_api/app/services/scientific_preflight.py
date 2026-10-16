"""Read-only preflight. No runtime, model loaders or scientific execution imports."""
from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from app.db import read_only_transaction
from app.repositories.artifacts import ArtifactReadRepository
from app.repositories.assessments import AssessmentReadRepository
from app.repositories.scientific_results import ScientificReadRepository
from app.schemas.scientific_preflight import PreflightRequest, PreflightResponse
from app.services.scientific_public import public_evidence
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError

STATES = ('COMPARABLE', 'COMPARABLE_CON_ADVERTENCIAS', 'NO_COMPARABLE', 'EVIDENCIA_INSUFICIENTE')
CONFIG_FIELDS = (
    'architecture', 'random_seed', 'normalization', 'internal_preprocessing',
    'optimizer', 'learning_rate', 'batch_size', 'loss_function',
    'checkpoint_monitor', 'checkpoint_mode', 'early_stopping',
    'max_epochs', 'fine_tune_epochs', 'fine_tune_learning_rate',
    'early_stopping_patience', 'early_stopping_monitor', 'early_stopping_mode',
    'restore_best_weights', 'dropout', 'l2', 'input_height', 'input_width', 'input_channels',
)
PROTOCOL_FIELDS = ('protocol', 'decision', 'metrics_definition', 'batch_size', 'model')
DEPENDENCIES = {
    'curves': ('A1', 'A4'),
    'metrics': ('A1', 'A2', 'A3', 'A5', 'A6'),
    'consensus': ('A2', 'A3', 'A5', 'A6'),
    'xai': ('A3', 'A5'), 'embeddings': ('A3', 'A5'),
    'pca': ('A3', 'A5'), 'umap': ('A3', 'A5'), 'cka': ('A3', 'A5'),
}


def known(value, refs=()):
    return {'state': 'known', 'value': jsonable_encoder(value), 'evidence_ids': list(refs)}


def unknown(reason, refs=()):
    return {'state': 'unknown', 'reason': reason, 'evidence_ids': list(refs)}


def verdict(state=None, errors=()):
    blocked = bool(errors) and state != 'NO_COMPARABLE'
    return {'evaluation_status': 'not_evaluated' if blocked else 'evaluated',
                'scientific_state': None if blocked else state, 'error_ids': list(dict.fromkeys(errors))}


def safe_configuration(config):
    """Allowlisted effective fields; free-form snapshots never become public payloads."""
    if not config:
        return {}
    result = {key: config.get(key) for key in CONFIG_FIELDS}
    # Preserve absence; do not infer augmentation from current runtime defaults.
    extension = config.get('extension_configuration') or {}
    execution = extension.get('execution') or {}
    augment = execution.get('no_augment')
    result['no_augment'] = augment if isinstance(augment, bool) else None
    result['augmentation'] = (extension.get('recipe') or {}).get('augmentation')
    result['checkpoint_policy'] = execution.get('checkpoint_policy')
    result['clinical_objective'] = (extension.get('selection') or {}).get('clinical_objective')
    result['optimizer_parameters'] = (extension.get('optimizer') or {}).get('parameters')
    return public_evidence(result)


class ScientificPreflightService:
    def __init__(self, scientific=None, assessments=None, artifacts=None, transaction=None):
        self.scientific = scientific or ScientificReadRepository()
        self.assessments = assessments or AssessmentReadRepository()
        self.artifacts = artifacts or ArtifactReadRepository()
        self.transaction = transaction or read_only_transaction

    def read(self, request: PreflightRequest, datasource: str, correlation_id: str) -> PreflightResponse:
        started = datetime.now(timezone.utc)
        evidence, errors, selections, checkpoints, populations = [], [], [], [], []
        rows = []
        findings = {d: [] for d in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6')}
        domain_errors = {d: [] for d in findings}
        all_ids = [str(s.training_run_id) for s in request.selections]
        selection_ids = [f'train:{i}' for i in all_ids]
        history_errors = []
        history_findings = []

        def finding(dim, code, kind, message, ids, refs=()):
            value = {'reason_id': f'{dim}:{code}:{len(findings[dim])}', 'code': code,
                         'kind': kind, 'message': message, 'condition': code,
                         'affected_selection_ids': list(ids), 'evidence_ids': list(refs)}
            findings[dim].append(value)
            return value

        def query(connection, domain, sid, operation, callback):
            try:
                with connection.begin_nested():
                    value = callback()
            except SQLAlchemyError:
                eid = f'query:{len(errors)}'
                errors.append({'error_id': eid, 'state': 'ERROR_DE_CONSULTA',
                    'code': 'EVIDENCE_QUERY_FAILED', 'message': 'No se pudo consultar esta evidencia.',
                    'operation': operation, 'scope_ids': [domain], 'selection_ids': [sid],
                    'correlation_id': correlation_id, 'retryable': True})
                (history_errors if domain == 'history' else domain_errors[domain]).append(eid)
                observation = {'state': 'query_error', 'error_ids': [eid]}
                value = None
            else:
                observation = known(value) if value is not None else unknown('Registro ausente.')
            ref = f'evidence:{len(evidence)}'
            # Values are projected below; never return raw identities/configurations/errors.
            evidence.append({'evidence_id': ref, 'source': domain, 'operation': operation,
                'record_keys': {'training_run_id': sid.removeprefix('train:')},
                'field': None, 'selection_ids': [sid], 'observed_at': started,
                'verification': 'operational', 'value': observation if value is None else known(True)})
            return value, ref, observation.get('error_ids', [])

        try:
            with self.transaction(datasource, repeatable_read=True) as connection:
                for selected, sid in zip(request.selections, selection_ids):
                    train, train_ref, train_errors = query(connection, 'A1', sid,
                        'ScientificReadRepository.preflight_training',
                        lambda selected=selected: self.scientific.preflight_training(connection, selected.training_run_id))
                    if not train and not train_errors:
                        raise HTTPException(404, 'TRAIN no encontrado.')
                    if train and train['run_type'] != 'training':
                        raise HTTPException(422, 'La selección debe identificar un TRAIN.')
                    if train and train.get('dataset'):
                        evidence[-1]['value'] = known(train['dataset'], [train_ref])
                        governance, gref, _ = query(connection, 'A2', sid,
                            'ScientificReadRepository.comparison_governance',
                            lambda: self.scientific.comparison_governance(connection, selected.training_run_id))
                        if governance:
                            evidence[-1]['value'] = known(public_evidence(governance), [gref])
                            if any(check['status'] != 'PASS' for check in governance['checks']):
                                finding('A2', 'GOVERNANCE_CHECK_WARNING', 'warning', 'El split oficial tiene controles sin PASS.', [sid], [gref])
                    config, config_ref, config_errors = query(connection, 'A4', sid,
                        'ScientificReadRepository.preflight_configuration',
                        lambda selected=selected: self.scientific.preflight_configuration(connection, selected.training_run_id))
                    config = safe_configuration(config)
                    evidence[-1]['value'] = known(config, [config_ref]) if config else evidence[-1]['value']
                    history, history_ref, herrors = query(connection, 'history', sid,
                        'ScientificReadRepository.preflight_history',
                        lambda selected=selected: self.scientific.preflight_history(connection, selected.training_run_id))
                    if history and not herrors and not config_errors:
                        config['executed_epochs'] = history['rows']
                        next(e for e in evidence if e['evidence_id'] == config_ref)['value'] = known(config, [config_ref])
                    row = {'sid': sid, 'train': train, 'config': config, 'history': history,
                               'history_ref': history_ref, 'history_errors': herrors,
                               'attempt': None, 'identity': {}, 'evaluation_errors': [], 'refs': [train_ref, config_ref]}
                    rows.append(row)
                    if train_errors:
                        # Identity failure prevents dependent claims, even if ancillary reads succeed.
                        for dim in ('A2', 'A3', 'A5', 'A6'):
                            domain_errors[dim].extend(train_errors)
                    if train and (not train.get('dataset_version_id') or not train['dataset_registered']):
                        finding('A1', 'DATASET_UNATTRIBUTED', 'missing',
                                'Versión de dataset sin relación registrada.', [sid], [train_ref])
                    required = (*CONFIG_FIELDS, 'no_augment')
                    missing = [key for key in required if config.get(key) is None]
                    if missing:
                        finding('A4', 'CONFIGURATION_INCOMPLETE', 'missing',
                                'Configuración no acreditada: ' + ', '.join(missing), [sid], [config_ref])
                    ev = selected.evaluation
                    effective = unknown('Evaluación no seleccionada; no existe política automática.')
                    if ev is not None:
                        if ev.source == 'assessment':
                            attempt_id = ev.attempt_id
                        else:
                            historical, href, herr = query(connection, 'A6', sid,
                                'ScientificReadRepository.evaluation',
                                lambda ev=ev: self.scientific.evaluation(connection, ev.evaluation_id))
                            row['evaluation_errors'].extend(herr)
                            if historical is None and not herr:
                                raise HTTPException(404, 'Evaluación no encontrada.')
                            if historical:
                                if str(historical['training_run_id']) != str(selected.training_run_id):
                                    raise HTTPException(404, 'Evaluación no encontrada para este TRAIN.')
                                row['historical'] = historical
                                effective = known({'source': 'evaluations', 'evaluation_id': ev.evaluation_id,
                                    'execution_run_id': historical['run_id'],
                                    'source_assessment_attempt_id': historical['source_assessment_attempt_id']}, [href])
                            attempt_id = historical.get('source_assessment_attempt_id') if historical else None
                            if historical and not attempt_id:
                                from app.services.scientific_report import ScientificReportService
                                report = ScientificReportService(repository=self.scientific)
                                metric, mref, merr = query(connection, 'A6', sid,
                                    'ScientificReadRepository.comparison_metrics',
                                    lambda: report.metrics(connection, selected))
                                row['evaluation_errors'].extend(merr)
                                row['historical_metric'] = metric
                                if historical.get('split') == 'val':
                                    finding('A6', 'DEVELOPMENT_VALIDATION', 'warning',
                                        'VALIDATION final de desarrollo; no equivale a TEST independiente.', [sid], [href])
                                if metric and metric['state'] == 'available':
                                    evidence[-1]['value'] = known({'split': historical['split'],
                                        'evaluation_role': historical['evaluation_role'], 'purpose': historical['purpose'],
                                        'threshold': historical['threshold_used'], 'sample_count': metric['clinical']['sample_count'],
                                        'metric_definition': historical['metric_definition']}, [mref])
                                    population, pref, perr = query(connection, 'A3', sid,
                                        'ScientificReadRepository.comparison_predictions',
                                        lambda: report.prediction_population(connection, selected, metric))
                                    if population:
                                        row['historical_population'], row['population_issues'] = population
                                    else:
                                        row['population_issues'] = ['No se pudo consultar población.']
                                elif not merr:
                                    finding('A6', 'HISTORICAL_RESULTS_UNATTRIBUTED', 'missing',
                                        'Métricas históricas ausentes o con atribución contradictoria.', [sid], [mref])
                        if attempt_id:
                            attempt, aref, aerr = query(connection, 'A6', sid,
                                'AssessmentReadRepository.preflight_detail',
                                lambda attempt_id=attempt_id: self.assessments.preflight_detail(connection, UUID(str(attempt_id))))
                            row['evaluation_errors'].extend(aerr)
                            row['refs'].append(aref)
                            if attempt is None and not aerr:
                                raise HTTPException(404, 'Intento no encontrado.')
                            if attempt:
                                if str(attempt['training_run_id']) != str(selected.training_run_id):
                                    raise HTTPException(404, 'Intento no encontrado para este TRAIN.')
                                if ev.source == 'assessment' and str(attempt['identity_id']) != str(ev.identity_id):
                                    raise HTTPException(422, 'Identidad e intento no corresponden.')
                                row['attempt'] = attempt
                                row['identity'] = attempt['identity']
                                aid = attempt['identity']
                                # Public semantic projection, not arbitrary snapshots or locators.
                                evidence[-1]['record_keys'].update(
                                    attempt_id=str(attempt['attempt_id']), identity_id=str(attempt['identity_id']))
                                evidence[-1]['field'] = 'identity, state, verification.metrics'
                                evidence[-1]['value'] = known(public_evidence({
                                    'identity_id': str(attempt['identity_id']), 'attempt_id': str(attempt['attempt_id']),
                                    'identity_hash': attempt['identity_hash'], 'attempt_state': attempt['state'],
                                    'split': aid.get('split'), 'metrics_definition': aid.get('metrics_definition'),
                                    'batch_size': aid.get('batch_size'),
                                    'protocol': {k: (aid.get('protocol') or {}).get(k) for k in
                                              ('version', 'splits', 'purposes', 'allowed_numeric_thresholds')},
                                    'decision': {k: (aid.get('decision') or {}).get(k) for k in
                                              ('effective', 'score_domain', 'positive_class', 'comparison')},
                                }), [aref])
                                if ev.source == 'assessment':
                                    effective = known({'source': 'assessment', 'identity_id': attempt['identity_id'],
                                        'attempt_id': attempt['attempt_id'], 'identity_hash': attempt['identity_hash'],
                                        'attempt_state': attempt['state']}, [aref])
                                if attempt['kind'] != 'evaluate':
                                    finding('A6', 'NOT_EVALUATE', 'incompatibility',
                                        'El intento no corresponde a una evaluación.', [sid], [aref])
                    else:
                        candidates, cref, cerr = query(connection, 'A6', sid,
                            'AssessmentReadRepository.preflight_candidates',
                            lambda selected=selected: self.assessments.preflight_candidates(connection, selected.training_run_id))
                        row['evaluation_errors'].extend(cerr)
                        code = 'EVALUATION_SELECTION_REQUIRED'
                        if candidates and (candidates['attempts'] > 1 or candidates['evaluations'] > 1):
                            code = 'AMBIGUOUS_EVALUATION'
                        finding('A6', code, 'missing', 'Seleccione evaluación e intento explícitos.', [sid], [cref])
                    identity = row['identity']
                    historical = row.get('historical') or {}
                    actual_split = identity.get('split') or historical.get('split')
                    if identity and historical:
                        pairs = (
                            ('split', identity.get('split'), historical.get('split')),
                            ('checkpoint', (identity.get('model') or {}).get('checkpoint_artifact_id'), historical.get('checkpoint_artifact_id')),
                            ('dataset', (identity.get('dataset') or {}).get('dataset_version_id'), historical.get('dataset_version_id')),
                        )
                        for field, attributed, recorded in pairs:
                            if attributed is not None and recorded is not None and str(attributed) != str(recorded):
                                finding('A6', 'HISTORICAL_LINK_CONFLICT_' + field.upper(), 'incompatibility',
                                    'La evaluación y su intento vinculado contienen referencias contradictorias.', [sid])
                        if historical.get('metric_definition') and identity.get('metrics_definition') != historical['metric_definition']:
                            finding('A6', 'HISTORICAL_METRIC_DEFINITION_CONFLICT', 'incompatibility',
                                'La definición histórica no coincide con el intento vinculado.', [sid])
                    if actual_split not in ('train', 'val', 'test'):
                        actual_split = None
                    if selected.split and actual_split and selected.split != actual_split:
                        finding('A2', 'REQUESTED_SPLIT_MISMATCH', 'incompatibility',
                                'El split solicitado contradice la evaluación seleccionada.', [sid], row['refs'])
                    if not actual_split:
                        finding('A2', 'SPLIT_UNKNOWN', 'missing', 'Split efectivo no acreditado.', [sid])
                    dataset = (identity.get('dataset') or {}).get('dataset_version_id') or historical.get('dataset_version_id')
                    if dataset and train and str(dataset) != str(train.get('dataset_version_id')):
                        finding('A1', 'EVALUATION_DATASET_DIFFERS', 'warning',
                            'La evaluación usa otra versión de dataset; se verifica su población separadamente.', [sid])
                    model = identity.get('model') or {}
                    if model.get('training_run_id') and str(model['training_run_id']) != str(selected.training_run_id):
                        finding('A5', 'MODEL_TRAIN_LINEAGE_CONFLICT', 'incompatibility',
                                'El modelo del intento declara otro TRAIN de origen.', [sid])
                    checkpoint_id = model.get('checkpoint_artifact_id') or historical.get('checkpoint_artifact_id')
                    if selected.checkpoint_artifact_id and checkpoint_id and str(selected.checkpoint_artifact_id) != str(checkpoint_id):
                        finding('A5', 'CHECKPOINT_SELECTION_CONFLICT', 'incompatibility',
                            'Checkpoint solicitado distinto del atribuido a la evaluación.', [sid])
                    checkpoint_id = checkpoint_id or selected.checkpoint_artifact_id
                    if checkpoint_id:
                        artifact, artref, arterr = query(connection, 'A5', sid, 'ArtifactReadRepository.get',
                            lambda checkpoint_id=checkpoint_id: self.artifacts.get(datasource, str(checkpoint_id), 'artifacts', connection=connection))
                        lineage = bool(artifact and str(artifact['training_run_id']) == str(selected.training_run_id))
                        obs = {'state': 'query_error', 'error_ids': arterr} if arterr else known(lineage, [artref])
                        checkpoints.append({'selection_id': sid, 'artifact_id': checkpoint_id,
                            'registered': {'state': 'query_error', 'error_ids': arterr} if arterr else known(artifact is not None, [artref]),
                            'lineage': obs, 'availability': 'not_checked', 'integrity': 'not_checked',
                            'checked_at': None, 'evidence_ids': [artref], 'error_ids': arterr})
                        if artifact and not lineage:
                            finding('A5', 'CHECKPOINT_LINEAGE_CONFLICT', 'incompatibility',
                                'El checkpoint está registrado para otro TRAIN.', [sid], [artref])
                        elif not artifact and not arterr:
                            finding('A5', 'CHECKPOINT_UNREGISTERED', 'missing',
                                'Checkpoint sin registro recuperable.', [sid], [artref])
                    else:
                        finding('A5', 'CHECKPOINT_UNKNOWN', 'missing', 'Checkpoint no atribuido.', [sid])
                    if identity:
                        decision = identity.get('decision') or {}
                        protocol = identity.get('protocol') or {}
                        if (any(identity.get(k) is None for k in PROTOCOL_FIELDS)
                                or model.get('input_contract') is None
                                or any(decision.get(k) is None for k in
                                       ('effective', 'score_domain', 'positive_class', 'comparison'))
                                or 'calibrator' not in decision or not protocol.get('version')):
                            finding('A6', 'PROTOCOL_INCOMPLETE', 'missing',
                                    'Protocolo, decisión, definición o contrato de entrada incompletos.', [sid])
                        if not (row['attempt'].get('verification') or {}).get('metrics'):
                            finding('A6', 'RESULTS_NOT_OBSERVED', 'missing',
                                    'No hay métricas observadas para el intento exacto.', [sid])
                        if row['attempt']['state'] != 'verified':
                            finding('A6', 'ATTEMPT_NOT_VERIFIED', 'missing',
                                    'El intento no acredita resultados terminales verificados.', [sid])
                    elif ev is not None and not row.get('historical_metric'):
                        finding('A6', 'PROTOCOL_UNATTRIBUTED', 'missing',
                                'No se recuperó protocolo completo con resultados atribuibles.', [sid])
                    if row.get('historical_metric') and row['historical_metric'].get('checkpoint'):
                        evidence.append({'evidence_id': f'evidence:{len(evidence)}', 'source': 'A5',
                            'operation': 'ScientificReadRepository.comparison_checkpoint',
                            'record_keys': {'training_run_id': str(selected.training_run_id)}, 'field': 'selected_checkpoint',
                            'selection_ids': [sid], 'observed_at': started, 'verification': 'operational',
                            'value': known(row['historical_metric']['checkpoint'])})
                    if row['evaluation_errors']:
                        effective = {'state': 'query_error', 'error_ids': row['evaluation_errors']}
                        for dim in ('A2', 'A3', 'A5'):
                            domain_errors[dim].extend(row['evaluation_errors'])
                    row['split'] = actual_split
                    selections.append({'selection_id': sid, 'training_run_id': selected.training_run_id,
                        'dataset_version_id': {'state': 'query_error', 'error_ids': train_errors} if train_errors else
                            known(train['dataset_version_id'], [train_ref]) if train and train.get('dataset_version_id') else unknown('Dataset ausente.'),
                        'evaluation': effective, 'split': known(actual_split) if actual_split else unknown('Split no acreditado.'),
                        'checkpoint': known(checkpoint_id) if checkpoint_id else unknown('Checkpoint no atribuido.'),
                        'selection_reason': 'Selección explícita del cliente.' if ev else 'Sin selección automática.'})

                attempt_rows = [r for r in rows if r['attempt'] and r['attempt']['kind'] == 'evaluate']
                if len(attempt_rows) == len(rows):
                    coverage, pref, perr = query(connection, 'A3', selection_ids[0],
                        'AssessmentReadRepository.preflight_population',
                        lambda: self.assessments.preflight_population(connection, [r['attempt']['attempt_id'] for r in rows]))
                    evidence[-1]['selection_ids'] = selection_ids
                    evidence[-1]['record_keys'] = {
                        r['sid']: str(r['attempt']['attempt_id']) for r in rows}
                    for error in errors:
                        if error['error_id'] in perr:
                            error['selection_ids'] = selection_ids
                    if coverage is not None:
                        populations.append(self._population(coverage, rows, pref, finding))
                elif all(r.get('historical_population') is not None for r in rows):
                    from app.services.scientific_report import population_coverage
                    population = population_coverage([r['historical_population'] for r in rows])
                    issues = [issue for r in rows for issue in r.get('population_issues', [])]
                    complete = not issues and not population['label_conflicts'] and population['common_count'] > 0
                    if issues or population.get('label_conflicts'):
                        finding('A3', 'HISTORICAL_POPULATION_CONFLICT', 'incompatibility',
                            '; '.join(issues) or 'Etiquetas contradictorias.', selection_ids)
                    elif not complete:
                        finding('A3', 'HISTORICAL_POPULATION_INCOMPLETE', 'missing', 'Población común no acreditada.', selection_ids)
                    members = []
                    for r, coverage in zip(rows, population['coverage']):
                        n, common = coverage['population'], coverage['common']
                        if n != common:
                            finding('A3', 'PARTIAL_INTERSECTION', 'warning', 'Comparación limitada a la intersección.', [r['sid']])
                        members.append(dict(selection_id=r['sid'], expected_unique=known(r['historical_metric']['clinical']['sample_count']),
                            retrieved_rows=known(n), retrieved_unique=known(n), duplicate_count=known(0) if not issues else unknown('Revisar conflictos.'),
                            label_conflict_count=known(population['label_conflicts']), missing_count=known(coverage['missing']),
                            exclusive_count=known(coverage['exclusive']), numerator=known(common), denominator=known(n),
                            ratio=known(coverage['ratio']), evidence_ids=[]))
                    populations.append(dict(population_id='selected-training-validation', scope_id='A3:requested',
                        alignment_key=known('train_execution_records.payload.samples.sample'), complete=known(complete),
                        intersection_unique=known(population['common_count']), per_selection=members,
                        identity_references=[str(r['historical']['id']) for r in rows],
                        subset_rule='Intersección por sample y etiqueta; no acredita identidad binaria ni consumo TRAIN.'))
                else:
                    finding('A3', 'POPULATION_UNATTRIBUTED', 'missing',
                        'No todos los participantes tienen un intento EVALUATE exacto con población verificable.', selection_ids)
        except SQLAlchemyError:
            # Opening/losing the snapshot is technical, never an empty scientific success.
            raise HTTPException(503, 'No se pudo establecer la lectura consistente del Preflight.') from None

        if populations and populations[0]['complete'].get('value') is True:
            if any(f['code'] == 'PARTIAL_INTERSECTION' for f in findings['A3']):
                finding('A2', 'SPLIT_POPULATIONS_DIFFER', 'warning',
                        'Splits gobernados con poblaciones distintas; el nombre no acredita igualdad.',
                        selection_ids)
        elif not domain_errors['A3']:
            finding('A2', 'SPLIT_MEMBERSHIP_UNVERIFIED', 'missing',
                    'El nombre de split no acredita su pertenencia poblacional.', selection_ids)
        else:
            domain_errors['A2'].extend(domain_errors['A3'])
        # Independent conditions are preserved, including missing + incompatible.
        self._differences(rows, finding)
        dimensions = []
        analyses = []
        ids = [s.training_run_id for s in request.selections]

        def scope(name, population, question):
            return {'scope_id': name, 'requested_training_run_ids': ids,
                'participating_training_run_ids': [r['train']['id'] for r in rows if r['train']],
                'selection_ids': selection_ids, 'population': population, 'question': question}

        def parts(items):
            incompatible = [f for f in items if f['kind'] == 'incompatibility']
            missing = [f for f in items if f['kind'] == 'missing']
            if incompatible and missing:
                return [('incompatibilities', 'NO_COMPARABLE', incompatible),
                        ('missing_evidence', 'EVIDENCIA_INSUFICIENTE', [f for f in items if f['kind'] != 'incompatibility'])]
            return [('requested', 'NO_COMPARABLE' if incompatible else 'EVIDENCIA_INSUFICIENTE' if missing else
                     'COMPARABLE_CON_ADVERTENCIAS' if items else 'COMPARABLE', items)]

        for dim, items in findings.items():
            for suffix, state, subset in parts(items):
                dimensions.append({'dimension': dim, 'scope': scope(f'{dim}:{suffix}', 'original', suffix),
                    'verdict': verdict(state, domain_errors[dim]), 'evidence_ids': [e['evidence_id'] for e in evidence if e['source'] == dim],
                    'findings': subset})
        for module, dependencies in DEPENDENCIES.items():
            items = [f for d in dependencies for f in findings[d]]
            module_errors = list(dict.fromkeys(e for d in dependencies for e in domain_errors[d]))
            if module == 'curves':
                module_errors += history_errors
                # Configuration omissions limit descriptive curves; they do not erase history.
                items = [{**f, 'kind': 'warning'} if f['code'] == 'CONFIGURATION_INCOMPLETE' else f for f in items]
                for r in rows:
                    h = r['history']
                    if not h or not h['rows'] or h['unknown_axes'] or h['rows'] != h['unique_epochs'] or not r['config'].get('loss_function'):
                        history_findings.append({'reason_id': f"curves:history:{r['sid']}",
                            'code': 'CURVE_SEMANTICS_INSUFFICIENT', 'kind': 'missing',
                            'message': 'Historia, eje o definición de pérdida no acreditados.',
                            'condition': 'persisted_history_and_loss_definition',
                            'affected_selection_ids': [r['sid']], 'evidence_ids': [r['history_ref']]})
                items += history_findings
            if module == 'metrics':
                items = [{**f, 'reason_id': 'metrics:' + f['reason_id'],
                          'kind': 'incompatibility', 'code': 'ORIGINAL_POPULATIONS_DIFFER',
                          'message': 'Las métricas originales pertenecen a poblaciones distintas; no se recalculan.'}
                         if f['code'] == 'PARTIAL_INTERSECTION' else f for f in items]
            if module in ('xai', 'embeddings', 'pca', 'umap', 'cka'):
                items.append({'reason_id': f'{module}:methodology', 'code': 'METHODOLOGY_NOT_VERIFIED',
                    'kind': 'missing', 'message': 'Se requiere selección y evidencia metodológica específica del módulo.',
                    'condition': 'P5', 'affected_selection_ids': selection_ids, 'evidence_ids': []})
            if len(rows) < 2:
                items.append({'reason_id': f'{module}:participants', 'code': 'COMPARISON_REQUIRES_PARTICIPANTS',
                    'kind': 'missing', 'message': 'Se necesitan al menos dos TRAIN para comparación conjunta.',
                    'condition': 'participants', 'affected_selection_ids': selection_ids, 'evidence_ids': []})
            for suffix, state, subset in parts(items):
                population = 'intersection' if module == 'consensus' else 'original'
                analyses.append({'analysis_id': f'{module}:{suffix}', 'module_id': module,
                    'scope': scope(f'{module}:{suffix}', population, f'{module}: {suffix}'),
                    'verdict': verdict(state, module_errors), 'dimension_refs': [d['scope']['scope_id'] for d in dimensions if d['dimension'] in dependencies],
                    'evidence_ids': [e['evidence_id'] for e in evidence if e['source'] in dependencies],
                    'findings': subset, 'individual_data': self._individual(module, rows),
                    'interpretation_limits': ['Las métricas originales no se recalculan sobre la intersección.',
                        'Disponibilidad física e integridad de checkpoints no comprobadas.']})
        for error in errors:
            error['scope_ids'] = [
                item['scope']['scope_id'] for item in [*dimensions, *analyses]
                if error['error_id'] in item['verdict']['error_ids']]
        counts = Counter(a['verdict']['scientific_state'] for a in analyses)
        completed = datetime.now(timezone.utc)
        return PreflightResponse.model_validate({'contract_version': 'scc_pre_1',
            'generated_at': completed, 'correlation_id': correlation_id,
            'consistency': {'mode': 'repeatable_read', 'started_at': started, 'completed_at': completed,
                             'limitations': ['El snapshot SQL no verifica bytes de archivos.']},
            'selections': selections, 'dimensions': dimensions, 'analyses': analyses, 'evidence': evidence,
            'populations': populations, 'checkpoints': checkpoints, 'technical_errors': errors,
            'summary': {'by_state': {s: counts[s] for s in STATES}, 'not_evaluated': counts[None],
                'analysis_count': len(analyses), 'warning_reason_ids': sorted({f['reason_id'] for a in analyses for f in a['findings'] if f['kind'] in ('warning', 'difference')}),
                'technical_error_ids': [e['error_id'] for e in errors]}})

    @staticmethod
    def _individual(module, rows):
        values = []
        for r in rows:
            error_ids = r['history_errors'] if module == 'curves' else r['evaluation_errors']
            if error_ids:
                availability = {'state': 'query_error', 'error_ids': error_ids}
            elif module == 'curves':
                availability = known(bool(r['history'] and r['history']['rows']))
            elif module == 'metrics' and r['attempt']:
                availability = known(bool((r['attempt'].get('verification') or {}).get('metrics')))
            elif module == 'metrics' and r.get('historical_metric'):
                availability = known(r['historical_metric']['state'] == 'available')
            elif module in ('metrics', 'consensus'):
                availability = unknown('Consultar resultados de la fuente y selección exactas.')
            else:
                availability = unknown('Disponibilidad individual pendiente de consulta del módulo.')
            values.append({'selection_id': r['sid'], 'availability': availability, 'references': r['refs']})
        return values

    @staticmethod
    def _differences(rows, finding):
        def compare(dim, code, values, kind='warning'):
            present = [v for v in values if v is not None]
            if len(present) > 1 and any(v != present[0] for v in present[1:]):
                finding(dim, code, kind, 'La evidencia persistida difiere entre participantes.',
                        [r['sid'] for r in rows])
        compare('A1', 'TRAIN_DATASET_DIFFERENCE', [str(r['train']['dataset_version_id']) if r['train'] else None for r in rows])
        compare('A2', 'SPLIT_DIFFERENCE', [r['split'] for r in rows], 'incompatibility')
        for field in (*CONFIG_FIELDS, 'no_augment'):
            compare('A4', f'CONFIGURATION_DIFFERENCE_{field.upper()}', [r['config'].get(field) for r in rows])
        compare('A6', 'INFERENCE_INPUT_CONTRACT_DIFFERENCE',
                [(r['identity'].get('model') or {}).get('input_contract') for r in rows])
        compare('A6', 'INFERENCE_BATCH_SIZE_DIFFERENCE', [r['identity'].get('batch_size') for r in rows])
        for field in ('score_domain', 'positive_class'):
            compare('A6', 'DECISION_SEMANTICS_DIFFERENCE_' + field.upper(),
                    [(r['identity'].get('decision') or {}).get(field) for r in rows], 'incompatibility')
        for field in ('protocol_hash', 'metric_definition', 'threshold_used', 'evaluation_role'):
            compare('A6', 'HISTORICAL_PROTOCOL_DIFFERENCE_' + field.upper(),
                    [(r.get('historical') or {}).get(field) for r in rows],
                    'incompatibility' if field == 'metric_definition' else 'warning')
        for field in ('protocol', 'decision', 'metrics_definition'):
            compare('A6', f'PROTOCOL_DIFFERENCE_{field.upper()}', [r['identity'].get(field) for r in rows],
                    'incompatibility' if field == 'metrics_definition' else 'warning')

    @staticmethod
    def _population(coverage, rows, ref, finding):
        by_attempt = {str(c['attempt_id']): c for c in coverage}
        members = []
        complete = len(coverage) == len(rows)
        intersection = coverage[0]['intersection_unique'] if coverage else None
        for r in rows:
            c = by_attempt.get(str(r['attempt']['attempt_id']))
            if c is None:
                complete = False
                continue
            duplicate = c['retrieved_rows'] - c['retrieved_unique'] + c['expected_rows'] - c['expected_unique']
            conflict = c['label_conflicts'] + c['declared_label_conflicts']
            verified = c['verified_count'] is not None and str(c['verified_count']) == str(c['retrieved_rows'])
            good = (c['state'] == 'verified' and verified and c['expected_unique'] > 0 and
                    not any(c[k] for k in ('missing_count', 'unexpected_count', 'ungoverned_count', 'missing_labels')) and not duplicate)
            complete &= good
            if duplicate:
                finding('A3', 'DUPLICATE_SAMPLES', 'incompatibility', 'Duplicados impiden alineación inequívoca.', [r['sid']], [ref])
            if conflict:
                finding('A3', 'LABEL_CONFLICT', 'incompatibility', 'Etiquetas reales contradictorias.', [r['sid']], [ref])
            if not good:
                finding('A3', 'COVERAGE_NOT_VERIFIED', 'missing',
                        'Población incompleta, no gobernada o intento no verificado.', [r['sid']], [ref])
            n = c['retrieved_unique']
            members.append({'selection_id': r['sid'], 'expected_unique': known(c['expected_unique'], [ref]),
                'retrieved_rows': known(c['retrieved_rows'], [ref]), 'retrieved_unique': known(n, [ref]),
                'duplicate_count': known(duplicate, [ref]), 'label_conflict_count': known(conflict, [ref]),
                'missing_count': known(c['missing_count'], [ref]), 'exclusive_count': unknown('Intersección aún no acreditada.'),
                'numerator': unknown('Intersección aún no acreditada.'), 'denominator': known(n, [ref]),
                'ratio': unknown('Cobertura no verificada.'), 'evidence_ids': [ref]})
        if len(coverage) != len(rows):
            finding('A3', 'COVERAGE_ROWS_MISSING', 'missing', 'Faltan agregados de participantes.', [r['sid'] for r in rows], [ref])
        if complete:
            if intersection == 0:
                finding('A3', 'EMPTY_INTERSECTION', 'incompatibility', 'Intersección acreditada vacía.', [r['sid'] for r in rows], [ref])
            for member in members:
                n = member['denominator']['value']
                member.update(numerator=known(intersection, [ref]), exclusive_count=known(n - intersection, [ref]),
                              ratio=known(intersection / n, [ref]) if n else unknown('Denominador cero.'))
                if n != intersection:
                    finding('A3', 'PARTIAL_INTERSECTION', 'warning',
                        'El análisis pareado se limita a la intersección; métricas originales conservan su población.',
                        [member['selection_id']], [ref])
        return {'population_id': 'selected-assessments', 'scope_id': 'A3:requested',
            'alignment_key': known('dataset_source_records.id', [ref]) if complete else unknown('Pertenencia completa no acreditada.'),
            'complete': known(complete, [ref]), 'per_selection': members,
            'intersection_unique': known(intersection, [ref]) if complete else unknown('Cobertura no verificada.'),
            'identity_references': [f"assessment:{r['attempt']['attempt_id']}:results" for r in rows],
            'subset_rule': 'Intersección de todas las poblaciones seleccionadas; sin exclusión de duplicados o conflictos.'}
