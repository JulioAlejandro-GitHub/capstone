"""NLM technical cross-source keys, not clinically verified biological identities.

Cell identifiers remain verbatim after the existing official CSV loader. Full
smear grammar is restricted to the 15 structural forms observed in all 193 RAW
directories (S1.2). Case and acquisition suffixes are significant. The three-digit
prefix is a source directory component of undocumented semantic meaning.
"""
from __future__ import annotations

import re
from collections.abc import Collection

_NUMBER = r"[1-9][0-9]*"
# Alternatives preserve observed combinations; no arbitrary trailing text.
_COMPONENT = (
    rf"C{_NUMBER}(?:"
    rf"P{_NUMBER}(?:ThinF|thinF|NThinF|N_ThinF|_ThinF|thinF_original|"
    rf"thin_Original_Motic|ReThinF|thinOriginalOlympusCX21|thin_original)"
    rf"|AP{_NUMBER}thinF|ThinF|thin_original|NThinF|NthinF)"
)
FULL_SMEAR_PATTERN = rf"[1-9][0-9]{{2}}(?P<canonical>{_COMPONENT})"


def canonical_nlm_cell_patient_key(
    official_patient_id: str, *, official_patient_ids: Collection[str]
) -> str:
    """Accept an ID only from the governed official mapping; preserve it exactly."""
    if not official_patient_id or official_patient_id not in official_patient_ids:
        raise ValueError(f"Unknown official NLM Cell Patient-ID: {official_patient_id!r}")
    return official_patient_id


def canonical_nlm_full_smear_patient_key(source_patient_id: str) -> str:
    """Parse a complete NLM directory ID, failing closed outside observed grammar."""
    match = re.fullmatch(FULL_SMEAR_PATTERN, source_patient_id)
    if match is None:
        raise ValueError(f"Invalid NLM Full Smear Patient-ID: {source_patient_id!r}")
    return match.group("canonical")
