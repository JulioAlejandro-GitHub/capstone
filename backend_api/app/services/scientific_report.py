"""Scientific calculations over immutable evidence; no model/runtime execution."""
import math

from app.db import read_only_transaction
from app.repositories.assessments import AssessmentReadRepository
from app.repositories.scientific_results import ScientificReadRepository, metric_dto
from app.schemas.scientific_report import ScientificReportResponse
from app.services.scientific_public import public_evidence
from app.services.scientific_representations import representations
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError

METRICS = {'accuracy': 'Accuracy', 'precision': 'Precision', 'recall': 'Sensibilidad',
           'specificity': 'Especificidad', 'f1': 'F1', 'f2': 'F2', 'roc_auc': 'ROC-AUC',
           'pr_auc': 'PR-AUC', 'balanced_accuracy': 'Balanced accuracy'}


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def checkpoint_evidence(record, run_id):
    record = record or {}
    selection = record.get('selection') or {}
    metadata = record.get('metadata') or {}
    epoch = selection.get('selected_epoch')
    valid = (record.get('id') is not None and str(record.get('run_id')) == str(run_id)
             and isinstance(epoch, int) and not isinstance(epoch, bool) and epoch > 0
             and metadata.get('epoch') == epoch and metadata.get('phase') == selection.get('phase'))
    return {'artifact_id': record.get('id'), 'selected_epoch': epoch,
                'phase': selection.get('phase'), 'metric': selection.get('selected_metric'),
                'policy': selection.get('policy'), 'logical_lineage': valid,
                'checksum_registered': record.get('checksum'),
                'file_availability': 'not_checked', 'physical_checksum': 'not_checked'}


def validate_samples(samples, threshold, expected):
    """Never deduplicate or repair a scientific population silently."""
    issues, indexed = [], {}
    counts = {'tn': 0, 'fp': 0, 'fn': 0, 'tp': 0}
    threshold = number(threshold)
    if threshold is None or not 0 <= threshold <= 1:
        return {}, counts, ['Umbral ausente o inválido.']
    for item in samples:
        if not isinstance(item, dict):
            issues.append('Registro de predicción inválido.')
            continue
        sample, label, score = item.get('sample'), item.get('label'), number(item.get('score'))
        if not isinstance(sample, str) or not sample or label not in (0, 1) or isinstance(label, bool) or score is None or not 0 <= score <= 1:
            issues.append('Identificador, etiqueta o score inválido.')
            continue
        if sample in indexed:
            issues.append('Predicciones duplicadas.')
            continue
        prediction = int(score >= threshold)
        indexed[sample] = {'label': label, 'score': score, 'prediction': prediction, 'correct': prediction == label}
        counts[('tn', 'fp', 'fn', 'tp')[label * 2 + prediction]] += 1
    if expected.get('sample_count') != len(samples):
        issues.append('Cantidad de predicciones distinta de la evaluación.')
    if any(expected.get(k) is None or expected[k] != v for k, v in counts.items()):
        issues.append('La matriz reconstruida no coincide con las métricas persistidas.')
    return indexed, counts, sorted(set(issues))


def population_coverage(populations):
    sets = [set(p) for p in populations]
    common = set.intersection(*sets) if sets else set()
    union = set.union(*sets) if sets else set()
    conflicts = sum(len({p[s]['label'] for p in populations if s in p}) > 1 for s in union)
    coverage = [{'population': len(p), 'common': len(common), 'missing': len(union-set(p)),
                     'exclusive': len(set(p)-common), 'ratio': len(common)/len(p) if p else None} for p in populations]
    return {'common_count': len(common), 'union_count': len(union), 'label_conflicts': conflicts, 'coverage': coverage}


