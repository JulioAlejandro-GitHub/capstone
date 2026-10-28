"""Child consumes only identifiers; retrieves and validates frozen DB configuration."""

import argparse
import os
import re
import signal
import sys
from uuid import UUID

from ..campaigns.contracts import CampaignError, canonical, member_configuration
from ..campaigns.repository import identifier
from .campaign import preflight
from .repository import ExecutionRepository
from .composition import build_docker_run_reporter
from .contracts import ExecutionContext, ExecutionMode, RunEventType
from .emitter import RunEventEmitter


def docker_context(session, row, attempt, member) -> ExecutionContext:
    """Identity from the reserved DB session and its validated frozen lineage."""
    if (session['state'] != 'active' or attempt['state'] != 'active'
            or member['state'] != 'active' or row['state'] not in ('active', 'paused')
            or str(attempt['id']) != str(session['attempt_id'])
            or str(attempt['training_run_id']) != str(session['run_id'])
            or str(attempt['member_id']) != str(member['id'])
            or str(member['campaign_id']) != str(row['id'])
            or str(row['dataset_version_id']) != session['dataset']['dataset_version_id']):
        raise CampaignError('CHILD_FROZEN_IDENTITY_CONFLICT')
    config = session['configuration']
    return ExecutionContext(
        run_id=UUID(str(session['run_id'])), owner=UUID(str(session['owner'])),
        attempt_id=UUID(str(session['attempt_id'])), 
        # execution_mode=ExecutionMode.DOCKER,
        execution_mode=(
            ExecutionMode.DOCKER
            if os.path.exists("/.dockerenv")
            else ExecutionMode.LOCAL_PYTHON
        ),
        dataset_version_id=UUID(session['dataset']['dataset_version_id']),
        model_id=config['model_id'], adapter_version=config['adapter_version'],
        campaign_id=UUID(str(row['id'])), member_id=UUID(str(member['id'])),
        configuration_hash=member['configuration_hash'], contract_hash=row['contract_hash'],
    )


def run_scientific_train(repository, session, descriptor, event_emitter: RunEventEmitter):
    """Keep the original failure and let the coordinator own legacy failure states."""
    from .train import train

    try:
        train(repository, session, descriptor, event_emitter=event_emitter)
    except BaseException as original:
        if event_emitter.pending is None and not event_emitter.closed:
            try:
                # The reporter rechecks current authorization under DB locks.
                # Do not copy arbitrary exception messages into scientific evidence.
                event_emitter.emit(RunEventType.TRAINING_FAILED, {"cause": "TRAIN_RUNTIME_FAILED"})
            except BaseException:
                original.add_note('E10_FAILURE_EVENT_UNCONFIRMED')
        raise


def main():
    from .global_gate import attach_worker
    attach_worker()
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True, type=identifier)
    p.add_argument("--owner", required=True, type=identifier)
    args = p.parse_args()
    repo = ExecutionRepository()
    try:
        session = repo.session(args.run_id)
        if str(session["owner"]) != args.owner or session["state"] != "active":
            raise CampaignError("TRAIN_OWNER_FENCED")
        repo.preflight_result_events(session['run_id'])
        repo.child_started(args.run_id, args.owner, os.getpid())
        from ..campaigns.repository import execute

        with repo.transaction(readonly=True) as c:
            cid = execute(
                c,
                "SELECT m.campaign_id FROM campaign_members m JOIN campaign_attempts a ON a.member_id=m.id WHERE a.id=CAST(:id AS uuid) AND a.training_run_id=CAST(:run AS uuid)",
                id=str(session["attempt_id"]),
                run=args.run_id,
            ).scalar_one()
        row = repo.get(cid)
        from .controlled import effective_row
        row = effective_row(repo, row, session)
        attempt = next(
            a for a in row["attempts"] if str(a["id"]) == str(session["attempt_id"])
        )
        member = next(m for m in row["members"] if m["id"] == attempt["member_id"])
        expected = member_configuration(
            row["contract"]["matrix"]["configurations"][member["configuration_hash"]][
                "configuration"
            ],
            member["seed"],
        )
        if (
            canonical(expected) != canonical(session["configuration"])
            or session["dataset"] != row["dataset_snapshot"]
            or session["environment"] != row["environment"]
        ):
            raise CampaignError("CHILD_FROZEN_IDENTITY_CONFLICT")
        preflight(repo, row, os.path.dirname(session["artifact_root"]))
        from ..models.registry import resolve_descriptor
        from .global_gate import token

        context = docker_context(session, row, attempt, member)
        reporter = build_docker_run_reporter(context, execution_token=UUID(token()))
        event_emitter = RunEventEmitter(reporter, run_id=context.run_id, attempt_id=context.attempt_id)

        def stop(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, stop)
        run_scientific_train(repo, session, resolve_descriptor(session["configuration"]["model_id"]), event_emitter)
        return 0
    except (CampaignError, OSError) as exc:
        # Systemic stop: the coordinator pauses the campaign. CampaignError messages are
        # closed codes; an OSError keeps only its class and errno.
        code = str(exc) if isinstance(exc, CampaignError) else f"errno={getattr(exc, 'errno', None)}"
        print(f"TRAIN_CHILD_SYSTEMIC {type(exc).__name__}[{code}] " + failure_signature(exc),
              file=sys.stderr, flush=True)
        return 3
    except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 -- sanitized child category
        print("TRAIN_CHILD_FAILED " + failure_signature(exc), file=sys.stderr, flush=True)
        return 2


def failure_signature(exc, depth=5):
    """Exception classes along the chain plus database guard codes; never free-text messages."""
    parts, seen = [], set()
    while exc is not None and len(parts) < depth and id(exc) not in seen:
        seen.add(id(exc))
        part = type(exc).__name__
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        code = getattr(diag, "message_primary", None)
        if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", code):
            part += f"[{code}]"
        parts.append(part)
        exc = exc.__cause__ or exc.__context__
    return " <- ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
