# Estado actual de la fundación — Prompt 2

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; “estado actual” se refiere exclusivamente al cierre de Prompt 2.
> **Snapshot:** `main@d7e3bbd45e4c772ab063d7e1027923e12b38e9cd`.

Snapshot inicial: rama `main`, commit `d7e3bbd45e4c772ab063d7e1027923e12b38e9cd`, árbol limpio. Difiere del snapshot auditado `3c79bb0`: el delta agrega la documentación de arquitectura v1.1 y `complemento e2.txt`; no había fundación Prompt 2. Snapshot final de trabajo: misma rama y commit (sin commits por instrucción), con cambios no confirmados enumerables mediante `git status`.

Validación local: frontend 59/59, ML rápido 17/17, backend 56 passed/4 skipped y build TypeScript/Vite correcto. Docker Compose test valida. El bootstrap PostgreSQL/Alembic y Docker build no pudieron ejecutarse porque el daemon Docker local no estaba iniciado; deben ejecutarse en CI o tras iniciar Docker Desktop.

|Área|Estado inicial|Cambio|
|---|---|---|
|Python|ML 3.12/TensorFlow 2.17.1; backend local 3.14|Se soporta 3.12 para API, ML y futuro worker|
|Configuración|`dotenv`, URLs personales por defecto, CORS fijo|Configuración validada local/test/demo; sin DB personal por defecto|
|DB/migraciones|Runner SQL 001–029, ledger con checksum|Se conserva y se agrega baseline Alembic|
|Seguridad|Sin auth; actor aportado por cliente|JWT, Argon2, usuarios, cinco roles y permisos centrales|
|Observabilidad|Health dependía de DB; logging parcial|Liveness, readiness, JSON logs y correlation ID|
|Tests|unittest/pytest mixto; varios tests PostgreSQL personales|Compose PostgreSQL 17 efímero y guards|
|Frontend|React 19/TS/Vite, cliente fetch central|Contexto auth, login, bearer, 401 y ruta protegida|
|Entrega|Sin Docker ni Actions|Imagen no-root, Compose y CI|

Reutilizable: monolito FastAPI, cliente HTTP, runner SQL/checksums, paquete canónico y adaptadores. Inconsistente: requirements sin cotas superiores, dos runtimes Python, `.env` locales ignorados y errores heterogéneos. Diferido: migrar cada error legacy al envelope, audit ledger completo, OIDC, rate limiting y pipeline científico.