def consensus(populations, thresholds, offset=0, limit=25, category='all', sort_by=None, sort_desc=False,
              sample_query=None, label=None, score_ranges=None):
    """All ratios use the explicitly identified common population."""
    base = population_coverage(populations)
    common = set.intersection(*(set(p) for p in populations)) if populations else set()
    conflicts = base['label_conflicts']
    # One RUN is the "qué aprendió el modelo" case: categories are its own TP/TN/FP/FN and nothing is compared.
    if conflicts or not common:
        return dict(base, state='incompatible' if conflicts or populations else 'missing',
                    issues=['Etiquetas contradictorias.' if conflicts else 'Sin población de predicciones.'])
    distribution = dict.fromkeys(['CONSENSUS_TP', 'CONSENSUS_TN', 'CONSENSUS_FP', 'CONSENSUS_FN', 'disagreement'], 0)
    agreement = [[0 for _ in populations] for _ in populations]
    overlap = [[0 for _ in populations] for _ in populations]
    exclusive_errors, exclusive_correct = [0]*len(populations), [0]*len(populations)
    oracle = 0
    all_wrong = 0
    matches = []
    high_count = low_count = 0
    query, label_filter = (sample_query or '').strip().lower(), label
    for sample in sorted(common):
        values = [p[sample] for p in populations]
        correct = [v['correct'] for v in values]
        oracle += any(correct)
        all_wrong += not any(correct)
        label = values[0]['label']
        predictions = [v['prediction'] for v in values]
        kind = ('CONSENSUS_' + ('TP' if label else 'FP') if predictions[0] else 'CONSENSUS_' + ('FN' if label else 'TN')) if len(set(predictions)) == 1 else 'disagreement'
        distribution[kind] += 1
        high = any(not v['correct'] and (v['score'] >= .9 if v['prediction'] else v['score'] <= .1) for v in values)
        low = any(abs(v['score'] - t) <= .05 for v, t in zip(values, thresholds))
        high_count += high
        low_count += low
        for i, v in enumerate(values):
            exclusive_errors[i] += not correct[i] and sum(correct) == len(values)-1
            exclusive_correct[i] += correct[i] and sum(correct) == 1
            for j, w in enumerate(values):
                agreement[i][j] += v['prediction'] == w['prediction']
                overlap[i][j] += not v['correct'] and not w['correct']
        in_category = category in ('all', kind) or (category == 'high_confidence_error' and high) or (category == 'low_confidence' and low)
        in_columns = ((not query or query in sample.lower()) and (label_filter is None or label == label_filter)
                      and all(i < len(values) and (lo is None or values[i]['score'] >= lo) and (hi is None or values[i]['score'] <= hi)
                              for i, (lo, hi) in (score_ranges or {}).items()))
        if in_category and in_columns:
            matches.append({'sample': sample, 'label': label, 'category': kind, 'runs': values,
                                'high_confidence_error': high, 'low_confidence': low})
    if sort_by:
        if sort_by.startswith('run-'):
            index = int(sort_by[4:])
            key = lambda item: (item['runs'][index]['score'] if index < len(item['runs']) else float('-inf'), item['sample'])
        else:
            key = lambda item: (item[sort_by], item['sample'])
        matches.sort(key=key, reverse=sort_desc)
    return dict(base, state='available', distribution=distribution, agreement=agreement,
                error_overlap=overlap, exclusive_errors=exclusive_errors, exclusive_correct=exclusive_correct,
                oracle={'numerator': oracle, 'denominator': len(common), 'ratio': oracle/len(common)},
                all_wrong=all_wrong, high_confidence_errors=high_count, low_confidence=low_count,
                samples=matches[offset:offset+limit], total=len(matches), offset=offset, limit=limit,
                definitions={
                    'decision': 'score >= umbral persistido; clase positiva parasitada (1).',
                    'consensus': 'Todos predicen la misma clase; TP/TN/FP/FN según etiqueta real.',
                    'agreement': 'Predicciones iguales entre i,j / N común; se muestran conteos y N.',
                    'error_overlap': 'Número de muestras comunes donde i y j fallan.',
                    'exclusive': 'Error (o acierto) de un único RUN; los demás tienen el resultado contrario.',
                    'oracle': 'Muestras donde al menos un RUN acierta / N común. Límite descriptivo, no modelo desplegable.',
                    'high_confidence_error': 'Error con score >= 0.9 para predicción positiva o <= 0.1 para negativa; no acredita calibración.',
                    'low_confidence': '|score - umbral| <= 0.05; cercanía a la decisión, no incertidumbre calibrada.',
                    'coverage': 'N común / muestras únicas de cada RUN; faltantes relativos a la unión.'})


