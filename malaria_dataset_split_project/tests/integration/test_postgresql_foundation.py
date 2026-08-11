"""SPLIT 2A checks against malaria_experiments using a rolled-back transaction."""

from __future__ import annotations

import os
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


DATABASE_URL = os.environ.get("DATABASE_URL")


def _sync_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class TestPostgresqlFoundation:
    @classmethod
    def setup_class(cls):
        assert DATABASE_URL, "DATABASE_URL must point to malaria_experiments"
        cls.engine = create_engine(_sync_url(DATABASE_URL))

    @classmethod
    def teardown_class(cls):
        cls.engine.dispose()

    def test_schema_and_nullable_legacy_extensions(self):
        expected = {
            "dataset_versions", "dataset_version_sources", "dataset_source_records",
            "clinical_identities", "identity_evidence", "dataset_split_assignments",
            "dataset_split_statistics", "dataset_split_validation_checks",
            "dataset_materializations", "dataset_materialization_activations",
        }
        inspector = inspect(self.engine)
        assert expected <= set(inspector.get_table_names(schema="public"))
        run_columns = {column["name"]: column for column in inspector.get_columns("runs")}
        assert run_columns["dataset_version_id"]["nullable"] is True

    def test_new_tables_are_empty(self):
        tables = (
            "dataset_versions", "dataset_version_sources", "dataset_source_records",
            "clinical_identities", "identity_evidence", "dataset_split_assignments",
            "dataset_split_statistics", "dataset_split_validation_checks",
            "dataset_materializations", "dataset_materialization_activations",
        )
        with self.engine.connect() as connection:
            for table in tables:
                assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0

    def test_ratio_and_version_uniqueness_constraints_with_rollback(self):
        with self.engine.connect() as connection, connection.begin():
            base = {
                "id": uuid4(), "name": "split-2a-transaction-fixture",
                "semantic_version": "0.0.0", "grouping_strategy": "fixture",
                "grouping_field": "patient_id", "stratification_strategy": "fixture",
                "split_algorithm": "fixture", "split_algorithm_version": "0",
                "random_seed": 1, "train": 0.8, "val": 0.1, "test": 0.1,
                "positive_class": "positive",
            }
            sql = text("""
                INSERT INTO dataset_versions (
                  id,name,semantic_version,grouping_strategy,grouping_field,
                  stratification_strategy,split_algorithm,split_algorithm_version,
                  random_seed,target_train_ratio,target_val_ratio,target_test_ratio,positive_class
                ) VALUES (
                  :id,:name,:semantic_version,:grouping_strategy,:grouping_field,
                  :stratification_strategy,:split_algorithm,:split_algorithm_version,
                  :random_seed,:train,:val,:test,:positive_class
                )
            """)
            connection.execute(sql, base)
            nested = connection.begin_nested()
            try:
                connection.execute(sql, {**base, "id": uuid4()})
                raise AssertionError("version uniqueness was not enforced")
            except IntegrityError:
                nested.rollback()
            nested = connection.begin_nested()
            try:
                connection.execute(sql, {
                    **base, "id": uuid4(), "name": "invalid-ratios", "train": 0.7,
                })
                raise AssertionError("ratio sum was not enforced")
            except IntegrityError:
                nested.rollback()
            connection.rollback()

    def test_legacy_counts_are_unchanged(self):
        with self.engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM datasets")).scalar_one() == 2
            assert connection.execute(text("SELECT count(*) FROM dataset_split_images")).scalar_one() == 27558
            assert connection.execute(text("SELECT count(*) FROM runs WHERE run_type='training'")).scalar_one() == 12
            assert connection.execute(text("SELECT count(*) FROM runs WHERE run_type='evaluation'")).scalar_one() == 12

    def test_source_record_and_assignment_uniqueness_with_rollback(self):
        with self.engine.connect() as connection, connection.begin():
            dataset_id = connection.execute(text("SELECT id FROM datasets ORDER BY id LIMIT 1")).scalar_one()
            identity_id = uuid4()
            connection.execute(text("""
                INSERT INTO clinical_identities (
                  id,dataset_id,identity_type,source_identifier,status
                ) VALUES (:id,:dataset_id,'PATIENT',:source_identifier,'VERIFIED')
            """), {
                "id": identity_id, "dataset_id": dataset_id,
                "source_identifier": f"split-2a-fixture-{identity_id}",
            })
            record_id = uuid4()
            source_key = f"split-2a-fixture-{record_id}"
            source_sql = text("""
                INSERT INTO dataset_source_records (
                  id,dataset_id,clinical_identity_id,source_record_key,class_index,
                  class_name,identity_status
                ) VALUES (
                  :id,:dataset_id,:identity_id,:source_key,0,'uninfected','VERIFIED'
                )
            """)
            source_values = {
                "id": record_id, "dataset_id": dataset_id,
                "identity_id": identity_id, "source_key": source_key,
            }
            connection.execute(source_sql, source_values)
            nested = connection.begin_nested()
            try:
                connection.execute(source_sql, {**source_values, "id": uuid4()})
                raise AssertionError("source record uniqueness was not enforced")
            except IntegrityError:
                nested.rollback()

            version_id = uuid4()
            connection.execute(text("""
                INSERT INTO dataset_versions (
                  id,name,semantic_version,grouping_strategy,grouping_field,
                  stratification_strategy,split_algorithm,split_algorithm_version,
                  random_seed,target_train_ratio,target_val_ratio,target_test_ratio,positive_class
                ) VALUES (
                  :id,:name,'0.0.0','fixture','patient_id','fixture','fixture','0',
                  1,0.8,0.1,0.1,'positive'
                )
            """), {"id": version_id, "name": f"split-2a-fixture-{version_id}"})
            assignment_sql = text("""
                INSERT INTO dataset_split_assignments (
                  id,dataset_version_id,source_record_id,clinical_identity_id,
                  split_name,class_index,class_name
                ) VALUES (
                  :id,:version_id,:record_id,:identity_id,'train',0,'uninfected'
                )
            """)
            assignment_values = {
                "id": uuid4(), "version_id": version_id,
                "record_id": record_id, "identity_id": identity_id,
            }
            connection.execute(assignment_sql, assignment_values)
            nested = connection.begin_nested()
            try:
                connection.execute(assignment_sql, {**assignment_values, "id": uuid4()})
                raise AssertionError("assignment uniqueness was not enforced")
            except IntegrityError:
                nested.rollback()
            connection.rollback()
