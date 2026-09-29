"""Reproduce stage A evidence using a fixed list of offline-only commands.

This runner never calls upgrade/stamp/downgrade, Docker, psql, or application
tests. Interpreter choices permit separate local Alembic/parser environments.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parser-python", default=sys.executable)
    parser.add_argument("--alembic-python", default=sys.executable)
    args = parser.parse_args()
    py, alembic_py = args.parser_python, args.alembic_python
    selected = [
        "alembic_v2",
        "scripts/db/build_v2_baseline.py",
        "scripts/db/validate_v2_static.py",
        "scripts/db/check_v2_stage_a.py",
        "tests/db_v2",
    ]
    commands = [
        [py, "scripts/db/build_v2_baseline.py", "--check"],
        [
            py,
            "scripts/db/validate_v2_static.py",
            "--report",
            "docs/audits/e10_10_5a_static_results.json",
        ],
        [
            py,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/db_v2",
            "-p",
            "test_static_baseline.py",
            "-v",
        ],
        [
            alembic_py,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/db_v2",
            "-p",
            "test_alembic_envelope.py",
            "-v",
        ],
        [alembic_py, "-m", "alembic", "-c", "alembic_v2.ini", "heads"],
        [alembic_py, "-m", "alembic", "-c", "alembic_v2.ini", "history"],
        ["ruff", "check", *selected],
        ["ruff", "format", "--check", *selected],
        [
            py,
            "-c",
            "from pathlib import Path; paths=list(Path('alembic_v2').rglob('*.py'))+list(Path('tests/db_v2').glob('*.py'))+[Path('scripts/db/'+n) for n in ('build_v2_baseline.py','validate_v2_static.py','check_v2_stage_a.py')]; [compile(p.read_text(),str(p),'exec') for p in paths]; print(str(len(paths))+' Python modules compiled in memory')",
        ],
    ]
    report = {
        "stage": "E10.10.5A",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "offline static validation only; no PostgreSQL/Docker execution",
        "commands": [],
    }
    destination = ROOT / "docs/audits/e10_10_5a_commands.json"
    for command in commands:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False
        )
        report["commands"].append(
            {
                "argv": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        report["status"] = "FAILED" if completed.returncode else "RUNNING"
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(
            ("PASS " if completed.returncode == 0 else "FAIL ") + " ".join(command[:6])
        )
        if completed.returncode:
            raise SystemExit(completed.returncode)
    report["status"] = "PASSED_PENDING_REVIEW"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"{len(commands)} offline commands passed; report: {destination.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
