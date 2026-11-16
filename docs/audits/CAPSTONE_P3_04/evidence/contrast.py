from pathlib import Path
import json,csv,collections,itertools
import numpy as np
B=Path(__file__).resolve().parents[1];R=B.parents[2]
def read(n):return json.loads((B/'evidence'/f'{n}.json').read_text())
def save(n,v):(B/'evidence'/f'{n}.json').write_text(json.dumps(v,indent=2))
rows=read('principal_calibration_record')[0]['payload']['samples'];print('calibration row keys',list(rows[0]));
y=np.array([r['label'] for r in rows]);s=np.array([r['score'] for r in rows]);candidates=sorted(set([0.,.5,1.]+s.tolist()));best=None
for threshold in candidates:
 p=s.astype('float32')>=threshold;tp=int(((y==1)&p).sum());fn=int(((y==1)&~p).sum());tn=int(((y==0)&~p).sum());fp=int(((y==0)&p).sum());recall=tp/(tp+fn);specificity=tn/(tn+fp);precision=tp/(tp+fp) if tp+fp else 0;f2=5*tp/(5*tp+4*fn+fp) if 5*tp+4*fn+fp else 0
 if recall>=.98:
  key=(specificity,precision,f2,(recall+specificity)/2,threshold)
  if best is None or key>best[0]:best=(key,dict(threshold=threshold,tn=tn,fp=fp,fn=fn,tp=tp,recall=recall,specificity=specificity))
save('threshold_reproduction',dict(candidates=len(candidates),selected=best[1],persisted=read('principal_calibration_record')[0]['payload']['result']))
pops={'00b8d407-c672-4b68-9814-53c092d034ba':{r['sample_id']:r['payload'] for r in read('principal_scores')}}
for r in read('comparison_test_scores'):pops.setdefault(r['attempt_id'],{})[r['sample_id']]=r['payload']
comparison=[]
for (u,a),(v,b) in itertools.combinations(pops.items(),2):
 common=sorted(set(a)&set(b));assert all(a[s]['label']==b[s]['label'] for s in common);ea={s for s in common if a[s]['predicted']!=a[s]['label']};eb={s for s in common if b[s]['predicted']!=b[s]['label']};comparison.append(dict(left=u,right=v,n=len(common),agreement=sum(a[s]['predicted']==b[s]['predicted'] for s in common),left_errors=len(ea),right_errors=len(eb),shared_errors=len(ea&eb),left_only_errors=len(ea-eb),right_only_errors=len(eb-ea),shared_fn=sum(a[s]['label']==1 for s in ea&eb),shared_fp=sum(a[s]['label']==0 for s in ea&eb),oracle=(len(common)-len(ea&eb))/len(common)))
save('pairwise_errors',comparison)
epochs=read('report_curves')['data'][0]['epochs'];minimum=min(epochs,key=lambda r:r['values']['val_loss']);last=epochs[-1];save('learning_reproduction',dict(epochs=len(epochs),phases=collections.Counter(r['phase'] for r in epochs),minimum_val_loss=minimum,last=last,selected=epochs[0]))
# Compare the actual pooled features between principal and secondary VGG.
a=read('assessment_artifacts');ids=['d6f269de-ba63-4a17-9df8-3bd2ce1871b2','2e2c20ac-9014-4e2b-9d6c-7d820bed4f2f'];xs=[np.load(next(x['payload']['path'] for x in a if x['attempt_id']==u and x['role']=='embeddings'),allow_pickle=False) for u in ids];save('vgg_embedding_identity',dict(attempts=ids,array_equal=bool(np.array_equal(*xs)),max_abs_difference=float(np.max(np.abs(xs[0]-xs[1])))))
print('contrasts complete')
