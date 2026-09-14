# E9.3 — TRAIN en seguimiento, sin cierre

Autorización del usuario: dejar continuar coordinador existente y verificar TRAIN; sin evaluaciones posteriores ni cambios TEST/publicación. **E9.3 no completada; E9 no aprobada.** No se inició un coordinador, no se reanudó ni se detuvo trabajo.

## Estado observado

Snapshot consistente REPEATABLE READ, READ ONLY: **2026-09-14 15:46:56.574274 UTC / 12:46:56.574274 America/Santiago**. Campaña `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`, active: 36 miembros, **32 pendientes, 1 activo, 3 fallidos, 0 completados/verificados**, 4 intentos. Fuente vigente igual al environment congelado; no se tocaron src/configs.

| Miembro | Run ID | Estado | Épocas registradas |
| --- | --- | --- | ---: |
| Custom CNN/Adadelta/11 | a5f36df1-3341-43fd-94b9-ee1cedb834c5 | failed | 4 |
| Custom CNN/Adadelta/29 | 8ebbd308-2cec-4275-93b7-ad56fa9e6931 | failed | 6 |
| Custom CNN/Adadelta/47 | 3894deef-252f-424e-a4ad-d6cd555e063e | failed | 7 |
| Custom CNN/adam/11 | 61bf6d6d-9db9-498e-a9ee-c26e94e46f2d | active | 1 |

La identificación de cada configuración procede del contrato por hash, no de una inferencia por orden. Cada fallido conserva artifact/artifact_prepared/epoch/predictions/selection por época y runtime, pero no phase/completion. Su causa persistida es CHILD_EXIT_OR_INCOMPLETE_RESULTS. No se aceptan checkpoints intermedios como TRAIN completado ni se excluyen semillas por desempeño.

## Actividad y recursos

Padre PID3475 y worker PID64462 presentes, mismo host, argumentos correspondientes. Entre 15:46:56 y15:47:51 UTC el start_ticks del worker permanece21995365; utime aumenta733314→781018 y stime333429→342403. **Actividad confirmada**. No duplicar ni invocar resume.

A las15:47:51 UTC: memoria de cgroup6564876288 bytes; worker VmRSS6071412kB y máximo observado6889960kB,103 threads. memory.events registra oom_kill=3, oom=0, memory.max=max. El contador oom_kill acredita que hubo tres muertes por OOM en este cgroup; no permite asignar automáticamente cada una a los tres runs fallidos ni determinar el instante. memory.max=max no significa memoria física infinita. El preflight histórico observó una VM de aproximadamente8GB.

El código usa map/prefetch AUTOTUNE. Esto es una vía de consumo que merece investigación, **no una causa demostrada ni una corrección aplicada**. No se modificaron batch, paralelismo, fuentes, presupuesto, servicios o memoria mientras el coordinador sigue activo. La combinación de fallos incompletos y presión de memoria impide acreditar que el presupuesto total finalizará con estos recursos. Preservar los intentos y obtener diagnóstico específico antes de proponer correcciones operativas; no reinterpretarlos como fallo clínico.

## Verificación y límites

No hay sesiones completed/verified que verificar íntegramente en esta observación. El script reutilizado E9.1 compara configuración/dataset/environment contra contrato y, sólo para completadas, comprueba documentación/bytes sin cargar modelos; aquí no aplicó esa rama. No se ejecutó inferencia, calibración ni EVALUATE. La verificación completa de TRAIN seguirá correspondiendo al coordinador y sus validadores antes de estado verified. No se escribe ese estado manualmente.

TEST: snapshot sin identidades E6/locks; no se abrió. La referencia de publicación leída coincide con E9.1: publicación81d69942-17eb-4999-a6bd-2b05779a65a4 y deploymentcf2f20d3-a1e0-499c-b5ab-501b7c1ae198, versión172b7031-9f79-44e3-a7ad-2dc10a9ffd08. No se modificaron.

No se ejecutó aprendizaje ponderado. La nueva propuesta se guarda fuera del árbol src/configs recargable. La aprobación pendiente de esa enmienda no se usa para detener TRAIN.

## Seguimiento reproducible

Consulta únicamente de estado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --inspect
```

Snapshot usado: comando Compose con entrada `docs/audits/etapa_9_1_consulta_2026-09-14.py`, salida preservada en `etapa_9_3_snapshot_2026-09-14.json`. Observación de recursos mediante lectura de `/sys/fs/cgroup/memory.events`, memory.current, memory.max y `/proc/{PID}/stat,status`. Sin señales a procesos.

Próxima acción operativa: continuar seguimiento del propietario actual y sus registros. No ejecutar otro coordinador ni reanudación mientras siga activo. Cualquier intervención sobre memoria/código requiere un procedimiento posterior compatible con la fuente congelada y la instrucción de mantener actividad. Este informe es un punto de seguimiento, **no cierre prematuro de E9.3**.