def superiority_answer(splits: set) -> str:
    # The answer must match the evaluated population: TEST is descriptive, VAL also selected the checkpoint.
    if splits == {'test'}:
        return ('Las métricas TEST describen esta población y estos umbrales; sin una prueba pareada acreditada '
                '(p. ej. McNemar o bootstrap) no se infiere superioridad clínica ni estadística.')
    if 'val' in splits:
        return 'No se infiere generalización TEST ni superioridad estadística desde VALIDATION.'
    return 'Sin evaluación atribuible común: no se infiere superioridad clínica.'


class ScientificReportService:
    def __init__(self, repository=None, transaction=None):
        self.repository = repository or ScientificReadRepository()
        self.transaction = transaction or read_only_transaction

    def historical(self, connection, selection):
        ev = selection.evaluation
        if not ev or ev.source != 'evaluations':
            return None
        evaluation = self.repository.evaluation(connection, ev.evaluation_id)
        if not evaluation or str(evaluation['training_run_id']) != str(selection.training_run_id):
            raise HTTPException(404, 'Evaluación no encontrada para este TRAIN.')
        if selection.split and selection.split != evaluation['split']:
            raise HTTPException(422, 'Split distinto de la evaluación.')
        if selection.checkpoint_artifact_id and str(selection.checkpoint_artifact_id) != str(evaluation['checkpoint_artifact_id']):
            raise HTTPException(422, 'Checkpoint distinto de la evaluación.')
        return evaluation

    def metrics(self, connection, selection):
        evaluation = self.historical(connection, selection)
        if not evaluation and selection.evaluation and selection.evaluation.source == 'assessment':
            return self.assessment_metrics(connection, selection)
        if not evaluation:
            return {'training_run_id': selection.training_run_id, 'state': 'missing',
                        'issues': ['Seleccione una evaluación con métricas clínicas persistidas.']}
        records = self.repository.comparison_metrics(connection, evaluation['id'])
        issues = []
        if len(records) != 1:
            issues.append('Métricas ausentes o ambiguas para esta evaluación.')
        elif (str(records[0]['run_id']) != str(evaluation['run_id'])
              or number(records[0]['threshold_used']) != number(evaluation['threshold_used'])):
            issues.append('Linaje o umbral de métricas contradictorio.')
        checkpoint = checkpoint_evidence(self.repository.comparison_checkpoint(connection, selection.training_run_id), selection.training_run_id)
        if evaluation.get('evaluation_role') == 'training_validation_final' and (
                not checkpoint['logical_lineage'] or str(checkpoint['artifact_id']) != str(evaluation['checkpoint_artifact_id'])):
            issues.append('Checkpoint final no corresponde a la selección persistida.')
        return {'training_run_id': selection.training_run_id, 'state': ('missing' if not records else 'incompatible') if issues else 'available',
                    'issues': issues, 'evaluation': public_evidence(evaluation), 'checkpoint': checkpoint,
                    'clinical': metric_dto(records[0]) if len(records) == 1 else None}

    def assessment_metrics(self, connection, selection):
        selected = selection.evaluation
        attempt = AssessmentReadRepository().preflight_detail(connection, selected.attempt_id)
        if not attempt or str(attempt['training_run_id']) != str(selection.training_run_id) or str(attempt['identity_id']) != str(selected.identity_id):
            raise HTTPException(404, 'Intento no encontrado para esta identidad y TRAIN.')
        identity = attempt['identity']
        model, decision = identity.get('model') or {}, identity.get('decision') or {}
        if selection.split and selection.split != identity.get('split'):
            raise HTTPException(422, 'Split distinto del intento.')
        if selection.checkpoint_artifact_id and str(selection.checkpoint_artifact_id) != str(model.get('checkpoint_artifact_id')):
            raise HTTPException(422, 'Checkpoint distinto del intento.')
        observed = (attempt.get('verification') or {}).get('metrics') or {}
        issues = []
        if attempt['kind'] != 'evaluate' or attempt['state'] != 'verified' or not observed:
            issues.append('El intento no acredita resultados EVALUATE verificados.')
        if model.get('training_run_id') and str(model['training_run_id']) != str(selection.training_run_id):
            issues.append('Linaje de modelo contradictorio.')
        evaluation = {'id': None, 'source': 'assessment', 'source_assessment_attempt_id': attempt['attempt_id'],
                          'identity_id': attempt['identity_id'], 'split': identity.get('split'), 'purpose': identity.get('purpose'),
                          'evaluation_role': 'independent_evaluate', 'checkpoint_artifact_id': model.get('checkpoint_artifact_id'),
                          'dataset_version_id': (identity.get('dataset') or {}).get('dataset_version_id'),
                          'threshold_used': decision.get('effective'), 'protocol_hash': identity.get('protocol'),
                          'metric_definition': identity.get('metrics_definition'), 'population_hash': None}
        clinical = dict(sample_count=observed.get('count'), threshold_used=decision.get('effective'),
                        **{key: observed.get(key) for key in ('tn', 'fp', 'fn', 'tp')},
                        metrics={key: {'value': observed.get(key), 'undefined_reason': None if key in observed else 'not_persisted'} for key in METRICS})
        return {'training_run_id': selection.training_run_id, 'state': 'incompatible' if issues else 'available',
                    'issues': issues, 'evaluation': evaluation, 'clinical': clinical}

    def prediction_population(self, connection, selection, metric):
        evaluation = metric.get('evaluation') or {}
        checkpoint = metric.get('checkpoint') or {}
        attempt_id = evaluation.get('source_assessment_attempt_id')
        if attempt_id and metric['state'] == 'available':
            assessments = AssessmentReadRepository()
            attempt = assessments.preflight_detail(connection, attempt_id)
            if not attempt or str(attempt['training_run_id']) != str(selection.training_run_id) or attempt['kind'] != 'evaluate' or attempt['state'] != 'verified':
                return {}, ['Intento independiente no atribuible o no verificado.']
            identity = attempt['identity']
            decision = identity.get('decision') or {}
            if decision.get('score_domain') != 'raw' or decision.get('positive_class') != 1 or decision.get('comparison') != '>=' or decision.get('calibrator') is not None:
                return {}, ['Semántica de decisión independiente no compatible con scores binarios sin calibración.']
            if identity.get('split') != evaluation.get('split') or number(decision.get('effective')) != number(evaluation.get('threshold_used')):
                return {}, ['Protocolo del intento contradice la evaluación.']
            coverage = assessments.preflight_population(connection, [attempt_id])
            if len(coverage) != 1:
                return {}, ['Población independiente no acreditada.']
            c = coverage[0]
            if any(c[k] for k in ('missing_count','unexpected_count','ungoverned_count','missing_labels','label_conflicts','declared_label_conflicts')) or c['expected_rows'] != c['expected_unique'] or c['retrieved_rows'] != c['retrieved_unique']:
                return {}, ['Población independiente incompleta, duplicada o contradictoria.']
            records = assessments.comparison_results(connection, attempt_id)
            samples = []
            for row in records:
                payload = row['payload']
                if number(payload.get('threshold')) != number(evaluation.get('threshold_used')) or str(payload.get('sample_id')) != str(row['sample_id']):
                    return {}, ['Identidad o umbral por muestra contradictorio.']
                samples.append({'sample': str(row['sample_id']), 'label': payload.get('label'), 'score': payload.get('raw_score')})
            indexed, _, issues = validate_samples(samples, evaluation.get('threshold_used'), metric['clinical'])
            return indexed, issues
        if metric['state'] != 'available' or evaluation.get('evaluation_role') != 'training_validation_final' or evaluation.get('split') != 'val':
            return {}, ['Predicciones VAL de checkpoint seleccionado no atribuibles a esta evaluación.']
        config = self.repository.preflight_configuration(connection, selection.training_run_id) or {}
        contract = (config.get('extension_configuration') or {}).get('input_contract') or {}
        if (contract.get('output') or {}).get('meaning') != 'probability_parasitized' or (contract.get('label_mapping') or {}).get('positive_class') != 1:
            return {}, ['Semántica de scores o clase positiva no acreditada.']
        events = self.repository.comparison_predictions(connection, selection.training_run_id,
                                                       checkpoint['selected_epoch'], checkpoint['phase'])
        if len(events) != 1 or not isinstance(events[0].get('samples'), list):
            return {}, ['Evento de predicciones ausente o ambiguo para época, fase y rol seleccionados.']
        indexed, _, issues = validate_samples(events[0]['samples'], evaluation.get('threshold_used'), metric['clinical'])
        return indexed, issues

    def read(self, request, datasource):
        repo = self.repository
        warnings = []
        try:
            with self.transaction(datasource, repeatable_read=True) as connection:
                for selection in request.selections:
                    train = repo.preflight_training(connection, selection.training_run_id)
                    if not train:
                        raise HTTPException(404, 'TRAIN no encontrado.')
                    if train['run_type'] != 'training':
                        raise HTTPException(422, 'Se requiere TRAIN.')
                if request.module == 'catalog':
                    data = [{'training_run_id': s.training_run_id,
                                 'evaluations': repo.comparison_catalog(connection, s.training_run_id),
                                 'governance': public_evidence(repo.comparison_governance(connection, s.training_run_id)),
                                 'checkpoint': checkpoint_evidence(repo.comparison_checkpoint(connection, s.training_run_id), s.training_run_id)} for s in request.selections]
                elif request.module == 'representations':
                    data, notes = representations(repo, connection, request.selections)
                    warnings += notes
                elif request.module == 'curves':
                    data = []
                    for s in request.selections:
                        events = repo.comparison_epochs(connection, s.training_run_id)
                        epochs = []
                        seen = set()
                        issues = []
                        for event in events:
                            payload = event['payload']
                            epoch = payload.get('epoch')
                            if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1 or epoch in seen:
                                issues.append('Eje de época inválido o duplicado; no se superponen fases ambiguas.')
                                continue
                            seen.add(epoch)
                            epochs.append({'epoch': epoch, 'phase': event['phase'], 'values': {k: number(v) for k, v in payload.items() if number(v) is not None}})
                        config = repo.preflight_configuration(connection, s.training_run_id) or {}
                        data.append({'training_run_id': s.training_run_id, 'epochs': sorted(epochs, key=lambda e: e['epoch']) if not issues else [],
                                         'executed_epochs': len(events), 'final_epoch': max(seen) if seen else None,
                                         'max_epochs': config.get('max_epochs'), 'fine_tune_epochs': config.get('fine_tune_epochs'), 'loss_definition': config.get('loss_function'),
                                         'metrics_definition': ((config.get('extension_configuration') or {}).get('recipe') or {}).get('metrics'),
                                         'checkpoint': checkpoint_evidence(repo.comparison_checkpoint(connection, s.training_run_id), s.training_run_id), 'issues': issues})
                else:
                    metrics = [self.metrics(connection, s) for s in request.selections]
                    split_set = {m['evaluation']['split'] for m in metrics if m.get('evaluation')}
                    if len(split_set) > 1:
                        warnings.append('Selección VAL/TEST mixta: resultados individuales, no una población comparable.')
                    if 'val' in split_set:
                        warnings.append('VALIDATION de desarrollo: selección de checkpoint y comparación reutilizan VAL; no acredita desempeño TEST ni superioridad estadística.')
                    if request.module == 'metrics':
                        highlights = []
                        comparable = len(split_set) == 1 and all(m['state'] == 'available' for m in metrics)
                        for field in ('dataset_version_id', 'population_hash', 'metric_definition', 'protocol_hash', 'threshold_used'):
                            values = [m.get('evaluation', {}).get(field) for m in metrics]
                            comparable &= bool(values) and all(v is not None and str(v) == str(values[0]) for v in values)
                        if comparable:
                            for field, label, lowest in [('recall', 'Mayor sensibilidad observada', False), ('specificity', 'Mayor especificidad observada', False), ('fn', 'Menos falsos negativos', True), ('f2', 'Mayor F2 observada', False)]:
                                values = [(i, number(m['clinical'].get('fn') if field == 'fn' else m['clinical']['metrics'][field]['value'])) for i, m in enumerate(metrics)]
                                values = [(i, v) for i, v in values if v is not None]
                                if values:
                                    best = (min if lowest else max)(v for _, v in values)
                                    highlights.append({'label': label, 'value': best, 'runs': [i for i, v in values if v == best]})
                        else:
                            warnings.append('Comparación descriptiva individual: población, protocolo, umbral o atribución no comunes; no se destacan máximos conjuntos.')
                        data = {'runs': metrics, 'highlights': highlights, 'comparable': comparable}
                    else:
                        populations, issues, thresholds = [], [], []
                        for i, (s, m) in enumerate(zip(request.selections, metrics)):
                            p, errors = self.prediction_population(connection, s, m)
                            populations.append(p)
                            issues.extend(f'RUN {chr(65+i)}: {e}' for e in errors)
                            thresholds.append(number(m.get('evaluation', {}).get('threshold_used')))
                        for field in ('dataset_version_id', 'split', 'metric_definition', 'protocol_hash'):
                            values = [m.get('evaluation', {}).get(field) for m in metrics]
                            if not values or any(v is None or str(v) != str(values[0]) for v in values):
                                issues.append(f'No se acredita {field} común.')
                        namespaces = {bool(m.get('evaluation', {}).get('source_assessment_attempt_id')) for m in metrics}
                        if len(namespaces) > 1:
                            issues.append('Identidades sample relativas y sample_id no tienen correspondencia acreditada.')
                        data = {'state': 'incompatible' if any(m['state'] == 'incompatible' for m in metrics) or any(populations) else 'missing', 'issues': issues} if issues else consensus(populations, thresholds, request.offset, request.limit, request.category, request.sort_by, request.sort_desc,
                            request.sample_query, request.label, request.score_ranges)
                        if data.get('state') == 'available':
                            # EVALUATE attempt of each RUN: the lineage under which a sample's original image is served.
                            data['sources'] = [{'training_run_id': str(s.training_run_id), 'attempt_id': str(e['source_assessment_attempt_id']),
                                                'dataset_version_id': str(e['dataset_version_id']), 'split': e.get('split')}
                                               if (e := m.get('evaluation') or {}).get('source_assessment_attempt_id') and e.get('dataset_version_id') else None
                                               for s, m in zip(request.selections, metrics)]
                        if request.module == 'questions':
                            data = {'consensus': data, 'answers': [
                                ('Con un solo RUN no hay complementariedad que medir; los errores del modelo están en Errores.' if len(request.selections) == 1 else
                                 'El oracle cubre ' + str(data['oracle']['numerator']) + ' de ' + str(data['oracle']['denominator']) + ' muestras comunes; no es un modelo desplegable.') if data.get('oracle') else 'Faltan predicciones compatibles y reconciliadas para medir complementariedad.',
                                superiority_answer(split_set),
                                'Las explicaciones visuales requieren artefactos atribuidos a muestra, método y checkpoint.']}
        except SQLAlchemyError:
            raise HTTPException(503, 'Error de consulta de evidencia científica; puede reintentar.') from None
        return ScientificReportResponse(module=request.module, data=jsonable_encoder(public_evidence(data)), warnings=warnings)
