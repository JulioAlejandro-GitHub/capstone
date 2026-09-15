> Actualización E9.3 (14/09/2026): [operación secuencial global preparada](e9_3_operacion_secuencial_2026-09-14.md). La campaña permanece pausada; los comandos de activación requieren autorización posterior.

# E9 — Seguimiento y reanudación

Campaña vigente: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`. PostgreSQL es la autoridad. La campaña anterior `ec442763-7eea-499d-a94f-9a3ddfb7c0f0` queda pausada con sus fallos; no ejecutar ambas. No editar fuentes/configuraciones congeladas mientras se ejecuta sin gestionar explícitamente una nueva revisión/campaña.

Consulta segura de estado (no inicia procesos):

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --inspect
```

Comando de inicio ya ejecutado, no repetir mientras exista propietario activo:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
  --artifact-root /app/var/artifacts/campaign_runs
```

Tras una interrupción acreditada, el mismo comando con `--resume` usa la reconciliación E5: verifica los completados y rechaza propietarios vivos/no acreditados como muertos. No borrar sesiones ni forzar estados. No ofrece resume intraépoca: preserva intentos y aplica presupuesto de reintentos. Cambiar fuente congelada exige una sucesora; la primera sucesora ya documenta el motivo numérico.

El proceso iniciado en esta sesión tiene seguimiento en train_execution_sessions, campaign_attempts y train_execution_records. No garantiza continuidad tras cerrar/reemplazar el contenedor, apagar Docker o suspender el host. ARTIFACTS_ROOT es escribible pero no tiene volumen propio en el Compose inspeccionado; no mover artefactos ni alterar referencias para remediarlo silenciosamente.

Pruebas reproducibles:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaign_environment_e9.py tests/test_campaign_executor_e5.py \
  tests/test_stage2_publication_eligibility.py

docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE9_POSTGRES_TESTS=1 -e RUN_STAGE7_POSTGRES_TESTS=1 \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_persistence_e9_postgres.py tests/test_science_postgres.py \
  tests/test_publication_e9_postgres.py
```

El primer grupo pasó 26 casos. El segundo se ejecutó en dos invocaciones: 4 casos de commit/regresión E7 y 1 de publicación. No hay prueba de reinicio ni promoción operativa. Los fixtures eliminan únicamente su esquema sintético.

Para reproducir la verificación E1 de lectura sin persistir auditoría:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -c \
  'from src.malaria_dl.data.governed_dataset import resolve_governed_dataset; s=resolve_governed_dataset("d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"); print(s.metadata())'
```

TEST permanece cerrado: faltan matriz completa, selección VAL, pesos ponderados, manifiesto de contrastes persistido y soporte final de ensembles. No ejecutar freeze-final ni evaluar TEST como atajo. El reporte de seguimiento no es el reporte científico final ni un manifiesto de candidato congelado.
