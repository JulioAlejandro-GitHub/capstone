"""Inventory only: derived runtime roots, never dataset/source/config roots."""
import hashlib,json
from pathlib import Path
ROOTS=(('/app/malaria_dl_local_project/outputs','ml_outputs'),('/app/malaria_dl_local_project/releases','releases'),('/app/malaria_dl_local_project/local_execution_artifacts','local_execution'),('/app/var/artifacts','artifacts'),('/app/var/storage/cell-crops','cell_crops'),('/app/var/storage/cell-explanations','cell_explanations'),('/app/var/storage/model-explanations','model_explanations'),('/app/var/storage/.staging','staging'))
def main():
 result={'roots':ROOTS,'files':[],'preserved_markers':[]}
 for root,label in ROOTS:
  base=Path(root)
  if not base.exists():continue
  for path in sorted(base.rglob('*')):
   if path.is_symlink():raise RuntimeError('SYMLINK_REQUIRES_REVIEW:'+str(path))
   if not path.is_file():continue
   if path.name in ('.gitkeep','.DS_Store','.training.lock'):
    result['preserved_markers'].append(str(path));continue
   before=path.stat()
   with path.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
   after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
   result['files'].append({'source':str(path),'relative':label+'/'+str(path.relative_to(base)),'bytes':before.st_size,'sha256':h})
 result['count']=len(result['files']);result['bytes']=sum(f['bytes'] for f in result['files'])
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
