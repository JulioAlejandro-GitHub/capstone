"""All candidate training is sequential; final clean runs follow validation."""
import sys
from pathlib import Path
from campaign import HERE,seal,run

commands=[[sys.executable,str(HERE/script),*args] for script,args in [
    ('freeze_runtime.py',['before_candidate']),
    ('regression_campaign.py',[]),
    ('candidate_profile_campaign.py',[]),
    ('campaign.py',['final']),
    ('analyze.py',['final']),
]]
seal('post_profile_plan_v1',list(HERE.glob('*.py')),commands)
for index,command in enumerate(commands):
    run(command,f'post_profile_{index}_{Path(command[1]).stem}')
