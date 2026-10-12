"""Short transactions, immutable batches, one live attempt per scientific identity."""

import os
import socket
from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import canonical, digest
from ..campaigns.repository import CampaignRepository, execute, identifier
from .contracts import require


class AssessmentRepository(CampaignRepository):
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
