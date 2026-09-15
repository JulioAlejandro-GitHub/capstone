# E9.3: operación secuencial global preparada

Decisión del usuario del 14/09/2026: un experimento global en ejecución y avance automático de la campaña; la optimización de memoria no es requisito previo. Esta preparación no autoriza activar la campaña.

Campaña: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`. Dataset único: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. Se conservan matriz, split, hashes, semillas y configuración científica. TEST permanece cerrado. E9.2 parcial; no se inicia E9.4.

## Contrato técnico

El coordinador mantiene un advisory lock PostgreSQL global, una identidad de propietario y evidencia de procesos. Los triggers requieren propietario vigente y los índices parciales excluyen TRAIN/assessment concurrentes, incluso entre campañas. Las rutas de coordinador, standalone, intento controlado y assessment utilizan el mismo cerrojo. La reserva y el vínculo de revisión son transaccionales. No se completa ninguna asociación histórica por inferencia ni se impone campaign_id NOT NULL global.

Cada hijo espera un handshake antes de ejecutar. Se registra PID, inicio y sesión; se espera su terminación y la de descendientes, incluidos nietos adoptados mediante subreaper. La comprobación del checkpoint usa un proceso desechable con el cargador oficial. Sólo después de verificar artefactos y persistir la verificación se permite reservar el siguiente. El cierre de una conexión no demuestra liberación de recursos. Una desaparición sin evidencia de liberación, o un proceso de otro host/namespace, bloquea la ejecución: no hay expiración que lo dé por terminado automáticamente.

Política `e93_sequential_v1`: pendientes primero, orden congelado; presupuesto de intentos congelado (máximo 3), sin reintentos ilimitados. Dos fallos técnicos consecutivos dentro de un coordinador pausan; un nuevo incremento de oom_kill o menos de 1 GiB disponible abre el circuito inmediatamente. Se conservan código de salida, fase y Run ID. Un checkpoint inválido impide avanzar. La pausa solicitada entre trabajos conserva el trabajo activo y detiene nuevas asignaciones.

El GiB es margen de admisión, no garantía de que un modelo quepa. Los OOM anteriores ocurrieron con un TRAIN: la secuencialidad no los resuelve ni acredita optimización. Las atribuciones individuales antiguas siguen siendo probables. Si reaparecen, queda pausado antes de consumir la matriz. El entorno soportado es Linux en Compose y la base canónica; no se acredita coordinación con sistemas ajenos a estas rutas.

## Instalación futura: NO ejecutada

1. Confirmar pausa y ausencia física de coordinador, TRAIN e hijos. Revisar auditoría y hashes. Conservar respaldo y revisión original.
2. Ejecutar `make db-migrate-check`. Revisar el SQL preparado. Para reproducirlo:

```sh
docker compose exec -T backend python -B -m alembic upgrade 20260912_02:20260914_02 --sql
```

3. Tras autorización de instalación, usar exclusivamente `make db-migrate`: backup, preflight transaccional y rollback del wrapper. Instala las revisiones 20260914_01 y 20260914_02; no reinicia contenedores. Agrega tablas, triggers e índices y requiere un límite sin trabajos activos. Si encuentra activos incompatibles, falla sin limpiar registros. No sustituir por `stamp` ni saltar el wrapper.
4. Revisar y aprobar `revision_propuesta.json`, actualizar su autorización y hashes si cambió el código, y registrar la revisión mediante `src.malaria_dl.execution.controlled register`. No sobrescribir la fuente congelada. Consultar `--help` y usar la campaña/dataset explícitos, member `2fbd5862-b68b-4845-9445-a30d7ec61382` y previous-attempt `8279db36-7bfe-4e22-8bf3-872ac215eae2`. Elegir y conservar un UUID de revisión para idempotencia. Este registro no activa el intento controlado.
5. Con `PYTHONHASHSEED=42`, repetir dry-run con `--technical-revision-id UUID`. El preflight E1 canónico debe validar archivos sellados antes de cualquier reserva; el dry-run no sustituye esa lectura íntegra.
6. Sólo con autorización posterior de activación, ejecutar un único coordinador:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONHASHSEED=42 -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
  --technical-revision-id UUID_APROBADO \
  --artifact-root /app/var/artifacts/campaign_runs --resume
```

La cola secuencial avanza automáticamente; controlled execute conserva su alcance de un intento y pausa. Nunca lanzar ambos. Un circuito exige diagnóstico y reconocimiento explícito mediante `src.malaria_dl.execution.global_gate ack-breaker --reason MOTIVO` antes de una reanudación autorizada. Ese comando no reanuda ni permite eludir ausencia de prueba sobre procesos. No ejecutar reconocimientos repetidos para forzar intentos.

## Seguimiento reproducible sin escrituras

```sh
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 \
 backend python -B - < docs/audits/e9_3_secuencial_global_2026-09-14/comprobar_solo_lectura.py
```

La auditoría complementaria contiene snapshot, dry-run, propuesta, SQL offline y resultados de pruebas. El SQL offline no acredita instalación pública. Una caída sin prueba de salida necesita recuperación auditada; no se ofrece un desbloqueo forzado.
