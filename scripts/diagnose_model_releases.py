#!/usr/bin/env python3
"""Read-only inventory of governed and legacy model artifacts."""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "malaria_dl_local_project"
sys.path.insert(0, str(APP))
from src.model_governance.releases import inventory_artifacts, resolve_lineage  # noqa:E402

def database_snapshot():
    from sqlalchemy import inspect, text
    from src.db import get_connection
    with get_connection() as c:
        inspector=inspect(c)
        tables=set(inspector.get_table_names())
        columns=lambda table: {x["name"] for x in inspector.get_columns(table)} if table in tables else set()
        runs = [dict(r) for r in c.execute(text("SELECT id::text id, status FROM runs WHERE run_type='training'" )).mappings()]
        artifact_cols=columns("artifacts")
        checksum="checksum" if "checksum" in artifact_cols else "NULL::text"
        artifacts = [dict(r) for r in c.execute(text(f"SELECT id::text id, run_id::text run_id, path, {checksum} AS checksum FROM artifacts" )).mappings()]
        version_cols=columns("model_versions")
        optional=lambda name,default="NULL::text": name if name in version_cols else f"{default} AS {name}"
        versions = [dict(r) for r in c.execute(text(f"SELECT id::text id, training_run_id::text training_run_id, {optional('model_name')}, {optional('status', "'discovered'::text")}, {optional('lineage_status', "'legacy_unresolved'::text")}, {optional('evaluation_run_id')}, {optional('explainability_run_id')}, {optional('threshold_calibration_id')} FROM model_versions" )).mappings()]
        deployments=int(c.execute(text("SELECT count(*) FROM deployed_model_versions")).scalar_one()) if "deployed_model_versions" in tables else 0
        prediction_cols=columns("predictions")
        predictions=int(c.execute(text("SELECT count(*) FROM predictions WHERE model_version_id IS NULL")).scalar_one()) if "model_version_id" in prediction_cols else 0
        missing=[name for name in ("model_name","status","lineage_status","artifact_sha256") if name not in version_cols]
        counts={"deployments":deployments,"predictions_without_model_version":predictions,"missing_governance_columns":missing}
    return runs, artifacts, versions, counts

def diagnose(args):
    try:
        runs, db_artifacts, versions, counts = database_snapshot()
        db_error = None
    except Exception as exc:
        if args.strict: raise
        runs, db_artifacts, versions, counts = [], [], [], {"deployments": 0, "predictions_without_model_version": 0}
        db_error = str(exc)
    known = [r["id"] for r in runs]
    items = resolve_lineage(inventory_artifacts(APP, [a["path"] for a in db_artifacts if a.get("path")]), known)
    resolved = [x for x in items if x["lineage_status"] == "resolved"]
    unresolved = [x for x in items if x["lineage_status"] != "resolved"]
    completed = [r for r in runs if r.get("status") == "completed"]
    with_checkpoint = {x["training_run_id"] for x in resolved}
    report = {
      "project_root": str(APP.resolve()), "database_error": db_error,
      "database_missing_governance_columns": counts.get("missing_governance_columns", []),
      "summary": {
        "completed_training_runs": len(completed),
        "training_runs_without_checkpoint": sum(r["id"] not in with_checkpoint for r in completed),
        "checkpoints_found": len(items), "checkpoints_with_hash": len(items),
        "checkpoints_exact_lineage": len(resolved), "checkpoints_ambiguous_or_unresolved": len(unresolved),
        "generic_paths": sum(x["generic_path"] for x in items),
        "model_versions_existing": len(versions),
        "model_versions_candidate": sum(v.get("status") == "candidate" for v in versions),
        "model_versions_unresolved": sum(v.get("lineage_status") != "resolved" for v in versions),
        "model_versions_without_evaluation": sum(not v.get("evaluation_run_id") for v in versions),
        "model_versions_without_explainability": sum(not v.get("explainability_run_id") for v in versions),
        "model_versions_without_threshold": sum(not v.get("threshold_calibration_id") for v in versions),
        "deployments_existing": int(counts.get("deployments", 0)),
        "historical_predictions_without_model_version_id": int(counts.get("predictions_without_model_version", 0)),
      }, "artifacts": items, "model_versions": versions,
    }
    return report

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output-json", type=Path); p.add_argument("--output-csv", type=Path)
    p.add_argument("--model-name"); p.add_argument("--training-run-id"); p.add_argument("--verbose", action="store_true"); p.add_argument("--strict", action="store_true")
    a=p.parse_args(); report=diagnose(a)
    if a.model_name: report["artifacts"]=[x for x in report["artifacts"] if x.get("model_name")==a.model_name]
    if a.training_run_id: report["artifacts"]=[x for x in report["artifacts"] if x.get("training_run_id")==a.training_run_id]
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    if a.verbose: print(json.dumps(report["artifacts"], indent=2, ensure_ascii=False))
    if a.output_json: a.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str)+"\n")
    if a.output_csv:
        with a.output_csv.open("w", newline="") as f:
            fields=list(report["artifacts"][0]) if report["artifacts"] else ["relative_path"]
            w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(report["artifacts"])
    if a.strict and (report["database_error"] or report["summary"]["checkpoints_ambiguous_or_unresolved"]): return 2
    return 0
if __name__ == "__main__": raise SystemExit(main())
