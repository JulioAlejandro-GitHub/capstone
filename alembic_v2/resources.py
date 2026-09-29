"""Read and verify every frozen resource before the first application DDL."""

import hashlib
import json
from pathlib import Path

BASELINE = Path(__file__).resolve().parent / "baseline"
REVISION = "pg_v2_baseline"


def load_baseline(directory=BASELINE):
    manifest = json.loads((directory / "catalog_manifest.json").read_text())
    if manifest["format_version"] != 1 or manifest["revision"] != REVISION:
        raise RuntimeError("V2_MANIFEST_UNSUPPORTED")
    if "d03_contract_sha256" in manifest:
        decision = (Path(__file__).parent / "d03_contract.json").read_bytes()
        if hashlib.sha256(decision).hexdigest() != manifest["d03_contract_sha256"]:
            raise RuntimeError("V2_D03_CONTRACT_CHECKSUM_MISMATCH")
    resources = {}
    for name, expected in manifest["files"].items():
        if Path(name).name != name or not name.endswith(".sql"):
            raise RuntimeError("V2_RESOURCE_PATH_INVALID")
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError("V2_RESOURCE_CHECKSUM_MISMATCH")
        resources[name] = data
    statements = []
    for entry in manifest["statements"]:
        data = resources[entry["file"]][entry["start"] : entry["end"]]
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise RuntimeError("V2_STATEMENT_CHECKSUM_MISMATCH")
        statements.append(data.decode("utf-8"))
    return manifest, statements
