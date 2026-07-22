#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"malaria_dl_local_project"))
from src.model_deployment_service import ModelDeploymentService
def serial(value):
    if hasattr(value,"__dict__"): return value.__dict__
    return str(value)
def main():
    p=argparse.ArgumentParser();p.add_argument("--model-version-id",required=True);p.add_argument("--deployment-name",required=True)
    p.add_argument("--environment",required=True);p.add_argument("--alias",required=True,choices=["candidate","challenger","champion","experimental"])
    p.add_argument("--threshold-profile-id",required=True);p.add_argument("--activate",action="store_true");p.add_argument("--deployed-by")
    p.add_argument("--metadata",default="{}");p.add_argument("--dry-run",action="store_true");a=p.parse_args()
    try: metadata=json.loads(a.metadata)
    except json.JSONDecodeError as exc:p.error(f"--metadata debe ser JSON válido: {exc}")
    service=ModelDeploymentService(); result=service.create(model_version_id=a.model_version_id,deployment_name=a.deployment_name,
      environment=a.environment,alias=a.alias,threshold_profile_id=a.threshold_profile_id,deployed_by=a.deployed_by,metadata=metadata,dry_run=a.dry_run)
    if a.activate and not a.dry_run: result=service.activate(result.id,actor=a.deployed_by)
    print(json.dumps(result,default=serial,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
