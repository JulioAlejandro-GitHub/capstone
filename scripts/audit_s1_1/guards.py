"""Fail-closed guard for this audit's fixed, read-only SELECT statements."""
import re

def require_read_only_select(sql: str) -> None:
    if not re.match(r'^SELECT\s', sql, re.IGNORECASE):
        raise ValueError('Only SELECT statements are permitted')
    if re.search(r';|--|/\*|\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE|COPY|CALL|DO|INTO|LOCK|SET)\b',sql,re.IGNORECASE):
        raise ValueError('Statement outside the audit SELECT allowlist')
