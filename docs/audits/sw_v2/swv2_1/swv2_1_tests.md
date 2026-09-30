# SWV2.1 — Tests

Suites relevantes ejecutadas **antes** (HEAD `78a9ef2`, backend como `julio`) y **después** (SWV2.1, backend como `capstone_v2_runtime`).

| Suite | Intérprete | Antes | Después | Nuevos fallos |
|---|---|---|---|---|
| `backend_api/tests -m "not requires_docker_postgres"` (comando CI) | host, Python 3.12 | 536 pass / 2 fail | 539 pass / 2 fail | 0 |
| ML: `test_schema_revision_contract`, `test_label_mapping`, `test_decision`, `test_image_quality` (+ `test_v2_runtime_contract_guard` después) | `capstone_backend` | 22 pass | 51 pass | 0 |
| `tests/db_v2` | venv temporal (`alembic_v2/requirements*.txt` + pytest) | 36 pass | 39 pass | 0 |
| `tests/adoption_v2` | idem | 25 pass / 45 fail | 25 pass / 45 fail | 0 |
| `scripts/check_docker_postgres_contract.py` | host | 33 infracciones | 33 infracciones (conjunto idéntico línea a línea) | **0** |
| `build_v2_runtime_contract.py --check` | host | — | PASS | — |
| `git diff --check` | — | limpio | limpio | — |

## Fallos preexistentes (no relacionados, no modificados)

- `test_mutation_security_policy::test_every_legacy_mutation_has_central_audited_policy`: rutas `POST /execution/local/{operation}`, `/events`, `/event-state` (bloque local_execution E9.3) sin política central de auditoría.
- `test_scientific_storage_docker_contract::test_compose_declares_one_private_read_write_scientific_volume_for_backend` (§44): falla en `assert "STORAGE_ROOT" not in backend_override` por la subcadena de `CAPSTONE_LOCAL_STORAGE_ROOTS` del bloque **TEMPORAL** de `docker-compose.override.yml` (2026-09-15). La expectativa no quedó obsoleta por el contrato aprobado en SWV2.0 (la aserción de volumen ya fue actualizada en SWV2.0 y pasa); lo que falla es un bloque temporal cuya reversión es decisión del usuario. **Se mantiene preexistente; test no modificado.**
- `tests/adoption_v2` (45): `adoption_v2.core.Blocked: CERTIFIED_BASELINE_CHANGED` — herramienta de adopción E10.10.5 fijada a la baseline candidata anterior; histórica.
- Dentro del contenedor, `pytest tests` además tiene errores de colección/lecturas de archivos del repo no montados (compose, Dockerfile, scripts); por eso la suite backend se registra con el comando CI en host.

## No ejecutado deliberadamente

- `test_e10_preclaim_schema_postgres.py` y demás `requires_docker_postgres`: crean schemas/tablas en la base (DDL) — prohibido sobre la BD canónica en SWV2.1.
- Frontend: fuera de alcance (sin cambios).

## Tests nuevos (32)

- `malaria_dl_local_project/tests/test_v2_runtime_contract_guard.py` (29, catálogo falso, sin BD): contrato commiteado = baseline certificada (13/21/40/2, sin `v2_xai_comparison_guard`); catálogo exacto → PASS sólo con SELECT; `pg_v2_baseline` + contrato exacto → PASS de `require_e10_schema`; revisión desconocida / vacía / sin filas / múltiples heads → REJECT sin consultar contrato; hash de función incorrecto, función ausente, función inesperada → `v2_function_contract`; trigger ausente/alterado → `v2_trigger_contract`; constraint alterada → `v2_evaluation_contract`; índice ausente → `v2_calibration_uniqueness_contract`; schema sombra → `v2_public_schema_required`; error SQL → `schema_inspection_failed`; 13 variantes de contrato incompleto/ajeno/ilegible → `v2_contract_incomplete` sin consultar catálogo.
- `tests/db_v2/test_v2_runtime_contract.py` (3): fuente = structural manifest certificado; dos derivaciones = archivo commiteado; manifest alterado → rechazo.
- `backend_api/tests/test_backend_runtime_role_contract.py` (3): `DATABASE_URL` backend sólo con `capstone_v2_runtime`; sin `POSTGRES_USER`/`POSTGRES_PASSWORD`/`julio`/migrator; login admin vaciado en el backend; `.env.example` declara la variable sin valor.
