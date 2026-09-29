"""Offline plan by default; D execution requires an explicit reviewed authorization."""

import argparse
import json
import os
from pathlib import Path

from alembic_v2.safety import UnsafeTarget

from .core import Blocked, decode
from .execute import apply, private_write
from .planner import build_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["plan", "apply"])
    parser.add_argument("--snapshot")
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--authorization")
    parser.add_argument("--backup")
    parser.add_argument("--completed-plan")
    args = parser.parse_args()
    try:
        bindings = json.loads(Path(args.bindings).read_text())
        if args.mode == "plan":
            snapshot = decode(json.loads(Path(args.snapshot).read_text()))
            result = build_plan(snapshot, bindings)
            private_write(args.output, result)
        else:
            approval = (
                json.loads(Path(args.authorization).read_text())
                if args.authorization
                else {}
            )
            completed = (
                decode(json.loads(Path(args.completed_plan).read_text()))
                if args.completed_plan
                else None
            )
            apply(
                approval,
                os.environ.get("PGV2_ADOPTION_URL", ""),
                bindings,
                args.output,
                backup_path=args.backup,
                completed_plan=completed,
            )
    except (Blocked, UnsafeTarget) as error:
        parser.exit(2, str(error) + "\n")
    except Exception:  # noqa: BLE001 -- driver exceptions may contain private row values.
        parser.exit(
            2,
            "ADOPTION_FAILED_OR_COMMIT_UNCERTAIN: revisar evidencia privada y estado del destino aislado antes de reintentar\n",
        )


if __name__ == "__main__":
    main()
