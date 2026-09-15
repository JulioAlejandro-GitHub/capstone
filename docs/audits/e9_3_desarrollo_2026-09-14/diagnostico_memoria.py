"""Bounded technical diagnostic; no operational experiment or TEST access.
Limits per child: 150 seconds, RSS 3 GiB, cgroup 5 GiB; 2 train steps,
12 prediction passes, one checkpoint. Only this owned child can be stopped.
"""
import json, subprocess, sys, time, tempfile
from pathlib import Path
CHILD = r'''
import os,json,time,hashlib,tempfile
from pathlib import Path
import numpy as np
import tensorflow as tf
from src.malaria_dl.data.governed_dataset import dataset_read_connection
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.campaigns.contracts import member_configuration
from src.malaria_dl.models.registry import resolve_descriptor
from src.malaria_dl.models.adapters import compile_phase
from contextlib import contextmanager
mode=__import__('sys').argv[1]
CID='3acf89b7-dc42-4b7a-8e2a-ca6ea024c344'; DID='d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
def measure(stage):
 vals={}
 for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
  if line.split(':')[0] in ('Rss','Pss','Shared_Clean','Shared_Dirty','Private_Clean','Private_Dirty'):vals[line.split(':')[0]]=int(line.split()[1])*1024
 print(json.dumps({'stage':stage,'mode':mode,'memory_bytes':vals}),flush=True)
with dataset_read_connection() as c:
 @contextmanager
 def scope(readonly=False):
  assert readonly
  yield c
 row=ExecutionRepository(scope).get(CID)
 assert row['state']=='paused' and row['dataset_snapshot']['dataset_version_id']==DID
 m=min(row['members'],key=lambda m:m['position'])
 cfg=member_configuration(row['contract']['matrix']['configurations'][m['configuration_hash']]['configuration'],m['seed'])
 root=Path(row['dataset_snapshot']['dataset_root'])
 assert root.name==DID
r=cfg['resolved']; tf.keras.utils.set_random_seed(r['execution']['seed']);tf.config.experimental.enable_op_determinism()
paths=[]
for label in ('uninfected','parasitized'):
 paths.extend(sorted((root/'train'/label).glob('*.png'))[:32])
assert len(paths)==64 and r['execution']['batch_size']==64
samples=[{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
print(json.dumps({'dataset_id':DID,'campaign_id':CID,'samples':samples,'configuration':cfg,'gpu_devices':[x.name for x in tf.config.list_physical_devices('GPU')]}),flush=True)
measure('start')
x=tf.stack([tf.image.resize(tf.io.decode_png(tf.io.read_file(str(p)),channels=3),r['model']['input_shape'][:2])/255 for p in paths]);y=tf.constant([0.]*32+[1.]*32)
measure('load_train_subset')
adapter=resolve_descriptor(cfg['model_id']).create_adapter();built=adapter.build(r);compile_phase(adapter,built,r,'base');model=built.model
measure('build_compile')
# Technical steps on fixed TRAIN subset; no operational metrics or results persisted.
for i in range(2):
 model.train_on_batch(x,y)
 measure('train_step_'+str(i+1))
for i in range(12):
 if mode=='before':out=model.predict(x,verbose=0)
 else:out=np.concatenate([model.predict_on_batch(x[j:j+32]) for j in range(0,64,32)])
 measure('prediction_'+str(i+1))
# Same model/inputs, compare only technical outputs; no scientific metric.
original=model.predict(x,verbose=0)
replacement=np.concatenate([model.predict_on_batch(x[j:j+32]) for j in range(0,64,32)])
print(json.dumps({'equivalence_max_abs':float(np.max(np.abs(original-replacement)))}),flush=True)
with tempfile.TemporaryDirectory(prefix='capstone_memory_') as d:
 model.save(Path(d)/'fixture.keras');measure('checkpoint')
'''
for mode in ('before','after'):
 with tempfile.TemporaryFile(mode='w+') as log:
  child=subprocess.Popen([sys.executable,'-B','-c',CHILD,mode],stdout=log,stderr=subprocess.DEVNULL)
  start=time.monotonic(); reason=None;peak=0
  while child.poll() is None:
   try:
    rss=next(int(x.split()[1])*1024 for x in Path(f'/proc/{child.pid}/status').read_text().splitlines() if x.startswith('VmRSS:'))
    peak=max(peak,rss)
    cgroup=int(Path('/sys/fs/cgroup/memory.current').read_text())
    if rss>3*1024**3 or cgroup>5*1024**3:reason='memory_limit'
   except (OSError,StopIteration):pass
   if time.monotonic()-start>150:reason='duration_limit'
   if reason:
    child.terminate()
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:child.kill();child.wait()
    break
   time.sleep(.1)
  log.seek(0)
  print(json.dumps({'mode':mode,'returncode':child.wait(),'limit_stop':reason,'peak_rss':peak,'elapsed_seconds':time.monotonic()-start,'observations':log.read().splitlines()}),flush=True)
