# Consultas de solo lectura

Desde la raíz del repositorio:

```sh
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 backend python -B - < docs/audits/e9_3_intento_unico_2026-09-14/consultar.py
docker compose exec -T -w /app/malaria_dl_local_project -e PYTHONDONTWRITEBYTECODE=1 backend python -B - < docs/audits/e9_3_verificacion_2026-09-15/comprobar.py
docker inspect --format '{{.Id}} started={{.State.StartedAt}} restarts={{.RestartCount}} oom_killed={{.State.OOMKilled}}' capstone_backend
```

No ejecutar controlled execute/recover, ack-breaker ni --resume. El intento falló y la reserva quedó cerrada; el bloqueo OOM se conserva deliberadamente. No se necesita corregir estados manualmente. Antes de otro intento se requiere diagnóstico acotado de memoria y una corrección/requisito de recursos respaldado por evidencia, con autorización posterior.
