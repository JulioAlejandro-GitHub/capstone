"""EXEC.1: fixed splits and identical script/module orchestration."""
import argparse
import json

from ..campaigns.contracts import CampaignError
from ..campaigns.repository import identifier
from ..execution.selection import select_trainings
from .contracts import require
from .repository import AssessmentRepository
from .service import explanation_spec, prepare, run


def parser(kind: str, batch: bool = False) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=f"EXEC.1 {kind.upper()}: Campaign-ID and/or Source-Training-Run-ID")
    p.add_argument("--campaign-id", type=identifier)
    p.add_argument("--source-training-run-id", type=identifier)
    p.add_argument("--model-version-id", type=identifier)
    p.add_argument("--dataset-version-id", type=identifier)
    p.add_argument("--model")
    p.add_argument("--dataset-dir")
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--threshold", default="auto", help="auto: recover the threshold recorded by TRAIN; clinical: require VAL calibration; or an explicit number")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--artifact-root", default="artifacts/assessments")
    if kind == "explain":
        p.add_argument("--method", choices=("gradcam", "lime", "shap"))
        p.add_argument("--layer")
        p.add_argument("--class-id", type=int, choices=(0, 1), default=1)
        p.add_argument("--num-samples", type=int)
        p.add_argument("--background-sample-id", action="append", default=[])
        p.add_argument("--evaluation-id")
    return p


def main(kind: str = "evaluate", batch: bool = False, argv: list[str] | None = None) -> int:
    p = parser(kind, batch)
    args = p.parse_args(argv)
    if not (args.campaign_id or args.source_training_run_id):
        p.error("Se requiere --campaign-id y/o --source-training-run-id")
    from ..execution.local_launch import bootstrap
    bootstrap()
    if args.inspect:
        return _execute(kind, args)
    from ..execution.global_gate import GlobalGate
    with GlobalGate("assessment-" + kind):
        return _execute(kind, args)


def _execute(kind: str, args: argparse.Namespace) -> int:
    repository = AssessmentRepository()
    try:
        items = select_trainings(repository, args.campaign_id, args.source_training_run_id)
        split, purpose = ("test", "final") if kind == "test" else ("val", "development")
        protocol = {"version": "exec1", "splits": [split], "purposes": [purpose],
                    "allowed_numeric_thresholds": [] if args.threshold in ("auto", "clinical") else [float(args.threshold)]}
        spec = explanation_spec(args.method, args.layer, args.class_id, args.num_samples,
                                args.background_sample_id) if kind == "explain" else None
        output = []
        for item in items:
            entry = {"source_training_run_id": str(item["id"])}
            try:
                require(item["status"] == "completed", "TRAIN_NOT_COMPLETED")
                proof = {}
                value = prepare(repository, training_run_id=str(item["id"]),
                    model_version_id=args.model_version_id, dataset_version_id=args.dataset_version_id,
                    model=args.model, dataset_dir=args.dataset_dir, split=split, purpose=purpose,
                    protocol=protocol, requested_threshold=args.threshold, seed=args.seed,
                    batch_size=args.batch_size, explanation=spec,
                    evaluation_id=getattr(args, "evaluation_id", None),
                    inspection=args.inspect, verification=proof)
                value["campaign_id"] = args.campaign_id or (str(item["campaign_id"]) if item["campaign_id"] else None)
                if args.inspect:
                    entry.update(inspection=value, inspection_verification=proof)
                else:
                    result = run(repository, value, args.artifact_root)
                    entry.update(attempt_id=str(result["id"]), state=result["state"], verification=result["verification"])
            except Exception as exc:
                entry.update(state="failed", error=str(exc) if isinstance(exc, CampaignError) else "ASSESSMENT_OPERATION_FAILED")
            output.append(entry)
        print(json.dumps(output, default=str))
        return 0 if all("inspection" in x or x.get("state") == "verified" for x in output) else 2
    except Exception as exc:
        print(str(exc) if isinstance(exc, CampaignError) else "ASSESSMENT_OPERATION_FAILED")
        return 2
