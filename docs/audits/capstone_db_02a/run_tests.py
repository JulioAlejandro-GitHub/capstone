"""Run selected tests in the existing container against the isolated database."""
import os
import sys
from sqlalchemy.engine import make_url

url = make_url(os.environ['DATABASE_URL']).set(database='capstone_db02a_test_20261012')
os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
os.environ['TEST_EXECUTION'] = 'true'
os.environ['TEST_ISOLATION_MODE'] = 'transaction'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path[:0] = ['/tmp/capstone-db02a/backend_api', '/tmp/capstone-db02a/malaria_dl_local_project']
os.chdir('/tmp/capstone-db02a/backend_api')
import pytest
raise SystemExit(pytest.main(['-q', '--tb=short', '-p', 'no:cacheprovider', *sys.argv[1:]]))
