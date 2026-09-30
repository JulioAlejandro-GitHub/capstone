# DBV2.5 — Freeze estructural

## Manifest estructural (recalculado en vivo)

Procedimiento certificado (idéntico a DBV2.2/DBV2.4): `v2_catalog_probe.snapshot()` → `json.dumps(indent=2, sort_keys=True, ensure_ascii=False) + "\n"` → SHA-256.

| Momento | SHA-256 |
|---|---|
| Esperado | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |
| Verificación DBV2.5 | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |
| Antes del restart | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |
| Después del restart | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |
| Chequeo final | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |

Revisión raíz (archivo): `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279`. `alembic_version.version_num = pg_v2_baseline` (1 fila).

El snapshot hasheado incluye relaciones, columnas (tipos, NOT NULL, identity/generated, ACL de columna), constraints con definición, índices, views, funciones y cuerpos, triggers, secuencias, tipos, extensiones, ACL de schema/BD/default, roles y privilegios runtime. Por tanto, el digest idéntico prueba que las invariantes E-04, la corrección R1 (trigger XAI), ownership, ACL y tipos no cambiaron.

## Catálogo (mismo método de conteo que `certify_dbv22.py catalog()`)

| Objeto | Esperado | Observado |
|---|---|---|
| Tablas de aplicación (+ `alembic_version`) | 104 (+1) | 104 (+1) |
| PK de aplicación | 104 | 104 (ninguna tabla sin PK) |
| Views | 33 | 33 |
| FK | 251 | 251 |
| CHECK | 518 | 518 |
| UNIQUE constraints | 77 | 77 |
| Índices de aplicación | 413 | 413 (414 físicos incl. PK de `alembic_version`) |
| Funciones propias | 79 | 79 |
| Triggers | 105 | 105 |
| Extensiones | pgcrypto 1.3, plpgsql 1.0 | pgcrypto 1.3 (owner `capstone_v2_migrator`), plpgsql 1.0 |
| Ownership de relaciones | `capstone_v2_migrator` | `capstone_v2_migrator` (único) |
| Identity / generated relevantes | — | `experiment_execution_events.id` (identity ALWAYS), `assessment_identities.structural_hash` (STORED), `run_clinical_metrics.sample_count` (STORED) |

## XAI

Nueve tablas exactas: `xai_artifacts`, `xai_evaluation_members`, `xai_evaluation_protocols`, `xai_evidence`, `xai_interpretations`, `xai_method_configurations`, `xai_quantitative_evaluations`, `xai_region_attributions`, `xai_specialist_reviews`. `xai_explanations` no existe. Filas XAI: 0 en las nueve.

## clinical_target_recall

`run_configurations.clinical_target_recall numeric NOT NULL`, `pg_attrdef` = 0 (sin DEFAULT), único CHECK:
`CHECK (((clinical_target_recall > (0)::numeric) AND (clinical_target_recall <= (1)::numeric)))`. No existe DEFAULT 0.98 ni CHECK = 0.98.

## Baseline

`pg_v2_baseline` = **FROZEN / IMMUTABLE**. Ver `db_v2_final_certificate.md` §Política de inmutabilidad.
