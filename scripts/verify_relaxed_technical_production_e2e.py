#!/usr/bin/env python3
"""Real E2E: immutable model -> technical production champion -> inference."""
from __future__ import annotations
import json,sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT/"malaria_dl_local_project"
sys.path.insert(0,str(PROJECT))
from src.db import get_connection,get_engine
from src.model_governance.releases import sha256_file
from src.stage2_model_availability_service import Stage2ModelAvailabilityService

BASELINE_TRAINING="8dca1f53-bcb6-443e-8130-f654e6e518ae"
TARGET_TRAINING="371a9e75-2e87-4c22-b1d0-8f249007cc33"
TARGET_VERSION="8f5277bd-e2bb-4dff-a4d6-821f9f5a60e7"
TARGET_SHA="d54bbdcddbd4ca3b10ce675eb28f60b24a9718ffba881f83ca24ef19820415d8"

def service():
    return Stage2ModelAvailabilityService(
      get_connection,environment="production",alias="champion",
      deployment_name="malaria-classifier",production_scope="stage2_technical",
      release_channel="production")

def main():
    sql=(PROJECT/"db/init/028_stage2_model_availability.sql").read_text()
    with get_engine().begin() as c:c.exec_driver_sql(sql.replace("%","%%"))
    s=service()
    with get_connection() as c:
        active=c.execute(text("""SELECT id::text FROM deployed_model_versions
          WHERE environment='production' AND alias='champion' AND status='active'""")).scalar_one_or_none()
    if not active:
        s.enable(BASELINE_TRAINING,actor="codex-e2e",reason="Baseline real para rollback",
          confirm_stage2_enablement=True)
    before=s.models()[0]
    if before["model_version_id"]==TARGET_VERSION:
        with get_connection() as c:
            previous_id=c.execute(text("""SELECT id::text FROM deployed_model_versions
              WHERE environment='production' AND alias='champion' AND status='inactive'
                AND model_version_id<>CAST(:target AS uuid) ORDER BY created_at DESC LIMIT 1"""),
              {"target":TARGET_VERSION}).scalar_one()
        before=s._result(previous_id)
    preview=s.preview(TARGET_TRAINING);assert preview["eligible"],preview
    source=Path(preview["package"]["production_package"]["artifact_id"])
    result=s.enable(TARGET_TRAINING,actor="operador-web",
      reason="Modelo seleccionado para iniciar Etapa 2",confirm_stage2_enablement=True)
    immutable=PROJECT/"releases/production/custom_cnn"/TARGET_VERSION/"model.keras"
    assert immutable.is_file() and sha256_file(immutable)==TARGET_SHA
    assert result["model_version_id"]==TARGET_VERSION
    assert result["environment"]=="production" and result["alias"]=="champion"
    assert result["status"]=="active" and result["production_scope"]=="stage2_technical"
    assert result["technical_verification"]=="PASS" and result["available_for_inference"]
    assert result["rollback_available"] and before["deployment_id"]!=result["deployment_id"]
    models=s.models();assert len(models)==1 and models[0]["deployment_id"]==result["deployment_id"]
    second=s.enable(TARGET_TRAINING,actor="operador-web",reason="Reintento idempotente",
      confirm_stage2_enablement=True)
    assert second["idempotent"] and second["deployment_id"]==result["deployment_id"]
    print(json.dumps({"previous_champion":before,"result":result,
      "immutable_artifact":str(immutable.relative_to(PROJECT)),
      "selector_deployment_id":models[0]["deployment_id"],"idempotent":second["idempotent"]},
      ensure_ascii=False,indent=2,default=str))
if __name__=="__main__":main()
