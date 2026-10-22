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
