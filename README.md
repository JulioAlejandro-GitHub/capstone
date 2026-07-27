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
