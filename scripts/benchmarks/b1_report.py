"""Deterministic transformations and Spanish evidence reports for B1."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import groupby
from typing import Any

from b1_historical import OUT, ROOT, dumps, write_csv
from b1_queries import CAMPAIGN, QUERIES
from b1_discovery import DIAGNOSTICS

D = Decimal

def seconds(end: str, start: str) -> Decimal:
    delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    return D(delta.days * 86400 + delta.seconds) + D(delta.microseconds) / D(1000000)

def fmt(value: Any, places: int = 3) -> str:
    if value is None:
        return 'ND'
    if isinstance(value, (Decimal, float)):
        return f'{value:.{places}f}'
    return str(value)

def table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(v: Any) -> str:
        return fmt(v).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] +
                     ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows])

def metric_check(samples: list[dict[str, Any]], m: dict[str, Any]) -> dict[str, Any]:
    assert len({s['sample'] for s in samples}) == len(samples) == 2693
    assert all(s['label'] in (0,1) and 0 <= s['score'] <= 1 for s in samples)
    counts = Counter((s['label'], int(s['score'] >= m['threshold_used'])) for s in samples)
    tn,fp,fn,tp = [counts[k] for k in [(0,0),(0,1),(1,0),(1,1)]]
    assert [tn,fp,fn,tp] == [m[k] for k in ['tn','fp','fn','tp']]
    assert m['confusion_matrix'] == [[tn,fp],[fn,tp]]
    p,n = tp+fn,tn+fp
    assert (p,n)==(1325,1368)
    values = {'recall_parasitized':D(tp)/p,'specificity':D(tn)/n,
              'f1_parasitized':D(2*tp)/(2*tp+fp+fn), 'f2_parasitized':D(5*tp)/(5*tp+4*fn+fp)}
    # Exact tied-score ROC pair count and non-interpolated average precision.
    negatives_below = 0
    wins = D(0)
    for _,group in groupby(sorted(samples,key=lambda s:s['score']),key=lambda s:s['score']):
        labels = [s['label'] for s in group]
        pos,neg = sum(labels),len(labels)-sum(labels)
        wins += D(pos)*(D(negatives_below)+D(neg)/2)
        negatives_below += neg
    values['roc_auc_parasitized'] = wins / (p*n)
    seen = positive_seen = 0
    ap = D(0)
    for _,group in groupby(sorted(samples,key=lambda s:s['score'],reverse=True),key=lambda s:s['score']):
        labels = [s['label'] for s in group]
        seen += len(labels)
        positive_seen += sum(labels)
        ap += D(sum(labels))/p * D(positive_seen)/seen
    values['pr_auc_parasitized'] = ap
    errors = {k:abs(v-m[k]) for k,v in values.items()}
    assert max(errors.values()) < D('1e-12'), errors
    assert m['sensitivity_parasitized']==m['recall_parasitized']
    return {'recomputed':values,'absolute_errors':errors,'tolerance':D('1e-12'),'samples':len(samples),
            'tn':tn,'fp':fp,'fn':fn,'tp':tp,'status':'PASS'}

def generate(data: dict[str, list[dict[str, Any]]]) -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    campaign = data['Q03'][0]
    links = {r['run_id']:r for r in data['Q04']}
    metrics = {r['run_id']:r for r in data['Q08']}
    prediction_rows = {r['run_id']:r for r in data['Q17']}
    artifacts = {r['id']:r for r in data['Q09']}
    epochs_by_run: dict[str,list[dict[str,Any]]] = defaultdict(list)
    events: dict[tuple[str,str,str,str],dict[str,Any]] = {}
    for event in data['Q11']:
        if event['legacy_kind']:
            key = (event['run_id'],event['legacy_kind'],event['legacy_phase'],event['legacy_key'])
            assert key not in events
            events[key] = event
    for r in data['Q05']:
        ev = [e for e in data['Q11'] if e['run_id']==r['id']]
        assert [int(e['sequence']) for e in ev]==list(range(1,len(ev)+1))
        assert all(seconds(b['occurred_at'],a['occurred_at'])>=0 for a,b in zip(ev,ev[1:]))
    record_artifacts = {(r['run_id'],r['phase'],r['record_key']):r for r in data['Q10'] if r['kind']=='artifact'}
    epochs: list[dict[str,Any]] = []
    phase_rows: list[dict[str,Any]] = []
    for raw in data['Q06']:
        rid,phase,key = raw['run_id'],raw['phase'],raw['record_key']
        payload=raw['payload']; c=links[rid]
        epoch_event=events[(rid,'epoch',phase,key)]
        prepared=events[(rid,'artifact_prepared',phase,key)]
        created=events[(rid,'artifact',phase,key)]
        selected=events[(rid,'selection',phase,key)]
        predicted=events[(rid,'predictions',phase,key)]
        previous_key = str(int(key)-1)
        previous=events[(rid,'runtime',phase,'configuration')] if int(key)==1 else events[(rid,'epoch',phase,previous_key)]
        row = dict(run_id=rid,architecture=c['architecture'],optimizer=c['optimizer'],
                   source_query='Q06/Q11',source_table='train_execution_records',source_kind=raw['kind'],
                   source_phase=phase,source_record_key=key,source_created_at=raw['created_at'],
                   source_event_id=epoch_event['canonical_event_id'],source_event_sequence=epoch_event['sequence'],
                   epoch_event_at=epoch_event['occurred_at'],previous_boundary_at=previous['occurred_at'],
                   event_interval_seconds=seconds(epoch_event['occurred_at'],previous['occurred_at']),
                   artifact_prepared_event_at=prepared['occurred_at'],artifact_created_event_at=created['occurred_at'],
                   checkpoint_event_interval_seconds=seconds(created['occurred_at'],prepared['occurred_at']),
                   selection_event_at=selected['occurred_at'],predictions_event_at=predicted['occurred_at'],
                   postselection_prediction_interval_seconds=seconds(predicted['occurred_at'],selected['occurred_at']),
                   epoch_payload=payload,**payload)
        assert row['epoch']==int(payload['epoch']) and row['phase_epoch']==int(key)
        assert all(row[k]>=0 for k in ['event_interval_seconds','checkpoint_event_interval_seconds','postselection_prediction_interval_seconds'])
        epochs.append(row);epochs_by_run[rid].append(row)
    runs: list[dict[str,Any]] = []
    populations=[]
    for raw in data['Q05']:
        rid=raw['id'];c=links[rid];m=metrics[rid];rc=c['run_configuration']; es=epochs_by_run[rid]
        assert raw['status']=='completed' and raw['run_type']=='training' and raw['session_state']=='verified'
        assert c['accepted_attempt_id']==c['attempt_id']==raw['session_attempt_id']
        assert c['architecture']==c['campaign_architecture']==c['execution_architecture']==c['model_name']
        assert c['optimizer']==c['campaign_optimizer']==c['execution_optimizer']
        assert rc['random_seed']==c['seed']==raw['random_seed']==47
        assert hashlib.sha256(rc['canonical_configuration'].encode()).hexdigest()==rc['configuration_hash']
        canonical=json.loads(rc['canonical_configuration'],parse_float=D)
        assert canonical==rc['provenance_snapshot']['resolved']
        execution_config=raw['execution_parameters']['model_configuration_e2']['configuration']
        assert canonical==execution_config['resolved']
        # Campaign configuration excludes member seed; RUN resolves the same scientific recipe plus seed.
        base_config=json.loads(dumps(execution_config),parse_float=D)
        assert base_config['resolved']['execution'].pop('seed')==47
        assert base_config==c['campaign_configuration']
        assert sorted(e['epoch'] for e in es)==list(range(1,len(es)+1))
        assert raw['completion']['epochs']==len(es)
        assert raw['wall_seconds']==raw['duration_seconds']==seconds(raw['finished_at'],raw['started_at'])
        assert raw['wall_seconds']>0
        assert m['run_id']==m['training_run_id']==m['evaluation_run_id']==rid
        assert m['evaluation_dataset_version_id']==raw['dataset_version_id']==campaign['dataset_version_id']
        assert m['split_name']==m['evaluation_split']=='val'
        assert m['evaluation_threshold']==m['threshold_used']==D('0.5')
        checked=metric_check(prediction_rows[rid]['samples'],m)
        populations.append(sorted((s['sample'],s['label']) for s in prediction_rows[rid]['samples']))
        a=artifacts[m['checkpoint_artifact_id']];cp=raw['completion']['training_completion']
        assert a['checksum']==cp['checkpoint_sha256'] and a['file_size_bytes']==cp['checkpoint_bytes']
        assert a['metadata']['epoch']==cp['checkpoint_epoch']==raw['completion']['selection']['selected_epoch']
        assert a['metadata']['version_id']==cp['checkpoint_version_id']
        assert m['source_event_id']==cp['evaluation_event_id']
        selected_epoch=next(e for e in es if e['epoch']==a['metadata']['epoch'])
        for column,ekey in [('recall_parasitized','val_recall_parasitized'),('specificity','val_specificity'),
                           ('f2_parasitized','val_f2_parasitized'),('roc_auc_parasitized','val_roc_auc_parasitized'),
                           ('pr_auc_parasitized','val_pr_auc_parasitized')]:
            assert abs(m[column]-selected_epoch[ekey])<D('1e-12')
        phases=[]
        for p in [p for p in data['Q07'] if p['run_id']==rid]:
            phase=p['phase']; pe=[e for e in es if e['phase']==phase]
            assert sorted(e['phase_epoch'] for e in pe)==list(range(1,len(pe)+1))
            assert len(pe)==p['payload']['epochs']
            early=p['payload']['early_stopping'][0]
            max_epochs=rc['max_epochs'] if phase=='base' else rc['fine_tune_epochs']
            stopped=early['stopped_epoch']>0
            assert (stopped and early['stopped_epoch']+1==len(pe)) or (not stopped and len(pe)==max_epochs)
            start=events[(rid,'runtime',phase,'configuration')]['occurred_at']
            end=events[(rid,'phase',phase,'completed')]['occurred_at']
            duration=seconds(end,start)
            runtime=next(z['payload'] for z in data['Q12'] if z['run_id']==rid and z['phase']==phase)
            assert runtime['input_contract']['architecture']==c['architecture']
            assert runtime['optimizer_class'].lower()==c['optimizer']
            pr=dict(run_id=rid,architecture=c['architecture'],optimizer=c['optimizer'],phase=phase,epochs=len(pe),
                    max_epochs=max_epochs,best_epoch_zero_based=early['best_epoch'],stopped_epoch_zero_based=early['stopped_epoch'],
                    early_stopped=stopped,event_started_at=start,event_finished_at=end,event_wall_seconds=duration,
                    event_seconds_per_epoch=duration/len(pe),runtime=runtime,phase_record=p)
            phases.append(pr);phase_rows.append(pr)
        counts=Counter(e['phase'] for e in es)
        warnings=['No hay telemetría de uso CPU/GPU ni energía; gpu_available no prueba dispositivo efectivo.']
        if raw['completed_epochs']!=len(es):
            warnings.append('runs.completed_epochs difiere del recuento canónico; no se modifica.')
        row=dict(run_id=rid,campaign_id=CAMPAIGN,member_id=c['member_id'],attempt_id=c['attempt_id'],position=c['position'],
                 architecture=c['architecture'],optimizer=c['optimizer'],seed=c['seed'],
                 member_configuration_hash=c['member_configuration_hash'],run_configuration_hash=c['run_configuration_hash'],
                 started_at=raw['started_at'],finished_at=raw['finished_at'],duration_seconds=raw['duration_seconds'],
                 wall_seconds=raw['wall_seconds'],duration_difference_seconds=raw['duration_difference_seconds'],
                 epochs_completed=len(es),epochs_base=counts['base'],epochs_fine_tuning=counts['fine_tuning'],
                 seconds_per_epoch=raw['wall_seconds']/len(es),completed_epochs_stored=raw['completed_epochs'],
                 early_stopped_phases=sum(p['early_stopped'] for p in phases),
                 recall=m['recall_parasitized'],specificity=m['specificity'],f1=m['f1_parasitized'],f2=m['f2_parasitized'],
                 roc_auc=m['roc_auc_parasitized'],pr_auc=m['pr_auc_parasitized'],threshold=m['threshold_used'],
                 tn=m['tn'],fp=m['fp'],fn=m['fn'],tp=m['tp'],sample_count=m['sample_count'],
                 clinical_objective_met=m['recall_parasitized']>D('0.98'),
                 clinical_objective_met_stored=raw['completion']['clinical_objective_met'],
                 checkpoint_policy_satisfied=raw['completion']['selection']['policy_satisfied'],
                 evaluation_id=m['evaluation_id'],clinical_metric_id=m['run_clinical_metric_id'],evaluation_source_event_id=m['source_event_id'],
                 selected_artifact_id=a['id'],selected_checkpoint=a['name'],selected_epoch=a['metadata']['epoch'],
                 selected_phase=a['metadata']['phase'],selected_checkpoint_sha256=a['checksum'],selected_checkpoint_path=a['path'],
                 gpu_available_stored=raw['gpu_available'],gpu_devices_stored=raw['gpu_devices'],
                 peak_cpu_memory_bytes=raw['peak_cpu_memory_bytes'],peak_gpu_memory_bytes=raw['peak_gpu_memory_bytes'],
                 checkpoint_event_intervals_seconds=sum(e['checkpoint_event_interval_seconds'] for e in es),
                 postselection_prediction_intervals_seconds=sum(e['postselection_prediction_interval_seconds'] for e in es),
                 runtime_environment=raw['execution_parameters']['runtime_environment'],
                 campaign_environment=campaign['environment'],scientific_configuration=rc,
                 campaign_configuration=c['campaign_configuration'],execution_parameters=raw['execution_parameters'],
                 phase_details=phases,metric_validation=checked,final_validation_record=m,
                 completion=raw['completion'],verification=raw['verification'],warnings=warnings)
        assert row['clinical_objective_met']==row['clinical_objective_met_stored']
        runs.append(row)
    assert all(p==populations[0] for p in populations)
    assert len(runs)==len(links)==len(metrics)==len(prediction_rows)==12
    assert {(r['architecture'],r['optimizer']) for r in runs}=={(a,o) for a in ['custom_cnn','densenet121','vgg16'] for o in ['adam','adamw','sgd','adadelta']}
    assert all(v==0 for k,v in data['Q14'][0].items() if k not in ['members','runs','unique_pairs'])
    epoch_artifacts=[]
    for epoch in epochs:
        rid,phase,key=epoch['run_id'],epoch['phase'],epoch['source_record_key']
        rec=record_artifacts[(rid,phase,key)]; a=rec['payload'];run=next(r for r in runs if r['run_id']==rid)
        selected=a['epoch']==run['selected_epoch']
        projection=artifacts[run['selected_artifact_id']] if selected else None
        if projection:
            assert a['sha256']==projection['checksum'] and a['bytes']==projection['file_size_bytes']
        epoch_artifacts.append(dict(run_id=rid,architecture=run['architecture'],optimizer=run['optimizer'],
            phase=phase,epoch=a['epoch'],phase_epoch=a['phase_epoch'],source_table='train_execution_records',
            source_kind='artifact',source_record_key=key,source_created_at=rec['created_at'],
            version_id=a['version_id'],path=a['path'],file_size_bytes=a['bytes'],sha256=a['sha256'],
            selected=selected,artifact_id=projection['id'] if projection else None,
            artifact_status=projection['artifact_status'] if projection else None,
            catalog_projection=projection,source_payload=a))
    assert len(epoch_artifacts)==len(epochs)==396 and sum(a['selected'] for a in epoch_artifacts)==12
    total=sum(r['wall_seconds'] for r in runs)
    span=seconds(runs[-1]['finished_at'],runs[0]['started_at'])
    gaps=[seconds(b['started_at'],a['finished_at']) for a,b in zip(runs,runs[1:])]
    assert min(gaps)>=0 and sum(gaps)==span-total
    summary=dict(campaign_id=CAMPAIGN,campaign_name=campaign['name'],state=campaign['state'],dataset_version_id=campaign['dataset_version_id'],
        runs=12,architectures=3,optimizers=4,unique_pairs=12,seed=47,epochs=396,base_epochs=263,fine_tuning_epochs=133,
        first_run_started_at=runs[0]['started_at'],last_run_finished_at=runs[-1]['finished_at'],
        sum_run_seconds=total,run_span_seconds=span,inter_run_gap_seconds=sum(gaps),
        creation_to_last_run_seconds=seconds(runs[-1]['finished_at'],campaign['created_at']),
        sum_run_hours=total/D(3600),span_hours=span/D(3600),clinical_objective_passes=sum(r['clinical_objective_met'] for r in runs),
        phase_count=len(phase_rows),early_stopped_phase_count=sum(p['early_stopped'] for p in phase_rows),
        epoch_artifact_count=396,selected_artifact_count=12,
        epoch_artifact_bytes=sum(a['file_size_bytes'] for a in epoch_artifacts),
        selected_artifact_bytes=sum(a['file_size_bytes'] for a in epoch_artifacts if a['selected']),
        checkpoint_event_intervals_seconds=sum(e['checkpoint_event_interval_seconds'] for e in epochs),
        postselection_prediction_intervals_seconds=sum(e['postselection_prediction_interval_seconds'] for e in epochs),
        query_row_counts={q['id']:len(data[q['id']]) for q in QUERIES},
        integrity=data['Q14'][0],source_coverage=data['Q13'],evaluation_coverage=data['Q15'],
        snapshot=data['Q16'][0],dataset_version=campaign['dataset_version'],dataset_snapshot=campaign['dataset_snapshot'],
        campaign_protocol=campaign['protocol'],campaign_requested=campaign['requested'],
        campaign_environment=campaign['environment'],runtime_environment=runs[0]['runtime_environment'])
    write_csv('runs.csv',runs);write_csv('epochs.csv',epochs);write_csv('artifacts.csv',epoch_artifacts);write_csv('campaign_summary.csv',[summary])
    write_documents(data,runs,epochs,phase_rows,summary)
    # Re-read the final CSV to catch serialization, counts and precision regressions.
    loaded=list(csv.DictReader((OUT/'runs.csv').open()))
    assert len(loaded)==12 and sum(D(r['wall_seconds']) for r in loaded)==total
    assert sum(int(r['epochs_completed']) for r in loaded)==396
    print(f'PASS: 12 configuraciones, 396 épocas, 12 métricas VAL verificadas desde scores; {total} segundos.')


def write_documents(data: dict[str,list[dict[str,Any]]], runs: list[dict[str,Any]], epochs: list[dict[str,Any]],
                    phases: list[dict[str,Any]], summary: dict[str,Any]) -> None:
    banner='Estado documental: `HISTORICAL_AUDIT` — evidencia histórica B1; no autoriza entrenamientos ni comparación causal CPU/GPU.\n'
    snapshot=data['Q16'][0]['snapshot_at']
    fast=min(runs,key=lambda r:r['wall_seconds']);slow=max(runs,key=lambda r:r['wall_seconds'])
    best_recall=max(runs,key=lambda r:r['recall']);best_f2=max(runs,key=lambda r:r['f2']);best_f1=max(runs,key=lambda r:r['f1'])
    label=lambda r:f"{r['architecture']} / {r['optimizer']}"
    result_table=table(['Arquitectura','Optimizador','Épocas','Base','FT','Total s','s/época*','Recall','Specificity','F1','F2','ROC-AUC','PR-AUC (AP)','Checkpoint / fase'],[
        [r['architecture'],r['optimizer'],r['epochs_completed'],r['epochs_base'],r['epochs_fine_tuning'],fmt(r['wall_seconds'],6),fmt(r['seconds_per_epoch'],3),
         *[fmt(r[k],6) for k in ['recall','specificity','f1','f2','roc_auc','pr_auc']],f"{r['selected_checkpoint']} / {r['selected_phase']}"] for r in runs])
    aggregates=[]
    for architecture in ['custom_cnn','densenet121','vgg16']:
        rs=[r for r in runs if r['architecture']==architecture]
        aggregates.append([architecture,sum(r['epochs_completed'] for r in rs),sum(r['wall_seconds'] for r in rs)/3600,
                           sum(r['wall_seconds'] for r in rs)/sum(r['epochs_completed'] for r in rs),
                           f"{min(r['recall'] for r in rs):.6f}–{max(r['recall'] for r in rs):.6f}",
                           f"{min(r['specificity'] for r in rs):.6f}–{max(r['specificity'] for r in rs):.6f}"])
    arch_table=table(['Arquitectura','Épocas','Horas RUN acumuladas','s/época ponderados*','Rango recall','Rango specificity'],aggregates)
    phase_table=table(['Arquitectura','Optimizador','Fase','Épocas / máximo','Best (0-based)','Stopped (0-based)','EarlyStopping','Intervalo fase s','s/época fase*'],[
        [p['architecture'],p['optimizer'],p['phase'],f"{p['epochs']} / {p['max_epochs']}",p['best_epoch_zero_based'],p['stopped_epoch_zero_based'],
         'sí' if p['early_stopped'] else 'no; límite',p['event_wall_seconds'],p['event_seconds_per_epoch']] for p in phases])
    checkpoint_total=summary['checkpoint_event_intervals_seconds'];prediction_total=summary['postselection_prediction_intervals_seconds']
    maximum_error=max(v for r in runs for v in r['metric_validation']['absolute_errors'].values())
    findings=f'''# HALLAZGOS B1 — 12 entrenamientos históricos

{banner}
Snapshot de PostgreSQL: `{snapshot}`. Fuentes: [SQL_B1.md](SQL_B1.md); datos sin redondeo de presentación en los cuatro CSV. Las tablas Markdown redondean sólo para lectura.

## A. Resumen ejecutivo

Se reconstruyó la campaña **Campaña 1**, `{CAMPAIGN}`, finalizada, para caracterizar duración, aprendizaje y resultados VALIDATION de las 12 combinaciones de `custom_cnn`, `densenet121`, `vgg16` con `adam`, `adamw`, `sgd`, `adadelta`. Una ejecución por combinación y una única semilla **47**: no hay réplicas que permitan estimar variabilidad entre semillas.

Dataset **Malaria Patient Split v1**, versión `1.0.0`, estado `FROZEN`, ID `{summary['dataset_version_id']}`. El contrato registrado informa 27.558 imágenes: 22.180 TRAIN, 2.693 VAL y 2.685 reservadas TEST, agrupadas por paciente (161/20/20 respectivamente). La reconstrucción utilizó las 2.693 predicciones VAL de cada checkpoint: 1.325 parasitized y 1.368 uninfected. Las asignaciones de pacientes son evidencia del contrato persistido, no una nueva auditoría de las imágenes.

Entorno runtime registrado: **MacBook-Pro-de-Julio.local, Darwin, arm64, local_python; Python 3.12.13, TensorFlow 2.17.1, Keras 3.15.1, NumPy 1.26.4**. La CPU exacta, RAM física y número de núcleos no constan en estos registros. La etiqueta `cpu_historical` identifica esta línea base; `gpu_available=false` y `gpu_devices=[]` no certifican el dispositivo que ejecutó cada operación. No hay medición de utilización CPU/GPU ni benchmark Metal.

Se completaron **396 épocas: 263 base y 133 fine-tuning**. La suma de duración de RUNS es **{summary['sum_run_seconds']} s ({summary['sum_run_hours']:.6f} h)**. Desde `{summary['first_run_started_at']}` hasta `{summary['last_run_finished_at']}` transcurrieron **{summary['run_span_seconds']} s ({summary['span_hours']:.6f} h)**, incluidos **{summary['inter_run_gap_seconds']} s** entre RUNS. No hay solapamientos temporales entre los 12 RUNS. Desde la creación de la campaña al último término: {summary['creation_to_last_run_seconds']} s; esta cifra incluye espera previa y no es tiempo de entrenamiento.

La menor duración corresponde a **{label(fast)}** ({fast['wall_seconds']} s, {fast['epochs_completed']} épocas), la mayor a **{label(slow)}** ({slow['wall_seconds']} s, {slow['epochs_completed']} épocas). VGG16 presenta mayor tiempo medio por época que las otras arquitecturas. Ninguna configuración supera el objetivo de sensibilidad **estrictamente > 0,98**, al umbral histórico 0,5. El mayor recall es **{best_recall['recall']:.6f}** ({label(best_recall)}), con specificity **{best_recall['specificity']:.6f}**.

## B. Metodología

Auditoría retrospectiva, descriptiva, sin entrenar, cargar checkpoints, ejecutar inferencia, TEST ni EXPLAIN. PostgreSQL es la fuente de resultados; todos los SELECT finales se ejecutaron en una única transacción `REPEATABLE READ READ ONLY`, terminada con `ROLLBACK`. Q01–Q17 describen la extracción; [report.md](report.md) concentra el procedimiento reproducible y las comprobaciones.

**Selección.** Se identificó la única campaña y se conservaron todos sus miembros, intentos y RUNS. Los 12 son `training/completed`, con intento aceptado y sesión `verified`. No se excluyó ninguna combinación ni se filtró por desempeño clínico. Para métricas finales se exige `evaluations.split='val'` y `evaluation_role='training_validation_final'`; otras fases y eventos de métricas no se mezclan con ese resultado.

**Identificación semántica.** `run_configurations.architecture` y `.optimizer` coinciden en los 12 casos con `campaign_configurations.configuration.model_id` y `.resolved.optimizer.name`, con `runs.execution_parameters.model_configuration_e2.configuration` y con la configuración compilada del runtime (Q04/Q12). `models.architecture` contiene etiquetas descriptivas, como “Custom CNN”; `models.name` coincide con el identificador canónico. El `model_id` JSON es un nombre de arquitectura, mientras `runs.model_id` es un UUID de catálogo. `campaign_members` aporta semilla, posición y hash, no nombres de arquitectura/optimizador. El JOIN de configuración de campaña utiliza **campaign_id + configuration_hash**.

Los hashes de configuración de miembro y RUN son diferentes en los 12 casos: no deben equipararse ni usarse como JOIN entre esas tablas. Se comprobó que el SHA-256 del `run_configurations.canonical_configuration` coincide con su hash y que ese JSON es el `resolved` del RUN; la configuración de ejecución coincide con la de campaña al quitar únicamente la semilla 47 del miembro. Se preservan ambos hashes y snapshots en `runs.csv`.

**Duración.** `wall_seconds = EXTRACT(EPOCH FROM finished_at-started_at)` coincide exactamente con `runs.duration_seconds` en 12/12 casos. Es tiempo de pared del RUN: incluye inicialización, entrenamiento, validación, checkpoints, persistencia y cierre. `seconds_per_epoch = wall_seconds / número de registros kind='epoch'`. Es un promedio amortizado, no tiempo de kernel ni de `model.fit` aislado. Las divisiones se calculan con Decimal de 50 cifras significativas; los numeradores y denominadores se conservan para recuperar precisión arbitraria.

**Épocas y fases.** Se cuentan `train_execution_records(kind='epoch')` por RUN y fase, comprobando unicidad, secuencia global 1…N y local 1…N_fase. Los eventos canónicos `e10_event` no se vuelven a contar como épocas. Los conteos coinciden con los cierres `kind='phase'` y `train_execution_sessions.completion.epochs`. `training_history`, `run_metrics` y `run_checkpoint_policy` están vacíos. En **5/12 RUNS** `runs.completed_epochs=0` contradice la evidencia de épocas; en los otros 7 coincide. `runs.total_epochs`, `best_epoch`, `stopped_epoch` y `fine_tuning_start_epoch` están ausentes en los 12. Se informa la discrepancia sin reparar el histórico.

**EarlyStopping y selección.** Máximo base 100; fine-tuning 0 para Custom CNN y 20 para DenseNet121/VGG16. EarlyStopping activado, paciencia 12, min_delta 0,00001, restauración de mejores pesos. El monitor científico declarado es `val_f2_parasitized`; el callback compilado monitoriza `val_early_stopping_score`. Los índices `best_epoch` y `stopped_epoch` de los cierres de fase son locales y base cero, mientras que `payload.epoch` y `artifacts.metadata.epoch` son globales y base uno. `stopped_epoch=0` en las tres fases que completan 20 épocas significa que no se activó la detención. No se usa ese cero como cero épocas. La selección final se verifica por ID de artefacto, hash, época y evento de evaluación; no se asume que sea la última época ni que el mejor epoch local determine por sí solo el checkpoint final.

**Validación de métricas.** Q08 enlaza `run_clinical_metrics → evaluations → artifacts`; Q17 recupera las predicciones VAL persistidas de la época seleccionada. Se reconstruyeron las 12 matrices de confusión al umbral 0,5 y se recalcularon recall, specificity, F1, F2, ROC-AUC y PR-AUC como **average precision no interpolada**, sin nueva evaluación del modelo. Los 12 conjuntos contienen las mismas identidades y etiquetas VAL. Error absoluto máximo frente al dato publicado: **{maximum_error}**, menor que 1e-12. Además se cotejaron las métricas clínicas con la época seleccionada. `val_auc`/`val_pr_auc` de Keras (200 umbrales interpolados) no sustituyen los valores clínicos `val_roc_auc_parasitized`/`val_pr_auc_parasitized` ni las métricas finales. No se calcularon intervalos de confianza ni significancia.

## C. Resultados

{result_table}

Nota: promedio de pared del RUN dividido por épocas observadas. No mide velocidad computacional aislada. UUID originales, checkpoints completos, matrices, valores y procedencia están en `runs.csv`; métricas de cada época en `epochs.csv`.

{arch_table}

El menor promedio amortizado es **{label(min(runs,key=lambda r:r['seconds_per_epoch']))}**, {min(r['seconds_per_epoch'] for r in runs):.3f} s/época; el mayor es **{label(max(runs,key=lambda r:r['seconds_per_epoch']))}**, {max(r['seconds_per_epoch'] for r in runs):.3f} s/época. Estos extremos no coinciden necesariamente con los de duración total. Custom CNN/AdamW termina antes principalmente porque ejecuta 14 épocas, frente a 31 de Custom CNN/SGD. No se interpreta esa diferencia como superioridad de velocidad de AdamW.

## D. Hallazgos científicos

### Arquitecturas y optimizadores

Custom CNN acumula {aggregates[0][2]:.3f} h; DenseNet121, {aggregates[1][2]:.3f} h; VGG16, {aggregates[2][2]:.3f} h. Los promedios ponderados son {aggregates[0][3]:.3f}, {aggregates[1][3]:.3f} y {aggregates[2][3]:.3f} s/época, respectivamente. DenseNet121 y Custom CNN tienen costos por época cercanos en este registro, pero usan distinto preentrenamiento y régimen de fases; esto no prueba equivalencia de complejidad ni de rendimiento puro. VGG16 presenta aproximadamente {aggregates[2][3]/aggregates[0][3]:.2f} veces el promedio ponderado de Custom CNN bajo estas configuraciones.

Dentro de Custom CNN, AdamW obtiene el mayor recall y F2, mientras Adadelta obtiene el mayor F1, specificity, ROC-AUC y AP. En DenseNet121, Adadelta supera descriptivamente a los otros optimizadores en recall, F1, F2, ROC-AUC y AP; Adam tiene la mayor specificity. En VGG16, SGD obtiene el mayor recall, Adadelta el mayor F2 y AdamW el mayor F1, ROC-AUC y AP; Adam y AdamW empatan en specificity. No hay un optimizador ganador para todas las métricas y arquitecturas.

Las tasas iniciales también cambian: Adadelta 1 (base/FT), Adam/AdamW 0,0001 y 0,00001, SGD 0,001 y 0,0001. Custom CNN no usa pesos preentrenados; DenseNet121/VGG16 usan ImageNet y configuración de 4 capas para fine-tuning. Batch 64 e imágenes 200×200×3 en todos. Hay augmentation y ReduceLROnPlateau. Por tanto, la comparación caracteriza recetas completas, no un efecto causal aislado del optimizador. Orden fijo de campaña, una semilla, ausencia de réplicas y estado térmico/carga desconocidos limitan las inferencias.

### EarlyStopping, variabilidad de épocas y fine-tuning

Las ejecuciones duran entre 14 y 67 épocas. EarlyStopping se activa en **17 de 20 fases**: las 12 base y 5 de las 8 de fine-tuning. DenseNet121 con Adam, AdamW y SGD consume las 20 épocas de fine-tuning; las otras fases se detienen antes del máximo. En las 17 fases detenidas, el cierre registra 12 épocas entre best y stopped. El ahorro en número de épocas no identifica por sí solo mayor velocidad ni mejor generalización.

Los tres checkpoints finales de fine-tuning son DenseNet121/Adadelta y VGG16/Adam y AdamW. Los otros cinco modelos con fine-tuning conservan un checkpoint base. Para esos cinco, el costo FT no produjo un checkpoint preferido por el criterio registrado; esto no demuestra inutilidad general de fine-tuning. DenseNet121/Adam invierte 67 épocas y {next(r['wall_seconds'] for r in runs if r['architecture']=='densenet121' and r['optimizer']=='adam')} s, pero selecciona época 35 base y recall 0,784151. La mayor duración no garantiza una mejor métrica final.

{phase_table}

Nota: intervalos entre `phase_started` y `phase_completed`; incluyen entrenamiento, validación, callbacks y persistencia dentro de la fase, pero no toda la inicialización/cierre del RUN. Los tiempos FT no deben extrapolarse a base: cambian capas entrenables y se reinicia el estado del optimizador, según Q12.

### Tiempo y objetivo clínico

El mayor recall ({label(best_recall)}, {best_recall['recall']:.6f}) coexiste con specificity {best_recall['specificity']:.6f}; el mayor F2 corresponde a {label(best_f2)} ({best_f2['f2']:.6f}) y el mayor F1 a {label(best_f1)} ({best_f1['f1']:.6f}). La diferencia entre objetivos impide declarar un único mejor modelo sin una regla explícita.

**0/12 cumplen sensibilidad >0,98** al umbral 0,5; con 1.325 positivos se necesitarían al menos 1.299 verdaderos positivos (como máximo 26 falsos negativos), frente a {best_recall['tp']} TP y {best_recall['fn']} FN en el mejor recall observado. El umbral no se recalibró. La campaña registra `clinical_objective_met=false` en los 12, aunque `selection.policy_satisfied=true`: ese flag técnico no acredita sensibilidad objetivo. No se afirma que otro umbral tampoco pudiera alcanzarla; eso exigiría otro análisis de selección, con su compromiso en specificity.

Son resultados exploratorios en VAL, reutilizada para EarlyStopping, selección y comparación, con posible optimismo por selección. No constituyen validación clínica externa ni desempeño confirmado en TEST. Las células del mismo paciente no son réplicas independientes y 12 configuraciones no equivalen a 12 réplicas del mismo experimento.

## E. Hallazgos técnicos

### Proceso local y costo observado

La evidencia runtime atribuye las 12 ejecuciones al mismo host local Darwin/arm64. La campaña registra Python 3.12.14/SQLAlchemy 2.0.52, pero el runtime informa **3.12.13/2.0.53**; también difieren hashes de código y `git_commit` (nulo en campaña, `8411be7e71944370d017c96cc277e2b844c3de6e` en runtime). No se sustituyó el entorno ejecutado por el declarado. Los campos planos de versión/plataforma de `runs` son nulos: se conservó la procedencia JSON explícita.

El costo medible es {summary['sum_run_hours']:.6f} horas de pared acumuladas. No hay watts, kWh, tarifa, tiempo CPU de proceso ni GPU activo: no se puede calcular costo energético o monetario. Los 396 artefactos por época suman **{summary['epoch_artifact_bytes']} bytes** declarados; los 12 seleccionados suman **{summary['selected_artifact_bytes']} bytes**. Son tamaños registrados, no medición del espacio físico actual ni prueba de que todos esos archivos sigan disponibles.

### Validación, checkpoints y límites de temporización

Hay 396 eventos de epoch, artifact_prepared, artifact_created, selection y predictions, además de 20 aperturas y 20 cierres de fase. El código histórico del commit registrado (`execution/train.py`, `PersistEpoch.on_epoch_end`) persiste la época, guarda el checkpoint, selecciona y recoge de nuevo predicciones VAL. Es consistente con la secuencia observada; no se usaron los cambios locales sin confirmar como prueba de comportamiento histórico.

Los intervalos **artifact_prepared → artifact_created** suman **{checkpoint_total:.6f} s** ({checkpoint_total/summary['sum_run_seconds']*100:.3f}% de la suma de RUNS). Incluyen serialización/guardado, identidad de archivo y envío/persistencia entre las marcas; no aíslan escritura a disco. Los intervalos **selection_completed → predictions_completed** suman **{prediction_total:.6f} s** ({prediction_total/summary['sum_run_seconds']*100:.3f}%). Incluyen la recolección adicional de predicciones VAL y persistencia posterior, pero **no toda la validación**: la validación de fit y el callback clínico ocurren antes del evento epoch. Las marcas proceden del reloj del emisor, no de un profiler monotónico. Se conservan los endpoints y diferencias por época en `epochs.csv`; no se atribuye el residual a entrenamiento puro ni se suman intervalos solapados para estimar overhead total.

### Persistencia, trazabilidad e instrumentación

La cadena miembro → intento aceptado → RUN → evaluación VAL → checkpoint es íntegra en las comprobaciones de Q14. Se verificaron las 12 combinaciones únicas y las 396 épocas sin duplicar la representación legacy/canónica. `artifacts` cataloga 12 checkpoints seleccionados; `train_execution_records(kind='artifact')` conserva evidencia de los 396. `artifacts.csv` contiene 396 filas, con el ID de catálogo sólo cuando existe (12); no se inventan IDs para el resto.

La cobertura incompleta de proyecciones (`completed_epochs`, tablas vacías, campos nulos) obliga a reconstruir resultados desde eventos y sesiones. `gpu_available=false` y `gpu_devices=[]` no incluyen método de detección ni trazas de colocación de operaciones. Los 12 RUNS carecen de `peak_cpu_memory_bytes` y `peak_gpu_memory_bytes`; tampoco hay uso de CPU/GPU, RAM máxima acreditada, temperaturas, energía ni duración de batch. No se certifica uso exclusivo de CPU ni ausencia efectiva de Metal con estos registros.

## F. Conclusiones

### Hallazgos demostrados

- Existen las 12 configuraciones esperadas, con una semilla 47, 396 épocas reconciliadas y 12 evaluaciones finales VAL trazables a su checkpoint.
- Las duraciones almacenadas coinciden exactamente con inicio/término. La suma es {summary['sum_run_seconds']} s; el intervalo global incluye {summary['inter_run_gap_seconds']} s entre ejecuciones.
- Se verificaron las seis métricas solicitadas desde scores históricos; 0/12 alcanzan sensibilidad estrictamente >0,98 al umbral 0,5.
- Se documentaron 17 fases detenidas por EarlyStopping, tres fases FT agotadas y sólo tres checkpoints finales FT.
- VGG16 presenta mayor costo amortizado por época en estas ejecuciones; cinco proyecciones de épocas completadas son inconsistentes con sus registros fuente.

### Inferencias razonables

- La distinta cantidad de épocas explica parte importante de las diferencias de duración total; el régimen FT y la arquitectura probablemente también contribuyen, sin aislar efectos.
- Guardar un checkpoint y persistir predicciones cada época añade costo observable; su impacto total requiere instrumentación dedicada.
- El runtime local arm64 y los flags sin GPU son compatibles con una línea base CPU, pero no suficientes para certificarla.

### Aspectos no demostrados

No se ha demostrado aceleración Metal, utilización efectiva de CPU/GPU, efecto causal de arquitectura/optimizador, consumo energético, significancia estadística, estabilidad entre semillas, mejora general por fine-tuning ni desempeño clínico fuera de VAL. Tampoco se revalidó la integridad física de checkpoints y dataset ni la equivalencia temporal del entorno de campaña y ejecución.

### Datos necesarios para la comparación GPU Metal

Conservar UUID/hashes de dataset, población y configuración, arquitectura/optimizador, semilla, versiones, augmentation, precisión numérica, batch, preprocesamiento, política de checkpoint y EarlyStopping. Registrar chip/núcleos/RAM, macOS, TensorFlow y tensorflow-metal, dispositivos visibles y colocación efectiva, threads, carga concurrente, temperatura, memoria y energía. Usar tiempos monotónicos para carga/preprocesamiento, entrenamiento por batch/época, validación, checkpoints, persistencia e inicio/cierre; separar calentamiento y sincronización del dispositivo.

La comparación de **velocidad** necesita presupuestos y fases equivalentes, calentamiento y repeticiones con orden alternado; la comparación de **tiempo hasta criterio** debe mantener la política y reportar cantidad de épocas/métricas, pues Metal puede cambiar trayectorias numéricas. Calcular speedup = tiempo_CPU / tiempo_Metal sólo con trabajos equivalentes y dispositivo acreditado, separando base y FT, y mostrar dispersión. Mantener TEST reservado según el protocolo. Este B1 sirve como referencia histórica reproducible, con limitación explícita de certificación CPU; puede requerir una línea base CPU futura instrumentada para una comparación controlada. No se inició ninguna de esas ejecuciones.
'''
    (OUT/'HALLAZGOS_B1.md').write_text(findings)
    repro='''Desde la raíz del repositorio, con PostgreSQL ya activo en Docker:

```sh
python3 scripts/benchmarks/b1_historical.py
```

Usa sólo la biblioteca estándar de Python y `docker compose exec -T db … psql`. No inicia servicios ni importa TensorFlow. Abre `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`, verifica `transaction_read_only=on` y termina con `ROLLBACK`. Las credenciales se resuelven dentro del contenedor; no se imprimen. El proceso escribe únicamente los entregables locales. Si cambia la evidencia, las aserciones detienen la generación ante cardinalidades o semántica inesperadas. `--snapshot /tmp/b1_snapshot.json` permite guardar temporalmente los resultados de SELECT y `--from-snapshot /tmp/b1_snapshot.json` regenerar desde esa captura (incluye identidades de muestras VAL; no se publica como entregable).
'''
    provenance=table(['Archivo','Filas','Fuente y contenido'],[
        ['campaign_summary.csv',1,'Q01/Q03/Q13–Q16 y agregados; dataset, protocolo, entorno, conteos e integridad'],
        ['runs.csv',12,'Q04/Q05/Q07/Q08/Q12/Q17; identidades, tiempos, configuración, métricas y validación'],
        ['epochs.csv',396,'Q06/Q11; métricas sin redondeo, índices de fase, eventos y diferencias temporales'],
        ['artifacts.csv',396,'Q09/Q10; artefactos por época, 12 seleccionados con artifact_id de catálogo']])
    report=f'''# B1 — Reporte reproducible de resultados

{banner}
Snapshot: `{snapshot}`. Base `{data['Q16'][0]['database']}`; {data['Q16'][0]['server_version']}. Resultado: **auditoría B1 completada con limitaciones explícitas de instrumentación; no certifica benchmark CPU puro ni comparación GPU**.

## Reproducción

{repro}

Código de extracción: [b1_historical.py](../../../scripts/benchmarks/b1_historical.py); catálogo: [b1_queries.py](../../../scripts/benchmarks/b1_queries.py); fórmulas y generación: [b1_report.py](../../../scripts/benchmarks/b1_report.py). SQL completo y explicación de JOIN: [SQL_B1.md](SQL_B1.md). Interpretación científica/técnica y tablas de métricas: [HALLAZGOS_B1.md](HALLAZGOS_B1.md).

## Entregables y procedencia

{provenance}

Los CSV son UTF-8 con encabezado y JSON dentro de celdas estructuradas. Celda vacía representa ausencia, no cero; las estructuras JSON conservan null. Se preservan numeric de PostgreSQL con Decimal, sin convertir a float, y timestamps UTC con microsegundos. Los cocientes no terminantes usan precisión Decimal de 50 cifras; CSV conserva también sus componentes. Segundos para tiempo, bytes para tamaño/memoria, proporciones [0,1] para métricas. No se redondean los valores fuente para presentación en CSV.

## Identidad de los 12 RUNS

{table(['Posición','Arquitectura','Optimizador','RUN UUID','Miembro UUID','Intento UUID'],[[r['position'],r['architecture'],r['optimizer'],r['run_id'],r['member_id'],r['attempt_id']] for r in runs])}

## Totales verificados

{table(['Medida','Valor'],[[k,summary[k]] for k in ['sum_run_seconds','run_span_seconds','inter_run_gap_seconds','epochs','base_epochs','fine_tuning_epochs','phase_count','early_stopped_phase_count','clinical_objective_passes','epoch_artifact_count','selected_artifact_count']])}

Todas las selecciones de miembros se conservaron, sin exclusiones por métrica o duración. Los 12 RUNS tienen un intento aceptado y no se observan reintentos adicionales. Las consultas de métricas seleccionan sólo la evaluación final de VALIDATION; no ejecutan evaluación alguna.

## Comprobaciones ejecutadas

- 12 pares únicos = producto cartesiano 3×4, semilla 47, arquitectura/optimizador coincidentes entre configuración normalizada, campaña, snapshot de ejecución y runtime compilado.
- Claves e integridad Q14: `{dumps(data['Q14'][0])}`.
- Configuración RUN: SHA-256 válido, JSON canónico igual a resolved; configuración de campaña igual a ejecución salvo seed.
- 396 épocas globales y locales contiguas, cierres de 20 fases y completion coherentes; no se deduplicó ocultando conflictos.
- 12 duraciones positivas con diferencia exactamente cero entre campo duration y resta de timestamps; ningún solapamiento entre RUNS.
- 12 matrices de confusión reconstruidas, mismo conjunto de 2.693 identidades/etiquetas VAL, seis métricas recalculadas desde scores con tolerancia 1e-12 (máximo error {maximum_error}).
- Artefacto seleccionado conciliado entre evaluación, catálogo, registro por época y completion por SHA-256, tamaño, versión, época y source_event_id.
- 2.044 eventos canónicos con secuencias contiguas y tiempos no decrecientes; intervalos derivados no negativos.
- Relectura de CSV: 12 RUNS, suma exacta {summary['sum_run_seconds']} s y 396 épocas.

## Advertencias y alcance

Cinco valores `runs.completed_epochs=0` son inconsistentes; los otros siete coinciden. `training_history`, `run_metrics`, `run_checkpoint_policy`, `execution_logs` y `environment_packages` tienen cero filas para esta campaña. Los campos planos de entorno están vacíos, por lo que se conserva `execution_parameters.runtime_environment`. El entorno declarado difiere del registrado en ejecución. El flag `policy_satisfied` no implica objetivo clínico logrado. Se mantienen estas advertencias sin editar registros históricos.

No se verificaron archivos físicos ni se ejecutaron nuevas cargas de imágenes/modelos. `gpu_available=false` carece de telemetría de colocación: la aprobación documental de B1 no acredita ejecución exclusivamente CPU. Análisis descriptivo de una semilla y VAL reutilizada; no equivale a validación clínica o inferencia causal. La futura comparación Metal requiere la instrumentación detallada en HALLAZGOS_B1.

## Huellas de los CSV

SHA-256 del contenido exportado, para verificar que documentos y datos pertenecen a esta entrega:

{table(['Archivo','SHA-256'],[[name,hashlib.sha256((OUT/name).read_bytes()).hexdigest()] for name in ['campaign_summary.csv','runs.csv','epochs.csv','artifacts.csv']])}
'''
    (OUT/'report.md').write_text(report)
    sql_doc=f'''# SQL B1 — Consultas verificadas y transformaciones

{banner}
Snapshot principal: `{snapshot}`. Todas las consultas Q01–Q17 se ejecutaron exitosamente contra el esquema real; no hay DDL, DML, TEST ni EXPLAIN. Los nombres y columnas se verificaron con Q02. Los resultados se obtuvieron en una sola transacción de lectura repetible. Las proyecciones usan el estado existente: no se corrigió PostgreSQL.

## Ejecución y seguridad

{repro}

Cada bloque SELECT puede ejecutarse en psql dentro de esta envoltura de sesión (no modifica datos):

```sql
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SET LOCAL statement_timeout='120s';
-- Ejecutar aquí los SELECT del catálogo.
ROLLBACK;
```

El exportador agrega cada resultado con json_agg y lo transporta en un objeto JSON que contiene su identificador literal y sus filas; usa coalesce con un array vacío para fuentes sin registros. Esta envoltura de transporte está implementada en b1_historical.py y no altera los JOIN ni los valores. Q16 verificó read_only=`{data['Q16'][0]['read_only']}` e isolation=`{data['Q16'][0]['isolation']}`. Las consultas diagnósticas previas se ejecutaron con `PGOPTIONS=-c default_transaction_read_only=on`; se registran al final por separado.

## Catálogo de extracción

'''
    for q in QUERIES:
        rows=data[q['id']]
        fields=', '.join(f'`{k}`' for k in rows[0]) if rows else 'Sin filas; columnas indicadas por SELECT y Q02.'
        sql_doc+=f"""### {q['id']} — {q['objective']}

