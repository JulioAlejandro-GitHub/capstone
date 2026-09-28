"""Classify every deferred location; move ONLY verified disposable copies."""
import hashlib,json,os,re,shutil,tempfile
from collections import Counter
from pathlib import Path
from common import require,sha
HERE=Path(__file__).resolve().parent
UUID=re.compile(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',re.I)

def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def classify(manifest):
 known={str(row['id']) for table in ('runs','model_versions','experimental_campaigns','cell_detection_runs','microscopy_analysis_runs','cell_classification_runs') for row in manifest['tables'][table].get('ids',[])}
 known_run={row['id'] for row in manifest['tables']['runs']['ids']}
 result=[]
 for f in manifest['files']:
  if f['action']!='REVIEW_UNOWNED_DO_NOT_MOVE':continue
  p=Path(f['resolved_path']);require(p.is_file() and not p.is_symlink(),'MISSING_OR_SYMLINK:'+str(p));require(file_sha(p)==f['sha256'],'FILE_CHANGED:'+str(p))
  item={'canonical_location':f['canonical_location'],'path':str(p),'sha256':f['sha256'],'size':p.stat().st_size,'owners':[],'evidence':[],'classification':'NO_DEMONSTRABLE_RELATION','action':'PRESERVE_AMBIGUOUS'}
  if p.name in ('.gitkeep','.DS_Store'):
   item.update(classification='SHARED_PROJECT_MARKER',action='PRESERVE_SHARED')
  elif p.name.endswith('.lock'):
   item.update(classification='SHARED_COORDINATION_FILE',action='PRESERVE_SHARED')
  elif '/runs/' not in str(p) and '/releases/' not in str(p) and '/cell-crops/' not in str(p):
   item.update(classification='SHARED_MODEL_OUTPUT_ALIAS',action='PRESERVE_SHARED')
  else:
   # Exact content IDs from a sibling generated report/manifest, not directory membership alone.
   anchors=[p] if p.suffix.lower() in ('.json','.md') else []
   anchors += [p.parent/n for n in ('model_execution_summary.md','model_execution_summary.json','model_metadata.json','manifest.json')]
   for anchor in dict.fromkeys(anchors):
    if not anchor.is_file() or anchor.is_symlink() or anchor.stat().st_size>2_000_000:continue
    value=anchor.read_text(errors='replace');ids=set(UUID.findall(value))&known
    if ids:
     item['evidence'].append({'path':str(anchor),'sha256':file_sha(anchor),'matching_registered_ids':sorted(ids)})
     item['owners']=sorted(set(item['owners'])|ids)
   if item['owners']:
    item.update(classification='HISTORICAL_OWNER_IDENTIFIED',action='QUARANTINE_DISPOSABLE_COPY')
   # Explicitly keep truly ambiguous files; this is a closed decision, not a guessed owner.
  item['related_runs']=sorted(set(item['owners'])&known_run)
  result.append(item)
 require(len(result)==414,'DEFERRED_SET_CHANGED')
 return {'base_manifest_sha256':file_sha(HERE/'manifest.json'),'classified':result,'classifications':dict(Counter(r['classification'] for r in result)),'actions':dict(Counter(r['action'] for r in result)),'all_414_resolved_to_explicit_action':True}

class DisposableFiles:
 def __init__(self,manifest,classification):
  self.root=Path(tempfile.mkdtemp(prefix='reset1b-files-',dir=HERE));self.token=os.urandom(24).hex()
  (self.root/'identity.json').write_text(json.dumps({'task':'RESET.1B','token':self.token}));(self.root/'live').mkdir();(self.root/'quarantine').mkdir()
  updated={r['canonical_location']:r for r in classification['classified']};self.entries=[]
  for f in manifest['files']:
   if not f['exists'] or f.get('kind')!='file':continue
   src=Path(f['resolved_path']);require(src.is_file() and not src.is_symlink(),'SOURCE_NOT_REGULAR')
   owned=f['action']=='QUARANTINE_AFTER_APPROVAL' or updated.get(f['canonical_location'],{}).get('action')=='QUARANTINE_DISPOSABLE_COPY'
   require(not (owned and f['action'].startswith('PRESERVE')),'PROTECTED_SELECTED')
   key=hashlib.sha256(f['canonical_location'].encode()).hexdigest();dst=self.root/'live'/key
   shutil.copyfile(src,dst);dst.chmod(0o600);require(file_sha(dst)==f['sha256'],'SOURCE_CHANGED:'+str(src))
   self.entries.append({'key':key,'original':str(src),'canonical':f['canonical_location'],'sha256':f['sha256'],'bytes':f['size'],'move':owned})
  self.before=self.snapshot();self.write_journal('PREPARED')
 def verify_root(self):
  require(self.root.parent==HERE and self.root.name.startswith('reset1b-files-') and not self.root.is_symlink(),'DISPOSABLE_ROOT_REQUIRED')
  require(json.loads((self.root/'identity.json').read_text())['token']==self.token,'DISPOSABLE_IDENTITY_MISMATCH')
 def write_journal(self,state):
  self.verify_root();p=self.root/'journal.next';p.write_text(json.dumps({'state':state,'entries':self.entries}));p.replace(self.root/'journal.json')
 def snapshot(self):
  self.verify_root();result={}
  for e in self.entries:
   options=[self.root/'live'/e['key'],self.root/'quarantine'/e['key']];present=[p for p in options if p.is_file()]
   require(len(present)==1,'COPY_LOST_OR_DUPLICATED')
   p=present[0];require(not p.is_symlink(),'COPY_SYMLINK');value=file_sha(p);require(value==e['sha256'],'COPY_INTEGRITY_FAILED')
   result[e['key']]={'location':p.parent.name,'sha256':value}
  return result
 def quarantine(self):
  self.write_journal('QUARANTINING')
  for e in self.entries:
   if e['move']:
    src=self.root/'live'/e['key'];dst=self.root/'quarantine'/e['key']
    require(file_sha(src)==e['sha256'] and not dst.exists(),'QUARANTINE_CONFLICT');src.rename(dst)
  self.write_journal('QUARANTINED');self.snapshot()
 def restore(self):
  self.write_journal('RESTORING')
  for e in self.entries:
   if e['move']:
    src=self.root/'quarantine'/e['key'];dst=self.root/'live'/e['key']
    if src.exists():require(not dst.exists() and file_sha(src)==e['sha256'],'RESTORE_CONFLICT');src.rename(dst)
  require(self.snapshot()==self.before,'FILES_NOT_RESTORED');self.write_journal('RESTORED')
 def evidence(self):
  after=self.snapshot()
  require(all(after[e['key']]['location']=='live' for e in self.entries if not e['move']),'PROTECTED_FILE_MOVED')
  return {'disposable_root':str(self.root),'copied_files':len(self.entries),'quarantine_candidates':sum(e['move'] for e in self.entries),'protected_copies':sum(not e['move'] for e in self.entries),'all_copies_hash_verified':True,'protected_copies_still_live':True,'journal':str(self.root/'journal.json'),'operational_paths_ever_mutated':False,'copy_state_sha256':sha(after)}
 def verify_originals(self):
  for e in self.entries:require(file_sha(Path(e['original']))==e['sha256'],'OPERATIONAL_FILE_CHANGED')
  return {'all_original_files_unchanged':True,'files':len(self.entries)}

if __name__=='__main__':print(json.dumps(classify(json.loads((HERE/'manifest.json').read_text()))))
