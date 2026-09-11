"""E5 transactions. No file ledger; failed writes stop execution."""

from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import CampaignError, canonical, member_configuration
from ..campaigns.repository import CampaignRepository, execute, identifier


class ExecutionRepository(CampaignRepository):
    @staticmethod
    def authorize(c, owner):
        execute(
            c,
            "SELECT set_config('capstone.train_owner',:owner,true)",
            owner=identifier(owner),
        )

    def session(self, run_id):
        with self.transaction(readonly=True) as c:
            row = (
                execute(
                    c,
                    "SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid)",
                    id=identifier(run_id),
                )
                .mappings()
                .one()
            )
            return dict(row)

    def records(self, run_id):
        with self.transaction(readonly=True) as c:
            return [
                dict(r)
                for r in execute(
                    c,
                    "SELECT kind,phase,record_key,payload FROM train_execution_records WHERE run_id=CAST(:id AS uuid) ORDER BY kind,phase,record_key",
                    id=identifier(run_id),
                ).mappings()
            ]

    def claim(self, campaign_id, owner, host, parent_pid, artifact_root):
        with self.transaction() as c:
            campaign = self._campaign(c, campaign_id, True)
            if campaign["state"] not in ("frozen", "active"):
                raise CampaignError("CAMPAIGN_NOT_EXECUTABLE")
            member = (
                execute(
                    c,
                    """SELECT m.* FROM campaign_members m WHERE campaign_id=CAST(:id AS uuid)
              AND state IN ('pending','failed','interrupted') AND
              (SELECT count(*) FROM campaign_attempts a WHERE a.member_id=m.id)<:budget
              ORDER BY (state='pending') DESC,position LIMIT 1 FOR UPDATE""",
                    id=identifier(campaign_id),
                    budget=campaign["protocol"]["budget"]["max_attempts_per_member"],
                )
                .mappings()
                .one_or_none()
            )
            if not member:
                return None
            item = campaign["contract"]["matrix"]["configurations"][
                member["configuration_hash"]
            ]
            config = member_configuration(item["configuration"], member["seed"])
            attempt, run = str(uuid4()), str(uuid4())
            ordinal = execute(
                c,
                "SELECT coalesce(max(ordinal),0)+1 FROM campaign_attempts WHERE member_id=CAST(:id AS uuid)",
                id=str(member["id"]),
            ).scalar_one()
            execute(
                c,
                "INSERT INTO campaign_attempts(id,member_id,ordinal,state) VALUES(CAST(:id AS uuid),CAST(:member AS uuid),:ordinal,'active')",
                id=attempt,
                member=str(member["id"]),
                ordinal=ordinal,
            )
            self._create_run(
                c,
                run,
                config,
                campaign["dataset_snapshot"],
                campaign["environment"],
                campaign["experiment_id"],
                evidence_id=str(campaign["dataset_evidence_id"]),
            )
            execute(
                c,
                "UPDATE campaign_attempts SET training_run_id=CAST(:run AS uuid) WHERE id=CAST(:id AS uuid)",
                run=run,
                id=attempt,
            )
            root = str(Path(artifact_root).resolve() / run)
            execute(
                c,
                """INSERT INTO train_execution_sessions(run_id,attempt_id,owner,host,parent_pid,configuration,dataset,environment,artifact_root)
              VALUES(CAST(:run AS uuid),CAST(:attempt AS uuid),CAST(:owner AS uuid),:host,:pid,CAST(:config AS jsonb),CAST(:dataset AS jsonb),CAST(:environment AS jsonb),:root)""",
                run=run,
                attempt=attempt,
                owner=identifier(owner),
                host=host,
                pid=parent_pid,
                config=canonical(config),
                dataset=canonical(campaign["dataset_snapshot"]),
                environment=canonical(campaign["environment"]),
                root=root,
            )
            execute(
                c,
                "UPDATE experimental_campaigns SET state='active',updated_at=now() WHERE id=CAST(:id AS uuid)",
                id=identifier(campaign_id),
            )
        return self.session(run)

    @staticmethod
    def _create_run(
        c, run, config, dataset, environment, experiment=None, evidence_id=None
    ):
        # Relational identity must be unambiguous; never infer from folders/dates.
        models = (
            execute(
                c,
                "SELECT id FROM models WHERE name=:name ORDER BY id",
                name=config["model_id"],
            )
            .scalars()
            .all()
        )
        if len(models) != 1:
            raise CampaignError("CANONICAL_MODEL_CATALOG_IDENTITY_REQUIRED")
        snapshot = {
            "configuration": config,
            "dataset": dataset,
            "environment": environment,
        }
        execute(
            c,
            """INSERT INTO runs(id,model_id,experiment_id,run_type,status,random_seed,dataset_version_id,execution_parameters)
          VALUES(CAST(:id AS uuid),CAST(:model AS uuid),CAST(:experiment AS uuid),'training','running',:seed,CAST(:dataset AS uuid),CAST(:parameters AS jsonb))""",
            id=run,
            model=str(models[0]),
            experiment=str(experiment) if experiment else None,
            seed=config["resolved"]["execution"]["seed"],
            dataset=dataset["dataset_version_id"],
            parameters=canonical(
                {
                    "model_configuration_e2": snapshot,
                    "dataset_verification_evidence_id": evidence_id,
                }
            ),
        )

    def put(self, run_id, owner, kind, phase, key, payload):
        with self.transaction() as c:
            self.authorize(c, owner)
            session = (
                execute(
                    c,
                    "SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid) FOR UPDATE",
                    id=identifier(run_id),
                )
                .mappings()
                .one()
            )
            if (
                str(session["owner"]) != identifier(owner)
                or session["state"] != "active"
            ):
                raise CampaignError("TRAIN_OWNER_FENCED")
            old = execute(
                c,
                "SELECT payload FROM train_execution_records WHERE run_id=CAST(:id AS uuid) AND kind=:kind AND phase=:phase AND record_key=:key",
                id=identifier(run_id),
                kind=kind,
                phase=phase,
                key=str(key),
            ).scalar_one_or_none()
            if old is not None:
                if canonical(old) != canonical(payload):
                    raise CampaignError("RESULT_IDEMPOTENCY_CONFLICT")
                return
            execute(
                c,
                "INSERT INTO train_execution_records(run_id,kind,phase,record_key,payload) VALUES(CAST(:id AS uuid),:kind,:phase,:key,CAST(:payload AS jsonb))",
                id=identifier(run_id),
                kind=kind,
                phase=phase,
                key=str(key),
                payload=canonical(payload),
            )

    def child_started(self, run, owner, pid):
        with self.transaction() as c:
            self.authorize(c, owner)
            row = execute(
                c,
                "UPDATE train_execution_sessions SET child_pid=:pid,updated_at=clock_timestamp() WHERE run_id=CAST(:id AS uuid) AND child_pid IS NULL RETURNING run_id",
                pid=pid,
                id=identifier(run),
            ).first()
            if row is None:
                raise CampaignError("CHILD_ALREADY_REGISTERED")

    def finish(self, run, owner, state, evidence=None, cause=None):
        # Lock order: campaign, member, attempt, session, run.
        initial = self.session(run)
        with self.transaction() as c:
            self.authorize(c, owner)
            if initial["attempt_id"]:
                member = (
                    execute(
                        c,
                        "SELECT m.* FROM campaign_members m JOIN campaign_attempts a ON a.member_id=m.id WHERE a.id=CAST(:id AS uuid)",
                        id=str(initial["attempt_id"]),
                    )
                    .mappings()
                    .one()
                )
                self._campaign(c, str(member["campaign_id"]), True)
                execute(
                    c,
                    "SELECT id FROM campaign_members WHERE id=CAST(:id AS uuid) FOR UPDATE",
                    id=str(member["id"]),
                )
            col = "verification" if state == "verified" else "completion"
            execute(
                c,
                f"UPDATE train_execution_sessions SET state=:state,{col}=CAST(:evidence AS jsonb),cause=:cause,updated_at=clock_timestamp() WHERE run_id=CAST(:id AS uuid)",
                state=state,
                evidence=canonical(evidence) if evidence is not None else None,
                cause=cause,
                id=identifier(run),
            )
            if initial["attempt_id"]:
                execute(
                    c,
                    "UPDATE campaign_attempts SET state=:state,cause=:cause,finished_at=clock_timestamp() WHERE id=CAST(:id AS uuid)",
                    state=state,
                    cause=cause,
                    id=str(initial["attempt_id"]),
                )
            execute(
                c,
                "UPDATE runs SET status=:state,finished_at=clock_timestamp() WHERE id=CAST(:id AS uuid)",
                state="completed" if state in ("completed", "verified") else state,
                id=identifier(run),
            )

    def pause(self, campaign, code):
        with self.transaction() as c:
            self._campaign(c, campaign, True)
            execute(
                c,
                "UPDATE experimental_campaigns SET state='paused',updated_at=now() WHERE id=CAST(:id AS uuid) AND state IN ('frozen','active')",
                id=identifier(campaign),
            )
            execute(
                c,
                "INSERT INTO campaign_execution_events(campaign_id,code) VALUES(CAST(:id AS uuid),:code)",
                id=identifier(campaign),
                code=code,
            )

    def resume(self, campaign):
        with self.transaction() as c:
            self._campaign(c, campaign, True)
            execute(
                c,
                "UPDATE experimental_campaigns SET state='active',updated_at=now() WHERE id=CAST(:id AS uuid) AND state='paused'",
                id=identifier(campaign),
            )

    def preflight(self):
        with self.transaction() as c:
            execute(c, "SELECT run_id FROM train_execution_sessions LIMIT 0")
            execute(c, "SELECT kind FROM train_execution_records LIMIT 0")
            if not execute(
                c,
                "SELECT has_table_privilege(current_user,'train_execution_sessions','INSERT,UPDATE') AND has_table_privilege(current_user,'train_execution_records','INSERT')",
            ).scalar_one():
                raise CampaignError("PERSISTENCE_PERMISSION_REQUIRED")

    def summary(self, campaign):
        row = self.get(campaign)
        counts = {
            state: sum(m["state"] == state for m in row["members"])
            for state in (
                "pending",
                "active",
                "failed",
                "interrupted",
                "completed",
                "verified",
                "excluded",
            )
        }
        with self.transaction(readonly=True) as c:
            reasons = (
                execute(
                    c,
                    "SELECT code FROM campaign_execution_events WHERE campaign_id=CAST(:id AS uuid) ORDER BY created_at",
                    id=identifier(campaign),
                )
                .scalars()
                .all()
            )
        with self.transaction(readonly=True) as c:
            clinical = (
                execute(
                    c,
                    """SELECT s.completion->'clinical_objective_met' FROM train_execution_sessions s
              JOIN campaign_attempts a ON a.id=s.attempt_id JOIN campaign_members m ON m.accepted_attempt_id=a.id
              WHERE m.campaign_id=CAST(:id AS uuid)""",
                    id=identifier(campaign),
                )
                .scalars()
                .all()
            )
        return {
            "campaign_id": identifier(campaign),
            "state": row["state"],
            "expected": len(row["members"]),
            "members": counts,
            "attempts": len(row["attempts"]),
            "accepted": sum(
                m["accepted_attempt_id"] is not None for m in row["members"]
            ),
            "matrix_complete": counts["verified"] == len(row["members"]),
            "operational_terminal": counts["pending"] == counts["active"] == 0,
            "clinical_status": {
                "met": sum(x is True for x in clinical),
                "unmet": sum(x is False for x in clinical),
                "unknown": sum(x is None for x in clinical),
            },
            "reasons": reasons,
        }

    def standalone(self, config, dataset, environment, root, host, pid, evidence_id):
        run, owner = str(uuid4()), str(uuid4())
        with self.transaction() as c:
            self._create_run(
                c, run, config, dataset, environment, evidence_id=evidence_id
            )
            execute(
                c,
                """INSERT INTO train_execution_sessions(run_id,owner,host,parent_pid,child_pid,configuration,dataset,environment,artifact_root)
             VALUES(CAST(:run AS uuid),CAST(:owner AS uuid),:host,:pid,:pid,CAST(:config AS jsonb),CAST(:dataset AS jsonb),CAST(:environment AS jsonb),:root)""",
                run=run,
                owner=owner,
                host=host,
                pid=pid,
                config=canonical(config),
                dataset=canonical(dataset),
                environment=canonical(environment),
                root=str(Path(root).resolve() / run),
            )
        return self.session(run)

    def finalize_terminal(self, campaign):
        with self.transaction() as c:
            self._campaign(c, campaign, True)
            pending = execute(
                c,
                "SELECT count(*) FROM campaign_members WHERE campaign_id=CAST(:id AS uuid) AND state IN ('pending','active','completed')",
                id=identifier(campaign),
            ).scalar_one()
            if not pending:
                execute(
                    c,
                    "UPDATE experimental_campaigns SET state='finalized',updated_at=now() WHERE id=CAST(:id AS uuid) AND state='active'",
                    id=identifier(campaign),
                )
