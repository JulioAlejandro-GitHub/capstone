# Backend API

Runtime soportado: Python 3.12. Configure mediante las variables de la raíz, instale
`requirements.txt` y ejecute `PYTHONPATH=backend_api uvicorn app.main:app`. Auth está en
`/api/v1/auth`; liveness en `/health` y readiness en `/ready`.
