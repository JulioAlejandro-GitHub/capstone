# Frontend

Frontend React + Vite para visualizar experimentos ML del Capstone.

## Configuracion

```bash
cd frontend
cp .env.example .env
npm install
```

## Ejecutar

```bash
npm run dev
```

Por defecto se conecta a:

```text
http://localhost:8000
```

El frontend no se conecta a PostgreSQL directamente. Toda lectura pasa por `backend_api`.

