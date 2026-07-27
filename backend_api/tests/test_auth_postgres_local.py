import os
from contextlib import nullcontext
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine, text

import app.security as security
from app.config import Settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url


pytestmark = pytest.mark.requires_local_postgres


@pytest.fixture(autouse=True)
def require_local_gate():
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL local explícito")


class SharedConnectionEngine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return nullcontext(self.connection)


def test_disabled_synthetic_user_rejects_existing_token_and_rolls_back(monkeypatch):
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    user_id = uuid4()
    username = f"capstone_test_{uuid4().hex[:12]}"
    with engine.connect() as connection:
        assert_capstone_database(
            settings, connection.execute(text("SELECT current_database()")).scalar_one()
        )
        tx = connection.begin_nested() if connection.in_transaction() else connection.begin()
        try:
            role_id = connection.execute(
                text("SELECT id FROM roles WHERE name='read_only'")
            ).scalar_one()
            connection.execute(text("""
                INSERT INTO users(id,username,email,password_hash,status)
                VALUES(:id,:username,:email,:password_hash,'active')
            """), {
                "id": user_id, "username": username,
                "email": f"{username}@invalid.test",
                "password_hash": security.hash_password(uuid4().hex),
            })
            connection.execute(text("""
                INSERT INTO user_roles(user_id,role_id) VALUES(:user_id,:role_id)
            """), {"user_id": user_id, "role_id": role_id})
            monkeypatch.setattr(security, "get_primary_engine", lambda: SharedConnectionEngine(connection))
            token = security.create_access_token(user_id, username, ["read_only"])
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            assert security.current_principal(credentials).username == username
            connection.execute(
                text("UPDATE users SET status='disabled',disabled_at=now() WHERE id=:id"),
                {"id": user_id},
            )
            with pytest.raises(HTTPException) as rejected:
                security.current_principal(credentials)
            assert rejected.value.status_code == 401
        finally:
            tx.rollback()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM users WHERE id=:id"), {"id": user_id}
        ).scalar_one() == 0
    engine.dispose()
