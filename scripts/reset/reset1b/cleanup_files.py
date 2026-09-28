"""Remove only disposable copies created under this rehearsal's private directory."""
import json,re,shutil
from pathlib import Path
from common import require
HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/'target.json').read_text())
require(str(HERE)==cfg['backend_work'] and HERE.name.startswith('reset1b_') and HERE.parent==Path('/tmp'),'PRIVATE_REHEARSAL_DIRECTORY_REQUIRED')
removed=[]
for root in sorted(HERE.glob('reset1b-files-*')):
    require(root.is_dir() and not root.is_symlink() and root.parent==HERE,'DISPOSABLE_ROOT_REQUIRED')
    identity=json.loads((root/'identity.json').read_text())
    require(identity['task']=='RESET.1B' and re.fullmatch('[0-9a-f]{48}',identity['token']),'DISPOSABLE_MARKER_REQUIRED')
    require({p.name for p in root.iterdir()}<={'live','quarantine','identity.json','journal.json','journal.next'},'UNKNOWN_DISPOSABLE_CONTENT')
    count=0
    for name in ('live','quarantine'):
        folder=root/name;require(folder.is_dir() and not folder.is_symlink(),'INVALID_COPY_DIRECTORY')
        for p in folder.iterdir():
            require(p.is_file() and not p.is_symlink() and re.fullmatch('[0-9a-f]{64}',p.name),'INVALID_COPY_ENTRY')
            count+=1
    shutil.rmtree(root)
    removed.append({'private_directory':str(root),'disposable_copies_removed':count})
print(json.dumps({'removed':removed,'operational_paths_removed':0}))
