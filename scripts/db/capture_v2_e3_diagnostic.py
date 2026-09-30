"""Record a failed certification prerequisite; never issue a certificate."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "docs/audits/e10_10_5e3_evidence/route_a"
sys.path.insert(0, str(ROOT))
os.environ["PGV2_EVIDENCE_DIR"] = str(E)
os.environ["PGPASSFILE"] = json.loads((E / "private_paths.json").read_text())["pgpass"]
from verify_v2_route_a import connect, guard
from v2_catalog_probe import snapshot


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    target = guard()
    new = json.loads((E / "installed_catalog.json").read_text())
    old = json.loads((ROOT / "docs/audits/e10_10_5e1_evidence/route_a/installed_catalog.json").read_text())
    changes = {}
    for key in old:
        if old[key] != new[key]:
            changes[key] = dict(before=[r for r in old[key] if r not in new[key]],
                                after=[r for r in new[key] if r not in old[key]])
    assert set(changes) == {"constraints"}
    assert len(changes["constraints"]["before"]) == len(changes["constraints"]["after"]) == 1
    assert changes["constraints"]["before"][0]["name"] == "v2_evaluations_check_6a2239d39784"
    assert changes["constraints"]["after"][0]["name"] == "v2_evaluations_check_28938a6edbaa"
    with connect(target) as c:
        assert snapshot(c) == new
        counts = c.execute("SELECT (SELECT count(*) FROM evaluations) AS evaluations, "
            "(SELECT count(*) FROM run_clinical_metrics) AS metrics, "
            "(SELECT count(*) FROM run_threshold_calibration) AS calibrations, "
            "(SELECT count(*) FROM train_execution_records) AS ledger, "
            "(SELECT count(*) FROM runs) AS runs").fetchone()
        assert all(n == 0 for n in counts.values())
    history = {}
    paths = subprocess.check_output(["git", "ls-files", "docs/audits/e10_10_5d4_evidence",
        "docs/audits/e10_10_5e1_evidence", "docs/audits/e10_10_5e2_evidence",
        "docs/audits/e10_10_4_target_schema.sql"], cwd=ROOT, text=True).splitlines()
    for name in paths:
        previous = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT)
        assert previous == (ROOT / name).read_bytes(), name
        history[name] = sha(previous)
    (E.parent / "historical_preservation.json").write_text(json.dumps(history, indent=2) + "\n")
    diagnostic = json.loads((E / "e03_contract_diagnostic.json").read_text())
    assert diagnostic["passed"] is False
    report = dict(stage="E10.10.5E.3", status="BLOCKED_E04", certified=False,
        gate_e="BLOCKED_NOT_REQUESTED", postgres_version="17.9",
        postgres_system_identifier=target["postgres_system_identifier"],
        manifest_sha256=sha((ROOT / "alembic_v2/baseline/catalog_manifest.json").read_bytes()),
        catalog_sha256=sha(json.dumps(new, sort_keys=True, default=str).encode()),
        exact_catalog_changes=changes, diagnostic_fixture_counts_after_rollback=counts,
        required_rejections_absent=[r["name"] for r in diagnostic["results"] if not r["passed"]],
        historical_files_verified=len(history),
        pending="Guard decision; complete baseline recertification, E-02 regression and entire E matrix",
        certificate_issued=False)
    (E / "candidate_status.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "certified", "historical_files_verified"]}))


if __name__ == "__main__":
    main()
