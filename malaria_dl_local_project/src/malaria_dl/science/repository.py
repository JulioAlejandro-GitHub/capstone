"""E7 uses existing append-only audit and E6 final locks. No migration needed."""

from uuid import UUID, uuid5

from ..assessment.repository import AssessmentRepository
from ..campaigns.contracts import canonical, digest
from ..campaigns.repository import execute, identifier
from .protocol import load_protocol, require

EVENT = "ml.scientific_comparison"
NAMESPACE = UUID("76e7e366-f6f7-4642-9d27-54b79d307061")


def validate_report(report):
    protocol = load_protocol()
    require(
        report["schema"] == "scientific_comparison_e7_v1"
        and report["protocol"] == protocol
        and report["protocol_hash"] == digest(protocol),
        "REPORT_PROTOCOL_CONFLICT",
    )
    require(report["split"] in ("val", "test"), "REPORT_SPLIT_INVALID")
    for item in report["items"]:
        require(
            digest(item["lineage"]["identity"]) == item["lineage"]["identity_hash"],
            "REPORT_IDENTITY_HASH_CONFLICT",
        )
        require(
            item["lineage"]["prediction_reference"]["attempt_id"]
            == item["evaluation_id"],
            "REPORT_PREDICTION_REFERENCE_CONFLICT",
        )
    from .comparison import select_candidate

    require(
        report["selection"]
        == select_candidate(report["items"], protocol, report["split"]),
        "REPORT_SELECTION_CONFLICT",
    )
    for item in report["items"]:
        value = item["lineage"]["identity"]
        require(
            value["dataset"] == report["dataset"] and value["split"] == report["split"],
            "REPORT_DATASET_SPLIT_CONFLICT",
        )
        proof = item["lineage"]["prediction_reference"]["proof"]
        require(
            all(
                item["metrics"][k] == proof["metrics"][k]
                for k in ("tp", "tn", "fp", "fn")
            ),
            "REPORT_METRICS_PROOF_CONFLICT",
        )
    canonical(report)


