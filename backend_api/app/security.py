from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import text

from app.config import get_settings
from app.db import get_primary_engine


password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


class Permission(StrEnum):
    SYSTEM_READ = "system.read"
    SYSTEM_ADMIN = "system.admin"
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"
    MODELS_READ = "models.read"
    MODELS_PUBLISH = "models.publish"
    MODELS_DEACTIVATE = "models.deactivate"
    MODELS_SET_DEFAULT = "models.set_default"
    RUNS_READ = "runs.read"
    PREDICTIONS_READ = "predictions.read"
    PREDICTIONS_EXECUTE = "predictions.execute"
    DATASETS_READ = "datasets.read"
    ARTIFACTS_READ = "artifacts.read"
    AUDIT_READ = "audit.read"
    SCIENTIFIC_SUBJECTS_READ = "scientific.subjects.read"
    SCIENTIFIC_SUBJECTS_CREATE = "scientific.subjects.create"
    SCIENTIFIC_SUBJECTS_UPDATE = "scientific.subjects.update"
    SCIENTIFIC_SUBJECTS_ARCHIVE = "scientific.subjects.archive"
    SCIENTIFIC_CASES_READ = "scientific.cases.read"
    SCIENTIFIC_CASES_CREATE = "scientific.cases.create"
    SCIENTIFIC_CASES_UPDATE = "scientific.cases.update"
    SCIENTIFIC_CASES_ARCHIVE = "scientific.cases.archive"
    SCIENTIFIC_SAMPLES_READ = "scientific.samples.read"
    SCIENTIFIC_SAMPLES_CREATE = "scientific.samples.create"
    SCIENTIFIC_SAMPLES_UPDATE = "scientific.samples.update"
    SCIENTIFIC_SAMPLES_ARCHIVE = "scientific.samples.archive"
    SCIENTIFIC_SLIDES_READ = "scientific.slides.read"
    SCIENTIFIC_SLIDES_CREATE = "scientific.slides.create"
    SCIENTIFIC_SLIDES_UPDATE = "scientific.slides.update"
    SCIENTIFIC_SLIDES_ARCHIVE = "scientific.slides.archive"
    SCIENTIFIC_IMAGES_READ = "scientific.images.read"
    SCIENTIFIC_IMAGES_REGISTER = "scientific.images.register"
    SCIENTIFIC_IMAGES_UPDATE = "scientific.images.update"
    SCIENTIFIC_IMAGES_ARCHIVE = "scientific.images.archive"


READ = {
    Permission.SYSTEM_READ, Permission.MODELS_READ, Permission.RUNS_READ,
    Permission.PREDICTIONS_READ, Permission.DATASETS_READ, Permission.ARTIFACTS_READ,
}
SCIENTIFIC_READ = {
    Permission.SCIENTIFIC_SUBJECTS_READ, Permission.SCIENTIFIC_CASES_READ,
    Permission.SCIENTIFIC_SAMPLES_READ, Permission.SCIENTIFIC_SLIDES_READ,
    Permission.SCIENTIFIC_IMAGES_READ,
}
SCIENTIFIC_WRITE = {
    Permission.SCIENTIFIC_SUBJECTS_CREATE, Permission.SCIENTIFIC_SUBJECTS_UPDATE,
    Permission.SCIENTIFIC_CASES_CREATE, Permission.SCIENTIFIC_CASES_UPDATE,
    Permission.SCIENTIFIC_SAMPLES_CREATE, Permission.SCIENTIFIC_SAMPLES_UPDATE,
    Permission.SCIENTIFIC_SLIDES_CREATE, Permission.SCIENTIFIC_SLIDES_UPDATE,
    Permission.SCIENTIFIC_IMAGES_REGISTER, Permission.SCIENTIFIC_IMAGES_UPDATE,
}
ROLE_PERMISSIONS = {
    "administrator": set(Permission),
    "researcher": READ | SCIENTIFIC_READ | SCIENTIFIC_WRITE | {
        Permission.PREDICTIONS_EXECUTE, Permission.AUDIT_READ,
    },
    "operator": READ | SCIENTIFIC_READ | SCIENTIFIC_WRITE | {Permission.PREDICTIONS_EXECUTE},
    "reviewer": READ | SCIENTIFIC_READ,
    "read_only": READ | SCIENTIFIC_READ,
}


@dataclass(frozen=True)
class Principal:
    user_id: str
    username: str
    roles: tuple[str, ...]
    permissions: frozenset[Permission]
    insecure_local: bool = False


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("La password no puede estar vacía")
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: UUID | str, username: str, roles: list[str]) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id), "username": username, "roles": roles,
        "iat": now, "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    settings = get_settings()
    if settings.auth_mode == "disabled":
        return Principal("local-insecure", "local-insecure", ("administrator",), frozenset(Permission), True)
    if credentials is None:
        raise HTTPException(401, "Se requiere autenticación.", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if claims.get("type") != "access" or not claims.get("sub"):
            raise jwt.InvalidTokenError()
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(401, "Token expirado.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, "Token inválido.") from exc
    roles = tuple(role for role in claims.get("roles", []) if role in ROLE_PERMISSIONS)
    with get_primary_engine().connect() as connection:
        user = connection.execute(
            text("SELECT username, status FROM users WHERE id=CAST(:id AS uuid)"),
            {"id": str(claims["sub"])},
        ).mappings().first()
    if not user or user["status"] != "active":
        raise HTTPException(401, "Usuario inactivo.")
    roles = tuple(connection_role for connection_role in roles)
    permissions = frozenset().union(*(ROLE_PERMISSIONS[role] for role in roles))
    return Principal(str(claims["sub"]), str(user["username"]), roles, permissions)


def require_permission(permission: Permission):
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if permission not in principal.permissions:
            raise HTTPException(403, "Permiso insuficiente.")
        return principal
    return dependency
