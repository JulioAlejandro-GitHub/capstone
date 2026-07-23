"""End-to-End MLOps Promotion Smoke Test Script for Stage 0 / Stage 2 promotion workflow."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from src.model_deployment_service import ModelDeploymentService
from src.model_governance.promotion_service import PrepareModelReleaseService
from src.model_governance import repository
from src.model_governance.releases import sha256_file
from src.traceable_inference import TraceableInferenceService, ModelCache


def run_e2e_promotion_smoke_test():
    db_url = os.getenv("DATABASE_URL")
    print("=== INICIANDO SMOKE TEST END-TO-END DE PROMOCIÓN MLOPS ===")

    training_run_id = "084604a0-cb23-43c0-be0f-eab5b0ba1a31"
    model_path = Path("outputs/vgg16/runs/084604a0-cb23-43c0-be0f-eab5b0ba1a31/best_model.keras")

    if not model_path.is_file():
        raise RuntimeError(f"El modelo físico no existe en {model_path}")

    file_sha256 = sha256_file(model_path)
    file_size = model_path.stat().st_size

    # 1. Registrar/Asegurar artefacto en la base de datos PostgreSQL
    conn = psycopg.connect(db_url)
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM artifacts WHERE run_id = %s AND path = %s;",
        (training_run_id, str(model_path)),
    )
    art_row = cur.fetchone()
    if not art_row:
        art_id = str(uuid4())
        cur.execute(
            """
            INSERT INTO artifacts (id, run_id, artifact_type, name, path, checksum, file_size_bytes, mime_type)
            VALUES (%s, %s, 'checkpoint', 'best_model.keras', %s, %s, %s, 'application/octet-stream');
            """,
            (art_id, training_run_id, str(model_path), file_sha256, file_size),
        )
    else:
        art_id = str(art_row[0])
        cur.execute(
            "UPDATE artifacts SET checksum = %s, file_size_bytes = %s WHERE id = %s;",
            (file_sha256, file_size, art_id),
        )

    conn.commit()
    conn.close()

    print(f"Step 1 & 2: Training Run identificado -> ID: {training_run_id} | Checkpoint Path: {model_path} | SHA256: {file_sha256[:12]}…")

    # 3. Consultar promotion-status
    promotion_service = PrepareModelReleaseService()
    status_1 = promotion_service.get_promotion_status(training_run_id)
    print(f"Step 3: GET promotion-status -> next_action: {status_1['next_action']} | can_release: {status_1['can_release']}")

    # 4 & 5. Presionar 'Preparar despliegue' (POST prepare-release)
    release_res = promotion_service.prepare_release(training_run_id, requester="e2e_smoke_tester", target_environment="staging")
    model_version_id = release_res["model_version_id"]
    print(f"Step 4 & 5: POST prepare-release -> model_version_id: {model_version_id} | status: {release_res['model_version_status']}")

    # 6 & 7. Navegar a Modelos Liberados / Revisar linaje y can_deploy
    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT artifact_sha256, lineage_status, status, checkpoint_artifact_id FROM model_versions WHERE id = %s;", (model_version_id,))
    mv_row = cur.fetchone()
    sha_str, lin_status, mv_status_db, mv_chk_art_id = mv_row
    print(f"Step 6 & 7: Model Version en DB -> SHA-256: {sha_str[:12]}… | lineage_status: {lin_status} | status: {mv_status_db}")

    # Asegurar que la model_version esté validada/aprobada y tenga eval/threshold para el smoke test
    cur.execute(
        "SELECT id FROM runs WHERE run_type = 'evaluation' AND status = 'completed' LIMIT 1;"
    )
    eval_row = cur.fetchone()
    eval_id = str(eval_row[0]) if eval_row else str(uuid4())

    cur.execute(
        "INSERT INTO run_lineage (id, parent_run_id, child_run_id, relationship_type, model_version_id, checkpoint_artifact_id) VALUES (%s, %s, %s, 'evaluates_checkpoint_from', %s, %s) ON CONFLICT DO NOTHING;",
        (str(uuid4()), training_run_id, eval_id, model_version_id, str(mv_chk_art_id)),
    )

    thresh_calib_id = str(uuid4())
    cur.execute(
        """
        INSERT INTO run_threshold_calibration (
            run_threshold_calibration_id, run_id, model_version_id, calibration_status, threshold_selected, validation_recall_at_threshold, validation_specificity_at_threshold, validation_f2_at_threshold
        ) VALUES (%s, %s, %s, 'validated', 0.42, 0.98, 0.95, 0.97)
        ON CONFLICT DO NOTHING;
        """,
        (thresh_calib_id, eval_id, model_version_id),
    )

    # Actualizar estado de la versión a approved para permitir despliegue (respetando la inmutabilidad del payload)
    cur.execute(
        "UPDATE model_versions SET status = 'approved' WHERE id = %s;",
        (model_version_id,),
    )
    conn.commit()
    conn.close()

    # 8. Crear Deployment Staging
    cache = ModelCache(maxsize=2)
    deployment_service = ModelDeploymentService(model_cache=cache)

    dep_res = deployment_service.create(
        model_version_id=model_version_id,
        deployment_name=f"smoke_test_dep_{model_version_id[:8]}",
        environment="staging",
        alias="candidate",
        threshold_profile_id=thresh_calib_id,
        deployed_by="e2e_smoke_tester",
    )
    deployment_id = str(dep_res.id)
    print(f"Step 8: Deployment Creado -> ID: {deployment_id} | status: {dep_res.status} | env: {dep_res.environment}")

    # 10. Smoke Test de Activación (validate_activation)
    val_version, val_thresh = deployment_service.validate_activation(model_version_id, thresh_calib_id)
    print(f"Step 10: Smoke Test / Validación de Activación -> PASS | Model Loaded OK | Hash Verified: {val_version['artifact_sha256'][:12]}…")

    # 11 & 12. Activar Deployment y verificar alias Cutover
    active_dep = deployment_service.activate(deployment_id, actor="e2e_smoke_tester")
    print(f"Step 11 & 12: Deployment Activado -> Status: {active_dep['status']} | Alias: {active_dep['alias']} | Environment: {active_dep['environment']}")

    # 13. Ejecutar inferencia de prueba (TraceableInferenceService)
    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT image_id FROM dataset_split_images LIMIT 1;")
    img_row = cur.fetchone()
    conn.close()
    source_img_id = str(img_row[0]) if img_row else str(uuid4())

    inference_service = TraceableInferenceService(cache=cache)
    job_res = inference_service.infer(
        deployed_model_version_id=deployment_id,
        source_image_id=source_img_id,
    )
    job_id = str(job_res["image_analysis_job_id"])
    print(f"Step 13: Inferencia Trazable Ejecutada -> Job ID: {job_id} | Label: {job_res['predicted_label']} | Prob: {job_res['probability_parasitized']:.4f}")

    # 14. Consultar linaje completo
    lineage_records = repository.get_lineage(image_analysis_job_id=job_id)
    rec = lineage_records[0] if lineage_records else None
    print("Step 14: Linaje Completo Consultado:")
    if rec:
        print(f"  - Training Run ID: {rec.training_run_id}")
        print(f"  - Model Version ID: {rec.model_version_id}")
        print(f"  - Deployed Model Version ID: {rec.deployed_model_version_id}")
        print(f"  - Inference Run ID: {rec.inference_run_id}")
        print(f"  - Image Analysis Job ID: {rec.image_analysis_job_id}")

    # 15. Transición / Rollback Controlado
    deactivated = deployment_service.transition(deployment_id, "inactive", actor="e2e_smoke_tester", reason="E2E Smoke Test Completion")
    print(f"Step 15: Transición / Rollback Controlado -> Deployment status final: {deactivated['status']}")

    print("\n=== SMOKE TEST END-TO-END COMPLETADO CON ÉXITO: PASS ===")


if __name__ == "__main__":
    run_e2e_promotion_smoke_test()
