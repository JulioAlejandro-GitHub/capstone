"""Test process routing only: existing suites and their child Python processes use the isolated DB.

Not imported by product commands. Enable explicitly through PYTHONPATH for regression tests.
No schema/version checks, catalog filtering or behavioral mocks.
"""
import os
from urllib.parse import urlparse

url = os.environ.get('BIOMEDCLIP_TEST_DATABASE_URL')
if url:
    parsed = urlparse(url.replace('postgresql+psycopg:', 'postgresql:'))
    if parsed.hostname != '127.0.0.1' or parsed.port != 55439 or not parsed.path.startswith('/biomedclip_01c1'):
        raise RuntimeError('Disposable BiomedCLIP test database required')
    from src.malaria_dl.persistence import database
    database.get_database_url = lambda: url
