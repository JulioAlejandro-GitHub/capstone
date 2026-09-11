"""Planning CLI. Input JSON files are requests, never persistence fallbacks."""

import argparse
import json
from pathlib import Path

from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.campaigns.service import CampaignService
from src.malaria_dl.data.governed_dataset import GovernedDatasetError


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="E4 campaign planning only; never starts TRAIN"
    )
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("inspect", "create", "edit"):
        sub = commands.add_parser(name)
        sub.add_argument("--request", required=True, help="Input matrix JSON")
        sub.add_argument(
            "--protocol",
            required=name != "inspect",
            help="Input protocol JSON; never supplies implicit clinical decisions",
        )
        if name == "create":
            for field in ("name", "purpose", "dataset-version-id", "actor"):
                sub.add_argument("--" + field, required=True)
            sub.add_argument("--experiment-id")
        if name == "edit":
            sub.add_argument("--campaign-id", required=True)
    for name in ("validate", "freeze", "show"):
        sub = commands.add_parser(name)
        sub.add_argument("--campaign-id", required=True)
        if name in ("freeze", "show"):
            sub.add_argument("--dataset-version-id")
    args = parser.parse_args(argv)
    try:
        service = CampaignService()
        request = (
            json.loads(Path(args.request).read_text())
            if hasattr(args, "request")
            else None
        )
        protocol = (
            json.loads(Path(args.protocol).read_text())
            if getattr(args, "protocol", None)
            else None
        )
        if args.operation == "inspect":
            result = service.inspect(request, protocol)
        elif args.operation == "create":
            result = service.create(
                name=args.name,
                purpose=args.purpose,
                dataset_version_id=args.dataset_version_id,
                actor=args.actor,
                experiment_id=args.experiment_id,
                request=request,
                protocol=protocol,
            )
        elif args.operation == "edit":
            result = service.edit(args.campaign_id, request, protocol)
        elif args.operation == "validate":
            result = service.validate(args.campaign_id)
        elif args.operation == "freeze":
            result = service.freeze(args.campaign_id, args.dataset_version_id)
        else:
            result = service.repository.get(args.campaign_id, args.dataset_version_id)
        print(json.dumps(result, default=str, ensure_ascii=False, allow_nan=False))
        return 0
    except (CampaignError, GovernedDatasetError) as exc:
        print(str(exc))
        return 1
    except (OSError, ValueError):
        print("CAMPAIGN_REQUEST_INVALID")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
