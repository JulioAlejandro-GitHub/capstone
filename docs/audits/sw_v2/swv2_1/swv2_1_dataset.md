# SWV2.1 — Acceso al dataset desde el backend

## Endpoints gobernados (HTTP real, token del backend, rol `capstone_v2_runtime`)

`GET /api/datasets` → 200, 1 versión (`swv2_1_auth.json`):

| Campo | Valor |
|---|---|
| dataset_version_id | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` |
| status | FROZEN |
| train_records | 22,180 |
| val_records | 2,693 |
| test_records | 2,685 |
| source_record_count | 27,558 |
| patient_count | 201 |
| trainable | true |

`GET /api/datasets/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` → 200 (secciones `dataset`, `distribution`, `integrity`, `lifecycle`, `lineage`, `materialization`, `runs`, `validation`).

## Verificación independiente en base (READ ONLY, `swv2_1_check_*.json`)

`scientific_snapshot` = DBV2.5: FROZEN, TRAIN 22,180 / VALIDATION 2,693 / TEST 2,685 = 27,558, 201 pacientes, overlap 0/0/0; fingerprints almacenados = contrato de freeze; hashes de transferencia de las 16 tablas de dataset = DBV2.4. No se recalcularon imágenes ni se modificó el split.

## Observación para fase posterior (no bloqueante)

`GET /api/dataset/summary` y `/api/dataset/split` (browser legacy, `services/dataset_browser.py`) responden 200 pero agregan `dataset_split_images` sobre las **dos** raíces físicas certificadas (2 × 27,558 = 55,116; `dataset_version_id` NULL por diseño DBV2.4). Sus conteos por split/clase no equivalen al split gobernado. Igual antes y después de SWV2.1 (los datos no cambiaron). Corresponde adaptar ese consumidor en una fase posterior, no a la base.
