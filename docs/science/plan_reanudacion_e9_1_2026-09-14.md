# E9.1 — Plan preparado, sin ejecutar reanudación

Campaña a conservar: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`. Al snapshot 2026-09-14 09:24:39 America/Santiago: 1 activo y 35 pendientes. Actividad confirmada; **no ejecutar ahora un segundo coordinador, ni siquiera con --resume**. La antecesora `ec442763-7eea-499d-a94f-9a3ddfb7c0f0` sigue pausada, con fuente incompatible: no reanudarla.

| Condición de entrada | Acción preparada | Efecto esperado | Control posterior | Riesgo de duplicación | Dependencias |
| --- | --- | --- | --- | --- | --- |
| Actividad confirmada actual | Dejar continuar; consulta A | Sólo lectura del estado | Conteos e intentos fechados, época persistida y proceso asociado | No crear coordinador adicional | Compose disponible |
| Sospecha de detención | Consulta B y revisión de /proc por host/PIDs con dos observaciones | Diagnóstico, sin alterar sesiones | Correspondencia de Run ID, start_ticks y actividad; no interpretar sólo antigüedad | No intervenir si padre/hijo vivos o estado indeterminado | Acceso al mismo host; si no, obtener observación del propietario |
| Padre e hijo probados ausentes conforme a dead_local; fuente/environment compatibles; fuente original preservada | Comando C con --resume, **escritura preparada, no ejecutada** | Reconciliar sesiones, verificar completados y crear intentos conforme al presupuesto | Consulta A y nuevo intento/owner; verificar ausencia de otro coordinador | Asegurar que nadie lanza simultáneamente; --resume rechaza propietario no probado muerto | Revalidación E1 ejecutada por preflight oficial, PostgreSQL, permisos y ARTIFACTS_ROOT disponible |
| Completado sin verified | Misma recuperación oficial C, sólo tras cumplir sus condiciones | Validación de registros/checkpoint por E5 antes de aceptar | Estado verified o fallo explícito | No marcar verified por SQL ni elegir checkpoint por fecha | Carga del modelo pertenece a subetapa operativa posterior, no E9.1 |
| Intento failed/interrupted y presupuesto disponible | El coordinador oficial aplica claim; no creación manual | Nuevo ordinal/Run ID del mismo miembro; conserva historial | Configuración-semilla iguales y ordinal incrementado | Un reintento no aumenta los 36 miembros | Hasta 3 intentos por miembro; sin modificar estado o presupuesto |
| Código cambiado o propietario remoto/no observable | No ejecutar C; delimitar cambio o recuperar evidencia del host | Evitar recuperación insegura | Compatibilidad acreditada antes de operar | No eludir FROZEN_CODE_ENVIRONMENT_CONFLICT | Requiere decisión/desarrollo posterior si no puede probarse compatibilidad |
| Pesos ponderados ausentes | Mantener ese ensemble pendiente | TRAIN individuales pueden continuar | Pesos/procedencia predeclarados antes de comparar | No normalizar, inventar pesos ni optimizar con TEST | Decisión científica pendiente; fuera de E9.1 |

## A. Consulta de estado — sólo lectura

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 --inspect
```

Para conteos relacionados consistentes, usar B. A se apoya en las lecturas del repositorio pero no se presenta como un único snapshot de todas sus consultas.

## B. Conciliación reproducible — sólo lectura

Desde raíz del repositorio:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B - \
  < docs/audits/etapa_9_1_consulta_2026-09-14.py
```

El script ejecutado produce JSON de auditoría; no escribe resultados en PostgreSQL ni crea un ledger alternativo. En futuros casos completed, limita la comprobación a documentación/hash del checkpoint y omite explícitamente carga del modelo; no equivale a verified E5 completo. Nunca llama preflight/reconcile/claim. Para una segunda observación se conserva también el script de cierre con los PIDs de esta observación; esos PIDs **no deben asumirse vigentes en el futuro**. Obtener primero los PIDs de la sesión actual y verificar host/argumentos/start_ticks. No usar ese script para señalar procesos ni enviar señales.

## C. Reanudación — ESCRITURA PREPARADA, NO EJECUTADA

**No ejecutable ahora: el propietario actual está activo.** Sólo en una subetapa posterior autorizada y con todas las condiciones de la tabla:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B run_train_all_models.py \
  --campaign-id 3acf89b7-dc42-4b7a-8e2a-ca6ea024c344 \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
  --artifact-root /app/var/artifacts/campaign_runs --resume
```

`--resume` reanuda la **campaña**, no una época desde un checkpoint parcial. Cuando confirma una interrupción, conserva el intento y puede crear otro según la política; no continúa silenciosamente dentro del intento anterior. La elección del primer intento verified y el presupuesto se mantienen. No existe aquí una ruta segura para forzar recuperación de un propietario remoto/indeterminado: haría falta evidencia del host o desarrollo posterior de ownership/leases, no un UPDATE manual.

ARTIFACTS_ROOT actual es escribible pero no tiene volumen propio en Compose; no se acredita supervivencia a reemplazo del contenedor. No reiniciar ni recrear servicios para reanudar, ni mover rutas/artefactos sellados. Un problema de persistencia física debe resolverse mediante procedimiento autorizado posterior.

Ningún comando preparado abre TEST o altera pesos/protocolo/publicación. E9.1 termina en documentación; no inicia E9.2.
