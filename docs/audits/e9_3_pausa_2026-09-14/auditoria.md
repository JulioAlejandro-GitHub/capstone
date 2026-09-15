# Pausa oficial E9.3 — 2026-09-14

Campaña: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`.

Autorización explícita del usuario: impedir nuevas asignaciones sin interrumpir el TRAIN activo. Se inspeccionaron `ExecutionRepository.pause`, `claim`, `_campaign`, el bucle `execute_campaign` y la migración E5. Pausa y claim bloquean la misma fila de campaña mediante SELECT FOR UPDATE. Pause confirma estado paused y evento en una transacción; claim comprueba estado bajo ese bloqueo antes de insertar. Una asignación que hubiera ganado el bloqueo primero podría existir y se conservaría; no se observó ninguna.

## Acción y lectura posterior

Antes: 2026-09-14 21:07:38.385236 UTC / 18:07:38 America/Santiago, campaña active, cinco intentos: cuatro failed y uno active.

Se invocó exclusivamente el método oficial:

```python
ExecutionRepository().pause(
    "3acf89b7-dc42-4b7a-8e2a-ca6ea024c344",
    "USER_AUTHORIZED_E9_3_PAUSE_BETWEEN_TRAIN",
)
```

Solicitud 21:07:38.394171 UTC; retorno tras commit 21:07:38.461420 UTC. Evento persistido a 21:07:38.450556 UTC. Se releyó desde conexiones posteriores con transacciones READ ONLY a 21:07:38.473749 y 21:07:53.491419 UTC: estado paused y evento idénticos. No se llamó claim para probar sobre datos operativos.

## TRAIN preservado

Run `ec0975b2-b355-4d5c-a4ec-beac31da72dd`, CustomCNN/Adam/semilla29. Coordinador PID3475 y worker PID96740, con start_ticks sin cambios. Después del commit el worker aumentó utime 3201826→3211635 y stime 1426579→1431207 en unos15 segundos: actividad efectiva confirmada, sin señales ni interrupción. Sigue active; último registro persistido 21:00:49 UTC, cinco épocas según comprobación precedente.

Cinco intentos antes y después, IDs idénticos: cero asignaciones concurrentes observadas y cero nuevos TRAIN en el intervalo. La pausa permanece y el coordinador oficial rechazará el siguiente claim. El padre todavía espera al hijo: su salida al llegar al límite queda pendiente de observación. No se afirma haber observado un rechazo futuro. El código captura ese rechazo, conserva paused y puede registrar SYSTEMIC_CAMPAIGNERROR; ese nombre genérico no implica que la pausa haya interrumpido el TRAIN.

## Alcance y estado final

Pausa persistida y barrera de nuevas asignaciones acreditada por lectura y revisión de sincronización; TRAIN activo continúa. No se reinició contenedor, mató proceso, lanzó coordinador ni reintentó trabajo. No se modificó código funcional. Sólo la pausa/evento autorizados y estos documentos fueron escritos. TEST no fue leído ni ejecutado. Publicación y deployment inicial/final idénticos, IDs 81d69942-17eb-4999-a6bd-2b05779a65a4 y cf2f20d3-a1e0-499c-b5ab-501b7c1ae198.

Siguiente acción: dejar terminar el hijo y comprobar estado terminal y ausencia de nueva asignación. No ejecutar --resume: levantaría la pausa. No se promete observación automática fuera de esta sesión. E9.3 permanece sin completar.

Evidencia completa: evidencia.jsonl (snapshot previo y resultado con lecturas posteriores, procesos, intentos y referencias). No contiene credenciales ni predicciones científicas.
