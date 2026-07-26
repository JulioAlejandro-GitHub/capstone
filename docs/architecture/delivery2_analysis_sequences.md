# Secuencias de análisis — Entrega 2

## Imagen rechazada por calidad

```mermaid
sequenceDiagram
  actor U as Operator
  participant API
  participant S as StorageProvider
  participant Q as Quality Service
  participant DB as PostgreSQL
  participant UI as React
  U->>API: upload image
  API->>S: put_original
  S-->>API: URI + SHA + metadata
  API->>DB: image + quality assessment created
  API->>Q: assess(image, policy)
  Q->>DB: rejected + metrics + reasons
  API-->>UI: 422 QUALITY_REJECTED + assessment
  Note over DB: No analysis_job, detection_run or crops
```

## Flujo completo aceptado

```mermaid
sequenceDiagram
  actor U
  participant API
  participant Q as Quality
  participant DB
  participant W as Worker
  participant S as Storage
  Q-->>API: accepted assessment
  U->>API: create analysis job
  API->>DB: created + assignments; queued
  W->>DB: atomic claim + lease
  W->>S: open original
  W->>DB: detecting
  W->>DB: detections progressively
  W->>S: put crops
  W->>DB: crops ready progressively
  W->>DB: predictions per crop/model
  W->>S: put explanations
  W->>DB: aggregate + completed/partial
  API-->>U: polling state/cells/result
```

## Detección y crops

```mermaid
sequenceDiagram
  participant O as Orchestrator
  participant D as CellDetector
  participant DB
  participant C as Crop Generator
  participant S as Storage
  O->>D: detect(image URI, global contract, config)
  D-->>O: boxes local/global + scores
  O->>DB: detection run + detections
  loop each valid detection
    O->>C: bbox + crop policy
    C->>S: put_artifact create-only
    S-->>C: crop URI + SHA
    C->>DB: crop ready / cell error
  end
```

## Multimodelo

```mermaid
sequenceDiagram
  participant O as Orchestrator
  participant G as Governance Resolver
  participant M1 as Primary classifier
  participant M2 as Additional classifier
  participant DB
  O->>G: resolve frozen assignments
  G-->>O: active publications + checkpoint snapshots
  par per assignment
    O->>M1: batch crops
    M1-->>DB: individual predictions
  and
    O->>M2: batch crops
    M2-->>DB: individual predictions
  end
  Note over DB: Results remain parallel; no ensemble
```

## Explicabilidad

```mermaid
sequenceDiagram
  participant O as Orchestrator
  participant X as XAI Adapter
  participant S as Storage
  participant DB
  O->>X: prediction + exact model + crop, gradcam automatic
  alt success
    X->>S: explanation artifact
    X->>DB: completed result linked to prediction
  else technical limitation/failure
    X->>DB: unavailable/failed with error
  end
  Note over O,DB: Prediction stays valid
  O->>X: LIME/SHAP priority or on-demand
```

## Revisión humana

```mermaid
sequenceDiagram
  actor R as Reviewer
  participant UI
  participant API
  participant DB
  UI->>API: prediction + crop + original context + XAI
  API-->>UI: immutable automatic result + review history
  R->>API: corrected/confirmed/uncertain + reason
  API->>DB: append expert_review + audit before/after
  DB-->>API: review revision
  API-->>UI: automatic and human results side by side
```

## Linaje completo

```mermaid
flowchart LR
  SUB[subject]-->SAM[sample]-->IMG[full image]-->QC[quality assessment]-->JOB[analysis job]
  JOB-->PV[pipeline version]-->DR[detection run]-->DET[detection]-->CR[crop]
  CR-->CP[cell prediction]-->XR[XAI result]
  JOB-->IR[image result]-->ER[expert review]-->REP[report]
  CP-->MV[model version]-->PUB[stage2 publication]-->SLOT[stage2/default or assignment]
  MV-->TR[TRAIN]-->EV[EVALUATE]
  MV-->CHK[checkpoint SHA]
  TR-->DS[dataset version]
  CP-->PRE[preprocessing + threshold + mapping + Git]
```

## Fallos parciales

- Detector total: job `failed`, sin clasificación, retry permitido.
- Detección/crop individual: demás células continúan; cierre `partial_failure`.
- Batch clasificación: retry; si persiste, dividir; completed no se duplica.
- Modelo: otros assignments continúan; resultado de modelo partial/failed.
- XAI: prediction válida; XAI failed/unavailable y retry on-demand.
- Aggregator: conservar entradas; reconstrucción idempotente; job partial.
- Report: job permanece completed/partial; report failed regenerable.

## Dependencia entre prompts

```mermaid
flowchart LR
  P2[Foundation]-->P3[Data]-->P4[Storage/Ingest]-->P5[Quality]-->P6[Queue]
  P4-->P7[NIH Dataset]-->P8[Detector]-->P9[Crops]-->P10[Classifier]
  P6-->P8
  P10-->P11[Aggregation]-->P12[XAI]-->P13[Review]-->P14[Workbench]-->P15[Report/Validation]
```

