"""Derived audit artifacts from immutable PostgreSQL snapshots; never loads a model."""
from pathlib import Path
import json, csv, math, statistics, os
B=Path(__file__).resolve().parent
COHORT='eb7ae3da-c954-4f2f-8d19-0398824089c5'
CHAMPION='db31b6af-c2a2-44f0-9316-8f8c3492c0f1'
def read(n):return json.loads((B/(n+'.json')).read_text())
def writecsv(n,rows):
    with (B/(n+'.csv')).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def finite(v):return isinstance(v,(int,float)) and math.isfinite(v)
def diff(a,b):return a-b if finite(a) and finite(b) else None
def f2(p,r):return 5*p*r/(4*p+r) if finite(p) and finite(r) and 4*p+r else (0 if p==r==0 else None)
def mean(v):return statistics.mean(v) if v else None
def sd(v):return statistics.stdev(v) if len(v)>1 else None
runs=read('runs');sessions={s['run_id']:s for s in read('sessions')}
campaigns={r['id']:r['campaign_id'] for r in read('campaigns')['run_campaigns']}
epochs={};phases={}
for e in read('epochs'):
    (epochs if e['kind']=='epoch' else phases).setdefault(e['run_id'],[]).append({'phase':e['phase'],**e['payload']})
assessments=read('assessment_summary'); counts={a['attempt_id']:a for a in read('assessment_counts')}
# Validate every persisted verified attempt against SQL aggregates, including outside cohort.
for a in assessments:
    cm=counts[a['attempt_id']];m=a['verification']['metrics']
    assert all(cm[k]==m[k] for k in ['tn','fp','fn','tp'])
    assert cm['rows']==a['verification']['count']
    assert cm['threshold_min']==cm['threshold_max']==a['identity']['decision']['effective']
for run_id,ps in phases.items():
    for phase in ps:
        actual=sorted(e['phase_epoch'] for e in epochs[run_id] if e['phase']==phase['phase'])
        assert actual==list(range(1,phase['epochs']+1))
rows=[];flat=[]
for r in runs:
    es=sorted(epochs.get(r['id'],[]),key=lambda x:x['epoch']);s=sessions.get(r['id'],{});completion=s.get('completion') or {};c=(s.get('configuration') or {}).get('resolved',{});exe=c.get('execution',{});sel=completion.get('selection') or {}
    row={'run_id':r['id'],'model':r['model_name'],'status':r['status'],'campaign_id':campaigns[r['id']],'cohort':campaigns[r['id']]==COHORT and r['status']=='completed','optimizer':c.get('optimizer',{}).get('name'),'seed':exe.get('seed'),'dataset_version_id':r['dataset_version_id'],'session_state':s.get('state'),'epoch_count':len(es),'epochs_contiguous':bool(es) and [e['epoch'] for e in es]==list(range(1,len(es)+1)),'completion_epochs':completion.get('epochs'),'selected_epoch':sel.get('selected_epoch'),'checkpoint_monitor':sel.get('selected_metric'),'checkpoint_threshold':sel.get('threshold'),'configuration_hash':completion.get('training_completion',{}).get('configuration_hash')}
    for e in es:flat.append({'run_id':r['id'],'model':r['model_name'],'cohort':row['cohort'],'optimizer':row['optimizer'],'seed':row['seed'],**e})
    if es:
        last=es[-1];selected=next((e for e in es if e['epoch']==row['selected_epoch']),{});best=min(es,key=lambda e:e['val_loss']);finalphase=[e for e in es if e['phase']==last['phase']];phasebest=min(finalphase,key=lambda e:e['val_loss'])
        row.update(min_val_loss_epoch=best['epoch'],min_val_loss=best['val_loss'],final_phase_min_val_loss_epoch=phasebest['epoch'],final_phase_val_loss_rise=last['val_loss']-phasebest['val_loss'],final_phase_train_loss_change=last['loss']-phasebest['loss'])
        for prefix,e in [('selected',selected),('final',last)]:
            row.update({prefix+'_loss':e.get('loss'),prefix+'_val_loss':e.get('val_loss'),prefix+'_loss_gap':diff(e.get('val_loss'),e.get('loss')),prefix+'_accuracy':e.get('accuracy'),prefix+'_val_accuracy':e.get('val_accuracy'),prefix+'_accuracy_gap':diff(e.get('accuracy'),e.get('val_accuracy')),prefix+'_recall_gap':diff(e.get('recall_parasitized'),e.get('val_recall_parasitized')),prefix+'_f2_derived_train':f2(e.get('precision'),e.get('recall')),prefix+'_f2_gap_derived':diff(f2(e.get('precision'),e.get('recall')),e.get('val_f2_parasitized'))})
        row['auditor_last_epoch_heuristic']=(row['final_accuracy_gap']>0.05 or row['final_loss_gap']>0.10)
        row['within_final_phase_divergence_sign']=(row['final_phase_val_loss_rise']>0 and row['final_phase_train_loss_change']<0)
    # First verified attempt per split; choice never uses observed performance.
    pair={}
    for split in ['val','test']:
        candidates=sorted((a for a in assessments if a['training_run_id']==r['id'] and a['state']=='verified' and a['identity']['split']==split),key=lambda a:(a['started_at'],a['attempt_id']))
        a=candidates[0] if candidates else None
        row[split+'_attempt_count']=len(candidates);row[split+'_attempt_id']=a['attempt_id'] if a else None
        row[split+'_threshold']=a['identity']['decision']['effective'] if a else None
        row[split+'_checkpoint_sha256']=a['identity']['model']['sha256'] if a else None
        for m in ['recall','specificity','precision','f2','accuracy','tn','fp','fn','tp','roc_auc','pr_auc']:
            row[split+'_'+m]=a['verification']['metrics'].get(m) if a else None
        row[split+'_patients']=counts[a['attempt_id']]['patients'] if a else None
        if a:
            cm=counts[a['attempt_id']]; assert all(cm[k]==row[split+'_'+k] for k in ['tn','fp','fn','tp']);assert cm['rows']==a['verification']['count']
            assert cm['threshold_min']==cm['threshold_max']==row[split+'_threshold']
            pair[split]=a
    row['val_test_comparable']=False
    if len(pair)==2:
        vi,ti=(pair[x]['identity'] for x in ['val','test'])
        row['val_test_comparable']=vi['model']['sha256']==ti['model']['sha256'] and vi['decision']==ti['decision'] and vi['dataset']==ti['dataset'] and vi['metrics_definition']==ti['metrics_definition']
    for m in ['recall','specificity','f2','accuracy']:
        row['val_minus_test_'+m]=diff(row['val_'+m],row['test_'+m]) if row['val_test_comparable'] else None
    rows.append(row)
