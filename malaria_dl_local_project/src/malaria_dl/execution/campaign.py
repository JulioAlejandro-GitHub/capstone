"""Sequential process coordinator with transactional ownership and reconciliation."""

import argparse
import os
import platform
import signal
import socket
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import CampaignError, member_configuration
from ..campaigns.repository import identifier
from ..campaigns.service import planning_environment
from ..data.governed_dataset import (
    assert_run_dataset_snapshot_unchanged,
)
from ..persistence.dataset_evidence import verify_dataset_for_execution
from .artifacts import keras_loader, verify_session
from .repository import ExecutionRepository
from .schema import E10SchemaNotReady

# Keys of the campaign's reference environment. Compared only to REPORT runtime
# differences (plan, console); a difference is recorded on the run, never a barrier.
IDENTITY_KEYS = (
    "source_sha256",
    "python",
    "tensorflow",
    "packages",
    "determinism_environment",
)


def runtime_environment(environment=None):
    """What actually executes this TRAIN; stored as runs.execution_parameters.runtime_environment."""
    return {
        **(environment or planning_environment)(),
        "execution_mode": "docker" if Path("/.dockerenv").exists() else "local_python",
        "platform": platform.system(),
        "machine": platform.machine(),
        "host": socket.gethostname(),
    }


def runtime_differences(row, current):
    return sorted(k for k in IDENTITY_KEYS if current.get(k) != row["environment"].get(k))


def preflight(
    repository,
    row,
    root,
    verifier=verify_dataset_for_execution,
):
    """Protects the experiment: dataset, frozen configuration, TEST isolation, storage."""
    if row["state"] not in ("frozen", "active", "paused", "finalized"):
        raise CampaignError("CAMPAIGN_NOT_FROZEN")
    snapshot = verifier(
        str(row["dataset_version_id"]),
        expected_evidence_id=str(row["dataset_evidence_id"]),
        consumer="campaign.execute",
        required_splits=("train", "val"),
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
    log=lambda *_: None,
):
    """Sequential: claim, TRAIN, verify, next. A failed TRAIN stops the loop (exit 1)
    without claiming another member; rerunning retries it within the frozen budget."""
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
    runtime = runtime_environment()
    # First preflight is outside the systemic handler: a wrong dataset/config stops
    # with NO mutation (no pause, no attempt). Later rechecks pause, as before.
    row = runtime_row()
    check(repository, row, root)
    log("Preflight .......... OK (dataset, configuración congelada, TEST bloqueado, artifacts)")
    try:
        if resume:
            reconcile(repository, row, loader)
            repository.resume(campaign_id)
            if row["state"] == "finalized":
                summary = repository.summary(campaign_id)
                return (0 if summary["matrix_complete"] else 2), summary
        elif row["state"] not in ("frozen", "active"):
            raise CampaignError("USE_RESUME_FOR_STARTED_CAMPAIGN")
        checked = True
        while True:
            if repository.get(campaign_id)['state'] == 'paused':
                return 0, repository.summary(campaign_id)
            if gate is not None:
                gate.require_healthy()
            # Common integrity is rechecked before every claim, not only the first.
            if not checked:
                check(repository, runtime_row(), root)
            checked = False
            session = repository.claim(
                campaign_id, owner, socket.gethostname(), os.getpid(), root,
                **({'revision_id': revision_id} if revision_id else {}),
                observed_runtime=runtime,
            )
            if session is None:
                break
            if gate is not None:
                gate.active_run = str(session['run_id'])
            log(session)
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
                    log(repository.session(session["run_id"]))
                    return 1, repository.summary(campaign_id)
                if gate is not None:
                    gate.require_healthy()
                check(repository, runtime_row(), root)
                evidence = verify_session(repository, current, loader)
                repository.finish(session["run_id"], owner, "verified", evidence)
                if gate is not None:
                    gate.outcome(True)
                log(repository.session(session["run_id"]))
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
        log(exc)
        return (130 if isinstance(exc, KeyboardInterrupt) else 3), repository.summary(campaign_id)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Execute a frozen PostgreSQL campaign; no scientific overrides. "
        "Normal use: --campaign-id only (pending members run sequentially; an "
        "interrupted or paused campaign is resumed automatically)."
    )
    p.add_argument("--campaign-id", required=True, type=identifier)
    p.add_argument(
        "--dataset-version-id",
        type=identifier,
        help="Optional assertion only; the campaign's persisted dataset_version_id is the "
        "single source of truth and a different value is rejected",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--plan",
        action="store_true",
        help="Resolve the frozen campaign into its execution plan and report readiness; "
        "read-only, never reserves an attempt nor starts TRAIN",
    )
    mode.add_argument("--inspect", action="store_true")
    mode.add_argument("--resume", action="store_true",
                      help="Accepted for compatibility; resuming is now the default")
    mode.add_argument("--result", action="store_true")
    mode.add_argument('--dry-run', action='store_true',
                      help="Full preflight and next member; no attempt, no TRAIN, no DB writes")
    p.add_argument("--artifact-root", default=None,
                   help="Default: <project>/outputs/campaign_runs")
    p.add_argument('--technical-revision-id', type=identifier)
    p.add_argument('--revision-proposal', type=Path)
    return p.parse_args(argv)


def describe(configuration):
    resolved = configuration.get("resolved", {})
    return " / ".join(str(x) for x in (
        configuration.get("model_id"),
        resolved.get("optimizer", {}).get("name"),
        "seed %s" % resolved.get("execution", {}).get("seed"),
    ))


