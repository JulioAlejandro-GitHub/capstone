"""Synthetic persistent-target fixture proving approved lifecycle handling; always ROLLBACK."""

from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from dbv23_destination import certify, connect, guard
from dbv23_source import save
from psycopg import sql


def insert(c, table, values):
    c.execute(
        sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table),
            sql.SQL(",").join(map(sql.Identifier, values)),
            sql.SQL(",").join(sql.Placeholder() for _ in values),
        ),
        list(values.values()),
    )


def main():
    t = guard()
    results = []
    with connect(t) as c:
        c.execute("BEGIN")
        try:
            dataset, version, identity, record = uuid4(), uuid4(), uuid4(), uuid4()
            frozen = datetime(2026, 1, 1, tzinfo=timezone.utc)
            insert(
                c,
                "datasets",
                {
                    "id": dataset,
                    "name": "DBV23 synthetic rollback-only",
                    "source": "synthetic",
                },
            )
            v = {
                "id": version,
                "name": str(version),
                "semantic_version": "synthetic",
                "grouping_strategy": "synthetic",
                "grouping_field": "patient",
                "stratification_strategy": "synthetic",
                "split_algorithm": "synthetic",
                "split_algorithm_version": "1",
                "random_seed": 7,
                "target_train_ratio": 0.7,
                "target_val_ratio": 0.15,
                "target_test_ratio": 0.15,
                "positive_class": "parasitized",
                "status": "FROZEN",
                "frozen_at": frozen,
            }
            # Failed direct FROZEN load stays inside a savepoint; no scientific fixture persists.
            try:
                with c.transaction():
                    insert(c, "dataset_versions", v)
                    insert(
                        c,
                        "dataset_version_sources",
                        {
                            "dataset_version_id": version,
                            "dataset_id": dataset,
                            "role": "PRIMARY",
                        },
                    )
            except psycopg.Error as e:
                assert e.sqlstate == "23514" and "FROZEN" in str(e)
                results.append(
                    {
                        "case": "direct_FROZEN_child_insert_rejected",
                        "passed": True,
                        "sqlstate": e.sqlstate,
                    }
                )
            else:
                raise AssertionError("Expected FROZEN protection")
            insert(c, "dataset_versions", dict(v, status="VALIDATED"))
            insert(
                c,
                "dataset_version_sources",
                {
                    "dataset_version_id": version,
                    "dataset_id": dataset,
                    "role": "PRIMARY",
                },
            )
            insert(
                c,
                "clinical_identities",
                {
                    "id": identity,
                    "dataset_id": dataset,
                    "identity_type": "PATIENT",
                    "source_identifier": "synthetic",
                    "status": "VERIFIED",
                },
            )
            insert(
                c,
                "dataset_source_records",
                {
                    "id": record,
                    "dataset_id": dataset,
                    "source_record_key": "synthetic",
                    "clinical_identity_id": identity,
                    "class_index": 1,
                    "class_name": "parasitized",
                    "identity_status": "VERIFIED",
                },
            )
            insert(
                c,
                "dataset_split_assignments",
                {
                    "dataset_version_id": version,
                    "source_record_id": record,
                    "clinical_identity_id": identity,
                    "split_name": "train",
                    "class_index": 1,
                    "class_name": "parasitized",
                },
            )
            c.execute(
                "UPDATE dataset_versions SET status='FROZEN' WHERE id=%s", (version,)
            )
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            actual = c.execute(
                "SELECT status,frozen_at FROM dataset_versions WHERE id=%s", (version,)
            ).fetchone()
            assert actual == {"status": "FROZEN", "frozen_at": frozen}
            results.append(
                {
                    "case": "approved_VALIDATED_to_FROZEN_preserves_timestamp_and_children",
                    "passed": True,
                }
            )
        finally:
            c.execute("ROLLBACK")
    save(
        "lifecycle_fixture_results.json",
        {"results": results, "all_rolled_back": True, "source_connections": 0},
    )
    certify("after_fixture_rollback")
    print(
        "PASS approved lifecycle handling with active triggers; zero fixtures after rollback."
    )


if __name__ == "__main__":
    main()
