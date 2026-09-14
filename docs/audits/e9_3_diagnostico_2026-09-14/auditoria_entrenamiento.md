# E9.3 — Diagnóstico y verificación TRAIN, sesión 2026-09-14

**EN SEGUIMIENTO. No aprobada: 0/36 TRAIN verificados.** Esta sesión no crea campañas ni coordinadores, no reanuda intentos activos, no aplica migraciones, no ejecuta EVALUATE/EXPLAIN/ensembles/TEST ni activa aprendizaje ponderado. E9.2 sigue parcial; no bloquea el TRAIN existente. E9.4 no iniciada.

## Estado y alcance del coordinador

Snapshots del 2026-09-14 16:40:32.891432 UTC y **16:44:18.662913 UTC / 13:44:18.662913 America/Santiago**. Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`: active, 36 miembros = **32 pendientes +1 activo +3 fallidos +0 completed +0 verified**, 4 intentos (todos ordinal1; cero reintentos adicionales). El inventario completo está en snapshot_final_sesion.json; contiene también la antecesora, separada y pausada.

Se leyeron operación/protocolos y referencias E9 disponibles en la sesión; revisión del código y cambios locales preservados en manifiesto. E5 execute_campaign lanza sólo execution.worker→train, espera, verifica y finaliza; no encadena EVALUATE. Las 12 configuraciones E7 tienen calibrate_threshold=false y evaluate_best_on_test=false. El registro interno llamado calibration contiene estado disabled/threshold0.5 cuando finaliza TRAIN; **no es búsqueda de umbral**. No se cambió ese contrato.

Padre PID3475 y worker PID64462, Run ID `61bf6d6d-9db9-498e-a9ee-c26e94e46f2d`, Custom CNN/Adam/seed11. Host y argumentos coinciden; start_ticks21995365 estable. Entre snapshots utime2846940→2989225 y stime1194190→1257260: actividad confirmada. El coordinador ya existente continúa; no se abrió otro ni se envió señal. El snapshot final registra su avance disponible; el estado actual posterior debe consultarse en PostgreSQL.

## Fallos de esta campaña

| Run / Custom CNN-Adadelta | Semilla | Inicio UTC | Fin persistido UTC | Épocas íntegramente registradas | Clasificación |
| --- | ---: | --- | --- | ---: | --- |
| a5f36df1-3341-43fd-94b9-ee1cedb834c5 | 11 | 11:47:21.982186 | 13:01:39.652646 | 4 | Recursos/OOM probable; causa individual no confirmada |
| 8ebbd308-2cec-4275-93b7-ad56fa9e6931 | 29 | 13:01:49.723820 | 14:13:10.462958 | 6 | Recursos/OOM probable; causa individual no confirmada |
| 3894deef-252f-424e-a4ad-d6cd555e063e | 47 | 14:13:20.574288 | 15:27:23.155640 | 7 | Recursos/OOM probable; causa individual no confirmada |

Todos terminan sin phase/completion/calibration, durante la fase base o antes de registrar su cierre; no se puede identificar la instrucción exacta. Persisten epoch/artifact_prepared/artifact/selection/predictions por época y runtime. El estado genérico CHILD_EXIT_OR_INCOMPLETE_RESULTS no guarda código de salida. El padre lo conoce transitoriamente pero lo descarta al persistir la causa. No se inventa exit137, SIGKILL ni una traza faltante.

**Confirmado a nivel contenedor:** memory.events oom_kill=3. No identifica PIDs/horas. **Probable a nivel de runs:** concordancia del número de muertes con los tres fallos y presión de RAM observada, sin evidencia temporal/PID para asignación definitiva. No se suman ni confunden los tres fallos históricos anteriores por tipo Adadelta (antecesora) con estos nuevos fallos tras varias épocas.

A las16:41:31 UTC, cgroup usa6492561408 bytes; worker RSS6165600kB, HWM6889960kB, swap652756kB,103threads. VM aproximadamente8GB; al snapshot inicial MemAvailable711860kB. No es evidencia de GPU OOM: no hay GPU visible acreditada y los contadores son de memoria del sistema. memory.max=max no acredita capacidad física ilimitada.

Docker events OOM en intervalo11:40–16:41 UTC no devolvió eventos retenidos; no contradice el contador kernel ni demuestra que no hubo OOM. dmesg no accesible; no se elevaron privilegios del contenedor ni modificaron servicios para accederlo. No se reprodujo OOM con otro entrenamiento.

Datos/almacenamiento: no hay una excepción concreta registrada que los incrimine; las épocas guardadas y los checksums coincidentes apoyan integridad de lo persistido, sin descartar un error posterior desconocido. Serialización/código/coordinación: causa específica no determinada. No atribuirlo a mala sensibilidad ni retirar semillas por rendimiento.

## Artefactos y linaje

A las16:42:09 UTC se releyeron registros de los tres intentos terminales fallidos y se verificaron **17/17 checkpoints**, cada uno5150212 bytes, SHA-256 coincidente con payload PostgreSQL. Total87553604 bytes. Se usó file_identity del proyecto. No se hashearon archivos del worker activo ni se cargaron modelos incompletos. `checkpoints_fallidos.json` preserva evidencia individual.

Las referencias configuración/seed/dataset/environment se contrastan con contrato en el snapshot; fuente actual coincide con la congelada. Las sesiones fallidas tienen completion ausente. Los UUID de versión presentes en payloads intermedios no sustituyen una model_version relacional completa. No se selecciona la última versión ni se declara continuación exacta desde un checkpoint parcial.

No hay completed/verified aplicables para validación integral/carga segura. Los17 hashes **no equivalen a17 TRAIN ni a3 TRAIN aceptados**. La siguiente sesión deberá validar cualquier completed mediante verificador oficial, carga segura, registros completos, versión/checkpoint/linaje y lectura desde conexión nueva. No actualizar verified manualmente ni reconstruir metadatos ausentes por suposición.

Asociación de campaña: la ruta oficial actual crea intento→miembro→campaña y TRAIN en la misma transacción; las filas pertenecen al ID explícito. La columna directa runs.campaign_id no existe; su migración nullable/escritores sigue preparada en docs/engineering/campaign_scope_2026-09-14. No imponer NOT NULL global, no backfill de históricos ni inventar otra campaña para superar la guarda de fuente.

## Corrección preparada y prueba

Defecto de diagnóstico confirmado en fuente: el código de salida se pierde en favor de un texto genérico. `retener_exit_code.patch` conserva CHILD_EXIT_-9/2/etc o CHILD_EXIT_0_INCOMPLETE_RESULTS. Es **parche preparado, no aplicado**: no corrige OOM por sí mismo ni atribuye exit-9 a OOM automáticamente.

`prueba_parche_preparado.py` prueba en memoria el candidato con repositorio/proceso simulados, exit-9,2,0 con sesión incompleta. Resultado real Compose: **3 casos sintéticos aprobados**; cero BD y cero subprocess/fit. Se conserva fuente viva sin cambios. No se presentan las31 pruebas históricas como repetidas.

No aplicar parche al worker/coordinador activo: nuevos claims recalculan huella de fuente. Cambiar el archivo produciría conflicto con la campaña congelada. Antes de desplegarlo se requiere límite seguro y transición de revisión acreditada **conservando esta campaña**; no editar environment/hash para fingir compatibilidad ni crear otra campaña, ambas acciones fuera de esta autorización.

## Recursos y límite seguro: procedimiento pendiente

La arquitectura ya aísla cada TRAIN en proceso: añadir clear_session entre hijos no explica/resuelve por sí solo consumo dentro de un hijo. La ruta usa map y prefetch AUTOTUNE; acotar buffers/paralelismo puede ser candidato, pero no está demostrada la causa y puede afectar orden/RNG de aumentación. No se cambian batch,resolución,precisión,optimizer ni épocas.

Antes de una corrección de memoria: observar consumo por época/último registro sin relanzar; instrumentar exit/PID/tiempo/contadores en límite seguro; probar con fixtures acotados igualdad de etiquetas/orden y transformaciones bajo mismas semillas entre implementación anterior y candidata; medir memoria. Si cambia semántica o no se acredita, requiere enmienda, no un ajuste silencioso. No aumentar memoria sin acreditar RAM del host.

El coordinador ofrece pause en ExecutionRepository: bloquea siguientes claims sin matar el TRAIN ya activo, y triggers permiten finalizar/verificar el intento en paused. **No se invocó**: el alcance inspeccionado es sólo TRAIN y el usuario pide dejarlo continuar. Si se requiere detener nuevos claims para una corrección, debe ejecutarse ese mecanismo en la transición operativa correspondiente, no SIGKILL. No editar fuente esperando que un worker ya importado la incorpore.

No hay filtro oficial para bloquear sólo un miembro fallido manteniéndolo pendiente de diagnóstico: claim reintenta failed/interrupted tras pending, con máximo3 intentos. Antes de que alcance esos reintentos se requiere corrección acreditada o pausa oficial en límite seguro; no activar reintentos ilimitados ni reiterar manualmente los fallos sin nueva evidencia. No se lanzó ningún reintento en esta sesión. El diseño de transición compatible y el diagnóstico OOM por run siguen pendientes; no se ocultan cambiando la matriz.

## Seguimiento / recuperación

```sh
# Sólo consulta, no inicia otro coordinador:
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --inspect

# Prueba del parche preparado, no cambia código vivo ni escribe BD:
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B - \
  < docs/audits/e9_3_diagnostico_2026-09-14/prueba_parche_preparado.py
```

La recuperación oficial con --resume descrita en el plan E9.1 sólo procede sin propietario activo, fuente compatible y causa tratada. Reanuda campaña, no estado intraépoca. No ejecutar ahora. El coordinador/PIDs y ledger PostgreSQL son mecanismos reales existentes; no se promete monitorización por el asistente fuera de la sesión.

Publicación inicial/final idéntica en snapshot:81d69942-17eb-4999-a6bd-2b05779a65a4; deploymentcf2f20d3-a1e0-499c-b5ab-501b7c1ae198; versión172b7031-9f79-44e3-a7ad-2dc10a9ffd08. No se abrió TEST, ni evaluaciones posteriores. Resultado E9.3: **EN SEGUIMIENTO**, con presión de memoria y diagnóstico individual pendiente; no aprobación prematura.
