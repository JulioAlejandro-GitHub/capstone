# Contrato técnico y operación — preparación, sin instalación

Dataset obligatorio: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`. La matriz se conserva: 36 miembros, semillas11/29/47. Selección determinista para un futuro único intento: posición0, CustomCNN/Adadelta/11, miembro2fbd5862-b68b-4845-9445-a30d7ec61382, intento fallido8279db36-7bfe-4e22-8bf3-872ac215eae2. No se creó ese nuevo intento.

## Persistencia

Nueva migración20260914_01 sobre20260912_02, sólo preparada y probada en esquemas sintéticos. campaign_technical_revisions es append-only: environment original, environment técnico, contrato científico, archivos/hashes, motivo, pruebas, autorización y hash del payload. No sustituye los hashes ni contratos antiguos. campaign_controlled_requests es append-only y relaciona request_id, campaña, miembro, revisión, intento anterior, intento nuevo y Run ID. FK diferidas prueban la vinculación completa al commit. La revisión efectiva está en session.environment y en esa relación exacta, no se infiere por fecha/carpeta.

Revisión técnica: conserva todo environment salvo source_sha256 y git_commit, exige contract_hash original y configuración de miembro original. Worker/preflight usan sólo la revisión registrada y ligada al Run, con igualdad de fuente efectiva. La aprobación del cambio de código sigue requiriendo revisión humana de su semántica: un hash no prueba equivalencia científica. En este cambio los archivos de modelos/configuraciones/optimizadores/preprocesamiento no fueron modificados. No se acepta un contrato científico distinto como revisión técnica.

runs.campaign_id se añade nullable con FK. No hay backfill: históricos mantienen NULL. Nuevas reservas controladas lo crean explícitamente; claim normal también lo incluye cuando la extensión está instalada. No se incorpora historial mediante fallback. Las consultas controladas requieren campaña/dataset/miembro/previous explícitos.

La reserva bloquea campaña, valida pausa/ausencia de activo/presupuesto y crea request+attempt+run+session en una transacción. Misma request retorna mismo Run sin lanzar de nuevo; distinto request sobre el mismo fallo no puede consumirlo otra vez. La campaña nunca pasa a active. Un trigger impide levantar la pausa mientras el intento controlado siga active/completed. El ejecutor sólo lanza un hijo y no recorre cola. Una excepción de lanzamiento persiste fallo, el código no cero se conserva; la recuperación explícita no reserva ni lanza nada y exige propietario/hijo probados ausentes para reconciliar activos. Un propietario no observable se bloquea; no hay lease remoto inventado.

## Dry-run real ejecutado, sin escrituras

```sh
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.execution.controlled dry-run --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 --member-id 2fbd5862-b68b-4845-9445-a30d7ec61382 --previous-attempt-id 8279db36-7bfe-4e22-8bf3-872ac215eae2 --proposal /dev/stdin < docs/audits/e9_3_desarrollo_2026-09-14/revision_propuesta.json
```

Resultado: eligible_without_reservation=true, next_ordinal=2, writes=0, installed=false, revision_registered=false, execution_ready=false. La elegibilidad estructural no acredita resolver memoria ni autoriza ejecutar. Un primer dry-run sin PYTHONHASHSEED=42 fue rechazado por TECHNICAL_ENVIRONMENT_CONFLICT: el comando explícito conserva el valor original; no se debilitó el validador.

## Instalación y futura ejecución — NO EJECUTADAS

Trabajo A sigue parcial. No registrar esta propuesta como aprobación del OOM ni ejecutar hasta corregirlo/verificarlo y obtener autorización operativa. Si cambia la fuente, regenerar propuesta/hashes/pruebas, volver a revisar y repetir dry-run. Los siguientes UUID son sólo identificadores preparados, no registros existentes.

Tras autorización de instalación, conservar backup/preflight usando wrappers del proyecto:

```sh
make db-migrate-check
make db-migrate
```

No se ejecutó ninguno durante este desarrollo. No saltar backup ni preflight. Requiere instalar20260914_01; afecta esquema y validadores, no datos científicos. No exige alterar campaña ni despausar. El head local adelantado provoca /ready=503 migrations:not_ready hasta instalación autorizada; database/storage permanecen ready. No se ocultó el control ni se reinició deployment.

Después de aceptación de A y revisión operativa de la propuesta actualizada:

```sh
# ESCRITURA FUTURA: registro explícito; NO ejecutado.
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.execution.controlled register --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 --member-id 2fbd5862-b68b-4845-9445-a30d7ec61382 --previous-attempt-id 8279db36-7bfe-4e22-8bf3-872ac215eae2 --revision-id e54e4b68-4449-529f-af0d-a9084a57aea3 --proposal /dev/stdin < docs/audits/e9_3_desarrollo_2026-09-14/revision_propuesta.json
# Lectura previa; exige revisión registrada y fuente exacta.
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.execution.controlled dry-run --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 --member-id 2fbd5862-b68b-4845-9445-a30d7ec61382 --previous-attempt-id 8279db36-7bfe-4e22-8bf3-872ac215eae2 --revision-id e54e4b68-4449-529f-af0d-a9084a57aea3
# ÚNICO INTENTO FUTURO, DESDE CERO; NO ejecutado.
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.execution.controlled execute --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 --member-id 2fbd5862-b68b-4845-9445-a30d7ec61382 --previous-attempt-id 8279db36-7bfe-4e22-8bf3-872ac215eae2 --revision-id e54e4b68-4449-529f-af0d-a9084a57aea3 --request-id b0992d4a-ce54-5102-bdd7-68f879b91e7a --reason E9_3_single_controlled_recovery --artifact-root /app/var/artifacts/campaign_runs
# Sólo si se acredita pérdida del propietario; NO ejecutado.
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.execution.controlled recover --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 --member-id 2fbd5862-b68b-4845-9445-a30d7ec61382 --previous-attempt-id 8279db36-7bfe-4e22-8bf3-872ac215eae2 --request-id b0992d4a-ce54-5102-bdd7-68f879b91e7a
```

No usar --resume. Registrar el resultado y nueva verificación; no encadenar otra ejecución ni otra request ante el mismo fallo. El éxito se verifica con verify_session/keras_loader oficiales y nueva lectura; fixtures no acreditan un checkpoint operativo. Ningún comando abre EVALUATE, ensembles, TEST o E9.4.
