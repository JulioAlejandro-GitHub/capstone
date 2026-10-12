"""Docker-only migration, using a temporary login to the existing schema-owner role.

The login is dropped in finally; it owns no objects. No credentials are printed.
"""
import os
import argparse
from pathlib import Path
import secrets
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def admin(sql: str) -> str:
    result = subprocess.run(['docker','compose','exec','-T','db','sh','-c',
        'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'],
        input=sql, text=True, capture_output=True, cwd=ROOT)
    if result.returncode:
        raise RuntimeError('Local migration role operation failed; no credentials logged.')
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description='Apply the authorized EXEC.1 function update to the named local Compose database')
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    database = admin('SELECT current_database();')
    if database != args.database:
        raise RuntimeError('EXEC1_DATABASE_TARGET_MISMATCH')
    role = 'exec1_migration_' + secrets.token_hex(6)
    password = secrets.token_hex(32)
    created = False
    try:
        admin(f"BEGIN; CREATE ROLE {role} LOGIN PASSWORD '{password}'; GRANT capstone_v2_migrator TO {role}; COMMIT;")
        created = True
        with tempfile.TemporaryDirectory(prefix='capstone-exec1-migration-') as directory:
            envfile = Path(directory) / 'migration.env'
            envfile.write_text(f'PGV2_DATABASE_URL=postgresql+psycopg://{role}:{password}@db:5432/{database}\nPGV2_SET_ROLE=capstone_v2_migrator\n')
            os.chmod(envfile, 0o600)
            result = subprocess.run(['docker','compose','run','--rm','--no-deps','-T',
                '--env-from-file',str(envfile),
                '-v',f'{ROOT}/alembic_v2:/app/alembic_v2:ro',
                '-v',f'{ROOT}/alembic_v2.ini:/app/alembic_v2.ini:ro',
                '-e','PYTHONDONTWRITEBYTECODE=1','backend','python','/scripts/db/apply_exec1.py'],cwd=ROOT)
            if result.returncode:
                raise RuntimeError('EXEC.1 migration did not complete.')
    finally:
        if created:
            admin(f'DROP ROLE {role};')


if __name__ == '__main__':
    main()
