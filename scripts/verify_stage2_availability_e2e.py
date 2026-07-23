#!/usr/bin/env python3
"""One-shot real PostgreSQL verification for Stage 2 model availability."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/"malaria_dl_local_project"
sys.path.insert(0,str(PROJECT))

from src.db import get_connection,get_engine
from src.stage2_model_availability_service import Stage2ModelAvailabilityService

TRAINING_RUN_ID="8dca1f53-bcb6-443e-8130-f654e6e518ae"
EXPECTED_MODEL_VERSION_ID="03bf43fa-7e8a-4b3c-84ec-686238325322"
EXPECTED_SHA="70230aee19f14a4c570fc62dfcf79e1790e6c7674c49ab310d1abdfc056a86ab"


def champion():
    with get_connection() as connection:
        return connection.execute(text("""SELECT id::text FROM deployed_model_versions
          WHERE environment='production' AND alias='champion' AND status='active'
          ORDER BY deployed_at DESC LIMIT 1""")).scalar_one_or_none()


def main():
    migration=(PROJECT/"db/init/028_stage2_model_availability.sql").read_text(encoding="utf-8")
    with get_engine().begin() as connection:
        connection.exec_driver_sql(migration.replace("%","%%"))
    before=champion()
    service=Stage2ModelAvailabilityService(get_connection)
    preview=service.preview(TRAINING_RUN_ID)
    assert preview["model_version_id"]==EXPECTED_MODEL_VERSION_ID,preview
    assert preview["eligible"] or preview["available"],preview
    result=service.enable(
        TRAINING_RUN_ID,actor="codex-stage2-e2e",
        reason="Validación E2E real de disponibilidad técnica Etapa 2",
        confirm_stage2_enablement=True,
    )
    after=champion()
    assert before==after,(before,after)
    assert result["environment"]=="stage2" and result["alias"]=="default",result
    assert result["status"]=="active" and result["available_for_stage2"],result
    assert result["artifact_sha256"]==EXPECTED_SHA,result
    assert result["smoke_status"]=="PASS",result
    assert result["verification_inference"]["inference_run_id"],result
    assert result["verification_inference"]["image_analysis_job_id"],result
    output={"production_champion_unchanged":before==after,"result":result}
    print(json.dumps(output,ensure_ascii=False,indent=2,default=str))


if __name__=="__main__":
    main()