keys=list(dict.fromkeys(k for r in rows for k in r));rows=[{k:r.get(k) for k in keys} for r in rows];writecsv('per_run_indicators',rows)
keys=list(dict.fromkeys(k for r in flat for k in r));writecsv('epoch_metrics',[{k:r.get(k) for k in keys} for r in flat])
cohort=[r for r in rows if r['cohort']]; assert len(cohort)==60
assert all(sum(r['model']==model for r in cohort)==12 for model in {r['model'] for r in cohort})
assert all(r['val_test_comparable'] for r in cohort)
assert all(r['epoch_count']==r['completion_epochs'] and r['epochs_contiguous'] for r in cohort)
assert all(r['val_attempt_count']==r['test_attempt_count']==1 for r in cohort)
writecsv('cohort_60',cohort)
code_identity=[]
for r in cohort:
    va=next(a for a in assessments if a['attempt_id']==r['val_attempt_id'])['identity']
    te=next(a for a in assessments if a['attempt_id']==r['test_attempt_id'])['identity']
    code_equal={k:v for k,v in va['code'].items() if k!='git_commit'}=={k:v for k,v in te['code'].items() if k!='git_commit'}
    assert va['model']==te['model'] and code_equal
    code_identity.append({'run_id':r['run_id'],'val_attempt_id':r['val_attempt_id'],'test_attempt_id':r['test_attempt_id'],'val_git_commit':va['code']['git_commit'],'test_git_commit':te['code']['git_commit'],'source_sha256':va['code']['source_sha256'],'code_except_git_equal':code_equal,'full_model_identity_equal':va['model']==te['model']})
writecsv('cohort_code_identity',code_identity)
for population in read('cohort_population'):
    assert population['attempts']==population['min_participants']==population['max_participants']==60
    assert population['label_conflicts']==population['patient_conflicts']==population['ungoverned_samples']==0
summary=[]
for model in sorted({r['model'] for r in cohort}):
    group=[r for r in cohort if r['model']==model];out={'model':model,'runs':len(group),'epoch_records':sum(r['epoch_count'] for r in group),'history_complete':all(r['epochs_contiguous'] and r['epoch_count']==r['completion_epochs'] for r in group),'auditor_last_epoch_signals':sum(r['auditor_last_epoch_heuristic'] for r in group),'final_phase_divergence_signs':sum(r['within_final_phase_divergence_sign'] for r in group)}
    for m in ['selected_loss_gap','selected_accuracy_gap','selected_recall_gap','selected_f2_gap_derived','final_loss_gap','final_accuracy_gap','val_minus_test_recall','val_minus_test_specificity','val_minus_test_f2','val_recall','val_specificity','test_recall','test_specificity']:
        vals=[r[m] for r in group if finite(r.get(m))];out[m+'_n']=len(vals);out[m+'_mean']=mean(vals);out[m+'_sd']=sd(vals)
    summary.append(out)
