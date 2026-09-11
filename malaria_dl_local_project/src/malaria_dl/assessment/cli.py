"""Explicit E6 command contract. Old scientific defaults are not accepted."""

import argparse
import json

from .contracts import AssessmentError, require
from .lineage import campaign_inventory
from .repository import AssessmentRepository
from .service import explanation_spec, prepare, run


def parser(kind, batch=False):
    p = argparse.ArgumentParser(description="E6 exact lineage; PostgreSQL results")
    if batch:
        p.add_argument("--campaign-id", required=True)
    else:
        p.add_argument("--source-training-run-id")
        p.add_argument("--model-version-id")
        p.add_argument("--recover-attempt-id")
    p.add_argument("--dataset-version-id")
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--split", choices=("train", "val", "test"))
    p.add_argument("--purpose", choices=("development", "final"))
    p.add_argument("--protocol", help="Explicit JSON object; never a result sidecar")
    p.add_argument("--threshold")
    p.add_argument("--seed", type=int)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--artifact-root", default="artifacts/assessments")
    if kind == "explain":
        p.add_argument("--method", choices=("gradcam", "lime", "shap"))
        p.add_argument("--layer")
        p.add_argument("--class-id", type=int, choices=(0, 1), default=1)
        p.add_argument("--num-samples", type=int)
        p.add_argument("--background-sample-id", action="append", default=[])
        if not batch:
            p.add_argument("--evaluation-id")
    return p


def main(kind="evaluate", batch=False, argv=None):
    args = parser(kind, batch).parse_args(argv)
    repository = AssessmentRepository()
    try:
        if not batch and args.recover_attempt_id:
            repository.recover(args.recover_attempt_id)
            print("ASSESSMENT_INTERRUPTED_RETRY_CREATES_NEW_ATTEMPT")
            return 0
        if batch:
            _campaign, items = campaign_inventory(
                repository, args.campaign_id, args.dataset_version_id
            )
            if args.inspect:
                print(
                    json.dumps(
                        {"campaign_id": args.campaign_id, "members": items}, default=str
                    )
                )
                return 0
        require(
            all(
                x is not None
                for x in (
                    args.split,
                    args.purpose,
                    args.protocol,
                    args.threshold,
                    args.seed,
                )
            ),
            "EXPLICIT_PROTOCOL_SPLIT_PURPOSE_THRESHOLD_SEED_REQUIRED",
        )
        protocol = json.loads(args.protocol)
        spec = None
        if kind == "explain":
            spec = explanation_spec(
                args.method,
                args.layer,
                args.class_id,
                args.num_samples,
                args.background_sample_id,
            )
        options = {
            "dataset_version_id": args.dataset_version_id,
            "split": args.split,
            "purpose": args.purpose,
            "protocol": protocol,
            "requested_threshold": args.threshold,
            "seed": args.seed,
            "batch_size": args.batch_size,
            "explanation": spec,
            "inspection": args.inspect,
        }
        if batch:
            output = []
            for item in items:
                if not item["eligible"]:
                    output.append(item)
                    continue
                value = prepare(
                    repository,
                    training_run_id=item["model"]["training_run_id"],
                    model_version_id=item["model"]["model_version_id"],
                    **options,
                )
                result = run(repository, value, args.artifact_root)
                repository.consume(args.campaign_id, item["member_id"], result)
                output.append(
                    {
                        "member_id": item["member_id"],
                        "attempt_id": str(result["id"]),
                        "state": result["state"],
                    }
                )
            print(json.dumps(output))
            return 0 if all(x.get("state") == "verified" for x in output) else 2
        value = prepare(
            repository,
            training_run_id=args.source_training_run_id,
            model_version_id=args.model_version_id,
            evaluation_id=getattr(args, "evaluation_id", None),
            **options,
        )
        if args.inspect:
            print(json.dumps(value))
            return 0
        result = run(repository, value, args.artifact_root)
        print(
            json.dumps(
                {
                    "attempt_id": str(result["id"]),
                    "state": result["state"],
                    "verification": result["verification"],
                }
            )
        )
        return 0 if result["state"] == "verified" else 2
    except Exception as exc:  # noqa: BLE001 -- public sanitized CLI boundary
        # Never print connection strings, SQL parameters, paths or raw driver tracebacks.
        code = (
            str(exc)
            if isinstance(exc, AssessmentError)
            else "ASSESSMENT_OPERATION_FAILED"
        )
        print(code)
        return 2
