"""Provision the EXEC.1 fixture once with current DDL only; never copy scientific data."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ['docker','compose','-f','docker-compose.yml','-f','docker-compose.override.yml',
           '-f','docker-compose.exec1-test.yml']


def main() -> None:
    subprocess.run([*COMPOSE,'up','-d','--wait','exec1-postgres'],cwd=ROOT,check=True)
    # No production data, grants, owners, dataset files or historical migrations.
    schema = subprocess.run(['docker','compose','exec','-T','db','sh','-c',
        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only --no-owner --no-privileges'],
        cwd=ROOT,check=True,capture_output=True).stdout
    subprocess.run([*COMPOSE,'exec','-T','exec1-postgres','psql','-q','-v','ON_ERROR_STOP=1',
                    '-U','exec1_fixture','-d','exec1_fixture'],cwd=ROOT,input=schema,check=True)
    print('EXEC.1 isolated fixture initialized; operational data unchanged.')


if __name__ == '__main__':
    main()
