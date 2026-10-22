"""Public, enumerable EXPLAIN error codes."""
import re
from src.malaria_dl.campaigns.contracts import CampaignError


def safe_code(exc: BaseException) -> str:
    code = str(exc)
    return code if isinstance(exc, CampaignError) and re.fullmatch('[A-Z][A-Z0-9_]+', code) else 'EXPLAIN_EXECUTOR_FAILED'
