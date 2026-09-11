"""Transactional E4 repository. PostgreSQL is authoritative; no file fallback."""

import json
from contextlib import contextmanager
from uuid import UUID, uuid4

from sqlalchemy import text

from ..persistence.database import get_engine
from .contracts import CampaignError, canonical, digest, validate_frozen_contract


def identifier(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise CampaignError("UUID_REQUIRED") from None


@contextmanager
def connection_scope(readonly=False):
    engine = get_engine()
    try:
        with engine.begin() as connection:
            if readonly:
                connection.execute(text("SET TRANSACTION READ ONLY"))
            yield connection
    finally:
        engine.dispose()


def execute(c, sql, **params):
    return c.execute(text(sql), params)


class CampaignRepository:
    def __init__(self, scope=connection_scope):
        self.scope = scope

    @contextmanager
    def transaction(self, readonly=False):
        try:
            with self.scope(readonly=readonly) as c:
                yield c
        except CampaignError:
            raise
        except Exception:  # noqa: BLE001 -- sanitize driver details at public boundary
            raise CampaignError("CAMPAIGN_DATABASE_OPERATION_FAILED") from None

    @staticmethod
    def _campaign(c, campaign_id, lock=False):
        row = (
            execute(
                c,
                "SELECT * FROM experimental_campaigns WHERE id=CAST(:id AS uuid)"
                + (" FOR UPDATE" if lock else ""),
                id=identifier(campaign_id),
            )
            .mappings()
            .one_or_none()
        )
        if not row:
            raise CampaignError("CAMPAIGN_NOT_FOUND")
        return dict(row)

    def get(self, campaign_id, dataset_version_id=None):
        with self.transaction(readonly=True) as c:
            row = self._campaign(c, campaign_id)
            if dataset_version_id is not None and identifier(dataset_version_id) != str(
                row["dataset_version_id"]
            ):
                raise CampaignError("CAMPAIGN_DATASET_CONFLICT")
            configs = (
                execute(
                    c,
                    "SELECT * FROM campaign_configurations WHERE campaign_id=CAST(:id AS uuid) ORDER BY configuration_hash",
                    id=str(row["id"]),
                )
                .mappings()
                .all()
            )
            members = (
                execute(
                    c,
                    "SELECT * FROM campaign_members WHERE campaign_id=CAST(:id AS uuid) ORDER BY position",
                    id=str(row["id"]),
                )
                .mappings()
                .all()
            )
            attempts = (
                execute(
                    c,
                    """SELECT a.* FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
              WHERE m.campaign_id=CAST(:id AS uuid) ORDER BY m.position,a.ordinal""",
                    id=str(row["id"]),
                )
                .mappings()
                .all()
            )
            row.update(
                configurations=[dict(x) for x in configs],
                members=[dict(x) for x in members],
                attempts=[dict(x) for x in attempts],
            )
            if row["state"] != "draft":
                validate_frozen_contract(row["contract"])
                if (
                    digest(row["contract"]) != row["contract_hash"]
                    or canonical(row["contract"]) != row["canonical_contract"]
                ):
                    raise CampaignError("STORED_CAMPAIGN_HASH_CONFLICT")
                actual_configs = {
                    x["configuration_hash"]: {
                        "configuration": x["configuration"],
                        "requests": x["requests"],
                    }
                    for x in configs
                }
                actual_members = [
                    {
                        k: x[k]
                        for k in (
                            "configuration_hash",
                            "seed",
                            "position",
                            "exclusion_reason",
                        )
                    }
                    for x in members
                ]
                if (
                    actual_configs != row["contract"]["matrix"]["configurations"]
                    or actual_members != row["contract"]["matrix"]["members"]
                ):
                    raise CampaignError("STORED_MATRIX_CONFLICT")
                for x in configs:
                    if digest(x["configuration"]) != x["configuration_hash"]:
                        raise CampaignError("STORED_CONFIGURATION_HASH_CONFLICT")
            return row

    def create(
        self,
        *,
        name,
        purpose,
        dataset,
        evidence_id,
        requested,
        protocol,
        environment,
        actor,
        experiment_id=None,
    ):
        if any(not isinstance(x, str) or not x.strip() for x in (name, purpose, actor)):
            raise CampaignError("CAMPAIGN_NAME_PURPOSE_ACTOR_REQUIRED")
        campaign_id = str(uuid4())
        with self.transaction() as c:
            execute(
                c,
                """INSERT INTO experimental_campaigns
              (id,experiment_id,name,purpose,dataset_version_id,dataset_snapshot,dataset_evidence_id,requested,protocol,environment,actor)
              VALUES(CAST(:id AS uuid),CAST(:experiment AS uuid),:name,:purpose,CAST(:dataset AS uuid),CAST(:snapshot AS jsonb),
              CAST(:evidence AS uuid),CAST(:requested AS jsonb),CAST(:protocol AS jsonb),CAST(:environment AS jsonb),:actor)""",
                id=campaign_id,
                experiment=identifier(experiment_id) if experiment_id else None,
                name=name,
                purpose=purpose,
                dataset=identifier(dataset["dataset_version_id"]),
                snapshot=canonical(dataset),
                evidence=identifier(evidence_id),
                requested=canonical(requested),
                protocol=canonical(protocol),
                environment=canonical(environment),
                actor=actor,
            )
        stored = self.get(campaign_id)
        if any(
            stored[k] != v
            for k, v in {
                "requested": requested,
                "protocol": protocol,
                "environment": environment,
                "dataset_snapshot": dataset,
            }.items()
        ):
            raise CampaignError("CAMPAIGN_CREATE_READBACK_FAILED")
        return stored

    def edit(self, campaign_id, requested, protocol):
        with self.transaction() as c:
            row = self._campaign(c, campaign_id, True)
            if row["state"] != "draft":
                raise CampaignError("CAMPAIGN_NOT_DRAFT")
            execute(
                c,
                """UPDATE experimental_campaigns SET requested=CAST(:requested AS jsonb),protocol=CAST(:protocol AS jsonb)
              WHERE id=CAST(:id AS uuid)""",
                id=str(row["id"]),
                requested=canonical(requested),
                protocol=canonical(protocol),
            )
        return self.get(campaign_id)

    def freeze(self, campaign_id, contract, expected_draft):
        """No partially frozen matrix survives a failure, including audit insertion."""
        validate_frozen_contract(contract)
        with self.transaction() as c:
            row = self._campaign(c, campaign_id, True)
            if row["state"] != "draft":
                raise CampaignError("CAMPAIGN_NOT_DRAFT")
            actual = {k: row[k] for k in expected_draft}
            if actual != expected_draft:
                raise CampaignError("DRAFT_CHANGED_DURING_VALIDATION")
            for h, item in contract["matrix"]["configurations"].items():
                execute(
                    c,
                    """INSERT INTO campaign_configurations(campaign_id,configuration_hash,configuration,canonical_configuration,requests)
                  VALUES(CAST(:id AS uuid),:hash,CAST(:config AS jsonb),:canonical,CAST(:requests AS jsonb))""",
                    id=str(row["id"]),
                    hash=h,
                    config=canonical(item["configuration"]),
                    canonical=canonical(item["configuration"]),
                    requests=canonical(item["requests"]),
                )
            for m in contract["matrix"]["members"]:
                execute(
                    c,
                    """INSERT INTO campaign_members(id,campaign_id,configuration_hash,seed,position,state,exclusion_reason)
                  VALUES(CAST(:member AS uuid),CAST(:campaign AS uuid),:hash,:seed,:position,:state,:reason)""",
                    member=str(uuid4()),
                    campaign=str(row["id"]),
                    hash=m["configuration_hash"],
                    seed=m["seed"],
                    position=m["position"],
                    state="excluded" if m["exclusion_reason"] else "pending",
                    reason=m["exclusion_reason"],
                )
            execute(
                c,
                """UPDATE experimental_campaigns SET state='frozen',registry_snapshot=CAST(:registry AS jsonb),
              contract=CAST(:contract AS jsonb),canonical_contract=:canonical,contract_hash=:hash,
              expected_count=:count,frozen_at=now() WHERE id=CAST(:id AS uuid)""",
                id=str(row["id"]),
                registry=canonical(contract["matrix"]["registry"]),
                contract=canonical(contract),
                canonical=canonical(contract),
                hash=digest(contract),
                count=contract["matrix"]["expected_count"],
            )
        result = self.get(campaign_id)
        if result["contract"] != json.loads(canonical(contract)):
            raise CampaignError("CAMPAIGN_FREEZE_READBACK_FAILED")
        return result

    def transition(self, campaign_id, state):
        transitions = {
            "frozen": {"active", "paused"},
            "active": {"paused", "finalized"},
            "paused": {"active", "finalized"},
        }
        with self.transaction() as c:
            row = self._campaign(c, campaign_id, True)
            if state not in transitions.get(row["state"], set()):
                raise CampaignError("INVALID_CAMPAIGN_TRANSITION")
            execute(
                c,
                "UPDATE experimental_campaigns SET state=:state WHERE id=CAST(:id AS uuid)",
                id=str(row["id"]),
                state=state,
            )
        return self.get(campaign_id)

    def create_attempt(self, campaign_id, member_id):
        attempt = str(uuid4())
        with self.transaction() as c:
            self._campaign(c, campaign_id, True)
            member = (
                execute(
                    c,
                    """SELECT * FROM campaign_members WHERE id=CAST(:member AS uuid)
              AND campaign_id=CAST(:campaign AS uuid) FOR UPDATE""",
                    member=identifier(member_id),
                    campaign=identifier(campaign_id),
                )
                .mappings()
                .one_or_none()
            )
            if not member:
                raise CampaignError("MEMBER_CAMPAIGN_CONFLICT")
            ordinal = execute(
                c,
                "SELECT coalesce(max(ordinal),0)+1 FROM campaign_attempts WHERE member_id=CAST(:id AS uuid)",
                id=identifier(member_id),
            ).scalar_one()
            execute(
                c,
                """INSERT INTO campaign_attempts(id,member_id,ordinal,state)
              VALUES(CAST(:id AS uuid),CAST(:member AS uuid),:ordinal,'active')""",
                id=attempt,
                member=identifier(member_id),
                ordinal=ordinal,
            )
        return self.get(campaign_id)

    def update_attempt(
        self, campaign_id, attempt_id, *, training_run_id=None, state=None, cause=None
    ):
        if state is not None and state not in ("failed", "interrupted", "completed"):
            raise CampaignError("INVALID_ATTEMPT_TRANSITION")
        if state in ("failed", "interrupted") and (
            not isinstance(cause, str) or not cause.strip()
        ):
            raise CampaignError("ATTEMPT_CAUSE_REQUIRED")
        if state is None and training_run_id is None:
            raise CampaignError("ATTEMPT_CHANGE_REQUIRED")
        with self.transaction() as c:
            self._campaign(c, campaign_id, True)
            changed = execute(
                c,
                """UPDATE campaign_attempts a SET training_run_id=coalesce(CAST(:run AS uuid),a.training_run_id),
              state=coalesce(:state,a.state),cause=coalesce(:cause,a.cause),finished_at=CASE WHEN :terminal THEN now() ELSE a.finished_at END
              FROM campaign_members m WHERE m.id=a.member_id AND m.campaign_id=CAST(:campaign AS uuid) AND a.id=CAST(:id AS uuid)
              RETURNING a.id""",
                id=identifier(attempt_id),
                campaign=identifier(campaign_id),
                run=identifier(training_run_id) if training_run_id else None,
                state=state,
                cause=cause,
                terminal=state is not None,
            ).scalar_one_or_none()
            if changed is None:
                raise CampaignError("ATTEMPT_CAMPAIGN_CONFLICT")
        return self.get(campaign_id)
