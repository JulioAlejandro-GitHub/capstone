# DBV2.4 — Dataset certification

- dataset_version_id: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` — status FROZEN, frozen_at preserved
- Stored dataset fingerprints (from `dataset_versions.methodology_json.freeze_contract.fingerprints`, preserved byte-exact, NOT recomputed):
  - clinical_identity_sha256: `d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59`
  - record_assignment_sha256: `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`
  - source_population_sha256: `eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0`
  - patient_assignment_sha256: `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`
- TRAIN 22,180 · VALIDATION 2,693 · TEST 2,685 · TOTAL 27,558 (sum OK) · patients 201
- Patient overlap: TRAIN/VALIDATION 0, TRAIN/TEST 0, VALIDATION/TEST 0
- dataset_split_images: 55,116 = 2 physical roots × 27,558 (official versioned root + historical physical split); not deduplicated.
- Split authority: `dataset_split_assignments` (transferred unchanged). TEST not used for any decision.

## Per-table certification

| table | source_count | destination_count | transferred_count | primary_key_match | transfer_hash_match | transfer_hash | fk_status | semantic_transformations | result |
|---|---|---|---|---|---|---|---|---|---|
| datasets | 2 | 2 | 2 | True | True | `7c7b7e0c93083f3f…` | PASS | 0 | PASS |
| dataset_versions | 1 | 1 | 1 | True | True | `10c4c5ee792fabf5…` | PASS | 0 | PASS |
| clinical_identities | 201 | 201 | 201 | True | True | `4245bada9e232895…` | PASS | 0 | PASS |
| dataset_source_records | 27558 | 27558 | 27558 | True | True | `06ee0875340775fa…` | PASS | 0 | PASS |
| identity_evidence | 27558 | 27558 | 27558 | True | True | `a3be3698d7414d6e…` | PASS | 0 | PASS |
| dataset_version_sources | 1 | 1 | 1 | True | True | `912668b2d46d0d1f…` | PASS | 0 | PASS |
| dataset_split_assignments | 27558 | 27558 | 27558 | True | True | `ba113a20a42be3ae…` | PASS | 0 | PASS |
| dataset_split_statistics | 1 | 1 | 1 | True | True | `ce4c842fb342cd9c…` | PASS | 0 | PASS |
| dataset_split_validation_checks | 12 | 12 | 12 | True | True | `a138a3c8bcb0d999…` | PASS | 0 | PASS |
| dataset_splits | 0 | 0 | 0 | True | True | `e3b0c44298fc1c14…` | PASS | 0 | PRESERVED_EMPTY |
| dataset_materializations | 1 | 1 | 1 | True | True | `afa52f638b0ff9e2…` | PASS | 0 | PASS |
| dataset_materialization_activations | 0 | 0 | 0 | True | True | `e3b0c44298fc1c14…` | PASS | 0 | PRESERVED_EMPTY |
| dataset_split_images | 55116 | 55116 | 55116 | True | True | `5dd455bf143fc6da…` | PASS | 0 | PASS |

Full hashes in `dbv2_4_transfer_manifest.json`. **TRANSFER VERIFICATION HASH** = SHA-256 over length-prefixed PostgreSQL `to_jsonb(row)::text` ordered by PK; it does not replace scientific fingerprints.

## Stored hash columns (compared as stored values)

| table | column | non_null | column_digest | match |
|---|---|---|---|---|
| dataset_source_records | source_file_sha256 | 27558 | `59a43a0c57d22fce…` | True |
| dataset_source_records | decoded_pixel_sha256 | 27558 | `e874767563bfeb41…` | True |
| dataset_split_images | checksum_sha256 | 0 | `d09740170a198e45…` | True |

## Stored fingerprints / digests preserved

- `datasets[1].metadata.scientific_provenance.official_patient_mapping_sha256.patientid_cellmapping_uninfected.csv` = `a8577b21e7154724f4bbd18326218e2c63a99b22ab372b79a7530d36df6dab78`
- `datasets[1].metadata.scientific_provenance.official_patient_mapping_sha256.patientid_cellmapping_parasitized.csv` = `d0367e513397404e980baee2a641bce9ce329a22e62ea9007962dfca2f8418d3`
- `dataset_versions[0].methodology_json.freeze_contract.fingerprints.clinical_identity_sha256` = `d4bd79cb2327ca7aa1eeff19e14a9104af157984cccd9418c75b0f62ae3e8a59`
- `dataset_versions[0].methodology_json.freeze_contract.fingerprints.record_assignment_sha256` = `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`
- `dataset_versions[0].methodology_json.freeze_contract.fingerprints.source_population_sha256` = `eef647ce1f3040468a84cbad73ffb1b50b86d685313f1291693b16f4f1f635f0`
- `dataset_versions[0].methodology_json.freeze_contract.fingerprints.patient_assignment_sha256` = `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`
- `dataset_versions[0].methodology_json.generation_contract.record_assignment_digest` = `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`
- `dataset_versions[0].methodology_json.generation_contract.approved_assignment_digest` = `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`
- `dataset_split_statistics[0].details_json.record_assignment_digest` = `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`
- `dataset_split_statistics[0].details_json.patient_assignment_digest` = `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`
- `dataset_materializations[0].manifest_metadata.record_assignment_digest` = `9709ce48b9b41bcacca49ccfb53ec62b48c4822c2fb8e227643bf26aed196ea2`
- `dataset_materializations[0].manifest_metadata.patient_assignment_digest` = `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f`

- IDs preserved: PK sets identical per table (pk_hash + exact row equality). Stored hashes/fingerprints preserved: YES. Semantic transformations: 0.
