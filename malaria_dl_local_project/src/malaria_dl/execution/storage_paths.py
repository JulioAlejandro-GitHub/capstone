"""Resolve governed scientific binaries across Mac/Docker without rewriting identity."""
from pathlib import Path
from ..campaigns.contracts import CampaignError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
# campaign_runs holds checkpoints of campaign-launched TRAIN; same <tree>/<run uuid>/<file> layout.
ALLOWED_TREES = (('outputs', 'train_runs'), ('outputs', 'campaign_runs'), ('artifacts', 'assessments'))


def local_scientific_path(value: str | Path) -> Path:
    path = Path(value)
    if '..' in path.parts:
        raise CampaignError('SCIENTIFIC_PATH_INVALID')
    if path.exists():
        return path
    # Only registered project subtrees are portable, never arbitrary host paths.
    if path.parts.count('malaria_dl_local_project') != 1:
        return path
    suffix = path.parts[path.parts.index('malaria_dl_local_project') + 1:]
    if len(suffix) < 4 or tuple(suffix[:2]) not in ALLOWED_TREES:
        return path
    from uuid import UUID
    try:
        UUID(suffix[2])
    except ValueError:
        raise CampaignError('SCIENTIFIC_PATH_INVALID') from None
    tree = PROJECT_ROOT.joinpath(*suffix[:2]).resolve()
    root = PROJECT_ROOT.joinpath(*suffix[:3]).resolve()
    if not root.is_relative_to(tree):
        raise CampaignError('SCIENTIFIC_PATH_INVALID')
    candidate = PROJECT_ROOT.joinpath(*suffix)
    if not candidate.resolve().is_relative_to(root):
        raise CampaignError('SCIENTIFIC_PATH_INVALID')
    return candidate


def incorporate_training_files(run_id, files):
    """Copy verified external files to the existing standalone TRAIN tree.

    No overwrite or cleanup: failed transactions leave inspectable files, never
    remove potentially scientific evidence. The caller registers the final paths.
    """
    import os
    import shutil
    from uuid import UUID
    from ..pretrained.registration import verified_file

    run = str(UUID(str(run_id)))
    sources = [verified_file(item) for item in files]
    common = Path(os.path.commonpath([str(Path(item['path']).parent) for item in sources]))
    root = PROJECT_ROOT / 'outputs' / 'train_runs' / run
    if any(parent.is_symlink() for parent in root.parents):
        raise ValueError('Symlink in TRAIN artifact root')
    root.mkdir(parents=True, exist_ok=False)
    result = []
    for item in sources:
        target = root / Path(item['path']).relative_to(common)
        target.parent.mkdir(parents=True, exist_ok=True)
        with Path(item['path']).open('rb') as source, target.open('xb') as destination:
            shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        result.append(verified_file({**item, 'path': str(target)}))
    return result
