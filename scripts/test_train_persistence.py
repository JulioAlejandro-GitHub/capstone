"""Run synthetic schema fixtures in Compose, without granting runtime DDL rights."""
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    'test_train_run_persistence.py', 'test_docker_train_integration.py',
    'test_training_completion_postgres.py', 'test_result_service.py',
    'test_run_event_emitter.py', 'test_local_event_runtime.py',
    'test_local_docker_event_parity.py', 'test_event_journal.py',
]


def main() -> int:
    config = subprocess.run(['docker', 'compose', 'config', '--format', 'json'],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    db = json.loads(config.stdout)['services']['db']['environment']
    # The admin credential exists only in the pipe to this test process; never
    # change the backend environment, permissions, database or existing rows.
    url = ('postgresql+psycopg://' + quote(db['POSTGRES_USER'], safe='') + ':'
           + quote(db['POSTGRES_PASSWORD'], safe='') + '@db:5432/' + db['POSTGRES_DB'])
    env = dict(DATABASE_URL=url, PYTHONDONTWRITEBYTECODE='1', RUN_STAGE4_POSTGRES_TESTS='1',
               RUN_E10_POSTGRES_TESTS='1', RUN_E10_TRAIN_POSTGRES_TESTS='1')
    code = ('import os, sys\nos.environ.update(' + repr(env) + ')\n'
            'sys.dont_write_bytecode = True\nimport pytest\n'
            'raise SystemExit(pytest.main(' + repr(['-q', '-p', 'no:cacheprovider'] +
                                                 ['tests/' + name for name in TESTS]) + '))\n')
    return subprocess.run(['docker', 'compose', 'exec', '-T', '-w',
                           '/app/malaria_dl_local_project', 'backend', 'python', '-'],
                          cwd=ROOT, input=code, text=True).returncode


if __name__ == '__main__':
    raise SystemExit(main())
