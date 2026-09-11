"""Read exact experiments and persist a report. No training or inference entrypoint."""

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

from ..campaigns.contracts import digest
from ..data.governed_dataset import resolve_governed_dataset
from .comparison import compare, read_evaluation, safe_reason
from .protocol import PATH, campaign_plan, load_protocol, require
from .reporting import export_report
from .repository import ScienceRepository


def provenance():
    root = Path(__file__).resolve().parents[1]
    files = {
        p.relative_to(root).as_posix(): __import__("hashlib")
        .sha256(p.read_bytes())
        .hexdigest()
        for folder in (
            "science",
            "assessment",
            "execution",
            "data",
            "campaigns",
            "models",
        )
        for p in sorted((root / folder).rglob("*.py"))
    }
    return {
        "python": platform.python_version(),
        "packages": {
            n: importlib.metadata.version(n)
            for n in ("numpy", "scikit-learn", "scipy", "SQLAlchemy", "matplotlib")
        },
        "source_files": files,
        "source_sha256": digest(files),
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        description="E7 scientific comparison; explicit references, PostgreSQL authority"
    )
    sub = p.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-protocol")
    check.add_argument("--protocol", default=str(PATH))
    run = sub.add_parser("compare")
    run.add_argument("--protocol", default=str(PATH))
    run.add_argument("--dataset-version-id", required=True)
    run.add_argument("--split", required=True, choices=("val", "test"))
    run.add_argument(
        "--references",
        required=True,
        help="JSON list of {evaluation_id, explanation_ids?}; [] creates missing-evidence report",
    )
    run.add_argument("--export-dir")
    run.add_argument(
        "--campaign-id",
        help="Explicit E4 campaign inventory and first-verified-attempt reconciliation",
    )
    export = sub.add_parser("export")
    export.add_argument("--report-id", required=True)
    export.add_argument("--export-dir", required=True)
    freeze = sub.add_parser("freeze-final")
    freeze.add_argument("--report-id", required=True)
    freeze.add_argument("--identity-file", required=True)
    ensemble = sub.add_parser(
        "compare-ensembles", help="E8 extension over persisted ensemble evaluation IDs"
    )
    ensemble.add_argument("--evaluation-id", action="append", default=[])
    ensemble.add_argument("--export-dir")
    args = p.parse_args(argv)
    try:
        if args.command == "compare-ensembles":
            from .ensemble_cli import compare_command

            return compare_command(args.evaluation_id, args.export_dir)
        if args.command == "check-protocol":
            protocol = load_protocol(args.protocol)
            campaign_plan(protocol)
            print(
                json.dumps(
                    {
                        "version": protocol["version"],
                        "sha256": digest(protocol),
                        "configurations": len(protocol["configurations"]),
                    }
                )
            )
            return 0
        repo = ScienceRepository()
        if args.command == "export":
            print(export_report(repo, args.report_id, args.export_dir))
            return 0
        if args.command == "freeze-final":
            print(
                repo.freeze_final(
                    args.report_id, json.loads(Path(args.identity_file).read_text())
                )
            )
            return 0
        protocol = load_protocol(args.protocol)
        refs = json.loads(args.references)
        require(
            isinstance(refs, list)
            and all(
                isinstance(r, dict)
                and set(r) <= {"evaluation_id", "explanation_ids"}
                and "evaluation_id" in r
                for r in refs
            ),
            "EXPLICIT_REFERENCES_INVALID",
        )
        dataset = resolve_governed_dataset(args.dataset_version_id).metadata()
        report = compare(
            protocol,
            dataset,
            args.split,
            refs,
            lambda i, e: read_evaluation(repo, i, e),
            provenance=provenance(),
            campaign=repo.campaign_inventory(args.campaign_id)
            if args.campaign_id
            else None,
        )
        report_id = repo.persist_report(report)
        if args.export_dir:
            export_report(repo, report_id, args.export_dir)
        print(
            json.dumps(
                {
                    "report_id": report_id,
                    "report_hash": digest(report),
                    "state": report["state"],
                    "selected": report["selection"]["candidate"] is not None,
                }
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001 -- no driver details or result file fallback
        print("E7_FAILED: " + safe_reason(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