- **Objetivo:** {q['objective']}.
- **Tablas:** {q['tables']}.
- **JOIN:** {q['joins']}
- **Campos recuperados:** {fields}
- **Resultado:** {len(rows)} filas.
- **Validaciones:** {q['validation']}

```sql
{q['sql']};
```

"""
    sql_doc+='''## Transformaciones Python y fórmulas

Se ejecutan en `scripts/benchmarks/b1_report.py`; no entrenan ni infieren. Las fuentes temporales y métricas originales se conservan en los CSV.

1. **Identificación:** arquitectura/optimizador normalizados se contrastan con campaign_configuration, execution_parameters y runtime. No se extraen de run_name ni se interpreta models.architecture como código de arquitectura. Se conserva el JOIN compuesto campaña/hash. El hash de RUN corresponde al JSON resolved con seed; se valida SHA-256 del texto canónico y equivalencia estructural, sin igualarlo al hash del miembro.
2. **Épocas:** N = número de filas Q06 por run; N_base/N_FT por phase. Se exige `(run_id,phase,record_key)` único y epoch global 1…N; `phase_epoch` 1…N_fase. Se coteja Q07 y completion de Q05. No se utiliza `runs.completed_epochs` como fuente principal. No se suman legacy y e10_event.
3. **Duración:** `wall_seconds = finished_at-started_at` en segundos UTC; Q05 calcula EXTRACT(EPOCH). Python convierte timedelta exactamente con días×86400 + segundos + microsegundos/1e6. `seconds_per_epoch = wall_seconds/N`. `sum_run_seconds=Σ wall_seconds`; `run_span_seconds=max(finished_at)-min(started_at)`. Las pausas son Σ(inicio siguiente−fin anterior), sólo tras comprobar ausencia de solapamientos; sum_run_seconds+pausas=span. Desde creación se usa último fin−campaign.created_at y se etiqueta espera incluida.
4. **Fases:** inicio/fin por occurred_at de `phase_started` y `phase_completed` en Q11, con referencia legacy runtime/phase. `phase_event_seconds_per_epoch=(fin-inicio)/N_fase`; no incluye todo el RUN. EarlyStopping se identifica por stopped_epoch>0, verificando stopped_epoch+1=N_fase; best/stopped son locales 0-based. Cuando stopped_epoch=0 y se alcanza máximo no se declara parada anticipada. No se identifica el checkpoint con ese índice local.
5. **Intervalos por época:** `event_interval_seconds=occurred_at(epoch actual)−occurred_at(epoch anterior de misma fase)`; para primera época se usa phase_started. Incluye guardado y callbacks de la época anterior y trabajo previo al evento actual; no representa duración pura de esa época. `checkpoint_event_interval_seconds=artifact_created−artifact_prepared`. `postselection_prediction_interval_seconds=predictions_completed−selection_completed`. Se unen por run/fase/record_key, se conservan endpoints y se exige diferencia no negativa. Estos intervalos no aíslan todo el overhead y no se restan del RUN para inventar tiempo de cómputo.
6. **Métricas finales:** se mantienen los valores originales Q08. Para validar Q17, clase positiva parasitized=1, predicción positiva score≥0,5. Matriz filas reales [0,1], columnas predichas [0,1]: [[TN,FP],[FN,TP]]. Recall=TP/(TP+FN), specificity=TN/(TN+FP), F1=2TP/(2TP+FP+FN), F2=5TP/(5TP+4FN+FP). Ambos soportes son positivos (1325/1368); no se reemplazan denominadores nulos por cero. ROC-AUC: Σ_por_score(pos_en_grupo×(neg_de_score_inferior+0,5×neg_en_grupo))/(P×N), equivalente a comparación por pares con empate a mitad. AP=Σ_por_score_descendente[(pos_en_grupo/P)×(TP_acumulado/n_acumulado)], agrupando empates; no se integra trapecio de PR. Error absoluto=|recalculado−publicado|, tolerancia 1e-12. Se conserva el detalle en `runs.metric_validation`. No se confunden AUC aproximadas de Keras con AUC clínica final.
7. **Objetivo:** recall>0,98, sin redondear; umbral fijo 0,5. Se compara con completion.clinical_objective_met y no con selection.policy_satisfied. Los resultados corresponden al checkpoint enlazado en evaluations, no a la última época.
8. **Agregados:** horas=segundos/3600; promedio ponderado por arquitectura=Σsegundos/Σépocas; rangos=min/max entre sus cuatro recetas, no IC. Porcentaje de intervalo=100×Σintervalos/Σsegundos_RUN. Bytes=Σtamaños declarados por epoch artifact; seleccionado si su época global coincide con el artefacto evaluado. No se inventa artifact_id donde no existe proyección.
9. **Precisión:** json.loads(parse_float=Decimal), Decimal con precisión 50; numeric fuente conservado sin redondeo de presentación. JSON estructurado se serializa manteniendo números, no cadenas para decimales. Divisiones no terminantes están necesariamente limitadas a 50 cifras y los datos base permiten recalcularlas. Markdown redondea; CSV no usa ese formateo. Vacíos son ausencia, no cero.
10. **Controles:** aserciones de cardinalidad, integridad, población VAL compartida, checksum/configuración, secuencia y reconciliación. Los datos faltantes conocidos generan advertencias y se preservan; inconsistencias nuevas de identidad, duración, métricas o conteos abortan. No se excluyen RUNS por bajo recall, EarlyStopping o costo. `training_history` vacío no implica cero épocas.

## Cobertura de fuentes observada

'''+table(['Fuente','Filas'],[[r['source'],r['rows']] for r in data['Q13']])+'\n'
    sql_doc+='\n## Consultas diagnósticas previas (trazabilidad de exploración)\n\nEstos SELECT se ejecutaron durante el descubrimiento del esquema y datos. Los conteos de filas se volvieron a comprobar en la transacción final mediante SELECT count(*) FROM (consulta) q; son conteos del resultado, no necesariamente de la tabla. Las muestras LIMIT sin ORDER BY no fijan una identidad reproducible: sólo se usaron para inspeccionar estructura. Los resultados publicados provienen del catálogo Q, con selección explícita.\n\n'
    for q in DIAGNOSTICS:
        sql_doc+=f"### {q['id']} — {q['objective']}\n\n- **Objetivo:** {q['objective']}.\n- **Tablas:** {q['tables']}.\n- **JOIN:** {q['joins']}\n- **Campos:** {q['fields']}.\n- **Resultado:** {data[q['id']][0]['result_rows']} filas.\n- **Validaciones:** {q['validation']}\n\n```sql\n{q['sql']};\n```\n\n"
    sql_doc+='''### Incidencia diagnóstica descartada

Una llamada preliminar a `jsonb_object_keys(payload->'canonical_event')` (sobre train_execution_records, kind='e10_event', LIMIT 20, alias key) falló con `cannot call jsonb_object_keys on a scalar`. No produjo datos ni se usó para calcular resultados. D22 comprobó que el campo es una cadena JSON; Q11 utiliza `(payload->>'canonical_event')::jsonb` y fue ejecutada satisfactoriamente para 2.044 eventos. La expresión fallida se conserva sólo como incidente, no como consulta ejecutable del experimento.

La primera lectura local de los resultados JSON del catálogo también falló al asumir una línea por resultado: json_agg puede incluir saltos de línea. Se corrigió el lector con JSONDecoder.raw_decode y se repitió la extracción. No hubo cambios en PostgreSQL y sólo la captura íntegra verificada generó los entregables.
'''
    (OUT/'SQL_B1.md').write_text(sql_doc)
