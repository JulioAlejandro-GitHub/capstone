"""Short transactions, immutable batches, one live attempt per scientific identity."""

import os
import socket
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..campaigns.contracts import canonical, digest
from ..campaigns.repository import CampaignRepository, execute, identifier
from .contracts import require


class AssessmentRepository(CampaignRepository):
    def authorize_test_request(
        self, *, training_run_id: str | None, model_version_id: str | None,
        dataset_version_id: str | None, protocol: dict[str, Any],
        requested_threshold: str | float, seed: int, batch_size: int,
        explanation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Read the existing exact final lock before opening any dataset files.

        The persisted identity is required to establish its scope without reading
        TEST to discover that scope. Historical locks can use their identity row.
        """
        require(training_run_id or model_version_id, "EXPLICIT_MODEL_IDENTITY_REQUIRED")
        with self.transaction(readonly=True) as c:
            locks = list(execute(c, """
                SELECT l.identity_hash,l.evidence,
                       COALESCE(l.evidence->'final_identity',i.identity) AS identity
                FROM assessment_final_locks l
                LEFT JOIN assessment_identities i ON i.identity_hash=l.identity_hash
                WHERE (CAST(:train AS text) IS NULL OR l.evidence->'candidate'->>'training_run_id'=:train)
                  AND (CAST(:model AS text) IS NULL OR l.evidence->'candidate'->>'model_version_id'=:model)
            """, train=identifier(training_run_id) if training_run_id else None,
                model=identifier(model_version_id) if model_version_id else None).mappings())
        matches = []
        if explanation and explanation["method"] == "shap":
            explanation = {**explanation, "background": sorted(explanation["background"])}
        for row in locks:
            value, evidence = row["identity"], row["evidence"]
            if not value or digest(value) != row["identity_hash"]:
                continue
            spec = value.get("explanation")
            if spec and spec["method"] == "shap":
                spec = {**spec, "background": sorted(s["sample_id"] for s in spec["background"])}
            if (value["split"] == "test" and value["purpose"] == "final"
                    and value["kind"] == ("explain" if explanation else "evaluate")
                    and evidence.get("status") == "locked"
                    and evidence.get("candidate") == value["model"]
                    and evidence.get("decision") == value["decision"]
                    and value["protocol"] == protocol
                    and value["seed"] == seed and value["batch_size"] == batch_size
                    and value["decision"]["requested"] == str(requested_threshold)
                    and spec == explanation
                    and (dataset_version_id is None or identifier(dataset_version_id) == value["dataset"]["dataset_version_id"])):
                matches.append(value)
        require(len(matches) == 1, "TEST_FINAL_LOCK_REQUIRED")
        return matches[0]

    @staticmethod
    def authorize(c, owner):
        execute(
            c,
            "SELECT set_config('capstone.assessment_owner',:owner,true)",
            owner=identifier(owner),
        )

    def reserve(self, value, artifact_root):
        fingerprint = digest(value)
        with self.transaction() as c:
            execute(
                c,
                """INSERT INTO assessment_identities(id,identity_hash,training_run_id,kind,identity,canonical_identity)
              VALUES(CAST(:id AS uuid),:hash,CAST(:train AS uuid),:kind,CAST(:value AS jsonb),:canonical_value)
              ON CONFLICT DO NOTHING""",
                id=str(uuid4()),
                hash=fingerprint,
                train=identifier(value["model"]["training_run_id"]),
                kind=value["kind"],
                value=canonical(value),
                canonical_value=canonical(value),
            )
            row = (
                execute(
                    c,
                    "SELECT * FROM assessment_identities WHERE identity_hash=:hash FOR UPDATE",
                    hash=fingerprint,
                )
                .mappings()
                .one_or_none()
            )
            # Both unique hashes arbitrate insertion. A conflict on another identity
            # must fail closed, never select that row by date or structural hash.
            require(row is not None, "IDENTITY_CONFLICT_NOT_EXACT")
            require(row["identity"] == value, "IDENTITY_HASH_CONFLICT")
            existing = (
                execute(
                    c,
                    "SELECT * FROM assessment_attempts WHERE identity_id=CAST(:id AS uuid) AND state IN ('active','verified')",
                    id=str(row["id"]),
                )
                .mappings()
                .one_or_none()
            )
            if existing:
                return dict(existing), False
            attempt, owner = str(uuid4()), str(uuid4())
            n = execute(
                c,
                "SELECT coalesce(max(ordinal),0)+1 FROM assessment_attempts WHERE identity_id=CAST(:id AS uuid)",
                id=str(row["id"]),
            ).scalar_one()
            root = str(Path(artifact_root).resolve() / attempt)
            execute(
                c,
                """INSERT INTO assessment_attempts(id,identity_id,owner,host,pid,ordinal,artifact_root)
              VALUES(CAST(:id AS uuid),CAST(:identity AS uuid),CAST(:owner AS uuid),:host,:pid,:n,:root)""",
                id=attempt,
                identity=str(row["id"]),
                owner=owner,
                host=socket.gethostname(),
                pid=os.getpid(),
                n=n,
                root=root,
            )
        return self.attempt(attempt), True

    def attempt(self, attempt_id):
        with self.transaction(readonly=True) as c:
            r = (
                execute(
                    c,
                    "SELECT * FROM assessment_attempts WHERE id=CAST(:id AS uuid)",
                    id=identifier(attempt_id),
                )
                .mappings()
                .one()
            )
            return dict(r)

    def identity(self, identity_id):
        with self.transaction(readonly=True) as c:
            return execute(
                c,
                "SELECT identity FROM assessment_identities WHERE id=CAST(:id AS uuid)",
                id=identifier(identity_id),
            ).scalar_one()

    def results(self, attempt_id):
        with self.transaction(readonly=True) as c:
            return list(
                execute(
                    c,
                    "SELECT payload FROM assessment_results WHERE attempt_id=CAST(:id AS uuid) ORDER BY sample_id",
                    id=identifier(attempt_id),
                ).scalars()
            )

    def artifacts(self, attempt_id):
        with self.transaction(readonly=True) as c:
            return list(
                execute(
                    c,
                    "SELECT payload FROM assessment_artifacts WHERE attempt_id=CAST(:id AS uuid) ORDER BY sample_id,role",
                    id=identifier(attempt_id),
                ).scalars()
            )

    def write_batch(self, attempt_id, owner, rows):
        with self.transaction() as c:
            self.authorize(c, owner)
            a = (
                execute(
                    c,
                    "SELECT * FROM assessment_attempts WHERE id=CAST(:id AS uuid) FOR UPDATE",
                    id=identifier(attempt_id),
                )
                .mappings()
                .one()
            )
            require(
                a["state"] == "active" and str(a["owner"]) == identifier(owner),
                "ASSESSMENT_OWNER_FENCED",
            )
            for row in rows:
                old = execute(
                    c,
                    "SELECT payload FROM assessment_results WHERE attempt_id=CAST(:id AS uuid) AND sample_id=CAST(:sample AS uuid)",
                    id=identifier(attempt_id),
                    sample=identifier(row["sample_id"]),
                ).scalar_one_or_none()
                if old is not None:
                    require(old == row, "CONTRADICTORY_RESULT")
                else:
                    execute(
                        c,
                        "INSERT INTO assessment_results VALUES(CAST(:id AS uuid),CAST(:sample AS uuid),CAST(:payload AS jsonb))",
                        id=identifier(attempt_id),
                        sample=identifier(row["sample_id"]),
                        payload=canonical(row),
                    )

    def artifact(self, attempt_id, owner, payload):
        with self.transaction() as c:
            self.authorize(c, owner)
            execute(
                c,
                """INSERT INTO assessment_artifacts(attempt_id,artifact_id,sample_id,role,payload)
              VALUES(CAST(:id AS uuid),CAST(:artifact AS uuid),CAST(:sample AS uuid),:role,CAST(:payload AS jsonb))""",
                id=identifier(attempt_id),
                artifact=identifier(payload["artifact_id"]),
                sample=identifier(payload["sample_id"]),
                role=payload["role"],
                payload=canonical(payload),
            )

    def finish(self, attempt_id, owner, state, verification=None, cause=None):
        require(
            state in ("verified", "failed", "interrupted"), "INVALID_ASSESSMENT_STATE"
        )
        with self.transaction() as c:
            self.authorize(c, owner)
            execute(
                c,
                """UPDATE assessment_attempts SET state=:state,verification=CAST(:verification AS jsonb),cause=:cause,finished_at=clock_timestamp()
              WHERE id=CAST(:id AS uuid)""",
                id=identifier(attempt_id),
                state=state,
                verification=canonical(verification) if verification else None,
                cause=cause,
            )

    def consume(self, campaign, member, attempt):
        with self.transaction() as c:
            execute(
                c,
                """INSERT INTO assessment_campaign_consumers VALUES(CAST(:campaign AS uuid),CAST(:member AS uuid),CAST(:identity AS uuid)) ON CONFLICT DO NOTHING""",
                campaign=identifier(campaign),
                member=identifier(member),
                identity=str(attempt["identity_id"]),
            )

    def recover(self, attempt_id):
        a = self.attempt(attempt_id)
        require(a["state"] == "active", "ASSESSMENT_NOT_ACTIVE")
        require(a["host"] == socket.gethostname(), "ASSESSMENT_OWNER_LIVENESS_UNKNOWN")
        try:
            os.kill(a["pid"], 0)
        except ProcessLookupError:
            self.finish(
                attempt_id,
                a["owner"],
                "interrupted",
                cause="OWNER_PROCESS_ABSENT_RESTART_FULL_ATTEMPT",
            )
            return
        except PermissionError:
            pass
        require(False, "ASSESSMENT_OWNER_LIVENESS_UNKNOWN")
