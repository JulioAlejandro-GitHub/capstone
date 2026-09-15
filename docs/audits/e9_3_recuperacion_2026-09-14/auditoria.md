# Recuperación E9.3 — 2026-09-14

**BLOQUEADA para ejecutar el intento controlado; campaña paused, sin TRAIN activos.** Snapshot final 2026-09-14 22:24:02.366267+00:00 UTC (America/Santiago UTC−3). 36 experimentos:31 pendientes,5 fallidos,0 activos,0 completados,0 verificados;5 intentos,0 adicionales. E9.2 PARCIAL; E9 no aprobada.

El TRAIN ec0975b2-b355-4d5c-a4ec-beac31da72dd terminó failed a 2026-09-14 22:16:30.081125+00:00, después de12 épocas persistidas; no phase/completion ni TRAIN final válido. La consulta actual no registra sesiones activas y el barrido de /proc a22:21:57 UTC no encontró run_train/execution.worker. PID3475 y96740 ya no ejecutan. La pausa previa impidió el siguiente experimento: siguen los mismos cinco intentos. No hubo nueva intervención, señales, reinicio ni reintento.

OOM: memory.events oom_kill=5 (antes4); memory.current=625451008 bytes sin TRAIN. OOM del cgroup confirmado, atribución individual probable, no demostrada; no GPU OOM confirmado. Las causas persistidas antiguas siguen CHILD_EXIT_OR_INCOMPLETE_RESULTS. El nuevo diagnóstico no reconstruye retroactivamente códigos perdidos.

## Corrección efectiva

Después de acreditar ausencia de procesos, aplicado el parche de execution/campaign.py: conserva CHILD_EXIT_<código> para no cero y distingue CHILD_EXIT_0_INCOMPLETE_RESULTS. No cambia criterios de éxito, checkpoint ni ciencia. Fuente anterior guardada en campaign_original.py.txt, además de HEAD inicial1fc5201474bb158a8f84d12b543b255abb1d3d7e. Cambios documentales de pausa preexistentes preservados. Tests nuevos test_campaign_exit_diagnostics.py y regresión test_campaign_executor_e5.py: **21 passed,2 warnings de deprecación protobuf**,5.61s, ejecutados en Compose sin TRAIN ni BD operativa sintética.

Comando real:

```sh
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m pytest -q -p no:cacheprovider tests/test_campaign_exit_diagnostics.py tests/test_campaign_executor_e5.py
```

Fuente anterior usada por los cinco intentos: d8569d8faaa80eca42b130e6096203d851e2c663b4cdb8cd599dda950fbe6430.
Fuente corregida local: 5486ecaaa0e3db6a78eae17c208d22e2879d5f1aad2d4360616c1ef8d8785523.
El contrato y sus configuraciones originales permanecen en snapshot_inicial/final, sin modificaciones PostgreSQL. Los cinco Run IDs/miembros/ordinales y environment original constan allí. **La revisión corregida todavía no está autorizada/registrada en el contrato operativo ni ha ejecutado intentos.** El manifiesto registra archivos/hashes, no sustituye el mecanismo de revisión.

## Bloqueos y procedimiento

El parche conserva diagnóstico, no es una corrección demostrada de consumo RAM. No se afirma haber identificado la causa exacta del crecimiento. La revisión acotada y propuesta de comprobación constan en transicion_y_unico_intento.md. No se cambió prefetch, concurrencia, batch, resolución, precisión, optimizador o semillas.

Contrato actual exige environment original en preflight, worker y SQL; no admite revisión alternativa ni ejecución única de miembro fallido con campaña pausada. --resume seleccionaría pendientes antes de fallidos y puede encadenar trabajos. No se ejecutó. Preparada especificación mínima de migración append-only de revisiones, permiso único transaccional y validadores conservando linaje, más pruebas/instalación. No está implementada ni instalada: se documenta el bloqueo antes de ejecutar, conforme a la condición del usuario.

Representante determinista preparado: posición0, CustomCNN/Adadelta/11, Run anterior a5f36df1-3341-43fd-94b9-ee1cedb834c5. Intento controlado **NO EJECUTADO**; no se inventó Run ID, no se consumió presupuesto ni se atribuyó éxito.

Publicación/deployment relectos desde otra conexión y sin diferencias. TEST cerrado, sin EVALUATE/EXPLAIN/E9.4. No se cambiaron históricos/campaign_id ni se hicieron migraciones. Campaña queda paused.

Siguiente acción concreta: completar diagnóstico sintético acotado de RAM y desarrollar/verificar la extensión descrita; revisar su migración por wrapper preflight/backup antes de instalar. Después, una sola reserva del representante, desde cero y con revisión explícita, manteniendo paused. No hay comando de recuperación seguro disponible hoy; no usar --resume como sustituto.
