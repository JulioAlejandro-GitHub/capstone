import os
from uuid import UUID

from sqlalchemy import text

from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.splitting import (
    build_seeded_greedy_baseline,
    evaluate_candidate,
    load_patient_profiles,
    randomized_patient_sequence,
)
from malaria_split.splitting.patient_profiles import PatientClassProfile


V1 = UUID("d8c0cab5-09dd-597f-9de7-7ca01aee2ec2")


def test_real_patient_profiles_and_read_only_algorithm_contract():
    engine = create_postgresql_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as connection:
            profiles = load_patient_profiles(connection, V1)
            before = connection.execute(text(
                "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
            ), {"id": V1}).scalar_one()
            baseline = build_seeded_greedy_baseline(profiles)
            evaluation = evaluate_candidate(profiles, baseline)
            after = connection.execute(text(
                "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
            ), {"id": V1}).scalar_one()
    finally:
        engine.dispose()
    assert len(profiles) == 201
    assert sum(item.total_records for item in profiles) == 27558
    assert sum(item.parasitized_records for item in profiles) == 13779
    assert sum(item.uninfected_records for item in profiles) == 13779
    assert sum(item.patient_class_profile == PatientClassProfile.BOTH_CLASSES for item in profiles) == 151
    assert sum(item.patient_class_profile == PatientClassProfile.UNINFECTED_ONLY for item in profiles) == 50
    assert min(item.total_records for item in profiles) == 65
    assert max(item.total_records for item in profiles) == 702
    assert randomized_patient_sequence(profiles, 42) == randomized_patient_sequence(profiles, 42)
    assert evaluation.valid
    assert before == after == 0
