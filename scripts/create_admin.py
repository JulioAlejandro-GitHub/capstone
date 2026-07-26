#!/usr/bin/env python3
import argparse
import getpass
import os
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend_api"))
from app.db import get_primary_engine
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--email")
    args = parser.parse_args()
    password = os.getenv("INITIAL_ADMIN_PASSWORD") or getpass.getpass("Password: ")
    password_hash = hash_password(password)
    with get_primary_engine().begin() as connection:
        exists = connection.execute(text("SELECT 1 FROM users WHERE lower(username)=lower(:u)"),
                                    {"u": args.username}).first()
        if exists:
            raise SystemExit("El usuario ya existe; no se sobrescribió.")
        connection.execute(text("""INSERT INTO users(id,username,email,password_hash)
          VALUES(:id,:u,:e,:p)"""), {"id": uuid4(), "u": args.username, "e": args.email, "p": password_hash})
        connection.execute(text("""INSERT INTO user_roles(user_id,role_id)
          SELECT u.id,r.id FROM users u CROSS JOIN roles r
          WHERE u.username=:u AND r.name='administrator'"""), {"u": args.username})
    print(f"Administrador creado: {args.username}")


if __name__ == "__main__":
    main()
