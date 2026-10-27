"""TRAIN selection adapter: existing engines, new immutable run for every request.

``--campaign-id`` alone runs the frozen campaign through the campaign coordinator
(``execution.campaign``: claim -> worker -> E10 events), so attempts, members, the
registered checkpoint and the VAL evaluation projections exist for every member and
verified members are never retrained. ``--source-training-run-id`` creates one new
standalone run from that TRAIN's configuration (optionally recorded in a campaign).
"""
import argparse
import json
from types import SimpleNamespace
from typing import Any

from ..assessment.contracts import require
from ..campaigns.contracts import CampaignError
from ..campaigns.repository import identifier
from .repository import ExecutionRepository
from .selection import select_trainings


def training_plan(repository: ExecutionRepository, campaign_id: str | None,
                  training_run_id: str | None) -> list[dict[str, Any]]:
    require(bool(training_run_id), "SOURCE_TRAINING_RUN_REQUIRED")
    from ..pretrained.training import omit_training
    plan = []
    for source in select_trainings(repository, campaign_id, training_run_id):
        if omit_training(source.get("model_name"), source.get("model_metadata") or {}):
            continue
        configuration = source["configuration"]
        require(isinstance(configuration, dict)
                and {"model_id", "schema_version", "adapter_version", "resolved"} <= configuration.keys()
                and isinstance(configuration["resolved"], dict)
                and {"model", "optimizer", "execution", "selection", "input_contract", "recipe"}
                    <= configuration["resolved"].keys(), "SOURCE_TRAINING_CONFIGURATION_UNAVAILABLE")
        plan.append(dict(configuration=configuration, dataset_version_id=str(source["dataset_version_id"]),
                         campaign_id=campaign_id or (str(source["campaign_id"]) if source["campaign_id"] else None),
                         source_training_run_id=str(source["id"])))
    return plan


def campaign_arguments(campaign_id: str, mode: str | None) -> list[str]:
    """Coordinator arguments: --inspect/--plan resolve the frozen plan, --dry-run runs its preflight."""
    return ["--campaign-id", campaign_id] + {"inspect": ["--plan"], "plan": ["--plan"],
                                             "dry_run": ["--dry-run"]}.get(mode, [])


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(allow_abbrev=False, description="EXEC.1 TRAIN: runs a frozen campaign or creates a new run from a source TRAIN")
    p.add_argument("--campaign-id", type=identifier)
    p.add_argument("--source-training-run-id", type=identifier)
    mode = p.add_mutually_exclusive_group()
    for flag in ("--inspect", "--plan", "--dry-run"):
        mode.add_argument(flag, dest="mode", action="store_const", const=flag[2:].replace("-", "_"))
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if not (args.campaign_id or args.source_training_run_id):
        p.error("Se requiere --campaign-id y/o --source-training-run-id")
    from .local_launch import bootstrap
    bootstrap()
    try:
        if not args.source_training_run_id:
            from . import campaign
            return campaign.main(campaign_arguments(args.campaign_id, args.mode))
        plan = training_plan(ExecutionRepository(), args.campaign_id, args.source_training_run_id)
        if args.mode:
            print(json.dumps(plan, default=str))
            return 0
        from .train import standalone
        output = []
        for item in plan:
            entry = {"source_training_run_id": item["source_training_run_id"]}
            try:
                result = standalone(SimpleNamespace(
                    **item, model_configuration=item["configuration"], model=item["configuration"]["model_id"],
                    evaluate_best_on_test=False, threshold_output_json=None, dataset_dir=None,
                    data_source="physical", output_dir="outputs/train_runs"))
                entry.update(run_id=str(result["run_id"]), state=result["state"])
            except Exception as exc:
                entry.update(state="failed", error=str(exc) if isinstance(exc, CampaignError) else "TRAIN_OPERATION_FAILED")
            output.append(entry)
        print(json.dumps(output, default=str))
        return 0 if all(x["state"] == "verified" for x in output) else 2
    except CampaignError as exc:
        print(str(exc))
        return 2
