"""Close isolated evidence with read-only checks and content hashes."""
import ast,json,subprocess,sys
from pathlib import Path
from prepare import E,ROOT,WORK,sha,snapshot,write
# No scientific run writer is imported.
write('database_after.json',snapshot())
before=json.loads((E/'database_before.json').read_text());after=json.loads((E/'database_after.json').read_text())
db_equal=before==after
write('database_changes.json',{k:{'before':before[k],'after':after[k]} for k in before if before[k]!=after[k]})
assert (E/'production_environment_before.txt').read_bytes()==(E/'production_environment_after.txt').read_bytes()
original=json.loads((E/'original_assets.json').read_text())
assert all(sha(f['path'])==f['sha256'] for a in original for f in a['files'])
for file in Path(__file__).parent.glob('*.py'):ast.parse(file.read_text(),filename=str(file))
# Record exact effective AdamW defaults without another training step.
import torch
optimizer=torch.optim.AdamW([torch.nn.Parameter(torch.zeros(1))],lr=.001,weight_decay=0.)
write('optimizer_effective_defaults.json',{'torch_version':torch.__version__,'optimizer':'torch.optim.AdamW','defaults':optimizer.defaults,'groups_lr':[.001,.00001],'note':'same constructor/version as fine_tuning.py; no optimizer update in this inspection'})
files=list(E.glob('*'))+list(Path(__file__).parent.glob('*'))
files+=[Path(f['path']) for a in original for f in a['files']]
files+=[WORK/n for n in ['original_embeddings.npy','linear_epoch_1.keras','linear_epoch_2.keras','linear_epoch_3.keras','fine_tuning.pt','parity_and_representations.npz','linear_timing_probe.keras']]
manifest=[]
for p in files:
    if not p.is_file() or p.name=='manifest.json':continue
    manifest.append({'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
write('manifest.json',{'schema':'biomedclip_01b_experimental_manifest_v1','experimental_only':True,'production_database_written':False,'original_files_intact':True,'production_package_freeze_equal':True,'database_count_xmin_equal':db_equal,'concurrent_activity_evidence':'concurrent_assessments.txt','files':manifest})
print('VERIFIED',len(manifest),'files; original and production packages intact; database_equal=',db_equal)
