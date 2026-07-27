# Paridad local con CI — SUPERSEDED

Las referencias Docker posteriores son históricas. El workflow actual no contiene jobs
Docker ni PostgreSQL; `requires_local_postgres` pertenece al gate local.

|Job CI|Comandos remotos|Equivalente local|Dependencias|Resultado|Duración|Diferencias|Estado|
|---|---|---|---|---|---|---|---|
|docs-config|diff/config docs|`git diff --check`, compose config|Git/Docker CLI|PASS|<1 s|Working tree local|PASS|
|backend-unit|pytest foundation|suite backend|Python env|70 passed, 4 skipped|<1 s|Python local 3.14, CI 3.12|PASS|
|backend-integration|PG service/bootstrap|`make test-db-bootstrap`|postgres:17-alpine|No ejecutado|—|Pull bloqueado|BLOCKED|
|frontend|npm test/build|mismos comandos|Node 22|62 passed; build PASS|~2 s|Ninguna material|PASS|
|ml-fast|3 módulos pytest|`make test-ml`|venv Python 3.12|17 passed|11 s|Ninguna|PASS|
|docker|compose config/build|`make docker-build`|imágenes base|No ejecutado|—|Pull bloqueado|BLOCKED|

El workflow tiene permisos read-only, timeouts, PostgreSQL efímero, actions versionadas,
sin deployment ni publicación. No puede declararse `READY_FOR_REMOTE_CI` mientras los
jobs PostgreSQL y Docker estén bloqueados.
