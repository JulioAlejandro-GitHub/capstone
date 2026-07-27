from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.db import get_primary_engine
from app.audit import record_event
from app.security import Principal, create_access_token, current_principal, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response, request: Request):
    with get_primary_engine().begin() as connection:
        row = connection.execute(text("""
            SELECT u.id::text, u.username, u.password_hash, u.status,
                   COALESCE(array_agg(r.name) FILTER (WHERE r.name IS NOT NULL), '{}') roles
            FROM users u LEFT JOIN user_roles ur ON ur.user_id=u.id
            LEFT JOIN roles r ON r.id=ur.role_id WHERE lower(u.username)=lower(:username)
            GROUP BY u.id
        """), {"username": body.username}).mappings().first()
        if not row or row["status"] != "active" or not verify_password(body.password, row["password_hash"]):
            record_event(event_type="USER_LOGIN_FAILED", action="login", principal=None,
                         request=request, success=False, error_code="INVALID_CREDENTIALS",
                         metadata={"username_supplied": bool(body.username)})
            raise HTTPException(401, "Credenciales inválidas.")
        connection.execute(text("UPDATE users SET last_login_at=:now WHERE id=CAST(:id AS uuid)"),
                           {"now": datetime.now(timezone.utc), "id": row["id"]})
    response.headers["Cache-Control"] = "no-store"
    principal = Principal(row["id"], row["username"], tuple(row["roles"]), frozenset())
    record_event(event_type="USER_LOGIN_SUCCEEDED", action="login", principal=principal,
                 request=request, success=True)
    return {"access_token": create_access_token(row["id"], row["username"], list(row["roles"])),
            "token_type": "bearer", "expires_in": 1800}


@router.get("/me")
def me(response: Response, principal: Principal = Depends(current_principal)):
    response.headers["Cache-Control"] = "no-store"
    return {"id": principal.user_id, "username": principal.username, "roles": principal.roles,
            "permissions": sorted(principal.permissions), "insecure_local": principal.insecure_local}
