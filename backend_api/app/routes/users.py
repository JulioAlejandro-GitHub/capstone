"""Gestión de cuentas: perfil propio y administración de usuarios.

Dos routers:
- ``me_router`` (``/api/v1/auth/me``): operaciones de autocuidado disponibles para
  cualquier usuario autenticado (perfil y contraseña propios).
- ``router`` (``/api/v1/users``): administración, gobernada por ``USERS_READ`` /
  ``USERS_MANAGE`` (solo administrador).

Borrado lógico: "eliminar" = ``status='disabled'`` + ``disabled_at=NOW()``; nunca DELETE.
Toda mutación registra un evento de auditoría en la misma transacción, sin contraseñas
ni hashes en metadata / before_state / after_state.
"""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import text

from app.audit import (
    mutation_connection,
    record_event,
    transactional_auth,
    transactional_permission,
)
from app.db import get_primary_engine
from app.security import (
    ROLE_PERMISSIONS,
    Principal,
    current_principal,
    hash_password,
    require_permission,
    verify_password,
)
from app.security import Permission
from app.services.serialization import to_jsonable

me_router = APIRouter(prefix="/api/v1/auth/me", tags=["users"])
router = APIRouter(prefix="/api/v1/users", tags=["users"])

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 10
VALID_ROLE_NAMES = frozenset(ROLE_PERMISSIONS)
INSECURE_LOCAL_MESSAGE = "No disponible con autenticación deshabilitada."


