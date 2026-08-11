import os

from malaria_split.persistence.bootstrap import audit_scientific_bootstrap
from malaria_split.persistence.database import create_postgresql_engine


def test_real_scientific_bootstrap_contract():
    engine = create_postgresql_engine(os.environ["DATABASE_URL"])
    try:
        audit = audit_scientific_bootstrap(engine)
    finally:
        engine.dispose()
    assert audit["status"] == "PASS"
    assert audit["dataset_version_status"] == "DRAFT"
    assert audit["v1_assignment_count"] == 0
    assert audit["v1_materialization_count"] == 0
