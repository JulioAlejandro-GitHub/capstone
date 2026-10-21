"""Receipt-only recovery latency, not a model run or acceptance benchmark."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime,timezone
from ledger import Store,Aggregator
from recover_pending import recover
from analyze import stats

ROOT=Path(__file__).resolve().parent
sources=[Path(__file__),ROOT/'ledger.py',ROOT/'recover_pending.py']
with (ROOT/'recovery_profile_seal.json').open('x') as f:
    json.dump(dict(utc=datetime.now(timezone.utc).isoformat(),files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},commands=[[sys.executable,str(Path(__file__))]]),f,indent=2)
directory=ROOT/'recovery_profile';directory.mkdir(exist_ok=False)
rows=[]
for i in range(12):
    store=Store(directory/f'case_{i:02d}')
    agg=Aggregator(store);agg.open(dict(run_id='synthetic-recovery-profile',epoch_local=i+1))
    agg.add(list(range(8)));agg.flush()
    folder=next(store.root.iterdir());final=folder/'00000001.json';pending=folder/'00000001.pending'
    expected=final.read_bytes()
    os.rename(final,pending)
    fd=os.open(folder,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    started=time.perf_counter();result=recover(store);elapsed=time.perf_counter()-started
    verified=store.verify()
    assert result[0]['status']=='recovered_exact_bytes' and final.read_bytes()==expected
    assert verified['batches']==1 and verified['pending']==0 and verified['partial']==1
    rows.append(dict(recovery_seconds=elapsed,verification=verified,outcomes=result))
with (ROOT/'recovery_profile.json').open('x') as f:
    json.dump(dict(receipt_only=True,acceptance=False,rows=rows,recovery=stats([r['recovery_seconds'] for r in rows]),
        verification=stats([r['verification']['recovery_seconds'] for r in rows])),f,indent=2)
print('12 exact recovery simulations passed')
