"""Child consumes only identifiers; retrieves and validates frozen DB configuration."""

import argparse
import os
import signal

from ..campaigns.contracts import CampaignError, canonical, member_configuration
from ..campaigns.repository import identifier
from .campaign import preflight
from .repository import ExecutionRepository


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True, type=identifier)
    p.add_argument("--owner", required=True, type=identifier)
    args = p.parse_args()
    repo = ExecutionRepository()
    try:
        session = repo.session(args.run_id)
        if str(session["owner"]) != args.owner or session["state"] != "active":
            raise CampaignError("TRAIN_OWNER_FENCED")
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
        from .train import train

        def stop(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, stop)
        train(repo, session, resolve_descriptor(session["configuration"]["model_id"]))
        return 0
    except (CampaignError, OSError):
        return 3
    except (Exception, KeyboardInterrupt):  # noqa: BLE001 -- sanitized child category
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
