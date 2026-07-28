# Capstone MIA — plataforma científica experimental

Monolito modular con FastAPI, React/TypeScript, PostgreSQL y `malaria_dl`. No es una
herramienta diagnóstica. La fundación de Etapa 2 se documenta en
`docs/engineering/local_development.md` y `docs/engineering/test_environment.md`.

La API `/api/v1/scientific` registra trazabilidad pseudonimizada caso → muestra → frotis
→ imagen (sólo metadata). Véanse `docs/architecture/scientific_data_model.md` y
`docs/engineering/scientific_api.md`.

Comandos principales: `make validate`, `make test`, `make test-db-up`,
`make test-db-bootstrap` y `make test-db-down`.
# Operación de la fundación

Backend y frontend se ejecutan localmente con Python y Node/Vite contra PostgreSQL 17.9
Homebrew y la base `malaria_experiments`. Docker no forma parte de la arquitectura
operativa, CI ni criterios de aprobación. Consulte
`docs/engineering/local_development.md`.

La ingesta protegida está disponible en `/frotis/cargar`: resuelve identidad
pseudonimizada y preserva originales en `var/storage`.
# Control técnico de calidad

El dominio Análisis de frotis incluye carga inmutable y quality gate técnico en
`/frotis/analisis`; permanece separado del entrenamiento y Modelo IA. Consulta
`docs/architecture/microscopy_quality_gate.md`.

# Clasificación celular experimental

Prompt 8 añade clasificación por crop con el único slot productivo
`stage2/default`, threshold publicado, predicciones automáticas inmutables,
Grad-CAM manual y revisión humana separada. El resultado agregado es
experimental: no constituye diagnóstico ni estimación de parasitemia. Consulte
`docs/architecture/cell_classification_pipeline.md`.

El precheck de Prompt 8 no encontró un `stage2/default` real: la publicación
activa de catálogo no es fallback y el workflow queda de forma segura en
`awaiting_productive_model`. La cadena de datos requiere Alembic
`20260728_01 → 20260728_02 → 20260728_03`. Consulte la evidencia y los gates
pendientes en `docs/engineering/prompt8_validation.md`.
