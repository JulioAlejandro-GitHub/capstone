"""Sequential process coordinator with transactional ownership and reconciliation."""

import argparse
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import CampaignError
from ..campaigns.repository import identifier
from ..campaigns.service import planning_environment
from ..data.governed_dataset import (
    assert_run_dataset_snapshot_unchanged,
)
from ..persistence.dataset_evidence import verify_dataset_for_execution
from .artifacts import keras_loader, verify_session
from .repository import ExecutionRepository
from .schema import E10SchemaNotReady

IDENTITY_KEYS = (
    "source_sha256",
    "python",
    "tensorflow",
    "packages",
    "determinism_environment",
)


def preflight(
    repository,
    row,
    root,
    verifier=verify_dataset_for_execution,
    environment=planning_environment,
):
    if row["state"] not in ("frozen", "active", "paused", "finalized"):
        raise CampaignError("CAMPAIGN_NOT_FROZEN")
    current = environment()
    if any(current.get(k) != row["environment"].get(k) for k in IDENTITY_KEYS):
        raise CampaignError("FROZEN_CODE_ENVIRONMENT_CONFLICT_NEW_CAMPAIGN_REQUIRED")
    snapshot = verifier(
        str(row["dataset_version_id"]),
        expected_evidence_id=str(row["dataset_evidence_id"]),
        consumer="campaign.execute",
    )
    assert_run_dataset_snapshot_unchanged(snapshot, row["dataset_snapshot"])
    from ..models.registry import resolve_descriptor

    for item in row["contract"]["matrix"]["configurations"].values():
        config = item["configuration"]
        descriptor = resolve_descriptor(config["model_id"])
        frozen = next(
            d
            for d in row["contract"]["matrix"]["registry"]
            if d["id"] == config["model_id"]
        )
        if (
            descriptor.version != config["adapter_version"]
            or descriptor.adapter != frozen["adapter"]
        ):
            raise CampaignError("FROZEN_ADAPTER_CONFLICT")
        if config["resolved"]["execution"]["evaluate_best_on_test"] is not False:
            raise CampaignError("TEST_FORBIDDEN")
    repository.preflight()
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Capacity probe is neither a results file nor an alternate ledger.
    import tempfile

    with tempfile.TemporaryFile(dir=root) as probe:
        probe.write(b"capacity")
        probe.flush()
        os.fsync(probe.fileno())


def dead_local(session):
    if session["host"] != socket.gethostname():
        return False
    for pid in (session["parent_pid"], session["child_pid"]):
        if pid is None:
            continue
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            return False
        return False
    return True


def reconcile(repository, row, loader=keras_loader):
    for attempt in row["attempts"]:
        if not attempt["training_run_id"]:
            if attempt["state"] == "active":
                raise CampaignError("ACTIVE_LEGACY_ATTEMPT_REQUIRES_DIAGNOSIS")
            continue
        session = repository.session(attempt["training_run_id"])
        from .global_gate import CURRENT
        if CURRENT.get() is not None:
            CURRENT.get().active_run = str(session['run_id'])
        if session["state"] == "verified":
            verify_session(repository, session, loader)
        elif session["state"] == "completed":
            evidence = verify_session(repository, session, loader)
            repository.finish(session["run_id"], session["owner"], "verified", evidence)
        elif session["state"] == "active":
            if not dead_local(session):
                raise CampaignError("ACTIVE_OWNER_NOT_PROVEN_DEAD")
            repository.finish(
                session["run_id"],
                session["owner"],
                "interrupted",
                cause="OWNER_AND_CHILD_PROVEN_ABSENT",
            )


def run_child(session, repository):
    process = None
    from .global_gate import CURRENT
    gate = CURRENT.get()
    if gate is None:
        raise CampaignError('GLOBAL_EXECUTION_OWNER_REQUIRED')
    gate.require_healthy()
    gate.active_run = str(session['run_id'])
    read_fd, write_fd = os.pipe()

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    previous = {
        s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-m",
                "src.malaria_dl.execution.worker",
                "--run-id",
                str(session["run_id"]),
                "--owner",
                str(session["owner"]),
            ],
            start_new_session=True,
            pass_fds=(read_fd,),
            env={**os.environ, 'CAPSTONE_EXECUTION_TOKEN': gate.owner,
                 'CAPSTONE_START_FD': str(read_fd)},
            cwd=Path(__file__).resolve().parents[3],
        )
        gate.child_started(process.pid)
        os.write(write_fd, b'1')
        code = process.wait()
        gate.after_wait(process.pid, code, 'TRAIN')
        return code
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        for s, handler in previous.items():
            signal.signal(s, handler)
        os.close(read_fd)
        os.close(write_fd)


