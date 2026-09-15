# Comandos y activación futura

Ejecutados desde la raíz del repositorio, en Compose autorizado:

```sh
make db-migrate-check
make db-migrate

docker compose exec -T -w /app/malaria_dl_local_project \
 -e RUN_STAGE5_POSTGRES_TESTS=1 -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
 backend python -B -m pytest -q -p no:cacheprovider \
 tests/test_campaign_executor_postgres.py::test_public_e5_revision_readonly \
 tests/test_assessment_postgres.py::test_public_e6_revision_readonly
# Ejecutados ANTES de migrar: E5 falla sólo pin histórico; E6 pasa.

docker compose exec -T -w /app/malaria_dl_local_project \
 -e RUN_STAGE93_GLOBAL_POSTGRES_TESTS=1 -e RUN_STAGE93_CONTROLLED_POSTGRES_TESTS=1 \
 -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m pytest -q -p no:cacheprovider \
 tests/test_global_execution_postgres.py tests/test_controlled_train_postgres.py

docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 \
 backend python -B -m src.malaria_dl.execution.controlled register \
 --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 \
 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
 --member-id 2fbd5862-b68b-4845-9445-a30d7ec61382 \
 --previous-attempt-id 8279db36-7bfe-4e22-8bf3-872ac215eae2 \
 --revision-id 3ec6fa57-be3f-5433-8557-8c12c3eea740 --proposal /dev/stdin \
 < docs/audits/e9_3_instalacion_2026-09-14/revision_autorizada.json
# Registro exacto ejecutado dos veces; una sola fila persistente.
```

Comprobaciones repetibles sin reservas:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
 --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 \
 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
 --technical-revision-id 3ec6fa57-be3f-5433-8557-8c12c3eea740 --dry-run

docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B - \
 < docs/audits/e9_3_instalacion_2026-09-14/verificar_instalacion.py

docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONDONTWRITEBYTECODE=1 backend python -B - \
 < docs/audits/e9_3_instalacion_2026-09-14/verificar_revision.py

docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONDONTWRITEBYTECODE=1 backend python -B - \
 < docs/audits/e9_3_secuencial_global_2026-09-14/comprobar_solo_lectura.py
curl --fail --silent --show-error http://localhost:8000/ready
```

## Preparado, NO ejecutado: activación futura

Requiere autorización posterior. Primero verificar hashes de revisión, campaña/dataset exactos, ausencia física de coordinador/TRAIN/hijos y de intentos activos, salud y recursos. No lanzar otro coordinador si aparece uno existente. Si cambia la fuente efectiva, no modificar la revisión registrada: preparar otra revisión según contrato. El preflight E1 se ejecuta por la ruta oficial antes de reservar.

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
 --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 \
 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
 --technical-revision-id 3ec6fa57-be3f-5433-8557-8c12c3eea740 \
 --artifact-root /app/var/artifacts/campaign_runs --resume
```

Este comando no fue ejecutado. Continuará secuencialmente según el contrato congelado y verificará artefactos antes del siguiente. Mantener TEST cerrado y E9.4 fuera de alcance. Ante circuito de recursos/fallos, diagnosticar y conservar pausa; no encadenar reinicios ni reconocimientos ciegos. La instalación no acredita resolución de OOM ni aprobación de E9.3.
