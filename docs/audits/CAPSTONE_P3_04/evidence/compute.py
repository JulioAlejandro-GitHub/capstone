"""Independent in-memory calculations over existing evidence. Never imports a model runtime."""
from pathlib import Path
import json,csv,hashlib,datetime,collections,zipfile
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
B=Path(__file__).resolve().parents[1]; ROOT=B.parents[2]
def read(n):return json.loads((B/'evidence'/f'{n}.json').read_text())
def save(n,v):(B/'evidence'/f'{n}.json').write_text(json.dumps(v,indent=2))
def csvout(n,rows):
 if not rows:return
 with (B/'csv'/f'{n}.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)));w.writeheader();w.writerows(rows)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(4*1024*1024),b''):h.update(c)
 return h.hexdigest()
def local(p):
 p=Path(p)
 if p.exists():return p
 s=str(p);mark='/malaria_dl_local_project/'
 return ROOT/'malaria_dl_local_project'/s.split(mark,1)[1] if mark in s else p
T='87b3eff7-e09a-41c8-945d-bf31b3541adb';U='00b8d407-c672-4b68-9814-53c092d034ba'
a=read('assessments');case={x['id'] for x in a if x['training_run_id']==T}; inventory=[]
for table in ['artifacts','assessment_artifacts']:
 for row in read(table):
  p=row if table=='artifacts' else row['payload']; path=local(p['path']);focus=(row.get('run_id')==T or row.get('attempt_id') in case or row.get('role') in ('embeddings','pca','pca_variance','umap'))
  exists=path.is_file();computed=sha(path) if exists and focus else None
  expected=p.get('sha256',p.get('checksum'))
  inventory.append(dict(table=table,artifact_id=row.get('artifact_id',row.get('id')),run_id=row.get('run_id'),attempt_id=row.get('attempt_id'),sample_id=row.get('sample_id'),role=row.get('role',row.get('artifact_type')),extension=path.suffix,path_registered=p['path'],path_resolved=str(path),exists=exists,expected_bytes=p.get('bytes',p.get('file_size_bytes')),observed_bytes=path.stat().st_size if exists else None,expected_sha256=expected,observed_sha256=computed,hash_status=('match' if computed==expected else 'mismatch') if computed else 'not_checked'))
csvout('artifact_inventory',inventory)
save('artifact_summary',dict(count=len(inventory),exists=sum(r['exists'] for r in inventory),hashes=collections.Counter(r['hash_status'] for r in inventory)))
rows=[x['payload'] for x in read('principal_scores')];samples=read('principal_full_identity')['identity']['samples'];sm={s['sample_id']:s for s in samples};decision=read('principal_full_identity')['identity']['decision'];threshold=decision['effective'];counts=collections.Counter()
for row in rows:
 pred=int(row['raw_score']>=threshold);assert pred==row['predicted'];counts[['tn','fp','fn','tp'][2*row['label']+pred]]+=1
 row.update(sm[row['sample_id']]);row['outcome']=['TN','FP','FN','TP'][2*row['label']+pred]
tn,fp,fn,tp=[counts[x] for x in ['tn','fp','fn','tp']];n=len(rows)
metrics=dict(count=n,**counts,recall=tp/(tp+fn),specificity=tn/(tn+fp),precision=tp/(tp+fp),accuracy=(tp+tn)/n,f1=2*tp/(2*tp+fp+fn),f2=5*tp/(5*tp+4*fn+fp),balanced_accuracy=(tp/(tp+fn)+tn/(tn+fp))/2,roc_auc=roc_auc_score([r['label'] for r in rows],[r['raw_score'] for r in rows]),pr_auc=average_precision_score([r['label'] for r in rows],[r['raw_score'] for r in rows]))
persisted=next(x for x in a if x['id']==U)['verification']['metrics'];save('metric_reproduction',dict(attempt_id=U,threshold=threshold,computed=metrics,persisted=persisted,max_abs_difference=max(abs(v-persisted[k]) for k,v in metrics.items()),patients=len(set(r['patient_id'] for r in rows)),npv_derived=tn/(tn+fn),high_confidence_errors=sum(r['outcome'] in ['FN','FP'] and (r['raw_score']>=.9 if r['predicted'] else r['raw_score']<=.1) for r in rows),near_threshold=sum(abs(r['raw_score']-threshold)<=.05 for r in rows)))
csvout('principal_predictions',[{k:r.get(k) for k in ['sample_id','patient_id','relative_path','sha256','label','raw_score','threshold','predicted','outcome']} for r in rows]);csvout('principal_metrics',[dict(attempt_id=U,split='test',threshold=threshold,metric=k,computed=v,persisted=persisted[k]) for k,v in metrics.items()])
# Verify exactly three original target files plus a false negative, no dataset scan.
originals=[]
for sid in set(['01a133b1-74db-5f12-bf42-8db74b539b26','fb1c9a4b-cf64-5b03-a839-13a8bb677135','014d8b8e-3397-5ae8-88fd-8cef2a2d6c64',next(r['sample_id'] for r in rows if r['outcome']=='FN')]):
 s=sm[sid];p=ROOT/'malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'/s['relative_path'];originals.append(dict(**s,path=str(p),exists=p.is_file(),observed_sha256=sha(p) if p.is_file() else None))
save('original_verification',originals)
epochs=read('report_curves')['data'][0]['epochs'];csvout('principal_epochs',[dict(e['values'],epoch=e['epoch'],phase=e['phase']) for e in epochs])
fig,axes=plt.subplots(1,2,figsize=(11,4))
for ax,metric in zip(axes,['loss','accuracy']):
 for prefix in ['','val_']:ax.plot([e['epoch'] for e in epochs],[e['values'].get(prefix+metric,np.nan) for e in epochs],label='VAL' if prefix else 'TRAIN')
 ax.axvline(1,color='black',linestyle=':',label='Selected epoch 1');ax.axvline(next(e['epoch'] for e in epochs if e['phase']=='fine_tuning')-.5,color='grey',linestyle='--');ax.set(xlabel='Epoch',ylabel=metric,title='Principal TRAIN '+T[:8]);ax.legend()
fig.tight_layout();fig.savefig(B/'figures/principal_learning.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(5,4));ax.imshow([[tn,fp],[fn,tp]],cmap='Blues')
for i in range(2):
 for j in range(2):ax.text(j,i,str([[tn,fp],[fn,tp]][i][j]),ha='center')
ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Uninfected','Parasitized'],yticklabels=['Uninfected','Parasitized'],xlabel='Predicted',ylabel='True',title=f'Principal TEST N={n}, t={threshold:.6f}');fig.tight_layout();fig.savefig(B/'figures/principal_confusion.png',dpi=160);plt.close(fig)
# Persisted projections and aligned pairwise CKA; no new PCA/UMAP fit.
reps=[]
for attempt in a:
 if attempt['kind']!='represent' or attempt['state']!='verified':continue
 arts={r['role']:r['payload'] for r in read('assessment_artifacts') if r['attempt_id']==attempt['id']};arrays={role:np.load(local(p['path']),allow_pickle=False) for role,p in arts.items()}; reps.append((attempt,arrays));
 if attempt['training_run_id']==T:
  e=arrays['embeddings'];variance=arrays['pca_variance'];save('representation_reproduction',dict(attempt_id=attempt['id'],shapes={k:list(v.shape) for k,v in arrays.items()},all_finite=all(np.isfinite(v).all() for v in arrays.values()),mean_norm=float(np.linalg.norm(e,axis=1).mean()),variance_2=float(variance[:2].sum()),variance_50=float(variance.sum()),components_80=int(np.argmax(variance.cumsum()>=.8)+1) if variance.sum()>=.8 else None))
  ident=next(i for i in read('case_identities') if i['id']==attempt['identity_id'])['identity'];labels=np.array([s['label'] for s in ident['samples']]);
  fig,axs=plt.subplots(1,2,figsize=(10,4))
  for ax,role in zip(axs,['pca','umap']):
   ax.scatter(arrays[role][:,0],arrays[role][:,1],c=labels,s=3,cmap='coolwarm',alpha=.5);ax.set(title=role.upper()+' persisted · principal TEST',xlabel='Axis 1',ylabel='Axis 2')
  fig.tight_layout();fig.savefig(B/'figures/principal_representations.png',dpi=160);plt.close(fig)
cka=[]
identities={i['id']:i['identity'] for i in read('case_identities')+read('secondary_identities')}
for i,(left,xs) in enumerate(reps):
 for right,ys in reps[i+1:]:
  if left['identity_id'] not in identities or right['identity_id'] not in identities:continue
  sx=[s['sample_id'] for s in identities[left['identity_id']]['samples']];sy=[s['sample_id'] for s in identities[right['identity_id']]['samples']];common=sorted(set(sx)&set(sy))
  if len(common)<2:continue
  ix={s:k for k,s in enumerate(sx)};iy={s:k for k,s in enumerate(sy)};x=xs['embeddings'][[ix[s] for s in common]].astype('float64');y=ys['embeddings'][[iy[s] for s in common]].astype('float64');x-=x.mean(0);y-=y.mean(0);value=np.linalg.norm(y.T@x,'fro')**2/(np.linalg.norm(x.T@x,'fro')*np.linalg.norm(y.T@y,'fro'));cka.append(dict(left_train=left['training_run_id'],right_train=right['training_run_id'],left_attempt=left['id'],right_attempt=right['id'],split=left['identity']['split'],common=len(common),linear_cka=float(value)))
csvout('cka_comparisons',cka)
# XAI maps: numerical domain and no clinical meaning inferred.
xstats=[]
for r in read('assessment_artifacts'):
 if r['attempt_id'] not in case or r['role']!='map':continue
 p=local(r['payload']['path']);v=np.load(p,allow_pickle=False);xstats.append(dict(attempt_id=r['attempt_id'],sample_id=r['sample_id'],artifact_id=r['artifact_id'],shape=str(v.shape),minimum=float(v.min()),maximum=float(v.max()),positive=int((v>0).sum()),negative=int((v<0).sum()),finite=bool(np.isfinite(v).all())))
csvout('principal_xai_maps',xstats)
# Count availability by current effective architecture, not historical names.
runs=read('runs');modelrows=[]
for arch in sorted(set((r.get('execution_parameters',{}).get('model_configuration_e2',{}).get('configuration',{}).get('resolved',{}).get('input_contract',{}).get('architecture') or (r.get('model') or {}).get('name') or 'unknown') for r in runs)):
 group=[r for r in runs if (r.get('execution_parameters',{}).get('model_configuration_e2',{}).get('configuration',{}).get('resolved',{}).get('input_contract',{}).get('architecture') or (r.get('model') or {}).get('name') or 'unknown')==arch];ids={r['id'] for r in group};ass=[x for x in a if x['training_run_id'] in ids];modelrows.append(dict(architecture=arch,runs=len(group),completed=sum(r['status']=='completed' for r in group),epochs=sum(c['count'] for c in read('record_counts') if c['run_id'] in ids and c['kind']=='epoch'),evaluate_verified=sum(x['kind']=='evaluate' and x['state']=='verified' for x in ass),explain_verified=sum(x['kind']=='explain' and x['state']=='verified' for x in ass),explain_failed=sum(x['kind']=='explain' and x['state']=='failed' for x in ass),represent_verified=sum(x['kind']=='represent' and x['state']=='verified' for x in ass)))
csvout('modality_counts',modelrows)
save('computation_environment',dict(python=__import__('sys').version,numpy=np.__version__,sklearn=__import__('sklearn').__version__,matplotlib=matplotlib.__version__,captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
print('Computed metrics, hashes, projections and CKA; artifacts',len(inventory))
