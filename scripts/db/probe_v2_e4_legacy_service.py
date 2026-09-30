"""Legacy writer regression with real historical migrations, isolated schemas."""
import contextlib
import io
import os
import sys
from probe_v2_e4_contract import E, ROOT, guard
from sqlalchemy import create_engine


def main():
    t=guard()
    sys.path.insert(0,str(ROOT/'malaria_dl_local_project/tests'))
    os.environ['RUN_E10_POSTGRES_TESTS']='1'
    import test_campaigns_postgres as legacy
    import test_result_repository_postgres as repository
    url=f"postgresql+psycopg://capstone_v2_migrator@127.0.0.1:{t['host_port']}/{t['database']}"
    # Both infrastructure creation and every ResultRepository connection are
    # explicitly injected. No operational engine factory is called.
    legacy.get_engine=lambda:create_engine(url)
    repository.get_engine=lambda:create_engine(url)
    import pytest
    log=io.StringIO()
    tests='malaria_dl_local_project/tests/'
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        code=pytest.main(['-q',tests+'test_result_repository_postgres.py',
            tests+'test_training_results_postgres.py::test_atomic_merge_duplicate_immutable_and_hash',
            tests+'test_training_results_postgres.py::test_projection_failure_rolls_back_insert'])
    (E/'legacy_service_tests.txt').write_text(log.getvalue())
    print(log.getvalue())
    assert code==0


if __name__=='__main__': main()