writecsv('model_matrix',summary)
variability=[]
for model in sorted({r['model'] for r in cohort}):
    for opt in sorted({r['optimizer'] for r in cohort}):
        group=[r for r in cohort if r['model']==model and r['optimizer']==opt];assert sorted(r['seed'] for r in group)==[11,29,47]
        out={'model':model,'optimizer':opt,'n':len(group),'seeds':'11;29;47','run_ids':';'.join(r['run_id'] for r in group)}
        for m in ['val_recall','val_specificity','val_f2','test_recall','test_specificity','test_f2','selected_loss_gap','final_loss_gap']:
            out[m+'_mean']=mean([r[m] for r in group]);out[m+'_sd']=sd([r[m] for r in group])
        variability.append(out)
writecsv('optimizer_seed_summary',variability)
# Recompute metrics from already persisted scores; this is not model evaluation.
from sklearn.metrics import roc_auc_score,average_precision_score
scores=read('champion_scores');champ=[]
for attempt in sorted({s['attempt_id'] for s in scores}):
    a=next(a for a in assessments if a['attempt_id']==attempt);ps=[s['payload'] for s in scores if s['attempt_id']==attempt];m=dict(a['verification']['metrics']);y=[p['label'] for p in ps];p=[x['raw_score'] for x in ps];ra=float(roc_auc_score(y,p));ap=float(average_precision_score(y,p))
    for k,v in [('roc_auc',ra),('pr_auc',ap)]:
        if m.get(k) is not None: assert abs(m[k]-v)<1e-12
        m[k]=v
    assert all(x['predicted']==int(x['raw_score']>=a['identity']['decision']['effective']) for x in ps)
    champ.append({'run_id':CHAMPION,'attempt_id':attempt,'split':a['identity']['split'],'threshold':a['identity']['decision']['effective'],**{k:m[k] for k in ['tn','fp','fn','tp','recall','specificity','precision','f2','accuracy','roc_auc','pr_auc']},'auc_origin':'recomputed from persisted scores; TEST also verified in PostgreSQL'})
writecsv('champion_metrics',champ)
# Standalone scientific figures; no images or checkpoints read or edited.
os.environ.setdefault('MPLCONFIGDIR','/tmp/capstone_p3_matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':9,'savefig.dpi':180})
es=sorted(epochs[CHAMPION],key=lambda e:e['epoch']);fig,axs=plt.subplots(2,1,figsize=(9,7),sharex=True)
for ax,train,val,label in [(axs[0],'loss','val_loss','Loss'),(axs[1],'accuracy','val_accuracy','Accuracy')]:
    ax.plot([e['epoch'] for e in es],[e[train] for e in es],label='TRAIN');ax.plot([e['epoch'] for e in es],[e[val] for e in es],label='VALIDATION');ax.axvline(10.5,color='gray',ls=':',label='Inicio fine-tuning');ax.axvline(12,color='green',ls='--',label='Mínimo val_loss: 12');ax.axvline(20,color='purple',ls='--',label='Checkpoint F2: 20');ax.set_ylabel(label);ax.grid(alpha=.25)
axs[0].legend(ncol=2);axs[1].set_xlabel('Época global (1-based)');fig.suptitle('Campeón db31b6af · Adam · semilla 47\nCurvas persistidas; métricas por época a umbral 0,5');fig.tight_layout();fig.savefig(B/'champion_curves.png');fig.savefig(B/'champion_curves.pdf');plt.close(fig)
labels={'custom_cnn':'Custom CNN','vgg16':'VGG16','densenet121':'DenseNet121','biomedclip_linear':'BiomedCLIP Linear','biomedclip_fine_tuning':'BiomedCLIP Fine-tuning'};models=list(labels)
fig,axs=plt.subplots(1,2,figsize=(11,4.5))
for ax,key,title in [(axs[0],'selected_loss_gap','Loss VAL − TRAIN en checkpoint'),(axs[1],'val_minus_test_recall','Recall VAL − TEST (umbral congelado)')]:
    ax.boxplot([[r[key] for r in cohort if r['model']==mo] for mo in models],tick_labels=[labels[mo] for mo in models],showmeans=True);ax.tick_params(axis='x',rotation=24);ax.axhline(0,color='gray',ls=':');ax.set_title(title);ax.grid(axis='y',alpha=.25)
fig.suptitle('Cohorte all 1 · 12 RUN por modalidad · 4 optimizadores × 3 semillas\nDescriptivo: la diferencia VAL–TEST no diagnostica sobreajuste');fig.tight_layout();fig.savefig(B/'cohort_gaps.png');fig.savefig(B/'cohort_gaps.pdf');plt.close(fig)
(B/'computed_results.json').write_text(json.dumps({'cohort_id':COHORT,'cohort_n':len(cohort),'matrix':summary,'champion':champ,'checks':['60 complete, contiguous histories match completion epochs','20 groups of optimizers each with seeds 11,29,47','60 VAL/TEST pairs have same model hash, decision, dataset and metric definition','140 attempts counts match persisted individual predictions','thresholds constant per attempt','champion AUC recomputed from existing scores; TEST matches verification']},indent=2))
print(json.dumps(summary,indent=2));print('ALL AUDIT ASSERTIONS PASS; derived CSV and 4 figure artifacts created')
