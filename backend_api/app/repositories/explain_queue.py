"""Backend side of the host GPU queue: enqueue requests and read the agent heartbeat."""
import json
from typing import Any
from sqlalchemy import text
from app.db import get_primary_engine


class ExplainQueueRepository:
    def heartbeat(self) -> dict[str, Any] | None:
        with get_primary_engine().connect() as c:
            row = c.execute(text("""SELECT host, device, started_at, last_seen,
                    EXTRACT(EPOCH FROM clock_timestamp()-last_seen) AS age_seconds
                FROM executor_heartbeats WHERE executor='host_gpu' ORDER BY last_seen DESC LIMIT 1""")).mappings().one_or_none()
            return dict(row) if row else None

    def enqueue(self, request: dict[str, Any], key: str, actor: str) -> str:
        """Returns the pending request for this key, creating it only once (partial unique index)."""
        with get_primary_engine().begin() as c:
            created = c.execute(text("""INSERT INTO explain_requests(request,request_key,actor,executor)
                VALUES(CAST(:request AS jsonb),:key,:actor,'host_gpu')
                ON CONFLICT (request_key) WHERE state = ANY (ARRAY['queued', 'claimed']) DO NOTHING
                RETURNING id"""), dict(request=json.dumps(request), key=key, actor=actor)).scalar_one_or_none()
            if created:
                return str(created)
            return str(c.execute(text("""SELECT id FROM explain_requests WHERE request_key=:key
                AND state = ANY (ARRAY['queued', 'claimed'])"""), dict(key=key)).scalar_one())
