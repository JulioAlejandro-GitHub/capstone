# Diagrama de contenedores — Entrega 2

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; diagrama objetivo de Architecture Baseline v1.1.
> **Snapshot:** Entrega 2, previo a la implementación incremental.

```mermaid
flowchart TB
  B[Browser]
  API[FastAPI API\n/api/v1]
  WK[Python workers\nmalaria_dl canónico]
  PG[(PostgreSQL\nmetadatos + cola + auditoría)]
  LS[LocalStorageProvider\nstorage://]
  ML[Clasificador Etapa 1 reutilizado]
  DET[CellDetector adapters]

  B -->|HTTPS + polling| API
  API -->|transacciones cortas| PG
  API -->|stream/upload/access reference| LS
  WK -->|claim SKIP LOCKED, heartbeat, resultados| PG
  WK -->|read/write artifacts| LS
  WK --> DET
  WK --> ML
```

Estado actual: `backend_api/app/main.py`, React/Vite, PostgreSQL y filesystem ya existen; `TraceableInferenceService.infer()` es síncrono. Estado objetivo: API y workers son procesos del mismo monolito modular, comparten contratos, pero la API nunca ejecuta el pipeline pesado.

No se incorporan Redis, Celery, RQ, Dramatiq, RabbitMQ, object storage cloud ni WebSocket/SSE en el MVP.
