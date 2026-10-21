"""Final evidence checks, without interpreting a performance failure as success."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent
checks=[]
def check(name,value,**details):checks.append(dict(name=name,passed=bool(value),**details))
for seal in sorted(ROOT.glob('*_seal.json')):
    for name,expected in json.loads(seal.read_text())['files'].items():
        path=Path(name)
        check(seal.name+'/'+path.name,path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==expected)
for name,expected in json.loads((ROOT/'candidate_v1.json').read_text())['files'].items():
    check('candidate_v1/'+name,hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected)
runtime=json.loads((ROOT/'before_candidate_runtime_sources.json').read_text())
for name,expected in runtime['files'].items():
    check('runtime/'+name,hashlib.sha256((ROOT.parents[2]/name).read_bytes()).hexdigest()==expected)
comparison_count=0
for path in sorted(ROOT.glob('*.json')):
    if path.name.endswith(('_aa.json','_ab.json','_comparison.json','_science.json','_interference.json',
                           '_exact.json','_reference.json')) or path.name=='receipt_verification.json':
        result=json.loads(path.read_text())
        if 'passed' in result:
            check('scientific_or_receipt/'+path.name,result['passed'],total=result.get('total'))
            comparison_count+=1
for arch in ['custom_cnn','vgg16','densenet121']:
    for arm in 'ab':
        path=ROOT/f'{arch}_state_{arm}/step_devices.jsonl'
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        devices=[device for row in rows for device in row['devices'].values()]
        check(f'GPU_model/{arch}/{arm}',bool(devices) and all(d.endswith('/device:GPU:0') for d in devices),steps=len(rows))
for stage in ['reproduction','final']:
    result=json.loads((ROOT/(stage+'_performance.json')).read_text())
    for arch in ['custom_cnn','vgg16','densenet121']:
        check(f'complete_pairs/{stage}/{arch}',len(result[arch]['pairs'])==5)
        for row in result[arch]['pairs']:
            check(f'aggregator_bound/{stage}/{arch}/{row["pair"]}',row['arms']['b']['observer']['aggregator_peak_bound_bytes']<=32*1024*1024)
capacity=json.loads((ROOT/'capacity_allocation.json').read_text())
check('capacity/tracemalloc',capacity['tracemalloc_peak_bytes']<=32*1024*1024)
check('capacity/RSS_increment',capacity['process_rss_peak_increment_bytes']<=32*1024*1024)
kill=json.loads((ROOT/'killed_training/kill_verification.json').read_text())
check('SIGKILL',kill['returncode']==-9 and kill['recovery']['batches']==5 and kill['recovery']['partial']==1)
write=json.loads((ROOT/'write_failure/write_failure_verification.json').read_text())
check('write_failure_recovery',write['before_recovery']['pending']==1 and
      write['after_recovery']['batches']==5 and write['after_recovery']['partial']==1 and
      all(r['status']=='recovered_exact_bytes' for r in write['recovery']))
preparation=json.loads((ROOT/'preparation_control/result.json').read_text())
check('prefetch_no_confirmation',preparation['prepared_images']==8 and preparation['confirmed_batches']==0 and preparation['durable_events']==0)
duration=[json.loads(line) for line in (ROOT/'duration_30_epochs/epoch_memory.jsonl').read_text().splitlines()]
check('duration_30_epochs',len(duration)==30 and len({r['aggregator_live_bytes'] for r in duration})==1)
for arch in ['custom_cnn','vgg16','densenet121']:
    drain=json.loads((ROOT/f'{arch}_drain_probe/drain_measurement.json').read_text())
    check('drain/'+arch,drain['passed'] and drain['max_confirmed_to_durable_seconds']<=5)
ledger_log=(ROOT/'regression_test_ledger.log').read_text()
check('all_15_ledger_tests','Ran 15 tests' in ledger_log and ledger_log.rstrip().endswith('OK'))
for hist in ['before_diagnostics','final']:
    result=json.loads((ROOT/f'historical_integrity_{hist}.json').read_text())['results']
    for name,data in result.items():check(f'historical/{hist}/{name}',data['passed'],files=data['total'])
a=json.loads((ROOT/'historical_integrity_before_diagnostics.json').read_text())['results']
b=json.loads((ROOT/'historical_integrity_final.json').read_text())['results']
check('historical_inventory_hashes',all(a[k]['inventory_sha256']==b[k]['inventory_sha256'] for k in a))
result=dict(utc=datetime.now(timezone.utc).isoformat(),passed=all(c['passed'] for c in checks),
    checks=checks,total=len(checks),comparison_documents=comparison_count,
    note='Evidence validity only; performance verdict remains independently strict.')
with (ROOT/'closeout.json').open('x') as stream:json.dump(result,stream,indent=2)
print({k:v for k,v in result.items() if k!='checks'})
assert result['passed']
