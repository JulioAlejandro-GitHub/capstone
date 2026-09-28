"""Exercise the final runner's commit error branch without connecting to any DB.

Compile the actual isolated-commit block with transaction/filesystem doubles. This
checks exception handling only; it does not claim a real lost-connection rehearsal.
"""
import argparse,ast,json
from pathlib import Path
from types import SimpleNamespace

def verify():
 tree=ast.parse(Path(__file__).with_name('rehearsal.py').read_text())
 main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 block=next(n for n in main.body if isinstance(n,ast.With) and any(isinstance(v,ast.Name) and v.id=='commit_requested' for v in ast.walk(n)))
 code=compile(ast.fix_missing_locations(ast.Module(body=[block],type_ignores=[])),'isolated_commit_block','exec');results={}
 for case in ('sql_failure','commit_uncertain','success'):
  calls=[]
  class TX:
   def commit(self):
    calls.append('commit')
    if case=='commit_uncertain':raise ConnectionError('simulated acknowledgement loss')
   def rollback(self):calls.append('rollback')
  class Connection:
   def __enter__(self):return self
   def __exit__(self,*args):return False
   def begin(self):return TX()
  class Files:
   def quarantine(self):calls.append('quarantine')
   def restore(self):calls.append('restore')
   def write_journal(self,state):calls.append(state)
  def prepare(*args):
   if case=='sql_failure':raise RuntimeError('simulated SQL failure')
   return None,{}
  scope={'engine':SimpleNamespace(connect=Connection),'cfg':{},'assert_clone':lambda *args:None,'reset':prepare,'baseline':{},'keep':{},'fs':Files()}
  try:exec(code,scope)
  except (RuntimeError,ConnectionError):
   if case=='success':raise
  else:
   if case!='success':raise RuntimeError('EXPECTED_FAILURE_NOT_PROPAGATED')
  expected={'sql_failure':['rollback','restore'],'commit_uncertain':['quarantine','commit','COMMIT_UNCERTAIN'],'success':['quarantine','commit']}[case]
  if calls!=expected:raise RuntimeError('UNSAFE_COMMIT_BOUNDARY:'+str(calls))
  results[case]=calls
 return {'control_flow_cases':results,'real_network_failure_injected':False,'database_connections':0,'operational_file_operations':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if not str(a.output.resolve()).startswith(('/private/tmp/','/tmp/')):raise RuntimeError('PRIVATE_OUTPUT_REQUIRED')
 a.output.write_text(json.dumps(verify(),indent=2));print('Commit boundary checks passed')
