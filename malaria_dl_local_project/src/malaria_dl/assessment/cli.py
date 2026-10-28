"""Public scientific CLI: fixed splits and persisted TRAIN defaults."""
import argparse
import json

from ..campaigns.contracts import CampaignError
from ..campaigns.repository import identifier
from ..execution.selection import select_trainings
from .contracts import require
from .repository import AssessmentRepository
from .service import explanation_spec, prepare, run


def seed_arg(value: str) -> int | str:
    return "auto" if value == "auto" else int(value)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Debe ser un entero positivo")
    return number


def image_limit(value: str) -> int | str:
    return "all" if value == "all" else positive_int(value)


def internal_samples(value: str) -> int:
    number = int(value)
    if not 1000 <= number <= 5000:
        raise argparse.ArgumentTypeError("--num-samples requiere un entero entre 1000 y 5000")
    return number


def framework(item) -> str | None:
    """Engine family of the item's model; None when no implementation describes it."""
    from ..models.registry import resolve_descriptor

    try:
        return resolve_descriptor(item.get("model_name"), executable=False).framework
    except ValueError:
        return None


def not_convolutional(item) -> bool:
    return framework(item) == "pytorch_openclip"


def parser(kind: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(allow_abbrev=False, description=f"EXEC.1 {kind.upper()}: Campaign-ID and/or Source-Training-Run-ID")
    p.add_argument("--campaign-id", type=identifier)
    p.add_argument("--source-training-run-id", type=identifier)
    p.add_argument("--dataset-version-id", type=identifier,
                   help="Required for a logical (zero-shot) TRAIN; otherwise must equal the TRAIN dataset")
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--threshold", default="auto", help="auto: recover the threshold recorded by TRAIN; clinical: require VAL calibration; or an explicit number")
    p.add_argument("--seed", type=seed_arg, default="auto",
                   help="auto: TRAIN profile; a logical (zero-shot) TRAIN requires an explicit integer")
    p.add_argument("--batch-size", type=positive_int, default=None,
                   help="Defaults to the TRAIN profile; required for a logical (zero-shot) TRAIN")
    if kind == "explain":
        p.add_argument("--method", choices=("gradcam", "lime", "shap"), default="gradcam")
        p.add_argument("--layer")
        p.add_argument("--class-id", type=int, choices=(0, 1), default=1)
        p.add_argument("--num-samples", type=internal_samples, help="LIME/SHAP: muestras internas (1000–5000); no limita imágenes")
        selection = p.add_mutually_exclusive_group()
        selection.add_argument("--max-images", type=image_limit, default="all")
        selection.add_argument("--sample-id", type=identifier)
        p.add_argument("--background-sample-id", action="append", type=identifier, default=[])
    return p


def main(kind: str = "evaluate", argv: list[str] | None = None) -> int:
    p = parser(kind)
    args = p.parse_args(argv)
    if not (args.campaign_id or args.source_training_run_id):
        p.error("Se requiere --campaign-id y/o --source-training-run-id")
    if kind == "explain":
        try:
            explanation_spec(args.method, args.layer, args.class_id, args.num_samples, args.background_sample_id)
        except CampaignError as exc:
            p.error(str(exc))
    from ..execution.local_launch import bootstrap
    bootstrap()
    if args.inspect:
        return _execute(kind, args)
    from ..execution.global_gate import GlobalGate
    try:
        with GlobalGate("assessment-" + kind):
            return _execute(kind, args)
    except CampaignError as exc:
        print(f"STOP {exc}")
        return 2


def _execute(kind: str, args: argparse.Namespace) -> int:
    repository = AssessmentRepository()
    try:
        items = select_trainings(repository, args.campaign_id, args.source_training_run_id)
        output = []
        for item in items:
            entry = {"source_training_run_id": str(item["id"])}
            if args.campaign_id and kind == "explain" and args.method == "gradcam" and not_convolutional(item):
                # A campaign mixes CNNs and ViTs: Grad-CAM is skipped, never failed, on a ViT.
                entry.update(state="skipped", reason="GRADCAM_NOT_APPLICABLE_VIT")
            else:
                python = item_python(item)
                entry.update(_delegate(kind, args, item, python) if python and not args.inspect
                             else _assess(kind, args, item, repository))
            output.append(entry)
        print(json.dumps(output, default=str))
        return 0 if all("inspection" in x or x.get("state") in ("verified", "skipped") for x in output) else 2
    except Exception as exc:
        print(str(exc) if isinstance(exc, CampaignError) else "ASSESSMENT_OPERATION_FAILED")
        return 2


def item_python(item) -> str | None:
    """Interpreter of the item's framework environment when it is not this one (local only)."""
    import sys

    from ..execution.local_launch import framework_python

    family = framework(item)
    python = framework_python(family, sys.executable) if family else sys.executable
    return None if python == sys.executable else python


def _assess(kind: str, args: argparse.Namespace, item: dict, repository) -> dict:
    split, purpose = ("test", "final") if kind == "test" else ("val", "development")
    protocol = {"version": "exec1", "splits": [split], "purposes": [purpose],
                "allowed_numeric_thresholds": [] if args.threshold in ("auto", "clinical") else [float(args.threshold)]}
    spec = explanation_spec(args.method, args.layer, args.class_id, args.num_samples,
                            args.background_sample_id) if kind == "explain" else None
    # Evaluation-only (zero-shot) members of a campaign take its dataset, seed and batch.
    campaign_only = bool(args.campaign_id and item.get("evaluation_only"))
    try:
        require(item["status"] == "completed", "TRAIN_NOT_COMPLETED")
        proof = {}
        value = prepare(repository, training_run_id=str(item["id"]),
            dataset_version_id=args.dataset_version_id or (
                str(item["campaign_dataset_version_id"]) if campaign_only else None),
            split=split, purpose=purpose,
            protocol=protocol, requested_threshold=args.threshold,
            seed=item["campaign_seed"] if campaign_only and args.seed == "auto" else args.seed,
            batch_size=args.batch_size or (item["campaign_batch_size"] if campaign_only else None),
            explanation=spec,
            max_images=getattr(args, "max_images", "all"),
            sample_id=getattr(args, "sample_id", None),
            inspection=args.inspect, verification=proof)
        value["campaign_id"] = args.campaign_id or (str(item["campaign_id"]) if item["campaign_id"] else None)
        if args.inspect:
            return {"inspection": value, "inspection_verification": proof}
        result = run(repository, value, "artifacts/assessments")
        return {"attempt_id": str(result["id"]), "state": result["state"], "verification": result["verification"]}
    except Exception as exc:
        return {"state": "failed", "error": str(exc) if isinstance(exc, CampaignError) else "ASSESSMENT_OPERATION_FAILED"}


def _delegate(kind: str, args: argparse.Namespace, item: dict, python: str) -> dict:
    """Same assessment in an owned process of the item's framework (.venv-metal / .venv-torch)."""
    import os
    import tempfile

    from ..execution.process_verification import owned_process

    handle, path = tempfile.mkstemp(prefix="assessment-", suffix=".json")
    os.close(handle)
    try:
        code = owned_process(
            python, "import sys; from src.malaria_dl.assessment.cli import delegated; delegated(*sys.argv[1:])",
            [kind, json.dumps(vars(args), default=str), json.dumps(item, default=str), path], "ASSESSMENT")
        text = open(path, encoding="utf-8").read()
        if code != 0 or not text:
            return {"state": "failed", "error": "ASSESSMENT_PROCESS_FAILED"}
        return json.loads(text)
    finally:
        os.unlink(path)


def delegated(kind: str, args: str, item: str, path: str) -> None:
    result = _assess(kind, argparse.Namespace(**json.loads(args)), json.loads(item), AssessmentRepository())
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, default=str)
