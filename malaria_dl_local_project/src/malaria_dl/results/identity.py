"""Canonical event identity built solely from the E10.1 wire representation."""
import json

from ..execution.contracts import RunEvent


def canonical_event(event: RunEvent) -> str:
    """Compare full content, not repr, incidental key order or Python equality.

    Integral floats remain distinct from integers; bools remain distinct from
    numbers. UTC normalization comes from RunEvent. No payload interpretation.
    """
    return json.dumps(
        event.to_dict(), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
