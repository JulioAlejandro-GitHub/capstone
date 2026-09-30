"""Real DBV2.2 tests, runtime login, synthetic rows rolled back. No application imports."""

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from certify_dbv22 import E, connect, guard, save

os.environ["PGV2_EVIDENCE_DIR"] = str(E)
import psycopg
import test_v2_e4_server as retained

RESULTS = []
RECALL = 0.98
original_insert = retained.insert


def insert(c, table, values):
    # Adapt historical synthetic TRAIN fixtures to the newly explicit target contract.
    v = copy.deepcopy(values)
    if (
        table == "runs"
        and v.get("run_type") == "training"
        and "execution_parameters" in v
    ):
        v["execution_parameters"]["model_configuration_e2"]["configuration"][
            "resolved"
        ]["execution"]["target_recall"] = RECALL
    if table == "run_configurations":
        canonical = json.loads(v["canonical_configuration"])
        canonical["execution"]["target_recall"] = RECALL
        raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        v.update(
            clinical_target_recall=RECALL,
            canonical_configuration=raw,
            configuration_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
    original_insert(c, table, v)


def passed(name, **evidence):
    RESULTS.append(dict(name=name, passed=True, **evidence))
    save("dbv22_server_tests.json", RESULTS)


def negative(c, name, action, state, marker):
    # schema_migrations is absent by DBV2.1, not a read-only second ledger.
    if name == "no_ledger_write":
        state, marker = "42P01", "does not exist"
    try:
        with c.transaction():
            action()
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except psycopg.Error as e:
        ok = e.sqlstate == state and marker in str(e)
        RESULTS.append(
            {
                "name": name,
                "passed": ok,
                "expected_sqlstate": state,
                "actual_sqlstate": e.sqlstate,
                "expected_marker": marker,
                "actual_message": e.diag.message_primary,
            }
        )
        save("dbv22_server_tests.json", RESULTS)
        assert ok, f"{name}: {e}"
    else:
        RESULTS.append(
            {"name": name, "passed": False, "error": "invalid operation accepted"}
        )
        save("dbv22_server_tests.json", RESULTS)
        raise AssertionError(name)


retained.insert = insert
retained.guard = guard
retained.connect = connect
retained.save = lambda name, value: save("retained_" + name, value)
retained.negative = negative
retained.RESULTS = RESULTS


def recall_suite(t):
    global RECALL
    for value in (0.01, 0.95, 0.98, 0.99, 1.0, 0, -0.01, 1.01, None):
        RECALL = value
        with connect(t, role="capstone_v2_runtime") as c:
            c.execute("BEGIN")
            try:
                if value is None or value <= 0 or value > 1:
                    negative(
                        c,
                        "recall_reject_" + str(value),
                        lambda: retained.fixture(c),
                        "23502" if value is None else "23514",
                        "clinical_target_recall"
                        if value is None
                        else "v2_run_configurations_check_d6094850fee4",
                    )
                else:
                    ids = retained.fixture(c)
                    c.execute("SET CONSTRAINTS ALL IMMEDIATE")
                    assert (
                        float(
                            c.execute(
                                "SELECT clinical_target_recall FROM run_configurations WHERE run_id=%s",
                                (ids["train"],),
                            ).fetchone()["clinical_target_recall"]
                        )
                        == value
                    )
                    passed("recall_accept_" + str(value))
            finally:
                c.execute("ROLLBACK")
    RECALL = 0.98


def canonical(v):
    raw = json.dumps(v, sort_keys=True, separators=(",", ":"))
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def xai_suite(t):
    with connect(t, role="capstone_v2_runtime") as c:
        c.execute("BEGIN")
        try:
            ids = retained.fixture(c)
            config = {
                "method": "gradcam",
                "implementation": "synthetic.fixture",
                "implementation_version": "1",
                "parameters": {},
            }
            raw, h = canonical(config)
            config.update(id=uuid4(), canonical_configuration=raw, configuration_hash=h)
            insert(c, "xai_method_configurations", config)
            negative(
                c,
                "xai_configuration_unique",
                lambda: insert(
                    c, "xai_method_configurations", dict(config, id=uuid4())
                ),
                "23505",
                "uq_xai_method_configuration_hash",
            )
            input_id = uuid4()
            insert(
                c,
                "artifacts",
                {
                    "id": input_id,
                    "run_id": ids["train"],
                    "artifact_type": "image",
                    "path": "synthetic://input",
                    "checksum": "b" * 64,
                },
            )
            evidence = {
                "id": uuid4(),
                "run_id": ids["train"],
                "input_artifact_id": input_id,
                "checkpoint_artifact_id": ids["artifact"],
                "method_configuration_id": config["id"],
                "source_commit": "synthetic",
                "input_contract": {},
                "input_contract_hash": "c" * 64,
                "input_storage_uri": "synthetic://input",
                "input_sha256": "b" * 64,
                "checkpoint_sha256": "a" * 64,
                "target_class": 1,
                "explained_output": "raw_output",
                "processing_stage": "model_input",
                "environment_snapshot": {},
                "generated_at": datetime.now(timezone.utc),
            }
            insert(c, "xai_evidence", evidence)
            other = dict(evidence, id=uuid4())
            insert(c, "xai_evidence", other)
            artifact = {
                "evidence_id": evidence["id"],
                "role": "RAW_ATTRIBUTION",
                "storage_uri": "synthetic://numeric.npy",
                "sha256": "d" * 64,
                "byte_size": 32,
                "mime_type": "application/x-npy",
                "numeric_dtype": "float32",
                "availability": "available",
            }
            insert(c, "xai_artifacts", artifact)
            assert c.execute(
                "SELECT storage_uri,sha256 FROM xai_artifacts WHERE evidence_id=%s",
                (evidence["id"],),
            ).fetchone() == {
                "storage_uri": artifact["storage_uri"],
                "sha256": artifact["sha256"],
            }
            passed("xai_external_numeric_reference_and_hash")
            insert(
                c,
                "xai_artifacts",
                dict(
                    artifact,
                    role="OVERLAY",
                    storage_uri="synthetic://overlay.png",
                    mime_type="image/png",
                    numeric_dtype=None,
                ),
            )
            region = {
                "xai_evidence_id": evidence["id"],
                "region_type": "superpixel",
                "region_index": 0,
                "attribution_value": 0.4,
            }
            insert(c, "xai_region_attributions", region)
            negative(
                c,
                "xai_region_invalid_FK",
                lambda: insert(
                    c, "xai_region_attributions", dict(region, xai_evidence_id=uuid4())
                ),
                "23503",
                "fk_xai_region_evidence",
            )
            negative(
                c,
                "xai_region_duplicate_identity",
                lambda: insert(c, "xai_region_attributions", region),
                "23505",
                "xai_region_attributions_pkey",
            )
            proto = {
                "metric_name": "agreement_fixture",
                "metric_family": "agreement",
                "protocol_name": "synthetic",
                "protocol_version": "1",
                "parameters": {},
                "normalization_strategy": "none",
                "perturbation_strategy": None,
                "reference_definition": None,
            }
            raw, h = canonical(proto)
            proto.update(id=uuid4(), canonical_protocol=raw, protocol_hash=h)
            insert(c, "xai_evaluation_protocols", proto)
            members = [(evidence["id"], "reference"), (other["id"], "candidate")]
            membership = "\n".join(
                str(i) + ":" + role
                for i, role in sorted(members, key=lambda x: str(x[0]))
            )
            q = {
                "id": uuid4(),
                "protocol_id": proto["id"],
                "metric_name": proto["metric_name"],
                "membership_hash": hashlib.sha256(membership.encode()).hexdigest(),
                "metric_value": None,
                "undefined_reason": "not_computed_fixture",
                "sample_count": 1,
                "evaluated_at": datetime.now(timezone.utc),
            }

            def add_measurement(row, include=True):
                insert(c, "xai_quantitative_evaluations", row)
                if include:
                    for i, role in members:
                        insert(
                            c,
                            "xai_evaluation_members",
                            {
                                "evaluation_id": row["id"],
                                "xai_evidence_id": i,
                                "member_role": role,
                            },
                        )

            add_measurement(q)
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            c.execute("SET CONSTRAINTS ALL DEFERRED")
            passed("xai_valid_NM_NULL_metric_with_reason_deferred_validation")
            second = dict(q, id=uuid4(), metric_value=0.7, undefined_reason=None)
            add_measurement(second)
            c.execute("SET CONSTRAINTS ALL IMMEDIATE")
            c.execute("SET CONSTRAINTS ALL DEFERRED")
            assert (
                c.execute(
                    "SELECT count(*) AS n FROM xai_evaluation_members WHERE xai_evidence_id=%s",
                    (evidence["id"],),
                ).fetchone()["n"]
                == 2
            )
            passed("xai_evidence_participates_in_multiple_evaluations")
            negative(
                c,
                "xai_member_duplicate",
                lambda: insert(
                    c,
                    "xai_evaluation_members",
                    {
                        "evaluation_id": q["id"],
                        "xai_evidence_id": evidence["id"],
                        "member_role": "reference",
                    },
                ),
                "23505",
                "xai_evaluation_members_pkey",
            )
            negative(
                c,
                "xai_invalid_protocol_FK",
                lambda: add_measurement(dict(q, id=uuid4(), protocol_id=uuid4())),
                "23503",
                "fk_xai_metric_protocol",
            )
            negative(
                c,
                "xai_undefined_without_reason",
                lambda: add_measurement(dict(q, id=uuid4(), undefined_reason=None)),
                "23514",
                "ck_xai_metric_defined",
            )
            negative(
                c,
                "xai_no_members",
                lambda: add_measurement(
                    dict(
                        q, id=uuid4(), membership_hash=hashlib.sha256(b"").hexdigest()
                    ),
                    False,
                ),
                "P0001",
                "XAI_EVALUATION_MEMBERS_REQUIRED",
            )
            negative(
                c,
                "xai_wrong_membership",
                lambda: add_measurement(dict(q, id=uuid4(), membership_hash="f" * 64)),
                "P0001",
                "XAI_MEMBERSHIP_HASH_MISMATCH",
            )
            negative(
                c,
                "xai_evidence_immutable",
                lambda: c.execute(
                    "UPDATE xai_evidence SET seed=3 WHERE id=%s", (evidence["id"],)
                ),
                "P0001",
                "V2_SCIENTIFIC_EVIDENCE_IMMUTABLE",
            )
        finally:
            c.execute("ROLLBACK")


def main():
    t = guard()
    recall_suite(t)
    retained.main()
    retained.legacy_pair_suite(t)
    xai_suite(t)
    print(f"PASS {len(RESULTS)} PostgreSQL structural checks")


if __name__ == "__main__":
    main()
