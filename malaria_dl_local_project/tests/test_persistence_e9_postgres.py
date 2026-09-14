"""E9 confirmed commit, only in the disposable E4 schema."""
import os

import pytest
from sqlalchemy import text
from src.malaria_dl.science.repository import ScienceRepository
from test_campaigns_postgres import isolated, safe_test  # noqa: F401
from test_science_postgres import preparation

pytestmark = pytest.mark.skipif(os.getenv('RUN_STAGE9_POSTGRES_TESTS') != '1', reason='Compose E9 opt-in required')


@safe_test
def test_report_commit_visible_from_new_connection(isolated):  # noqa: F811
    s = isolated
    scope = s.make_visible()
    report = preparation(s.dataset)
    writer = ScienceRepository(scope)
    report_id = writer.persist_report(report)
    # Repository scope owns and commits a transaction; a fresh reader opens another.
    assert ScienceRepository(scope).read_report(report_id) == report
    with s.c.engine.connect() as c, c.begin():
        c.execute(text('SET TRANSACTION READ ONLY'))
        row = c.execute(text(f'SELECT after_state,success FROM {s.schema}.audit_events WHERE id=CAST(:id AS uuid)'), {'id': report_id}).mappings().one()
        assert row['after_state'] == report
        assert row['success'] is True
    print('E9 synthetic commit: exact report visible from a new connection; no restart/failure durability claim; disposable schema cleanup required')