def console(row):
    """Human progress lines; never prints credentials or the DATABASE_URL."""
    total = len(row["members"])
    done = [sum(m["state"] == "verified" for m in row["members"])]

    def log(item):
        if isinstance(item, str):
            print(item)
        elif isinstance(item, BaseException):
            print(f"ERROR {type(item).__name__}: {item}", file=sys.stderr)
        elif item["state"] == "active":
            print(f"\n[{done[0] + 1}/{total}] {describe(item['configuration'])}\nRun: {item['run_id']}",
                  flush=True)
        elif item["state"] == "verified":
            done[0] += 1
            print("TRAIN verified.", flush=True)
        else:
            print(f"TRAIN {item['state']}: {item.get('cause')} (run {item['run_id']}). "
                  "No se inicia otro miembro; re-ejecute el mismo comando para reintentar.",
                  file=sys.stderr, flush=True)
    return log


def dry_run(repository, campaign_id, root):
    """Everything execution checks before a claim, without claiming."""
    from ..data.governed_dataset import resolve_governed_dataset
    from .global_gate import status
    repository.preflight_e10_schema()
    row = repository.get(campaign_id)
    # Same integrity verification, without persisting a dataset evidence row.
    preflight(repository, row, root, verifier=lambda version, **kw: resolve_governed_dataset(
        version, required_splits=kw["required_splits"]))
    budget = row["protocol"]["budget"]["max_attempts_per_member"]
    eligible = sorted(
        (m for m in row["members"] if m["state"] in ("pending", "failed", "interrupted")
         and sum(a["member_id"] == m["id"] for a in row["attempts"]) < budget),
        key=lambda m: (m["state"] != "pending", m["position"]))
    gate = status(repository)
    nxt = eligible[0] if eligible else None
    return {"campaign_id": str(row["id"]), "state": row["state"], "writes": 0,
            "eligible_members": len(eligible), "global_execution": gate,
            "next_member": None if nxt is None else {
                "position": nxt["position"], "seed": nxt["seed"],
                "configuration": describe(member_configuration(row["contract"]["matrix"][
                    "configurations"][nxt["configuration_hash"]]["configuration"], nxt["seed"]))},
            "runtime_differences": runtime_differences(row, runtime_environment()),
            "execution_ready": bool(eligible) and gate["available"]}


def apply_determinism(row):
    """The campaign's determinism variables reach every TRAIN child process."""
    for key, value in (row["environment"].get("determinism_environment") or {}).items():
        if value is not None:
            os.environ.setdefault(key, str(value))


def main(argv=None):
    import json
    from ..common.paths import PROJECT_ROOT

    args = parse_args(argv)
    root = Path(args.artifact_root) if args.artifact_root else PROJECT_ROOT / "outputs" / "campaign_runs"
    repo = ExecutionRepository()
    if args.plan:
        from ..campaigns.plan import execution_readiness, resolve_plan
        row = repo.get(args.campaign_id, args.dataset_version_id)
        plan = resolve_plan(row)
        plan["execution_readiness"] = execution_readiness(repo, row)
        print(json.dumps(plan, sort_keys=True, default=str))
        return 0
    if args.inspect or args.result:
        repo.get(args.campaign_id, args.dataset_version_id)
        print(json.dumps(repo.summary(args.campaign_id), sort_keys=True))
        return 0
    if args.dataset_version_id is None:
        # Campaign mode: the dataset comes only from the persisted campaign. An explicit
        # --dataset-version-id stays an assertion checked by repository.get.
        args.dataset_version_id = str(repo.get(args.campaign_id)["dataset_version_id"])
    if args.dry_run and (args.technical_revision_id or args.revision_proposal):
        from .controlled import queue_dry_run
        proposal = json.loads(args.revision_proposal.read_text()) if args.revision_proposal else None
        print(json.dumps(queue_dry_run(repo, args.campaign_id, args.dataset_version_id,
                                      args.technical_revision_id, proposal)))
        return 0
    if args.dry_run:
        print(json.dumps(dry_run(repo, args.campaign_id, root), sort_keys=True, default=str, indent=1))
        return 0
    if args.revision_proposal is not None:
        raise CampaignError('PROPOSAL_ALLOWED_ONLY_IN_DRY_RUN')
    from .global_gate import GlobalGate
    repo.preflight_e10_schema()
    row = repo.get(args.campaign_id, args.dataset_version_id)
    apply_determinism(row)
    runtime = runtime_environment()
    differing = runtime_differences(row, runtime)
    print("Capstone TRAIN\n")
    print(f"Campaign : {row['id']}\nDataset  : {row['dataset_version_id']}\n"
          f"Mode     : {runtime['execution_mode']} ({runtime['platform']} {runtime['machine']})\n"
          f"State    : {row['state']}\nMembers  : {len(row['members'])}\n"
          f"Pending  : {sum(m['state'] != 'verified' for m in row['members'])}\n")
    if differing:
        print("Runtime ............ difiere de la referencia de la campaña en "
              f"{', '.join(differing)}; se registra en cada run (runtime_environment)")
    with GlobalGate('campaign'):
        print("Global gate ........ ACQUIRED", flush=True)
        code, summary = execute_campaign(
            repo, args.campaign_id, root,
            resume=True, dataset=args.dataset_version_id,
            revision_id=args.technical_revision_id, log=console(row),
        )
    m = summary["members"]
    print(f"\nCampaign state: {summary['state']} — verified {m['verified']}/{summary['expected']}, "
          f"failed {m['failed']}, interrupted {m['interrupted']}, pending {m['pending']}")
    return code
