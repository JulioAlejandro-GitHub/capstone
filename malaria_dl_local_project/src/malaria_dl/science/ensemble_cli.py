"""E8 reuses the ensemble entrypoint and E7 science comparison; no inference runtime."""

import argparse
import json
from pathlib import Path

from .cli import provenance
from .comparison import read_evaluation, safe_reason
from .ensemble import evaluate, prepare, validate_configuration
from .ensemble_reporting import compare_results, export
from .ensemble_repository import (
    ComparisonRepository,
    ConfigurationRepository,
    EvaluationRepository,
    FailureRepository,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="E8 probability ensembles from explicit verified E6 VAL predictions"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    choice = check.add_mutually_exclusive_group(required=True)
    choice.add_argument("--configuration")
    choice.add_argument("--configuration-id")
    prep = sub.add_parser("prepare")
    prep.add_argument(
        "--request",
        required=True,
        help="Configuration request JSON, not predictions or results",
    )
    run = sub.add_parser("combine")
    run.add_argument("--configuration-id", required=True)
    comp = sub.add_parser("compare")
    comp.add_argument("--evaluation-id", action="append", default=[])
    comp.add_argument("--export-dir")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            v = (
                ConfigurationRepository().read_report(args.configuration_id)
                if args.configuration_id
                else validate_configuration(
                    json.loads(Path(args.configuration).read_text())
                )
            )
            print(
                json.dumps(
                    {"revision": v["revision"], "validation": "structure_and_hash_only"}
                )
            )
            return 0
        if args.command == "compare":
            return compare_command(args.evaluation_id, args.export_dir)
        configs = ConfigurationRepository()
        reader = lambda eid: read_evaluation(configs, eid)
        if args.command == "prepare":
            config = prepare(
                json.loads(Path(args.request).read_text()), reader, code=provenance()
            )
            cid = configs.persist_report(config)
            print(json.dumps({"configuration_id": cid, "revision": config["revision"]}))
            return 0
        config = configs.read_report(args.configuration_id)
        result = evaluate(config, reader, configuration_id=args.configuration_id)
        eid = EvaluationRepository().persist_report(result)
        print(
            json.dumps(
                {
                    "evaluation_id": eid,
                    "state": "exploratory",
                    "prediction_hash": result["prediction_hash"],
                }
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 -- failure evidence has no raw driver details
        reason = safe_reason(exc)
        if args.command in ("prepare", "combine"):
            try:
                FailureRepository().persist_report(
                    {
                        "schema": "ensemble_failure_e8_v1",
                        "state": "failed",
                        "command": args.command,
                        "configuration_id": getattr(args, "configuration_id", None),
                        "reason": reason,
                    }
                )
            except Exception:  # noqa: BLE001 -- retain original diagnostic
                print("E8_FAILURE_AUDIT_UNCONFIRMED")
        print("E8_FAILED: " + reason)
        return 2


def compare_command(evaluation_ids, export_dir=None):
    report = compare_results(evaluation_ids, EvaluationRepository().read_verified)
    repo = ComparisonRepository()
    rid = repo.persist_report(report)
    if export_dir:
        export(repo, rid, export_dir)
    print(json.dumps({"report_id": rid, "state": report["state"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
