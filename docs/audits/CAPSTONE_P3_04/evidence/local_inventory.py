from pathlib import Path
import json,csv,hashlib
B=Path(__file__).resolve().parents[1];R=B.parents[2];T='87b3eff7-e09a-41c8-945d-bf31b3541adb';rows=[];traces=[]
for tree in [R/'malaria_dl_local_project/outputs/campaign_runs'/T,R/'var/storage/activation-traces'/T,R/'var/storage/model-structures']:
 for p in sorted(tree.glob('*')):
  if not p.is_file():continue
  h=hashlib.sha256(p.read_bytes()).hexdigest() if p.suffix=='.json' else None
  rows.append(dict(path=str(p),extension=p.suffix,bytes=p.stat().st_size,sha256=h,checksum_status='computed_no_registered_reference' if h else 'not_checked',source='bounded_local_directory'))
  if 'activation-traces' in str(p):
   x=json.loads(p.read_text());traces.append(dict(path=str(p),sample_id=p.stem,sha256=h,**{k:v for k,v in x.items() if k not in ['steps','input_image']},steps=[{k:v for k,v in s.items() if k not in ['maps']} for s in x['steps']]))
with (B/'csv/local_auxiliary_files.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
(B/'evidence/saved_traces_summary.json').write_text(json.dumps(traces,indent=2))
print('Bounded file inventory',len(rows),'saved traces',len(traces))