def _uid(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise HTTPException(422, "UUID inválido.") from exc


def _normalize_email(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip().lower()
    if not EMAIL_PATTERN.match(value):
        raise PydanticCustomError("invalid_email", "El formato del email no es válido.")
    return value


def _normalize_roles(value: list[str] | None, required: bool) -> list[str] | None:
    if value is None:
        if required:
            raise PydanticCustomError("roles_required", "Se requiere al menos un rol.")
        return None
    if not value:
        raise PydanticCustomError("roles_required", "Se requiere al menos un rol.")
    for role in value:
        if role not in VALID_ROLE_NAMES:
            raise PydanticCustomError("invalid_role", "Rol no válido: {role}", {"role": role})
    return list(dict.fromkeys(value))


def _fetch_user(connection, user_id: str) -> dict | None:
    row = connection.execute(
        text(
            """
            SELECT u.id::text, u.username, u.email, u.status,
                   u.created_at, u.updated_at, u.last_login_at, u.disabled_at,
                   COALESCE(array_agg(r.name) FILTER (WHERE r.name IS NOT NULL), '{}') roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE u.id = CAST(:id AS uuid)
            GROUP BY u.id
            """
        ),
        {"id": user_id},
    ).mappings().first()
    if not row:
        return None
    return to_jsonable(dict(row))


def _active_admin_count(connection, exclude_user_id: str | None = None) -> int:
    sql = (
        "SELECT COUNT(*) FROM users u "
        "JOIN user_roles ur ON ur.user_id = u.id "
        "JOIN roles r ON r.id = ur.role_id "
        "WHERE u.status = 'active' AND r.name = 'administrator'"
    )
    params: dict = {}
    if exclude_user_id:
        sql += " AND u.id <> CAST(:exclude AS uuid)"
        params["exclude"] = exclude_user_id
    return connection.execute(text(sql), params).scalar_one()


def _email_in_use(connection, email: str, exclude_user_id: str | None = None) -> bool:
    sql = "SELECT 1 FROM users WHERE lower(email) = lower(:email)"
    params: dict = {"email": email}
    if exclude_user_id:
        sql += " AND id <> CAST(:exclude AS uuid)"
        params["exclude"] = exclude_user_id
    return connection.execute(text(sql), params).first() is not None


def _replace_roles(connection, user_id: str, role_names: list[str]) -> None:
    connection.execute(
        text("DELETE FROM user_roles WHERE user_id = CAST(:id AS uuid)"),
        {"id": user_id},
    )
    role_ids = connection.execute(
        text("SELECT id FROM roles WHERE name = ANY(:names)"),
        {"names": role_names},
    ).fetchall()
    for (role_id,) in role_ids:
        connection.execute(
            text("INSERT INTO user_roles(user_id, role_id) VALUES(:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )


# --------------------------------------------------------------------------- #
# Cuenta propia (cualquier usuario autenticado)
# --------------------------------------------------------------------------- #
class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        return _normalize_email(value)


class OwnPasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


@me_router.get("/profile")
def get_profile(principal: Principal = Depends(current_principal)):
    if principal.insecure_local:
        raise HTTPException(409, INSECURE_LOCAL_MESSAGE)
    with get_primary_engine().connect() as connection:
        user = _fetch_user(connection, principal.user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado.")
    return {
        "username": user["username"],
        "email": user["email"],
        "roles": user["roles"],
        "status": user["status"],
        "created_at": user["created_at"],
        "last_login_at": user["last_login_at"],
    }


@me_router.patch("/profile")
def update_profile(
    body: ProfileUpdate,
    request: Request,
    principal: Principal = Depends(transactional_auth()),
):
    if principal.insecure_local:
        raise HTTPException(409, INSECURE_LOCAL_MESSAGE)
    email = body.email
    with mutation_connection(get_primary_engine()) as connection:
        before = _fetch_user(connection, principal.user_id)
        if not before:
            raise HTTPException(404, "Usuario no encontrado.")
        if email is not None and _email_in_use(connection, email, exclude_user_id=principal.user_id):
            raise HTTPException(409, "El email ya está en uso por otro usuario.")
        connection.execute(
            text("UPDATE users SET email = :email, updated_at = NOW() WHERE id = CAST(:id AS uuid)"),
            {"email": email, "id": principal.user_id},
        )
        after = _fetch_user(connection, principal.user_id)
        record_event(
            event_type="USER_UPDATED",
            action="profile",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=principal.user_id,
            before_state={"email": before["email"]},
            after_state={"email": after["email"]},
        )
    return {"username": principal.username, "email": email}


@me_router.post("/password")
def change_own_password(
    body: OwnPasswordChange,
    request: Request,
    principal: Principal = Depends(transactional_auth()),
):
    if principal.insecure_local:
        raise HTTPException(409, INSECURE_LOCAL_MESSAGE)
    with mutation_connection(get_primary_engine()) as connection:
        row = connection.execute(
            text("SELECT password_hash FROM users WHERE id = CAST(:id AS uuid)"),
            {"id": principal.user_id},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "Usuario no encontrado.")
        if not verify_password(body.current_password, row["password_hash"]):
            raise HTTPException(400, "La contraseña actual es incorrecta.")
        if len(body.new_password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(
                422, f"La nueva contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
            )
        if body.new_password == body.current_password:
            raise HTTPException(422, "La nueva contraseña debe ser distinta de la actual.")
        connection.execute(
            text("UPDATE users SET password_hash = :hash, updated_at = NOW() WHERE id = CAST(:id AS uuid)"),
            {"hash": hash_password(body.new_password), "id": principal.user_id},
        )
        record_event(
            event_type="USER_PASSWORD_CHANGED",
            action="password-change",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=principal.user_id,
            metadata={"username": principal.username},
        )
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Administración (USERS_READ / USERS_MANAGE)
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    email: str | None = None
    password: str = Field(min_length=1)
    roles: list[str] = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La contraseña no puede estar vacía.")
        return value

    @field_validator("roles")
    @classmethod
    def _validate_roles(cls, value: list[str]) -> list[str]:
        return _normalize_roles(value, required=True)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = None
    roles: list[str] | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        return _normalize_email(value)

    @field_validator("roles")
    @classmethod
    def _validate_roles(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_roles(value, required=False)


class PasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_password: str = Field(min_length=1)

    @field_validator("new_password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
        return value


@router.get("")
def list_users(
    status: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(require_permission(Permission.USERS_READ)),
):
    where: list[str] = []
    params: dict = {}
    if status in ("active", "disabled"):
        where.append("u.status = :status")
        params["status"] = status
    if q and q.strip():
        where.append("(lower(u.username) LIKE :q OR lower(u.email) LIKE :q)")
        params["q"] = f"%{q.strip().lower()}%"
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    with get_primary_engine().connect() as connection:
        total = connection.execute(
            text(f"SELECT COUNT(*) FROM users u {where_sql}"), params
        ).scalar_one()
        rows = connection.execute(
            text(
                f"""
                SELECT u.id::text, u.username, u.email, u.status,
                       u.created_at, u.last_login_at, u.disabled_at,
                       COALESCE(array_agg(r.name) FILTER (WHERE r.name IS NOT NULL), '{{}}') roles
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.id
                LEFT JOIN roles r ON r.id = ur.role_id
                {where_sql}
                GROUP BY u.id
                ORDER BY u.username
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": limit, "offset": offset},
        ).mappings().all()
    return {
        "items": [to_jsonable(dict(row)) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", status_code=201)
def create_user(
    body: UserCreate,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.USERS_MANAGE)),
):
    username = body.username.strip()
    if not username:
        raise HTTPException(422, "El username no puede estar vacío.")
    with mutation_connection(get_primary_engine()) as connection:
        if connection.execute(
            text("SELECT 1 FROM users WHERE lower(username) = lower(:username)"),
            {"username": username},
        ).first():
            raise HTTPException(409, "El username ya existe.")
        if body.email is not None and _email_in_use(connection, body.email):
            raise HTTPException(409, "El email ya está en uso por otro usuario.")
        user_id = str(uuid4())
        connection.execute(
            text(
                "INSERT INTO users(id, username, email, password_hash, status) "
                "VALUES(:id, :username, :email, :password_hash, 'active')"
            ),
            {
                "id": user_id,
                "username": username,
                "email": body.email,
                "password_hash": hash_password(body.password),
            },
        )
        _replace_roles(connection, user_id, body.roles)
        record_event(
            event_type="USER_CREATED",
            action="create",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=user_id,
            after_state={"username": username, "email": body.email, "roles": body.roles},
        )
    return {
        "id": user_id,
        "username": username,
        "email": body.email,
        "roles": body.roles,
        "status": "active",
    }


@router.patch("/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdate,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.USERS_MANAGE)),
):
    uid = _uid(user_id)
    with mutation_connection(get_primary_engine()) as connection:
        before = _fetch_user(connection, uid)
        if not before:
            raise HTTPException(404, "Usuario no encontrado.")
        email = body.email if body.email is not None else before["email"]
        if email is not None and _email_in_use(connection, email, exclude_user_id=uid):
            raise HTTPException(409, "El email ya está en uso por otro usuario.")
        new_roles = body.roles if body.roles is not None else before["roles"]
        # Salvaguarda: un administrador no puede quitarse el rol administrator.
        if (
            uid == principal.user_id
            and "administrator" in before["roles"]
            and "administrator" not in new_roles
        ):
            raise HTTPException(409, "No puedes quitarte el rol de administrador.")
        # Salvaguarda: no dejar el sistema sin ningún administrador activo.
        if (
            before["status"] == "active"
            and "administrator" in before["roles"]
            and "administrator" not in new_roles
            and _active_admin_count(connection, exclude_user_id=uid) == 0
        ):
            raise HTTPException(409, "No se puede dejar el sistema sin administradores activos.")
        connection.execute(
            text("UPDATE users SET email = :email, updated_at = NOW() WHERE id = CAST(:id AS uuid)"),
            {"email": email, "id": uid},
        )
        if body.roles is not None:
            _replace_roles(connection, uid, new_roles)
        after = _fetch_user(connection, uid)
        record_event(
            event_type="USER_UPDATED",
            action="update",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=uid,
            before_state={"email": before["email"], "roles": before["roles"]},
            after_state={"email": after["email"], "roles": after["roles"]},
        )
    return after


@router.post("/{user_id}/disable")
def disable_user(
    user_id: str,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.USERS_MANAGE)),
):
    uid = _uid(user_id)
    with mutation_connection(get_primary_engine()) as connection:
        before = _fetch_user(connection, uid)
        if not before:
            raise HTTPException(404, "Usuario no encontrado.")
        if before["status"] == "disabled":
            raise HTTPException(409, "El usuario ya está desactivado.")
        if uid == principal.user_id:
            raise HTTPException(409, "No puedes desactivar tu propia cuenta.")
        if (
            before["status"] == "active"
            and "administrator" in before["roles"]
            and _active_admin_count(connection, exclude_user_id=uid) == 0
        ):
            raise HTTPException(409, "No se puede desactivar al único administrador activo.")
        connection.execute(
            text(
                "UPDATE users SET status = 'disabled', disabled_at = NOW(), updated_at = NOW() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": uid},
        )
        after = _fetch_user(connection, uid)
        record_event(
            event_type="USER_DISABLED",
            action="disable",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=uid,
            before_state={"status": before["status"]},
            after_state={"status": after["status"]},
        )
    return after


@router.post("/{user_id}/enable")
def enable_user(
    user_id: str,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.USERS_MANAGE)),
):
    uid = _uid(user_id)
    with mutation_connection(get_primary_engine()) as connection:
        before = _fetch_user(connection, uid)
        if not before:
            raise HTTPException(404, "Usuario no encontrado.")
        if before["status"] == "active":
            raise HTTPException(409, "El usuario ya está activo.")
        connection.execute(
            text(
                "UPDATE users SET status = 'active', disabled_at = NULL, updated_at = NOW() "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": uid},
        )
        after = _fetch_user(connection, uid)
        record_event(
            event_type="USER_ENABLED",
            action="enable",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=uid,
            before_state={"status": before["status"]},
            after_state={"status": after["status"]},
        )
    return after


@router.post("/{user_id}/password")
def reset_user_password(
    user_id: str,
    body: PasswordReset,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.USERS_MANAGE)),
):
    uid = _uid(user_id)
    with mutation_connection(get_primary_engine()) as connection:
        before = _fetch_user(connection, uid)
        if not before:
            raise HTTPException(404, "Usuario no encontrado.")
        connection.execute(
            text("UPDATE users SET password_hash = :hash, updated_at = NOW() WHERE id = CAST(:id AS uuid)"),
            {"hash": hash_password(body.new_password), "id": uid},
        )
        record_event(
            event_type="USER_PASSWORD_RESET",
            action="password-reset",
            principal=principal,
            request=request,
            success=True,
            connection=connection,
            resource_type="users",
            resource_id=uid,
            metadata={"username": before["username"]},
        )
    return {"id": uid, "username": before["username"]}
