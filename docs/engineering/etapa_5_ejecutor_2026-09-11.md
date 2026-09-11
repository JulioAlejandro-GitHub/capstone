# E5 — Ejecutor de campañas

Estado de entrega: implementación local; integración PostgreSQL e instalación pendientes. No ejecutar campañas científicas extensas ni iniciar E6.

## Planificar, inspeccionar y ejecutar

La planificación sigue en el CLI E4 `python -m src.campaign` (consultar `--help` para create/edit/validate/freeze). Requiere dataset explícito y decisiones científicas aportadas; no se inventa un protocolo. `run_train_all_models.py` ya no ejecuta matrices sin campaña. Sus helpers Python históricos de planificación permanecen para compatibilidad de imports, pero el CLI exige campaign-id.

Desde `malaria_dl_local_project`:

```sh
python run_train_all_models.py --campaign-id <UUID> --inspect
python run_train_all_models.py --campaign-id <UUID> --result
python run_train_all_models.py --campaign-id <UUID> --artifact-root /ruta/artefactos
python run_train_all_models.py --campaign-id <UUID> --resume --artifact-root /ruta/artefactos
```

`--dataset-version-id` es sólo una aserción de identidad. Overrides de modelos, optimizadores, semillas, épocas o protocolo son rechazados. Inspect/result consultan BD sin ejecutar. El comando por defecto admite campañas frozen/active; resume reconcilia antes de reclamar. Dos procesos pueden competir por miembros; el paralelismo interno inicial es uno.

El preflight comprueba contrato/matriz E4, E1 y snapshot, versiones de adaptadores, fuente/dependencias/entorno congelados, privilegios y almacenamiento. Un cambio relevante de fuente, incluidas las modificaciones E5 respecto de una campaña congelada antes, exige una campaña nueva; no actualiza el contrato. Cambiar el registro no agrega miembros a campañas existentes.

## Propiedad y recuperación

El padre crea intento, TRAIN y sesión propietaria en una transacción. Orden de locks: campaña, miembro, intento/sesión, TRAIN. No hay locks de filas abiertos durante fit. El hijo recibe run-id/owner; obtiene el contrato de BD, registra su PID y contrasta miembro/configuración/dataset/entorno antes de fit. Las escrituras comprueban propietario y estado; los registros por kind/phase/key son idempotentes sólo si el contenido es idéntico. No hay leases ni expiración usada como prueba de muerte.

La recuperación de active sólo procede automáticamente cuando host coincide y los PID de padre/hijo ya no existen. PID reutilizado, permiso insuficiente, host diferente o proceso vivo bloquean la recuperación con una pausa y diagnóstico; no se mata un PID ajeno para desbloquear. Un hijo tardío encuentra la sesión interrumpida y no puede registrar resultados ni finalizar. SIGINT/SIGTERM del coordinador termina y recoge el grupo del hijo, escalando a SIGKILL si no responde, antes de registrar interrupción.

Completed significa resultados técnicos terminados, no aceptación. El padre verifica registros y checkpoint y transiciona a verified; el miembro acepta atómicamente su primer intento verified. La métrica no decide entre intentos. Resume revalida verified; no lo repite ni lo degrada silenciosamente. Completed conserva evidencia para reconciliar. Un fallo entre archivo y registro conserva ambos estados sin borrar evidencia parcial.

## Persistencia y artefactos

La revisión `20260912_01`, hija de `20260911_02`, añade `train_execution_sessions`, `train_execution_records` y `campaign_execution_events`. No modifica las migraciones aplicadas 01/02. Amplía las guardas reservadas de verified/accepted_attempt_id.

TRAIN nuevo por CLI individual y por campaña usa `execution/train.py`; mantiene dataset explícito para el individual. Guarda configuración/snapshot/entorno, runtime por fase, épocas y métricas/LR, selección por época, evidencia de predicciones VAL por muestra, calibración y resultados, identidad/hash/tamaño/versión de checkpoint, completitud y verificación en PostgreSQL. Las predicciones se almacenan como lotes JSONB con muestras identificadas por ruta relativa sellada; la clave de lote es run/kind/phase/record_key. No genera CSV ni resultados JSON laterales.

Cada run tiene directorio exclusivo creado con exist_ok=False. Cada época conserva su propio checkpoint; no existe sustitución por latest/final_model. La aceptación selecciona el epoch exacto de la política y comprueba hash/tamaño, carga y firmas E3, así como secuencia de épocas, fases, predicciones y calibración. Los identificadores de versión de checkpoint se registran en los artefactos estructurados E5; los consumidores de linaje/versiones EVALUATE/EXPLAIN deben adaptarse en E6 y no deben asumir que este flujo publica una versión.

La CLI individual no admite inferencia TEST ni `--threshold-output-json` en esta vía. EVALUATE/EXPLAIN legacy y los helpers históricos de `training/trainer.py` siguen presentes y pueden contener escritores antiguos; el entrypoint CLI TRAIN ya no los invoca. No se ha eliminado código histórico por conveniencia.

Los códigos de lote son 0 (matriz completa verified), 2 (incompleta) y 3 (fallo sistémico/interrupción). El resumen cuenta miembros una sola vez, intentos por separado, aceptados, causas, finalización operativa y cumplimiento clínico registrado. Excluidos y agotamiento de intentos pueden dar finalización operativa sin matriz verificada. No hay ranking ni promoción.

## Validación e instalación autorizadas

Primero, sin instalar en public:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE5_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaign_executor_postgres.py -k 'not public_e5_revision_readonly'
```

Esperado: 13 aprobadas, una deseleccionada. El fixture crea esquema sintético, aplica E4+E5 allí, revierte y comprueba ausencia desde otra conexión. El caso concurrente hace commits sólo en ese esquema y lo elimina con comprobación posterior. No usa campañas operativas.

Renderizado y precheck:

```sh
make db-migrate-check
docker compose exec -T backend python -m alembic upgrade 20260911_02:20260912_01 --sql
```

Sólo tras aprobar las pruebas sintéticas y verificar el precheck, aplicar mediante el wrapper autorizado por la solicitud E5:

```sh
make db-migrate
```

El wrapper conserva backup/preflight/upgrade. No saltar sus controles. Después ejecutar la suite E5 completa (mismo comando pytest sin `-k`; esperado 14 aprobadas), `make db-migrate-check` y comprobaciones `/ready` del procedimiento del repositorio. En esta sesión no se ha aplicado la migración.

No se acredita durabilidad ante reinicio o commit incierto. La prueba after_accept inyecta un error de aplicación posterior al método, no una pérdida real de confirmación de PostgreSQL. La aprobación técnica no acredita rendimiento clínico ni autoriza campañas extensas.
