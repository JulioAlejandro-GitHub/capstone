"""Read Keras ZIP metadata only, never deserialize weights or invoke Keras."""
from pathlib import Path
import json,zipfile,hashlib
B=Path(__file__).resolve().parents[1];R=B.parents[2];t='87b3eff7-e09a-41c8-945d-bf31b3541adb'
p=R/'malaria_dl_local_project/outputs/campaign_runs'/t/'epoch_1.keras'
with zipfile.ZipFile(p) as z:
 config=json.loads(z.read('config.json'));metadata=json.loads(z.read('metadata.json'));members=[dict(name=i.filename,bytes=i.file_size) for i in z.infolist()]
def sig(config):
 cfg=config.get('config',config)
 return [dict(name=l.get('name') or l.get('config',{}).get('name'),type=l['class_name'],trainable=l.get('config',{}).get('trainable'),kernel=l.get('config',{}).get('kernel_size'),units=l.get('config',{}).get('units')) for l in cfg['layers']]
runtime=json.loads((B/'evidence/runtime_records.json').read_text());records=[r for r in runtime if r['run_id']==t and r['record_key']=='configuration'];actual=sig(config)
result=dict(path=str(p),members=members,metadata=metadata,checkpoint_layer_signature=actual,runtime_phase_comparison=[dict(phase=r['phase'],signature_equal=actual==sig(r['payload']['architecture'])) for r in records])
(B/'evidence/checkpoint_zip_inspection.json').write_text(json.dumps(result,indent=2));print('checkpoint metadata inspected',len(actual),'layers')
