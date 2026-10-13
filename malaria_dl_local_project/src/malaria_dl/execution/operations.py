"""TRAIN selection adapter: existing engine, new immutable run for every request."""
import argparse
import json
from types import SimpleNamespace
from typing import Any

from ..assessment.contracts import require
from ..campaigns.contracts import CampaignError, member_configuration
from ..campaigns.repository import identifier
from .repository import ExecutionRepository
from .selection import select_trainings


def training_plan(repository: ExecutionRepository, campaign_id: str | None,
                  training_run_id: str | None) -> list[dict[str, Any]]:
    if training_run_id:
        source = select_trainings(repository, campaign_id, training_run_id)[0]
        configuration = source["configuration"]
        require(isinstance(configuration, dict)
                and {"model_id", "schema_version", "adapter_version", "resolved"} <= configuration.keys()
                and isinstance(configuration["resolved"], dict)
                and {"model", "optimizer", "execution", "selection", "input_contract", "recipe"}
                    <= configuration["resolved"].keys(), "SOURCE_TRAINING_CONFIGURATION_UNAVAILABLE")
        return [dict(configuration=source["configuration"], dataset_version_id=str(source["dataset_version_id"]),
                     campaign_id=campaign_id or (str(source["campaign_id"]) if source["campaign_id"] else None),
                     source_training_run_id=str(source["id"]))]
    require(bool(campaign_id), "CAMPAIGN_OR_SOURCE_TRAINING_RUN_REQUIRED")
    campaign = repository.get(campaign_id)
    configs = {c["configuration_hash"]: c["configuration"] for c in campaign["configurations"]}
    require(bool(campaign["members"]), "CAMPAIGN_CONFIGURATION_UNAVAILABLE")
    return [dict(configuration=member_configuration(configs[m["configuration_hash"]], m["seed"]),
                 dataset_version_id=str(campaign["dataset_version_id"]), campaign_id=str(campaign["id"]),
                 source_training_run_id=None) for m in campaign["members"]]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(allow_abbrev=False, description="EXEC.1 TRAIN: creates new runs from campaign configurations or a source TRAIN")
    p.add_argument("--campaign-id", type=identifier)
    p.add_argument("--source-training-run-id", type=identifier)
    p.add_argument("--dry-run", "--plan", "--inspect", dest="inspect", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if not (args.campaign_id or args.source_training_run_id):
        p.error("Se requiere --campaign-id y/o --source-training-run-id")
    from .local_launch import bootstrap
    bootstrap()
    try:
        plan = training_plan(ExecutionRepository(), args.campaign_id, args.source_training_run_id)
        if args.inspect:
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
