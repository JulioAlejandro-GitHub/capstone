# Validación runtime Alembic

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; los resultados no representan el head actual.
> **Snapshot:** head `20260726_02`; el head versionado actual es `20260812_02`.

|Gate|Resultado|Evidencia|
|---|---|---|
|Head único|PASS|`20260726_02`|
|Baseline|PASS estático|`20260726_00`, stamp-only posterior a 029|
|Auth/RBAC|PASS estático|`20260726_01`|
|Audit append-only|PASS estático|`20260726_02`|
|Adoption vacía/incompleta/incompatible|BLOCKED|Requiere PostgreSQL 17 efímero|
|Stamp + upgrade|BLOCKED|Imagen PostgreSQL no disponible|
|Downgrade/upgrade/idempotencia|BLOCKED|Imagen PostgreSQL no disponible|

El verificador sólo acepta revisiones conocidas y mantiene `--pre-stamp`. La migración
histórica 027 y su test acoplado fueron restaurados a la línea base; 001–029 no quedan
modificados en el working tree.
