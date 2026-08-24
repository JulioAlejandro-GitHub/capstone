# Diagrama de componentes — Entrega 2

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; diagrama objetivo de Architecture Baseline v1.1.
> **Snapshot:** Entrega 2, previo a la implementación incremental.

```mermaid
flowchart LR
  subgraph API[FastAPI]
    AUTH[Auth/RBAC]
    ING[Subject/Sample/Ingest]
    QC[Quality Service]
    JOB[Job Command/Query]
    GOV[Stage2 Governance]
    REV[Review/Report]
  end
  subgraph CORE[malaria_dl]
    STO[StorageProvider]
    QUE[PostgreSQL Queue]
    ORC[Pipeline Orchestrator]
    DINT[CellDetector]
    CROP[Crop Generator]
    CLS[CellClassifier Adapter]
    XAI[Explainability]
    AGG[Aggregator]
    AUD[Audit/Lineage]
  end
  AUTH --> ING
  ING --> STO
  ING --> QC
  QC --> JOB
  JOB --> QUE
  QUE --> ORC
  ORC --> DINT --> CROP --> CLS --> XAI
  CLS --> AGG
  XAI --> AGG
  GOV --> CLS
  REV --> AUD
  ORC --> AUD
```

Responsabilidades:

- `Quality Service` crea un assessment versionado antes del job.
- `PostgreSQL Queue` sólo reserva, arrienda y recupera jobs.
- `Pipeline Orchestrator` coordina stages; no implementa algoritmos.
- `CellDetector` retorna regiones candidatas, nunca clases parasitized/uninfected.
- `CellClassifier Adapter` conserva `0=uninfected`, `1=parasitized`.
- `Explainability` falla de forma no destructiva.
- `Aggregator` usa denominadores explícitos y lenguaje no diagnóstico.
- `Audit/Lineage` registra identidad, before/after, actor y correlación.