def execute_campaign(
    repository,
    campaign_id,
    root,
    *,
    resume=False,
    dataset=None,
    check=preflight,
    launch=run_child,
    loader=keras_loader,
    revision_id=None,
):
    from .global_gate import CURRENT
    from .controlled import technical_row
    gate = CURRENT.get()
    def runtime_row():
        original = repository.get(campaign_id, dataset)
        return technical_row(repository, original, revision_id) if revision_id else original
    if gate is not None and loader is keras_loader:
        from .process_verification import isolated_keras_loader
        loader = isolated_keras_loader
    # Outside the systemic-failure handler: incompatibility must not pause or
    # reconcile an existing campaign, nor consume a reservation.
    repository.preflight_e10_schema()
    owner = str(uuid4())
    try:
        row = runtime_row()
        check(repository, row, root)
        if resume:
            reconcile(repository, row, loader)
            repository.resume(campaign_id)
            if row["state"] == "finalized":
                summary = repository.summary(campaign_id)
                return (0 if summary["matrix_complete"] else 2), summary
        elif row["state"] not in ("frozen", "active"):
            raise CampaignError("USE_RESUME_FOR_STARTED_CAMPAIGN")
        while True:
            if repository.get(campaign_id)['state'] == 'paused':
                return 0, repository.summary(campaign_id)
            if gate is not None:
                gate.require_healthy()
            # Common integrity is rechecked before every claim, not only the first.
            check(repository, runtime_row(), root)
            session = repository.claim(
                campaign_id, owner, socket.gethostname(), os.getpid(), root,
                **({'revision_id': revision_id} if revision_id else {}),
            )
            if session is None:
                break
            if gate is not None:
                gate.active_run = str(session['run_id'])
            try:
                code = launch(session, repository)
                current = repository.session(session["run_id"])
                if code != 0 or current["state"] != "completed":
                    if current['state'] == 'active':
                        repository.finish(
                            session["run_id"], owner, "failed",
                            cause=(f"CHILD_EXIT_{code}" if code != 0
                                   else "CHILD_EXIT_0_INCOMPLETE_RESULTS"),
                        )
                    elif current['state'] not in ('failed', 'interrupted'):
                        raise CampaignError('CHILD_TERMINAL_STATE_CONFLICT')
                    if gate is not None:
                        gate.outcome(False)
                    if code == 3:
                        raise CampaignError("CHILD_SYSTEMIC_FAILURE")
                    continue
                if gate is not None:
                    gate.require_healthy()
                check(repository, runtime_row(), root)
                evidence = verify_session(repository, current, loader)
                repository.finish(session["run_id"], owner, "verified", evidence)
                if gate is not None:
                    gate.outcome(True)
            except KeyboardInterrupt:
                repository.finish(
                    session["run_id"],
                    owner,
                    "interrupted",
                    cause="PARENT_INTERRUPTED_CHILD_REAPED",
                )
                raise
            except Exception as original:
                try:
                    current = repository.session(session['run_id'])
                    if current['state'] == 'active':
                        repository.finish(session['run_id'], owner, 'failed',
                                          cause='CHILD_CONTROL_' + type(original).__name__.upper())
                    if gate is not None:
                        gate.event('control_failure', run_id=str(session['run_id']),
                                   exception_type=type(original).__name__)
                except Exception:
                    original.add_note('CHILD_FAILURE_RECORD_UNCONFIRMED')
                raise
        repository.finalize_terminal(campaign_id)
        summary = repository.summary(campaign_id)
        return (0 if summary["matrix_complete"] else 2), summary
    except E10SchemaNotReady:
        raise
    except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 -- unknown failures are systemic, never success
        repository.pause(campaign_id, "SYSTEMIC_" + type(exc).__name__.upper())
        return 3, repository.summary(campaign_id)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Execute a frozen PostgreSQL campaign; no scientific overrides"
    )
    p.add_argument("--campaign-id", required=True, type=identifier)
    p.add_argument(
        "--dataset-version-id",
        type=identifier,
        help="Assertion only; must match campaign",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--result", action="store_true")
    mode.add_argument('--dry-run', action='store_true')
    p.add_argument("--artifact-root", default="outputs/campaign_runs")
    p.add_argument('--technical-revision-id', type=identifier)
    p.add_argument('--revision-proposal', type=Path)
    return p.parse_args(argv)


def main(argv=None):
    import json

    args = parse_args(argv)
    repo = ExecutionRepository()
    if args.inspect or args.result:
        repo.get(args.campaign_id, args.dataset_version_id)
        print(json.dumps(repo.summary(args.campaign_id), sort_keys=True))
        return 0
    if args.dataset_version_id is None:
        raise CampaignError('EXPLICIT_DATASET_REQUIRED')
    if args.dry_run:
        from .controlled import queue_dry_run
        proposal = json.loads(args.revision_proposal.read_text()) if args.revision_proposal else None
        if proposal is None and args.technical_revision_id is None:
            raise CampaignError('EXPLICIT_TECHNICAL_REVISION_REQUIRED')
        print(json.dumps(queue_dry_run(repo, args.campaign_id, args.dataset_version_id,
                                      args.technical_revision_id, proposal)))
        return 0
    if args.revision_proposal is not None:
        raise CampaignError('PROPOSAL_ALLOWED_ONLY_IN_DRY_RUN')
    from .global_gate import GlobalGate
    repo.preflight_e10_schema()
    with GlobalGate('campaign'):
        code, summary = execute_campaign(
            repo, args.campaign_id, args.artifact_root,
            resume=args.resume, dataset=args.dataset_version_id,
            revision_id=args.technical_revision_id,
        )
    print(json.dumps(summary, sort_keys=True))
    return code