class ScienceRepository(AssessmentRepository):
    report_success = True
    report_error_code = staticmethod(lambda payload: None)
    report_event = EVENT
    report_resource_type = "scientific_report"
    report_source = "science.e7"
    report_validator = staticmethod(validate_report)

    def campaign_inventory(self, campaign_id):
        from ..campaigns.repository import CampaignRepository

        c = CampaignRepository(self.scope).get(identifier(campaign_id))
        require(c["state"] != "draft", "FROZEN_CAMPAIGN_REQUIRED")
        return {
            "id": str(c["id"]),
            "state": c["state"],
            "contract_hash": c["contract_hash"],
            "protocol": c["protocol"],
            "dataset": c["dataset_snapshot"],
            "configuration_hashes": sorted(
                x["configuration_hash"] for x in c["configurations"]
            ),
            "members": [
                {
                    "id": str(m["id"]),
                    "configuration_hash": m["configuration_hash"],
                    "seed": m["seed"],
                    "state": m["state"],
                    "exclusion_reason": m["exclusion_reason"],
                }
                for m in c["members"]
            ],
            "attempts": [
                {
                    "id": str(a["id"]),
                    "member_id": str(a["member_id"]),
                    "ordinal": a["ordinal"],
                    "state": a["state"],
                    "training_run_id": str(a["training_run_id"])
                    if a["training_run_id"]
                    else None,
                }
                for a in c["attempts"]
            ],
        }

    def associated_explanations(self, evaluation_id):
        with self.transaction(readonly=True) as c:
            return [
                str(v)
                for v in execute(
                    c,
                    """SELECT a.id FROM assessment_attempts a
                JOIN assessment_identities i ON i.id=a.identity_id
                WHERE a.state='verified' AND i.kind='explain'
                AND i.identity->'evaluation'->>'attempt_id'=:evaluation ORDER BY a.id""",
                    evaluation=identifier(evaluation_id),
                ).scalars()
            ]

    def persist_report(self, report):
        self.report_validator(report)
        fingerprint = digest(report)
        event_id = str(uuid5(NAMESPACE, fingerprint))
        with self.transaction() as c:
            execute(
                c,
                """INSERT INTO audit_events
              (id,event_type,action,resource_type,resource_id,request_method,request_path,correlation_id,after_state,metadata,success,error_code)
              VALUES(CAST(:id AS uuid),:event,'compare',:resource,:hash,'CLI',:source,CAST(:correlation AS text),CAST(:payload AS jsonb),'{}'::jsonb,:success,:error)
              ON CONFLICT (id) DO NOTHING""",
                id=event_id,
                event=self.report_event,
                resource=self.report_resource_type,
                source=self.report_source,
                hash=fingerprint,
                correlation=event_id,
                payload=canonical(report),
                success=self.report_success,
                error=self.report_error_code(report),
            )
        require(self.read_report(event_id) == report, "REPORT_ROUND_TRIP_CONFLICT")
        return event_id

    def read_report(self, report_id):
        with self.transaction(readonly=True) as c:
            row = (
                execute(
                    c,
                    "SELECT after_state,resource_id,success,error_code FROM audit_events WHERE id=CAST(:id AS uuid) AND event_type=:event",
                    id=identifier(report_id),
                    event=self.report_event,
                )
                .mappings()
                .one()
            )
            require(
                row["success"] is self.report_success
                and row["error_code"] == self.report_error_code(row["after_state"])
                and digest(row["after_state"]) == row["resource_id"],
                "REPORT_PERSISTENCE_CONFLICT",
            )
            self.report_validator(row["after_state"])
            return row["after_state"]

    def freeze_final(self, report_id, value):
        """Persist an exact future TEST identity, after full read-only validation; no inference."""
        from ..assessment import lineage
        from ..assessment.contracts import identity
        from .comparison import read_evaluation

        report = self.read_report(report_id)
        candidate = report["selection"]["candidate"]
        require(
            report["split"] == "val" and candidate is not None, "VAL_CANDIDATE_REQUIRED"
        )
        # Revalidate the representative and E1 files now, without changing historical results.
        source = read_evaluation(self, candidate["evaluation_id"])["identity"]
        require(
            value["kind"] == "evaluate"
            and value["split"] == "test"
            and value["purpose"] == "final",
            "FINAL_TEST_IDENTITY_REQUIRED",
        )
        require(
            value["model"] == candidate["model"] == source["model"]
            and value["decision"] == candidate["decision"] == source["decision"]
            and value["dataset"] == report["dataset"] == source["dataset"],
            "FINAL_CANDIDATE_CONFLICT",
        )
        require(
            value["protocol"] == candidate["e6_protocol"] == source["protocol"],
            "FINAL_PROTOCOL_CONFLICT",
        )
        require(
            value["seed"] == source["seed"]
            and value["batch_size"] == source["batch_size"],
            "FINAL_INFERENCE_OPTIONS_CONFLICT",
        )
        samples = lineage.dataset_samples(
            self, value["dataset"], "test", inspection=True
        )
        rebuilt = identity(
            value["model"],
            value["dataset"],
            samples,
            split="test",
            purpose="final",
            protocol=value["protocol"],
            decision=value["decision"],
            code=value["code"],
            seed=value["seed"],
            batch_size=value["batch_size"],
        )
        require(rebuilt == value, "FINAL_IDENTITY_CONFLICT")
        fingerprint = digest(value)
        evidence = {
            "status": "locked",
            "identity_hash": fingerprint,
            "schema": "e7_candidate_lock_v1",
            "report_id": identifier(report_id),
            "report_hash": digest(report),
            "protocol_hash": report["protocol_hash"],
            "candidate": value["model"],
            "decision": value["decision"],
            "final_identity": value,
            "selection": report["selection"],
        }
        with self.transaction() as c:
            execute(
                c,
                "INSERT INTO assessment_final_locks(id,identity_hash,evidence) VALUES(CAST(:id AS uuid),:hash,CAST(:payload AS jsonb)) ON CONFLICT (identity_hash) DO NOTHING",
                id=str(uuid5(NAMESPACE, "final:" + fingerprint)),
                hash=fingerprint,
                payload=canonical(evidence),
            )
        with self.transaction(readonly=True) as c:
            actual = execute(
                c,
                "SELECT evidence FROM assessment_final_locks WHERE identity_hash=:hash",
                hash=fingerprint,
            ).scalar_one()
            require(actual == evidence, "FINAL_LOCK_CONFLICT")
        return fingerprint
