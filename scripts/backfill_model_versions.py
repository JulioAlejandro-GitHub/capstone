#!/usr/bin/env python3
"""Idempotent, transactional backfill. Dry-run is intentionally the default."""
from __future__ import annotations
import argparse, json, sys, uuid
from pathlib import Path
from sqlalchemy import inspect, text
ROOT=Path(__file__).resolve().parents[1]; APP=ROOT/"malaria_dl_local_project"; sys.path.insert(0,str(APP))
from src.db import get_connection  # noqa:E402
from src.model_governance.releases import CLASS_MAPPING, inventory_artifacts, resolve_lineage  # noqa:E402

def plan(connection, model_name=None, training_run_id=None):
    required={"model_name","version_number","checkpoint_artifact_id","artifact_sha256","artifact_size_bytes","framework","status","lineage_status"}
    present={x["name"] for x in inspect(connection).get_columns("model_versions")}
    missing=sorted(required-present)
    if missing:
        raise RuntimeError("Migration 024_model_version_artifact_governance.sql is required; missing columns: "+", ".join(missing))
    runs=[str(r[0]) for r in connection.execute(text("SELECT id FROM runs WHERE run_type='training' AND status='completed'"))]
    artifacts=[dict(r) for r in connection.execute(text("SELECT id::text id, run_id::text run_id, path, checksum, file_size_bytes FROM artifacts" )).mappings()]
    items=resolve_lineage(inventory_artifacts(APP,[x["path"] for x in artifacts if x.get("path")]),runs)
    registered={(str(Path(x["path"]).resolve()),x.get("checksum")):x for x in artifacts if x.get("path")}
    actions=[]
    for item in items:
        if item["lineage_status"]!="resolved": continue
        if model_name and item.get("model_name")!=model_name: continue
        if training_run_id and item.get("training_run_id")!=training_run_id: continue
        artifact=registered.get((item["absolute_path"],item["sha256"]))
        if not artifact or artifact["run_id"]!=item["training_run_id"]: continue
        exists=connection.execute(text("SELECT id FROM model_versions WHERE checkpoint_artifact_id=:id OR artifact_sha256=:sha LIMIT 1"),{"id":artifact["id"],"sha":item["sha256"]}).scalar_one_or_none()
        if not exists: actions.append({"artifact":artifact,"item":item})
    return actions,items

def main():
    p=argparse.ArgumentParser(); mode=p.add_mutually_exclusive_group(); mode.add_argument("--dry-run",action="store_true"); mode.add_argument("--apply",action="store_true")
    p.add_argument("--model-name"); p.add_argument("--training-run-id"); p.add_argument("--output-report",type=Path); p.add_argument("--strict",action="store_true"); a=p.parse_args()
    with get_connection() as c:
        actions,items=plan(c,a.model_name,a.training_run_id); changes=[]
        if a.apply:
            for action in actions:
                item,artifact=action["item"],action["artifact"]
                number=c.execute(text("SELECT COALESCE(MAX(version_number),0)+1 FROM model_versions WHERE model_name=:name"),{"name":item["model_name"]}).scalar_one()
                model_id=c.execute(text("SELECT id FROM models WHERE name=:name LIMIT 1"),{"name":item["model_name"]}).scalar_one_or_none()
                result=c.execute(text("""INSERT INTO model_versions
                  (id,model_id,training_run_id,version_name,version_number,model_name,status,lineage_status,
                   checkpoint_path,checkpoint_artifact_id,artifact_sha256,artifact_size_bytes,framework,
                   preprocessing_profile_snapshot,class_mapping,input_signature,output_signature,metadata)
                  VALUES (:id,:model_id,:run,:version_name,:number,:name,'candidate','resolved',:path,:artifact_id,:sha,:size,:framework,
                    CAST(:pre AS jsonb),CAST(:mapping AS jsonb),CAST(:input AS jsonb),CAST(:output AS jsonb),CAST(:metadata AS jsonb))
                  ON CONFLICT (checkpoint_artifact_id) DO NOTHING RETURNING id::text"""),{
                    "id":str(uuid.uuid4()),"model_id":model_id,"run":item["training_run_id"],"version_name":f"backfill-v{number}","number":number,"name":item["model_name"],
                    "path":artifact["path"],"artifact_id":artifact["id"],"sha":item["sha256"],"size":item["size_bytes"],"framework":item["format"],
                    "pre":"{}","mapping":json.dumps(CLASS_MAPPING),"input":"{}","output":"{}","metadata":json.dumps({"backfilled":True,"lineage_evidence":item["lineage_evidence"],"legacy_generic_path":item["generic_path"]})}).scalar_one_or_none()
                if result: changes.append(result)
        unresolved=[x for x in items if x["lineage_status"]!="resolved"]
        report={"mode":"apply" if a.apply else "dry-run","planned":len(actions),"created":len(changes),"created_ids":changes,"unresolved":unresolved,"deployment_changes":0}
        if a.output_report: a.output_report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps({k:v for k,v in report.items() if k!="unresolved"},indent=2))
        if a.strict and unresolved: return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
