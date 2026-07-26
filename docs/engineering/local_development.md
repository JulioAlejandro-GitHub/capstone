# Desarrollo local

Use Python 3.12 y Node 22. Cree un entorno backend, instale `backend_api/requirements.txt`, copie `.env.example` a un `.env` no versionado y exporte sus valores. Inicie PostgreSQL controlado, ejecute el bootstrap y luego:

```bash
PYTHONPATH=backend_api uvicorn app.main:app --reload
npm --prefix frontend run dev
python scripts/create_admin.py --username admin --email admin@example.edu
```

TRAIN/EVALUATE/EXPLAIN conservan sus comandos y adaptadores actuales. Esta fundación no añade procesamiento científico.
