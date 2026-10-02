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
        """Historical TRAIN API: legacy evidence only, with unchanged hash bytes."""
        return self.legacy_records(run_id)

    def legacy_records(self, run_id):
        from ..persistence.execution_record_readers import read_legacy_execution_records
        with self.transaction(readonly=True) as c:
            return read_legacy_execution_records(c, run_id)

    def result_events(self, run_id):
        from ..persistence.execution_record_readers import read_result_events
        with self.transaction(readonly=True) as c:
            return read_result_events(c, run_id)

    def preflight_result_events(self, run_id):
        """Docker-only E10.3 schema capability/restart guard; never runs Alembic.

        Like controlled/global preflight, inspect installed schema objects rather
        than changing or stamping a database. Legacy and Local need not call this.
        """
        with self.transaction(readonly=True) as c:
            installed = execute(c, """
                SELECT
                  (SELECT count(*) FROM pg_attribute
                   WHERE attrelid=to_regclass('train_execution_records')
                     AND NOT attisdropped AND
                     ((attname='event_id' AND atttypid='uuid'::regtype) OR
                      (attname='event_sequence' AND atttypid='numeric'::regtype)))=2
                  AND EXISTS(SELECT 1 FROM pg_constraint
                    WHERE conrelid=to_regclass('train_execution_records')
                      AND conname='train_event_metadata' AND convalidated)
                  AND (SELECT count(*) FROM pg_index
                    WHERE indrelid=to_regclass('train_execution_records')
                      AND indexrelid IN (to_regclass('train_event_id_unique'),
                                         to_regclass('train_event_sequence_unique'))
                      AND indisunique AND indisvalid)=2
                  AND EXISTS(SELECT 1 FROM pg_trigger
                    WHERE tgrelid=to_regclass('train_execution_records')
                      AND tgname='a_train_event_guard' AND tgenabled IN ('O','A'))
                """).scalar_one()
            if not installed:
                raise CampaignError('E10_RESULT_EVENTS_MIGRATION_REQUIRED_20260922_01')
            if execute(c, """SELECT EXISTS(SELECT 1 FROM train_execution_records
                    WHERE run_id=CAST(:run AS uuid) AND event_id IS NOT NULL)""",
                    run=identifier(run_id)).scalar_one():
                raise CampaignError('E10_ACTIVE_STREAM_RECOVERY_UNSUPPORTED')

    def preflight_e10_schema(self):
        """Read-only readiness check before any campaign reservation."""
        from .schema import require_e10_schema
        with self.transaction(readonly=True) as c:
            return require_e10_schema(c)

    def claim(self, campaign_id, owner, host, parent_pid, artifact_root, revision_id=None,
              observed_runtime=None):
        from .schema import require_e10_schema
        with self.transaction() as c:
            require_e10_schema(c)
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
            runtime_environment = campaign['environment']
            if revision_id is not None:
                from .controlled import ControlledRepository, validate_revision
                payload = ControlledRepository(self.scope).revision(c, campaign_id, revision_id)
                validate_revision(campaign, payload)
                runtime_environment = payload['environment']
                execute(c, 'INSERT INTO train_execution_revisions(attempt_id,campaign_id,revision_id) '
                        'VALUES(CAST(:attempt AS uuid),CAST(:campaign AS uuid),CAST(:revision AS uuid))',
                        attempt=attempt, campaign=identifier(campaign_id), revision=identifier(revision_id))
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
                runtime_environment,
                campaign["experiment_id"],
                evidence_id=str(campaign["dataset_evidence_id"]),
                campaign_id=(campaign_id if execute(
                    c, "SELECT to_regclass('campaign_technical_revisions') IS NOT NULL"
                ).scalar_one() else None),
                runtime=observed_runtime,
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
                environment=canonical(runtime_environment),
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
        c, run, config, dataset, environment, experiment=None, evidence_id=None,
        campaign_id=None, runtime=None,
    ):
        from .schema import require_e10_schema, V2_REVISION
        revision = require_e10_schema(c)['revision']
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
        if not models:
            # First run of a registry model: the catalog row is derivable, not an
            # operator task. Duplicates remain an identity error, never a guess.
            from ..persistence.tracking import model_defaults
            d = model_defaults(config["model_id"])
            models = [execute(
                c,
                "INSERT INTO models(name,model_type,framework,architecture,pretrained,pretrained_source) "
                "VALUES(:name,:model_type,:framework,:architecture,:pretrained,:pretrained_source) RETURNING id",
                name=config["model_id"], **{k: d.get(k) for k in (
                    "model_type", "framework", "architecture", "pretrained", "pretrained_source")},
            ).scalar_one()]
        if len(models) != 1:
            raise CampaignError("CANONICAL_MODEL_CATALOG_IDENTITY_REQUIRED")
        snapshot = {
            "configuration": config,
            "dataset": dataset,
            "environment": environment,
        }
        execute(
            c,
            "INSERT INTO runs(id,model_id,experiment_id,run_type,status,random_seed,dataset_version_id,execution_parameters"
            + (",campaign_id" if campaign_id is not None else "")
            + ") VALUES(CAST(:id AS uuid),CAST(:model AS uuid),CAST(:experiment AS uuid),'training','running',:seed,CAST(:dataset AS uuid),CAST(:parameters AS jsonb)"
            + (",CAST(:campaign AS uuid)" if campaign_id is not None else "") + ")",
            id=run,
            model=str(models[0]),
            experiment=str(experiment) if experiment else None,
            seed=config["resolved"]["execution"]["seed"],
            dataset=dataset["dataset_version_id"],
            campaign=identifier(campaign_id) if campaign_id is not None else None,
            parameters=canonical(
                {
                    "model_configuration_e2": snapshot,
                    "dataset_verification_evidence_id": evidence_id,
                    # Observed runtime (host, OS, packages, code hash): recorded for
                    # reproducibility, never compared against the campaign reference.
                    **({"runtime_environment": runtime} if runtime is not None else {}),
                }
            ),
        )
        if revision == V2_REVISION:
            from ..persistence.v2_projection import project_configuration
            project_configuration(c, run, config)

    def bind_evaluation_context(self, run_id, owner, selected_epoch):
        """V2 producer, before VAL results are projected: register the selected
        checkpoint as the run's model_checkpoint artifact and record the evaluation
        provenance. Built only from persisted evidence (this run's artifact and
        prediction records, the campaign's frozen protocol). Idempotent; fenced."""
        from .schema import require_e10_schema, V2_REVISION
        from ..persistence.v2_projection import EVALUATION_CONTEXT_KEY, training_evaluation_context
        with self.transaction() as c:
            if require_e10_schema(c)['revision'] != V2_REVISION:
                return None  # E10 schema stores results in runs.parameters instead
            self.authorize(c, owner)
            session = execute(c, "SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid) FOR UPDATE",
                              id=identifier(run_id)).mappings().one()
            if str(session["owner"]) != identifier(owner) or session["state"] != "active":
                raise CampaignError("TRAIN_OWNER_FENCED")
            if not session["attempt_id"]:
                raise CampaignError("CAMPAIGN_PROTOCOL_REQUIRED")
            protocol = execute(c, """SELECT ec.protocol FROM experimental_campaigns ec
                JOIN campaign_members m ON m.campaign_id=ec.id
                JOIN campaign_attempts a ON a.member_id=m.id WHERE a.id=CAST(:attempt AS uuid)""",
                attempt=str(session["attempt_id"])).scalar_one()

            def record(kind):
                rows = execute(c, """SELECT payload FROM train_execution_records AS record
                    WHERE run_id=CAST(:id AS uuid) AND kind=:kind AND (to_jsonb(record)->>'event_id') IS NULL
                      AND (payload->>'epoch')::int=:epoch""",
                    id=identifier(run_id), kind=kind, epoch=int(selected_epoch)).scalars().all()
                if len(rows) != 1:
                    raise CampaignError("EXACT_CHECKPOINT_REQUIRED")
                return rows[0]

            artifact, predictions = record("artifact"), record("predictions")
            from .artifacts import file_identity
            if file_identity(artifact["path"]) != {"sha256": artifact["sha256"], "bytes": artifact["bytes"]}:
                raise CampaignError("CHECKPOINT_IDENTITY_CONFLICT")
            from uuid import uuid5, UUID
            artifact_id = str(uuid5(UUID(identifier(run_id)), "model_checkpoint:" + artifact["version_id"]))
            context = training_evaluation_context(
                checkpoint_artifact_id=artifact_id, protocol=protocol,
                dataset_version_id=session["dataset"]["dataset_version_id"],
                population=[s["sample"] for s in predictions["samples"]],
                input_contract=session["configuration"]["resolved"]["input_contract"])
            current = execute(c, "SELECT execution_parameters->:key FROM runs WHERE id=CAST(:id AS uuid) FOR UPDATE",
                              key=EVALUATION_CONTEXT_KEY, id=identifier(run_id)).scalar_one()
            if current is not None:
                if canonical(current) != canonical(context):
                    raise CampaignError("EVALUATION_CONTEXT_CONFLICT")
                return context
            execute(c, """INSERT INTO artifacts(id,run_id,artifact_type,name,path,mime_type,file_size_bytes,checksum,metadata)
                VALUES(CAST(:id AS uuid),CAST(:run AS uuid),'model_checkpoint',:name,:path,
                       'application/octet-stream',:bytes,:sha256,CAST(:metadata AS jsonb))""",
                id=artifact_id, run=identifier(run_id), name=Path(artifact["path"]).name,
                path=artifact["path"], bytes=artifact["bytes"], sha256=artifact["sha256"],
                metadata=canonical({"source": "e10_train", "role": "selected_checkpoint",
                                    "epoch": artifact["epoch"], "phase": artifact["phase"],
                                    "version_id": artifact["version_id"]}))
            execute(c, """UPDATE runs SET execution_parameters=execution_parameters ||
                    jsonb_build_object(CAST(:key AS text),CAST(:context AS jsonb)) WHERE id=CAST(:id AS uuid)""",
                key=EVALUATION_CONTEXT_KEY, context=canonical(context), id=identifier(run_id))
            return context

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
                "SELECT payload FROM train_execution_records AS record WHERE run_id=CAST(:id AS uuid) AND kind=:kind AND phase=:phase AND record_key=:key AND (to_jsonb(record)->>'event_id') IS NULL",
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
            if state in ('completed', 'verified'):
                if initial['attempt_id']:
                    execute(c, 'SELECT id FROM campaign_attempts WHERE id=CAST(:id AS uuid) FOR UPDATE',
                            id=str(initial['attempt_id'])).one()
                current = dict(execute(c, 'SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid) FOR UPDATE',
                                       id=identifier(run)).mappings().one())
                execute(c, 'SELECT id FROM runs WHERE id=CAST(:id AS uuid) FOR UPDATE', id=identifier(run)).one()
                if str(current['owner']) != identifier(owner) or current['attempt_id'] != initial['attempt_id']:
                    raise CampaignError('TRAIN_OWNER_FENCED')
                from .completion import TrainingCompletionValidator, is_e10_governed, CompletionError
                sources = self._completion_sources(c, run)
                if is_e10_governed(sources):
                    if current['state'] != ('active' if state == 'completed' else 'completed'):
                        raise CampaignError('TRAIN_TRANSITION_INVALID')
                    contract = TrainingCompletionValidator().validate(
                        sources, evidence if state == 'completed' else current['completion'], sealed=state == 'verified')
                    if state == 'completed':
                        if 'training_completion' in evidence:
                            raise CompletionError()
                        evidence = {**evidence, 'training_completion': contract.to_dict()}
                    else:
                        from ..campaigns.contracts import digest
                        from .artifacts import verify_checkpoint_file
                        if (not isinstance(evidence, dict) or evidence.get('status') != 'verified'
                                or evidence.get('training_completion_hash') != digest(contract.to_dict())
                                or evidence.get('records_hash') != contract.records_hash
                                or digest(evidence.get('artifact')) != contract.checkpoint_identity_hash
                                or canonical(evidence.get('selection')) != canonical(current['completion']['selection'])):
                            raise CompletionError()
                        verify_checkpoint_file(current, evidence['artifact'])
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

    @staticmethod
    def _completion_sources(c, run_id):
        from ..persistence.execution_record_readers import read_legacy_execution_records, read_result_events
        from ..results.errors import ResultPersistenceError
        from .completion import CompletionEvidence, InvalidEventStream
        params = {'id': identifier(run_id)}
        session = dict(execute(c, 'SELECT * FROM train_execution_sessions WHERE run_id=CAST(:id AS uuid)', **params).mappings().one())
        run = dict(execute(c, 'SELECT * FROM runs WHERE id=CAST(:id AS uuid)', **params).mappings().one())
        try:
            events = read_result_events(c, run_id)
        except ResultPersistenceError:
            raise InvalidEventStream() from None
        campaign_dataset = None
        if session['attempt_id']:
            campaign_dataset = execute(c, '''SELECT ec.dataset_snapshot FROM experimental_campaigns ec
                JOIN campaign_members m ON m.campaign_id=ec.id
                JOIN campaign_attempts a ON a.member_id=m.id WHERE a.id=CAST(:attempt AS uuid)''',
                attempt=str(session['attempt_id'])).scalar_one()
        projected = None
        if 'training_results' not in (run['parameters'] or {}) and execute(
                c, "SELECT to_regclass('run_clinical_metrics') IS NOT NULL").scalar_one():
            projected = execute(c, """SELECT e.source_event_id,e.threshold_used,e.threshold_source,
                    m.tn,m.fp,m.fn,m.tp,m.roc_auc_parasitized,m.pr_auc_parasitized
                FROM evaluations e JOIN run_clinical_metrics m ON m.evaluation_id=e.id
                WHERE e.run_id=CAST(:id AS uuid) AND e.evaluation_role='training_validation_final'""",
                **params).mappings().one_or_none()
            projected = dict(projected) if projected else None
        return CompletionEvidence(session, run, read_legacy_execution_records(c, run_id), events,
                                  campaign_dataset, projected)

    def scientific_completion(self, run_id):
        """Revalidate sealed E10 evidence; finish rechecks under transition locks."""
        from .completion import TrainingCompletionValidator, is_e10_governed, CompletionError
        with self.transaction(readonly=True) as c:
            sources = self._completion_sources(c, run_id)
            if not is_e10_governed(sources):
                return None
            if sources.session['state'] not in ('completed', 'verified'):
                raise CompletionError()
            return TrainingCompletionValidator().validate(sources, sources.session['completion'], sealed=True)

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
