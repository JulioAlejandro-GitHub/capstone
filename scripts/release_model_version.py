#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"malaria_dl_local_project"))
from src.model_governance.releases import create_release  # noqa:E402
def main():
    p=argparse.ArgumentParser(); p.add_argument("--training-run-id",required=True); p.add_argument("--evaluation-run-id"); p.add_argument("--explainability-run-id")
    group=p.add_mutually_exclusive_group(required=True); group.add_argument("--artifact-path",type=Path); group.add_argument("--artifact-id")
    p.add_argument("--model-name",required=True); p.add_argument("--status",default="candidate",choices=["discovered","candidate","rejected"])
    p.add_argument("--output-dir",type=Path,default=ROOT/"malaria_dl_local_project"/"releases")
    a=p.parse_args()
    from sqlalchemy import text
    from src.db import get_connection
    with get_connection() as c:
        training=c.execute(text("SELECT id::text id FROM runs WHERE id=:id AND run_type='training'"),{"id":a.training_run_id}).mappings().one_or_none()
    if not training: p.error("training-run-id does not identify a training run")
    if a.artifact_id:
        with get_connection() as c:
            row=c.execute(text("SELECT path FROM artifacts WHERE id=:id AND run_id=:run"),{"id":a.artifact_id,"run":a.training_run_id}).mappings().one_or_none()
        if not row: p.error("artifact-id does not exist or does not belong to training run")
        a.artifact_path=Path(row["path"])
    manifest=create_release(project_root=ROOT/"malaria_dl_local_project",artifact_path=a.artifact_path,training_run_id=a.training_run_id,model_name=a.model_name,output_dir=a.output_dir,status=a.status,evaluation_run_id=a.evaluation_run_id,explainability_run_id=a.explainability_run_id)
    print(json.dumps(manifest,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
