"""Hash every protected dataset/source/config file, without modifying any asset."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ROOTS=('malaria_dl_local_project/data','malaria_dataset_split_project/var',
       'malaria_dataset_split_project/config','malaria_dl_local_project/configs',
       'malaria_dl_local_project/src/malaria_dl/models','alembic/versions')

def snapshot():
 result={}
 for relative in ROOTS:
  root=ROOT/relative;entries=[];total=0
  for p in sorted(root.rglob('*')):
   if '__pycache__' in p.parts or p.suffix=='.pyc':continue
   if p.is_symlink():
    entries.append([str(p.relative_to(root)),'symlink',str(p.readlink())]);continue
   if not p.is_file():continue
   before=p.stat();h=hashlib.sha256()
   with p.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
   after=p.stat()
   if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('PROTECTED_FILE_CHANGED_DURING_READ')
   entries.append([str(p.relative_to(root)),before.st_size,h.hexdigest()]);total+=before.st_size
  result[relative]={'entries':len(entries),'bytes':total,'sha256':hashlib.sha256(json.dumps(entries,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()}
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 if not str(args.output.resolve()).startswith(('/private/tmp/','/tmp/')):raise RuntimeError('PRIVATE_OUTPUT_REQUIRED')
 args.output.write_text(json.dumps(snapshot(),indent=2));print('Protected assets hashed read-only')
