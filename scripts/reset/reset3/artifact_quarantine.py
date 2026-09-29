"""Copy-and-verify every planned derived file before withdrawing any active file.

Requires an explicit plan and private recovery root; never scans/deletes ad hoc.
The original DB must remain stopped through apply or restore.
"""
import argparse,hashlib,json,os,shutil
from pathlib import Path
from artifact_plan import ROOTS
parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['copy','withdraw','restore','verify']);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--recovery',type=Path,required=True);a=parser.parse_args()
assert str(a.recovery)=='/recovery/artifact_quarantine'
plan=json.loads(a.plan.read_text());assert plan['count']==len(plan['files'])
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def checked_paths(row):
 src=Path(row['source']);dst=a.recovery/row['relative']
 assert not src.is_symlink() and not dst.is_symlink()
 assert any(src.is_relative_to(Path(root)) and row['relative']==label+'/'+str(src.relative_to(root)) for root,label in ROOTS)
 assert dst.resolve().is_relative_to(a.recovery.resolve())
 return src,dst
# Preflight the entire set before any source removal or restoration.
for row in plan['files']:
 src,dst=checked_paths(row)
 if a.mode in ('copy','withdraw'):assert src.is_file() and digest(src)==row['sha256'],'SOURCE_CHANGED:'+str(src)
 if a.mode in ('withdraw','restore','verify'):assert dst.is_file() and digest(dst)==row['sha256'],'RECOVERY_CHANGED:'+str(dst)
 if a.mode=='restore' and src.exists():assert digest(src)==row['sha256'],'RESTORE_CONFLICT:'+str(src)
 if a.mode=='verify':assert not src.exists(),'ACTIVE_DERIVED_FILE:'+str(src)
a.recovery.mkdir(parents=True,exist_ok=True)
journal=a.recovery.parent/('artifact_'+a.mode+'.jsonl')
with journal.open('x') as log:
 for row in plan['files']:
  src,dst=checked_paths(row)
  if a.mode=='copy':
   assert not dst.exists();dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   with dst.open('rb') as f:os.fsync(f.fileno())
   assert digest(dst)==row['sha256']
  elif a.mode=='withdraw':src.unlink()
  elif a.mode=='restore' and not src.exists():
   src.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,src);assert digest(src)==row['sha256']
  log.write(json.dumps({'source':str(src),'recovery':str(dst),'sha256':row['sha256'],'mode':a.mode})+'\n');log.flush();os.fsync(log.fileno())
print(json.dumps({'result':'PASS_ARTIFACT_'+a.mode.upper(),'files':plan['count'],'bytes':plan['bytes']}))
