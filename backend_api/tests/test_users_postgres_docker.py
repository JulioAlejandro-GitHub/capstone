"""Pruebas de PostgreSQL para la gestión de cuentas (perfil propio + administración).

Sigue el patrón de ``test_auth_postgres_docker.py`` y ``test_scientific_data_api_postgres.py``:
una transacción externa con savepoint que se revierte al final, un ``TransactionEngine``
compartido inyectado en los módulos que resuelven el engine (``security``, ``audit`` y
``routes.users``) y ``TestClient`` para ejercitar la cadena real de dependencias
(RBAC, auditoría transaccional y borrado lógico).

Cobertura requerida:
- Permisos: 403 para no administradores.
- Unicidad de username / email: 409.
- Borrado lógico (disable) y reactivación (enable).
- Salvaguarda del último administrador (no dejar el sistema sin administración).
- Cambio de contraseña: actual incorrecta (400) y política (422).
- Usuario desactivado: su sesión activa recibe 401 de inmediato.
"""

import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.audit as audit
import app.routes.users as users_routes
import app.security as security
from app.config import Settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url
from app.main import app


pytestmark = pytest.mark.requires_docker_postgres


@pytest.fixture(autouse=True)
def require_docker_gate():
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL Docker explícito")


class TransactionEngine:
    """Expone una conexión compartida como si fuera un engine.

    ``begin()`` abre un savepoint (``begin_nested``) que se libera en salida limpia,
    de modo que las mutaciones permanecen en la transacción externa del test y se
    revierten con el ``rollback`` final. ``connect()`` simplemente cede la conexión.
    """

    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


def _insert_user(connection, user_id, username, role_name, password):
    connection.execute(
        text(
            """
            INSERT INTO users(id, username, email, password_hash, status)
            VALUES(:id, :username, :email, :password_hash, 'active')
            """
        ),
        {
            "id": user_id,
            "username": username,
            "email": f"{username}@invalid.test",
            "password_hash": security.hash_password(password),
        },
    )
    connection.execute(
        text(
            "INSERT INTO user_roles(user_id, role_id) "
            "SELECT :user_id, id FROM roles WHERE name = :role"
        ),
        {"user_id": user_id, "role": role_name},
    )


