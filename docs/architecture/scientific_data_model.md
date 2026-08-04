# Modelo científico de Etapa 2

```mermaid
erDiagram
    RESEARCH_SUBJECTS o|--o{ SCIENTIFIC_CASES : "subject_id opcional"
    SCIENTIFIC_CASES ||--o{ BLOOD_SAMPLES : contiene
    BLOOD_SAMPLES ||--o{ SMEAR_SLIDES : produce
    SMEAR_SLIDES ||--o{ MICROSCOPY_IMAGES : captura
    USERS ||--o{ RESEARCH_SUBJECTS : crea
    USERS ||--o{ SCIENTIFIC_CASES : crea

    RESEARCH_SUBJECTS {
      uuid id PK
      varchar subject_code UK
      jsonb metadata_json
      varchar status
    }
    SCIENTIFIC_CASES {
      uuid id PK
      varchar case_code UK
      uuid subject_id FK
      varchar source_type
      varchar status
    }
    BLOOD_SAMPLES {
      uuid id PK
      uuid case_id FK
      varchar sample_code
      varchar status
    }
    SMEAR_SLIDES {
      uuid id PK
      uuid sample_id FK
      varchar slide_code
      varchar smear_type
      varchar status
    }
    MICROSCOPY_IMAGES {
      uuid id PK
      uuid slide_id FK
      varchar image_code
      text storage_key
      char sha256
      varchar status
    }
```

Las relaciones son `RESTRICT`; no existen endpoints DELETE. Los binarios viven fuera de
PostgreSQL. `microscopy_images` registra identidad, ubicación lógica, integridad y metadata
técnica. No representa una predicción ni altera la convención futura
`0=uninfected`, `1=parasitized`, `raw_model_score=probability_parasitized`.

## Trazabilidad

`GET /api/v1/scientific/cases/{id}/traceability` ejecuta un join ordenado y arma
caso/sujeto/muestras/frotis/imágenes. La respuesta no incluye `storage_key`, rutas absolutas,
actores ni metadata libre.

Prompt 4 incorpora `image_ingestion_batches`, procedencia externa separada y
metadata técnica detectada. `microscopy_images.id` queda como identidad estable
para futuros análisis; los binarios permanecen fuera de PostgreSQL.
# Extensión Prompt 5

`microscopy_analysis_runs` referencia sujeto, caso, muestra, frotis y lote.
`microscopy_analysis_run_images` congela inputs; assessments, eventos y
decisiones conservan resultados técnicos y trazabilidad append-only.

# Extensión Prompt 8

`cell_classification_runs` enlaza analysis/detection y una publicación activa.
Los runs nuevos usan snapshot publication-first v2; el deployment de snapshots
v1 se conserva sólo como identidad histórica. Sus inputs congelados producen
`cell_predictions`; explicaciones, summaries, eventos y reviews se relacionan
por FK `RESTRICT`. Predicción y summary automático son inmutables. La revisión
de clasificación es independiente de `scientific_reviews`.

Los PNG Grad-CAM viven en storage local. PostgreSQL conserva solamente claves
relativas, SHA-256, tamaño y dimensiones.
