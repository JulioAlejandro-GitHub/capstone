"""Confirm removal of redundant materialization, separate from acceptance."""
import json
import sys
from pathlib import Path
from campaign import HERE,OLD,seal,run,compare

commands=[[sys.executable,str(HERE/'profile_candidate.py'),arch,'full']
          for arch in ['custom_cnn','vgg16','densenet121']]
seal('candidate_profiles_v1',[Path(__file__),HERE/'profile_candidate.py',HERE/'experiment_benchmarked.py',
     HERE/'observer.py',HERE/'ledger.py',OLD/'compare.py'],commands)
for command in commands:
    arch=command[-2]
    name=f'diagnostic_candidate_{arch}_full'
    run(command,name)
    result=compare(HERE/f'{arch}_b',HERE/name)
    (HERE/(name+'_science.json')).write_text(json.dumps(result,indent=2))
    if not result['passed']:raise RuntimeError('CANDIDATE_PROFILE_INTERFERENCE')
