# Certificado técnico final — PostgreSQL BD-v2

Proyecto: BD-v2 · Fase: DBV2.5 (Freeze final) · Gates previos: DBV2.1, DBV2.2, DBV2.3, DBV2.4 aprobados.

**DB_V2_FINAL_MANIFEST_SHA256 = `2c67232be938b25566fd16e7ed3052a0ed0eb419e1ae04d6259462b295976b4d`**
(SHA-256 de `db_v2_final_manifest.json`; el manifest no contiene su propio hash).

## Identidad

| Campo | Valor |
|---|---|
| PostgreSQL | 17.9 (`server_version_num` 170009) |
| Database | `capstone_v2_isolated_persistent` |
| OID | 16386 |
| Server sysid | 7691366089693499436 |
| Container | `capstone_db_v2` (`1dc48428c6b938da6525754cc4f26d535814f1f8c101928487f7c0d630ce4971`) |
| Endpoint | 127.0.0.1:56440 |
| Persistent volume | `capstone_v2_isolated_persistent_data` |

## Alembic

| Campo | Valor |
|---|---|
| Revision | `pg_v2_baseline` (archivo y `alembic_version`) |
| down_revision | None |
| Roots / heads | 1 / 1 |
| Baseline state | **FROZEN / IMMUTABLE** |

### Política de inmutabilidad

A partir de GATE DB-V2 queda prohibido editar retrospectivamente la revisión raíz `alembic_v2/versions/20260929_01_pg_v2_baseline.py`, sus recursos SQL `alembic_v2/baseline/*.sql` y `catalog_manifest.json`, el manifest estructural certificado y el contrato congelado de BD-v2. Todo cambio futuro de base de datos se realizará mediante una **nueva revisión Alembic v2** con `down_revision = pg_v2_baseline` (o la revisión v2 inmediatamente anterior si luego existe una cadena). Los hashes pinneados en `dbv2_5_hashes.sha256` permiten detectar cualquier edición.

## Catálogo

| Objeto | Valor |
|---|---|
| Tablas de aplicación | 104 (+ `alembic_version`) |
| PK de aplicación | 104 |
| Views | 33 |
| FK | 251 |
| CHECK | 518 |
| UNIQUE constraints | 77 |
| Índices de aplicación | 413 (414 físicos) |
| Funciones | 79 |
| Triggers | 105 |
| Extensiones | pgcrypto 1.3, plpgsql 1.0 |
| XAI | 9 tablas exactas; `xai_explanations` ausente |
| clinical_target_recall | `numeric NOT NULL`, sin DEFAULT, CHECK `> 0 AND <= 1` |
| E-04 / R1 / ownership / ACL / tipos | cubiertos por el manifest estructural idéntico |

## Dataset

| Campo | Valor |
|---|---|
| dataset_version_id | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` |
| Estado | FROZEN (`frozen_at` 2026-08-18 18:06:25.263208+00, preservado) |
| TRAIN / VALIDATION / TEST | 22,180 / 2,693 / 2,685 |
| TOTAL | 27,558 |
| Pacientes | 201 |
| Overlap (T/V, T/T, V/T) | 0 / 0 / 0 |
| dataset_split_images | 55,116 (2 raíces físicas × 27,558, sin deduplicar) |
| record_assignment_sha256 | `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2` |
| patient_assignment_sha256 | `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f` |
| clinical_identity_sha256 | `d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59` |
| source_population_sha256 | `eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0` |

## Usuario

| Campo | Valor |
|---|---|
| Preserved users | 1 |
| Roles | 1 (subconjunto referenciado aprobado; legacy 5) |
| User roles | 1 |
| password_hash_match | true |

## Ausencias

| Campo | Valor |
|---|---|
| Unauthorized transferred rows | 0 |
| audit_events | 0 |
| XAI history | 0 |
| E10 history | 0 |

## Hashes

| Artefacto | SHA-256 |
|---|---|
| Structural manifest | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |
| Root revision | `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279` |
| Resource manifest | `232871ff0241c2912eef40daeee2c849fde70bdec5d64784cb72844e667b009a` |
| DBV2.4 transfer manifest | `295ad3737e92d0e64333062f459a527026a4eacf6e9d36179ce31fbb89c33cf9` |
| DBV2.4 evidence hash set (67 archivos) | `eaecc880b60230c281c989857db2aea8b686b914fa492847e8b31aa3845e5f4e` |
| DBV2.5 final manifest | `2c67232be938b25566fd16e7ed3052a0ed0eb419e1ae04d6259462b295976b4d` |
| Git | baseline + evidencia DBV2.1–2.4 en `d8369f67be9a03166c3601356916529bb587b269`; Freeze commit = commit que introduce este archivo (`git log --format=%H -- docs/audits/db_v2/dbv2_5/db_v2_final_manifest.json`) |

## Infraestructura

| Campo | Valor |
|---|---|
| Persistencia | PASS (restart final stop/start, mismo contenedor y volumen) |
| capstone_db_v2 separado de capstone-malaria | YES (decisión para SW-V2) |
| Legacy | disponible, sin cambios; escrituras DBV2.5 = 0 (sesiones READ ONLY) |
| Application DATABASE_URL switched to v2 | NO |
| Cutover | NO |
| Secretos en evidencia | 0 |

## Estado

**PROJECT BD-v2 TECHNICALLY FROZEN**

La aprobación de **GATE DB-V2** corresponde al usuario/revisor; este certificado no la declara.
