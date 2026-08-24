# Capstone MIA — plataforma científica experimental

Monolito modular con FastAPI, React/TypeScript, PostgreSQL y `malaria_dl`. No es una
herramienta diagnóstica. La fundación de Etapa 2 se documenta en
`docs/engineering/local_development.md` y `docs/engineering/test_environment.md`.

La API `/api/v1/scientific` registra trazabilidad pseudonimizada caso → muestra → frotis
→ imagen (sólo metadata). Véanse `docs/architecture/scientific_data_model.md` y
`docs/engineering/scientific_api.md`.

Comandos principales: `make validate`, `make test`, `make test-db`,
`make db-status` y `make db-migrate-check`. PostgreSQL debe estar activo; el proyecto
no lo inicia, reconstruye ni detiene.
# Operación de la fundación

Backend y frontend se ejecutan localmente con Python y Node/Vite contra PostgreSQL 17.9
Homebrew y la base `malaria_experiments`. Docker no forma parte de la arquitectura
operativa, CI ni criterios de aprobación. Consulte
`docs/engineering/local_development.md`.

La ingesta protegida está integrada en el workflow canónico `/frotis/analizar`:
resuelve identidad pseudonimizada y preserva originales en `var/storage`.
# Control técnico de calidad

El dominio Análisis de frotis incluye carga inmutable, quality gate, detección,
clasificación y revisión en `/frotis/analizar`; permanece separado del entrenamiento
y Modelo IA. `/frotis/cargar`, `/frotis/analisis` y `/frotis/revision` son redirects
de compatibilidad. Consulta `docs/architecture/microscopy_quality_gate.md`.

# Clasificación celular experimental

La clasificación por crop consume una publicación Stage 2 activa, threshold
registrado, predicciones automáticas inmutables, Grad-CAM manual y revisión humana
separada. La elegibilidad mínima de publicación es `TRAIN completed + EVALUATE
completed`; la habilitación técnica falla cerrado si artefacto, contrato, threshold,
smoke o inferencia no son utilizables. El resultado es experimental: no constituye
diagnóstico ni estimación de parasitemia. Consulte
`docs/stage2_productive_training_card.md` y
`docs/architecture/cell_classification_pipeline.md`.

`docs/engineering/prompt8_validation.md` es evidencia histórica, no un gate vigente.
La operación debe comprobar `current=head`; al 2026-08-24 el head versionado es
`20260812_02`.