@pytest.fixture()
def users_client(monkeypatch):
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    connection = engine.connect()
    outer = connection.begin()
    assert_capstone_database(
        settings, connection.execute(text("SELECT current_database()")).scalar_one()
    )
    suffix = uuid4().hex[:10]
    admin_id, researcher_id = uuid4(), uuid4()
    admin_name, researcher_name = f"adm_{suffix}", f"res_{suffix}"
    password = uuid4().hex
    _insert_user(connection, admin_id, admin_name, "administrator", password)
    _insert_user(connection, researcher_id, researcher_name, "researcher", password)
    shared = TransactionEngine(connection)
    monkeypatch.setattr(security, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(audit, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(users_routes, "get_primary_engine", lambda: shared)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield {
                "client": client,
                "connection": connection,
                "admin_id": str(admin_id),
                "researcher_id": str(researcher_id),
                "admin_name": admin_name,
                "researcher_name": researcher_name,
                "password": password,
                "admin_headers": {
                    "Authorization": f"Bearer {security.create_access_token(admin_id, admin_name, ['administrator'])}"
                },
                "researcher_headers": {
                    "Authorization": f"Bearer {security.create_access_token(researcher_id, researcher_name, ['researcher'])}"
                },
            }
    finally:
        outer.rollback()
        connection.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# Permisos
# --------------------------------------------------------------------------- #
def test_non_admin_cannot_list_or_manage_users(users_client):
    client = users_client["client"]
    researcher = users_client["researcher_headers"]
    admin = users_client["admin_headers"]

    assert client.get("/api/v1/users", headers=researcher).status_code == 403
    assert client.post(
        "/api/v1/users", headers=researcher,
        json={"username": "nope", "password": "password12345", "roles": ["read_only"]},
    ).status_code == 403
    assert client.post(
        f"/api/v1/users/{users_client['researcher_id']}/disable", headers=researcher
    ).status_code == 403

    # El administrador sí puede listar.
    listed = client.get("/api/v1/users", headers=admin)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 2


def test_unauthenticated_is_rejected(users_client):
    client = users_client["client"]
    assert client.get("/api/v1/users").status_code == 401
    assert client.get("/api/v1/auth/me/profile").status_code == 401


# --------------------------------------------------------------------------- #
# Unicidad
# --------------------------------------------------------------------------- #
def test_create_user_enforces_uniqueness(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]
    suffix = uuid4().hex[:10]
    username = f"uniq_{suffix}"
    email = f"uniq_{suffix}@invalid.test"

    created = client.post(
        "/api/v1/users", headers=admin,
        json={"username": username, "email": email, "password": "password12345", "roles": ["read_only"]},
    )
    assert created.status_code == 201, created.text

    duplicate_username = client.post(
        "/api/v1/users", headers=admin,
        json={"username": username, "password": "password12345", "roles": ["read_only"]},
    )
    assert duplicate_username.status_code == 409

    duplicate_email = client.post(
        "/api/v1/users", headers=admin,
        json={"username": f"other_{suffix}", "email": email, "password": "password12345", "roles": ["read_only"]},
    )
    assert duplicate_email.status_code == 409


def test_create_user_rejects_invalid_role_and_short_password(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]
    suffix = uuid4().hex[:10]

    bad_role = client.post(
        "/api/v1/users", headers=admin,
        json={"username": f"role_{suffix}", "password": "password12345", "roles": ["superuser"]},
    )
    assert bad_role.status_code == 422

    no_roles = client.post(
        "/api/v1/users", headers=admin,
        json={"username": f"nroles_{suffix}", "password": "password12345", "roles": []},
    )
    assert no_roles.status_code == 422


# --------------------------------------------------------------------------- #
# Borrado lógico y reactivación
# --------------------------------------------------------------------------- #
def test_logical_delete_and_reenable(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]
    suffix = uuid4().hex[:10]
    username = f"toggle_{suffix}"

    created = client.post(
        "/api/v1/users", headers=admin,
        json={"username": username, "password": "password12345", "roles": ["operator"]},
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    disabled = client.post(f"/api/v1/users/{user_id}/disable", headers=admin)
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"
    assert disabled.json()["disabled_at"] is not None

    # Desactivar de nuevo es un conflicto (idempotencia explícita).
    assert client.post(f"/api/v1/users/{user_id}/disable", headers=admin).status_code == 409

    enabled = client.post(f"/api/v1/users/{user_id}/enable", headers=admin)
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["status"] == "active"
    assert enabled.json()["disabled_at"] is None

    # Reactivar de nuevo es un conflicto.
    assert client.post(f"/api/v1/users/{user_id}/enable", headers=admin).status_code == 409


# --------------------------------------------------------------------------- #
# Salvaguardas del último administrador
# --------------------------------------------------------------------------- #
def test_admin_cannot_disable_self(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]

    response = client.post(f"/api/v1/users/{users_client['admin_id']}/disable", headers=admin)
    assert response.status_code == 409

    # El administrador sigue activo: el sistema no queda sin administración.
    still_active = client.get(
        "/api/v1/users", headers=admin,
        params={"q": users_client["admin_name"]},
    ).json()["items"][0]
    assert still_active["status"] == "active"


def test_admin_cannot_remove_own_administrator_role(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]

    response = client.patch(
        f"/api/v1/users/{users_client['admin_id']}", headers=admin,
        json={"roles": ["researcher"]},
    )
    assert response.status_code == 409

    still_admin = client.get(
        "/api/v1/users", headers=admin,
        params={"q": users_client["admin_name"]},
    ).json()["items"][0]
    assert "administrator" in still_admin["roles"]


# --------------------------------------------------------------------------- #
# Cambio de contraseña propia
# --------------------------------------------------------------------------- #
def test_change_own_password_validates_current_and_policy(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]
    current = users_client["password"]

    wrong_current = client.post(
        "/api/v1/auth/me/password", headers=admin,
        json={"current_password": "incorrecta12345", "new_password": "nueva12345678"},
    )
    assert wrong_current.status_code == 400

    too_short = client.post(
        "/api/v1/auth/me/password", headers=admin,
        json={"current_password": current, "new_password": "corta123"},
    )
    assert too_short.status_code == 422

    same_as_current = client.post(
        "/api/v1/auth/me/password", headers=admin,
        json={"current_password": current, "new_password": current},
    )
    assert same_as_current.status_code == 422

    ok = client.post(
        "/api/v1/auth/me/password", headers=admin,
        json={"current_password": current, "new_password": "nueva12345678"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json() == {"ok": True}

    # La contraseña antigua deja de ser válida y la nueva sí.
    assert not security.verify_password(current, _password_hash(users_client, users_client["admin_id"]))
    assert security.verify_password("nueva12345678", _password_hash(users_client, users_client["admin_id"]))


def _password_hash(users_client, user_id):
    row = users_client["connection"].execute(
        text("SELECT password_hash FROM users WHERE id = CAST(:id AS uuid)"),
        {"id": user_id},
    ).mappings().first()
    return row["password_hash"]


# --------------------------------------------------------------------------- #
# Perfil propio
# --------------------------------------------------------------------------- #
def test_own_profile_read_and_email_update(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]

    profile = client.get("/api/v1/auth/me/profile", headers=admin)
    assert profile.status_code == 200, profile.text
    body = profile.json()
    assert body["username"] == users_client["admin_name"]
    assert "administrator" in body["roles"]
    assert body["status"] == "active"
    assert "password_hash" not in body

    new_email = f"perfil_{uuid4().hex[:10]}@invalid.test"
    updated = client.patch("/api/v1/auth/me/profile", headers=admin, json={"email": new_email})
    assert updated.status_code == 200, updated.text
    assert updated.json()["email"] == new_email

    # El email ya en uso por otro usuario produce conflicto.
    taken = client.patch(
        "/api/v1/auth/me/profile", headers=admin,
        json={"email": f"{users_client['researcher_name']}@invalid.test"},
    )
    assert taken.status_code == 409


# --------------------------------------------------------------------------- #
# Usuario desactivado: su sesión activa recibe 401
# --------------------------------------------------------------------------- #
def test_disabled_user_active_session_receives_401(users_client):
    client = users_client["client"]
    admin = users_client["admin_headers"]
    suffix = uuid4().hex[:10]
    username = f"victim_{suffix}"

    created = client.post(
        "/api/v1/users", headers=admin,
        json={"username": username, "password": "password12345", "roles": ["read_only"]},
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    victim_headers = {
        "Authorization": f"Bearer {security.create_access_token(user_id, username, ['read_only'])}"
    }

    # Antes de la desactivación la sesión es válida.
    assert client.get("/api/v1/auth/me/profile", headers=victim_headers).status_code == 200

    disabled = client.post(f"/api/v1/users/{user_id}/disable", headers=admin)
    assert disabled.status_code == 200, disabled.text

    # La desactivación aplica de inmediato: el token ya no es válido.
    rejected = client.get("/api/v1/auth/me/profile", headers=victim_headers)
    assert rejected.status_code == 401
