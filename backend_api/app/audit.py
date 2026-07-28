from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.db import get_primary_engine
from app.observability import correlation_id_context, sanitize
from app.security import Permission, Principal, require_permission


audit_transaction_connection: ContextVar[Connection | None] = ContextVar(
    "audit_transaction_connection", default=None
)


def _resource(request: Request) -> tuple[str, str | None]:
    params = dict(request.path_params)
    resource_id = next((str(value) for key, value in params.items() if key.endswith("_id")), None)
    parts = [part for part in request.url.path.split("/") if part and not part.startswith("{")]
    return (parts[-2] if resource_id and len(parts) > 1 else parts[-1], resource_id)


def record_event(
    *,
    event_type: str,
    action: str,
    principal: Principal | None,
    request: Request,
    success: bool,
    error_code: str | None = None,
    metadata: dict | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    connection: Connection | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> None:
    inferred_type, inferred_id = _resource(request)
    resource_type = resource_type or inferred_type
    resource_id = resource_id or inferred_id
    safe_metadata = sanitize(metadata or {})
    parameters = {
        "id": uuid4(), "event_type": event_type, "action": action,
        "actor_user_id": principal.user_id if principal and not principal.insecure_local else None,
        "username": principal.username if principal else None,
        "resource_type": resource_type, "resource_id": resource_id,
        "method": request.method, "path": request.url.path,
        "correlation_id": correlation_id_context.get(),
        "before_state": json.dumps(sanitize(before_state)) if before_state is not None else None,
        "after_state": json.dumps(sanitize(after_state)) if after_state is not None else None,
        "metadata": json.dumps(safe_metadata), "success": success, "error_code": error_code,
    }
    statement = text("""
          INSERT INTO audit_events(
            id,event_type,action,actor_user_id,actor_username_snapshot,
            resource_type,resource_id,request_method,request_path,correlation_id,
            before_state,after_state,metadata,success,error_code
          ) VALUES(
            :id,:event_type,:action,CAST(:actor_user_id AS uuid),:username,
            :resource_type,:resource_id,:method,:path,:correlation_id,
            CAST(:before_state AS jsonb),CAST(:after_state AS jsonb),
            CAST(:metadata AS jsonb),:success,:error_code
          )
        """)
    if connection is not None:
        connection.execute(statement, parameters)
    else:
        with get_primary_engine().begin() as owned_connection:
            owned_connection.execute(statement, parameters)


@contextmanager
def mutation_connection(engine: Engine):
    """Reuse the audited request transaction, or own one outside HTTP mutations."""
    shared = audit_transaction_connection.get()
    if shared is not None:
        yield shared
    else:
        with engine.begin() as connection:
            yield connection


def audited_permission(permission: Permission, event_type: str) -> Callable:
    permission_dependency = require_permission(permission)

    async def dependency(
        request: Request,
        principal: Principal = Depends(permission_dependency),
    ):
        with get_primary_engine().begin() as connection:
            connection.execute(text("SELECT 1 FROM audit_events LIMIT 1"))
            token = audit_transaction_connection.set(connection)
            try:
                yield principal
                record_event(
                    event_type=event_type, action=request.url.path,
                    principal=principal, request=request, success=True,
                    connection=connection,
                )
            finally:
                audit_transaction_connection.reset(token)

    return dependency


def transactional_permission(permission: Permission) -> Callable:
    """Authorize a mutation and expose one transaction for domain mutation + audit."""
    permission_dependency = require_permission(permission)

    async def dependency(
        request: Request, principal: Principal = Depends(permission_dependency),
    ):
        try:
            with get_primary_engine().begin() as connection:
                token = audit_transaction_connection.set(connection)
                try:
                    yield principal
                finally:
                    audit_transaction_connection.reset(token)
        except Exception:
            from app.services.local_storage import LocalStorage
            LocalStorage.cleanup(getattr(request.state, "storage_compensation", []))
            raise

    return dependency


def service_audited_permission(permission: Permission) -> Callable:
    """Authorize a mutation whose service owns and audits multiple transactions.

    Long-running synchronous workflows cannot keep the request transaction open
    while CPU work executes. The service must explicitly record its lifecycle
    audit events in each durable state transition.
    """
    permission_dependency = require_permission(permission)

    def dependency(
        principal: Principal = Depends(permission_dependency),
    ) -> Principal:
        return principal

    return dependency
