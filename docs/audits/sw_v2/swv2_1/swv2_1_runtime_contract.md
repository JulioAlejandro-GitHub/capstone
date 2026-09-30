# SWV2.1 — P-01 `v2_runtime_contract.json`

## Qué verifica la guarda (`schema_contract.require_v2_capabilities`)

Sólo SELECT sobre `pg_catalog`, ejecutada por `require_e10_schema` cuando `alembic_version = ['pg_v2_baseline']`:

| Sección | Proyección | Comparación |
|---|---|---|
| `functions` | `md5(pg_get_functiondef(oid))` de funciones `public.v2_*` / `public.e04_*` | dict exacto (mismo conjunto, mismos md5) → `v2_function_contract` |
| `triggers` | relation, name, `pg_get_triggerdef`, tgenabled, tgdeferrable, tginitdeferred de triggers `v2_*`/`e04_*` | lista exacta → `v2_trigger_contract` |
| `evaluation_constraints` | constraints de `public.evaluations` | lista exacta → `v2_evaluation_contract` |
| `calibration_indexes` | índices `uq_e04_*` de `evaluations` | lista exacta → `v2_calibration_uniqueness_contract` |

Alcance mínimo preservado: no es un hash de toda la base; sólo los objetos que demuestran que el runtime habla con el schema soportado. Algoritmo: MD5 de PostgreSQL sobre el texto UTF-8 de `pg_get_functiondef` (huella de contenido, no control criptográfico).

## Procedencia del contrato anterior

`scripts/db/capture_v2_e4_runtime.py` lo capturó de un **candidato E10.10.5E.4** instalado (`stage: "E10.10.5E.4"`, sha256 `b068c7af14aa4ec9ae11e273fcb0d171a90ed8a025c65ebe4a3bb69ba3588cb5`). DB-V2 cambió ese catálogo:

| Diferencia E.4 → pg_v2_baseline | Objeto |
|---|---|
| función eliminada | `v2_xai_comparison_guard` (rediseño XAI DBV2.1) |
| trigger eliminado | `v2_xai_comparison_guard` |
| cuerpo de función cambiado | `v2_calibration_pair_guard`, `v2_configuration_guard`, `v2_xai_lineage_guard` |
| sin cambios | 40 constraints de `evaluations`, 2 índices `uq_e04_*`, 10 funciones y 21 triggers restantes |

## Fuente de verdad y derivación

```
docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json   (congelado, GATE DB-V2)
  sha256 = 15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb  = structural manifest
        │  scripts/db/build_v2_runtime_contract.py   (stdlib, sin conexión a PostgreSQL)
        ▼
malaria_dl/persistence/v2_runtime_contract.json
  revision = pg_v2_baseline, source.sha256 = 15c95e0c…, sha256 = d77ace1422b46b6c1db970af7d291cbb518ae2258f5709d65d88e9ba107a3181
        │  require_e10_schema → require_v2_capabilities
        ▼
PostgreSQL real (capstone_v2_runtime) → PASS
```

El manifest contiene exactamente las mismas proyecciones del catálogo (`scripts/db/v2_catalog_probe.py`: `pg_get_functiondef`, `pg_get_triggerdef(oid,false)`, `pg_get_constraintdef(oid,false)`, `pg_get_indexdef`). El generador rechaza cualquier fuente cuyo sha256 ≠ structural manifest certificado y funciones sobrecargadas.

Verificación cruzada (antes de escribir): proyección viva como `capstone_v2_runtime` = derivación desde el manifest → funciones 13/13, triggers 21/21, constraints 40/40, índices 2/2 **idénticos**; capacidades E10 (event columns, metadata constraint, unique indexes, trigger guard) = 4/4 true.

## Reproducibilidad

| Ejecución | Resultado |
|---|---|
| `build_v2_runtime_contract.py` (1) | `WROTE d77ace14…a3181` |
| `--check` | `CHECK PASS d77ace14…a3181` |
| `build_v2_runtime_contract.py` (2) | `WROTE d77ace14…a3181` (idéntico byte a byte) |
| `--check` final (post-restart) | `CHECK PASS d77ace14…a3181` |
| `tests/db_v2/test_v2_runtime_contract.py` | fuente = manifest certificado; dos derivaciones independientes = archivo commiteado; manifest alterado → rechazo |

## Cambios en la guarda (sin debilitar fail-closed)

`schema_contract.py`:
- `load_contract()`: contrato ausente, JSON inválido, `revision ≠ pg_v2_baseline`, o sección faltante/vacía/tipo incorrecto → `E10SchemaNotReady(['v2_contract_incomplete'])` **antes** de consultar el catálogo.
- Constraints e índices se comparan ordenados por nombre en Python (antes dependían del `ORDER BY` bajo la collation de la base); la igualdad sigue siendo exacta.
- Sin try/except→continuar, sin warnings, sin `return True`, sin aceptar hashes/revisiones arbitrarias. El backend **nunca** reescribe el contrato: es código versionado; un cambio de schema futuro debe regenerarlo explícitamente junto a su migración.

`execution/schema.py` sin cambios: sólo `20260922_01` y `pg_v2_baseline`; vacía, desconocida o múltiples heads → `unsupported_alembic_revision`. No se usó `stamp`.

Resultado vivo (`swv2_1_runtime_*.json`): `require_e10_schema = PASS`, `revision = pg_v2_baseline`.
