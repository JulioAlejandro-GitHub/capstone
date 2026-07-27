# Desarrollo local

Use Python 3.12, Node 22 y PostgreSQL 17.9 Homebrew. Configure privadamente
`APP_ENV=development`, `DATABASE_URL`, `JWT_SECRET` y storage. No copie credenciales a Git.

```bash
PYTHONPATH=backend_api backend_api/.venv/bin/uvicorn app.main:app --reload
npm --prefix frontend run dev
```

Compruebe `/health`, `/ready` y el frontend Vite. Docker no forma parte de la arquitectura
operativa, del desarrollo ni de los gates. TRAIN/EVALUATE/EXPLAIN y sus adaptadores
permanecen sin cambios; esta fundación no añade procesamiento científico.
