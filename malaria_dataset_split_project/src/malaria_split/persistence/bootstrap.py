"""Two-phase, idempotent bootstrap for the malaria scientific population."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from PIL import Image
from sqlalchemy import Engine, text

from malaria_split.identity import (
    IdentityStatus,
    analyze_identities,
    build_source_identity_index,
    resolve_physical_manifest,
)

from .repositories import ScientificBootstrapRepository


EXPECTED_RECORDS = 27_558
EXPECTED_PATIENTS = 201
SOURCE_NAME = "NIH/NLM Malaria Cell Images"
SOURCE_PROVIDER = "NLM/LHNCBC"
SOURCE_REFERENCE = "https://data.lhncbc.nlm.nih.gov/public/Malaria/"
SOURCE_VERSION = "1.0.0"
VERSION_NAME = "Malaria Patient Split v1"
VERSION_SEMVER = "1.0.0"
ID_NAMESPACE = UUID("0372652d-465e-501a-95e7-eaf836c74430")


class BootstrapConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PreparedScientificPopulation:
    patients: tuple[str, ...]
    records: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
    source_mapping_sha256: dict[str, str]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_paths(original_root: Path) -> dict[tuple[str, str], Path]:
    result: dict[tuple[str, str], Path] = {}
    for path in sorted(original_root.glob("*/*.png")):
        key = (path.parent.name.lower(), path.name)
        if key in result:
            raise BootstrapConflict(f"Duplicate original source path: {key}")
        result[key] = path
    return result


def prepare_scientific_population(
    *, physical_root: Path, original_root: Path, mapping_paths: list[Path]
) -> PreparedScientificPopulation:
    """Phase A: reproduce SPLIT 1B and hash original sources without database writes."""
    source_index, diagnostics = build_source_identity_index(original_root, mapping_paths)
    resolved = resolve_physical_manifest(
        physical_root / "files_manifest.csv", physical_root, source_index
    )
    analysis = analyze_identities(resolved)
    required = {
        "total_records": EXPECTED_RECORDS,
        "patient_verified": EXPECTED_RECORDS,
        "patient_unresolved": 0,
        "patient_conflict": 0,
        "unique_patients_total": EXPECTED_PATIENTS,
        "min_cells_per_patient": 65,
        "max_cells_per_patient": 702,
        "patients_only_parasitized": 0,
        "patients_only_uninfected": 50,
        "patients_with_both_classes": 151,
    }
    mismatches = {key: (analysis.get(key), value) for key, value in required.items() if analysis.get(key) != value}
    if diagnostics["source_files"] != EXPECTED_RECORDS or diagnostics["mapping_errors"] or mismatches:
        raise BootstrapConflict(
            f"SPLIT 1B revalidation failed: diagnostics={diagnostics}, mismatches={mismatches}"
        )
    if diagnostics["source_files_without_official_metadata"] or diagnostics["colliding_mapping_keys"]:
        raise BootstrapConflict(f"Ambiguous source identity index: {diagnostics}")

    source_paths = _source_paths(original_root)
    if len(source_paths) != EXPECTED_RECORDS:
        raise BootstrapConflict("SOURCE_FILE_SHA256_SOURCE_UNAVAILABLE")
    manifest_rows: list[dict[str, str]] = []
    with (physical_root / "files_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest_rows = list(csv.DictReader(handle))

    records: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    keys: set[str] = set()
    class_counts: Counter[str] = Counter()
    for item, manifest in zip(resolved, manifest_rows, strict=True):
        if item.identity_status is not IdentityStatus.VERIFIED or not item.patient_id:
            raise BootstrapConflict(f"Unverified identity at tfds_index={item.tfds_index}")
        source_path = source_paths.get((item.class_name, item.source_filename or ""))
        if source_path is None:
            raise BootstrapConflict("SOURCE_FILE_SHA256_SOURCE_UNAVAILABLE")
        with Image.open(source_path) as image:
            rgb = image.convert("RGB")
            pixel_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
            width, height = rgb.size
        source_sha = _file_sha256(source_path)
        source_key = f"nlm_lhncbc_malaria_cell_images:{item.class_name}/{item.source_filename}"
        if source_key in keys:
            raise BootstrapConflict(f"Duplicate source_record_key: {source_key}")
        keys.add(source_key)
        class_counts[item.class_name] += 1
        records.append({
            "source_record_key": source_key,
            "tfds_index": item.tfds_index,
            "source_filename": item.source_filename,
            "class_index": item.label,
            "class_name": item.class_name,
            "original_label": int(manifest["original_tfds_label"]),
            "project_label": int(manifest["project_label"]),
            "relative_source_key": None,
            "source_file_sha256": source_sha,
            "decoded_pixel_sha256": pixel_sha,
            "image_width": width,
            "image_height": height,
            "file_size_bytes": source_path.stat().st_size,
            "patient_id": item.patient_id,
            "metadata": json.dumps({
                "technical_distribution": "tensorflow_datasets/malaria:1.0.0",
                "tfds_index_lineage": "historical files_manifest.csv order",
            }, sort_keys=True),
        })
        evidence.append({
            "source_record_key": source_key,
            "patient_id": item.patient_id,
            "evidence_type": "OFFICIAL_METADATA_AND_EXACT_PIXEL_MATCH",
            "evidence_level": "LEVEL_1_PLUS_LEVEL_4",
            "mapping_method": "decoded_pixel_hash_to_official_metadata",
            "evidence_reference": item.evidence_reference,
            "official_source_reference": SOURCE_REFERENCE,
            "evidence_json": json.dumps({
                "official_mapping": "NLM/LHNCBC Patient-ID to cell filename CSV",
                "source_filename": item.source_filename,
                "decoded_pixel_sha256": pixel_sha,
                "mapping_chain": [
                    "physical_or_tfds_decoded_rgb_pixels",
                    "original_source_image",
                    "official_source_filename",
                    "official_nlm_lhncbc_csv",
                    "patient_id",
                ],
            }, sort_keys=True),
        })
    if class_counts != {"parasitized": 13_779, "uninfected": 13_779}:
        raise BootstrapConflict(f"Unexpected class distribution: {class_counts}")
    mapping_sha = {path.name: _file_sha256(path) for path in mapping_paths}
    return PreparedScientificPopulation(
        patients=tuple(sorted({record["patient_id"] for record in records})),
        records=tuple(records), evidence=tuple(evidence),
        summary={**analysis, "class_counts": dict(class_counts), "source_index": diagnostics},
        source_mapping_sha256=mapping_sha,
    )


def expected_methodology() -> dict[str, Any]:
    return {
        "methodology_name": "patient_group_stratified_v1",
        "grouping_field": "patient_id",
        "identity_requirement": "100%",
        "seed": 42,
        "target_ratios": {"train": 0.80, "val": 0.10, "test": 0.10},
        "positive_class": "parasitized",
        "class_mapping": {"0": "uninfected", "1": "parasitized"},
        "hard_constraints": [
            "patient_disjointness", "exact_duplicate_cross_split_disjointness"
        ],
        "priorities": [
            "patient_disjointness", "exact_duplicate_disjointness",
            "clinical_representativeness", "class_balance", "source_balance",
            "approximate_80_10_10",
        ],
    }


def _assert_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise BootstrapConflict(f"{label} conflict: actual={actual!r}, expected={expected!r}")


def is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def verify_source_record_compatible(existing: dict[str, Any], expected: dict[str, Any]) -> None:
    """Reject an idempotency key whose scientific identity or content changed."""
    for field in (
        "clinical_identity_id", "class_index", "class_name", "source_file_sha256",
        "decoded_pixel_sha256",
    ):
        _assert_equal(f"source record {field}", existing[field], expected[field])


def verify_version_methodology(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    _assert_equal("dataset version methodology", actual, expected)


def verify_methodology_subset(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Verify bootstrap-owned fields while permitting later governed extensions."""
    for key, expected_value in expected.items():
        if key not in actual:
            raise BootstrapConflict(f"dataset version methodology missing field: {key}")
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            if not isinstance(actual_value, dict):
                raise BootstrapConflict(f"dataset version methodology field is not an object: {key}")
            verify_methodology_subset(actual_value, expected_value)
        else:
            _assert_equal(f"dataset version methodology {key}", actual_value, expected_value)


def audit_existing_scientific_bootstrap(
    engine: Engine, prepared: PreparedScientificPopulation
) -> dict[str, Any]:
    """Read-only recognition of the bootstrapped v1 after legitimate lifecycle advance."""
    version_id = uuid5(ID_NAMESPACE, f"{VERSION_NAME}:{VERSION_SEMVER}")
    with engine.connect() as connection:
        version = connection.execute(text("""
            SELECT * FROM dataset_versions WHERE id=:id
        """), {"id": version_id}).mappings().one_or_none()
        if version is None:
            raise BootstrapConflict("Expected Malaria Patient Split v1 was not found")
        _assert_equal("dataset version name", version["name"], VERSION_NAME)
        _assert_equal("dataset version semantic_version", version["semantic_version"], VERSION_SEMVER)
        for field, expected in {
            "grouping_strategy": "patient_group", "grouping_field": "patient_id",
            "stratification_strategy": "patient_group_stratified",
            "split_algorithm": "patient_group_stratified_v1",
            "split_algorithm_version": "1.0.0", "random_seed": 42,
            "positive_class": "parasitized", "source_record_count": EXPECTED_RECORDS,
            "class_mapping": {"0": "uninfected", "1": "parasitized"},
        }.items():
            _assert_equal(f"dataset version {field}", version[field], expected)
        for field, expected in {
            "target_train_ratio": "0.8000000", "target_val_ratio": "0.1000000",
            "target_test_ratio": "0.1000000",
        }.items():
            _assert_equal(field, str(version[field]), expected)
        verify_methodology_subset(version["methodology_json"], expected_methodology())

        links = connection.execute(text("""
            SELECT d.* FROM dataset_version_sources dvs
            JOIN datasets d ON d.id=dvs.dataset_id
            WHERE dvs.dataset_version_id=:id AND dvs.role='PRIMARY'
        """), {"id": version_id}).mappings().all()
        if len(links) != 1:
            raise BootstrapConflict("Expected exactly one PRIMARY source link")
        source = links[0]
        for field, expected in {
            "name": SOURCE_NAME, "provider": SOURCE_PROVIDER,
            "source_reference": SOURCE_REFERENCE, "source_version": SOURCE_VERSION,
        }.items():
            _assert_equal(f"dataset source {field}", source[field], expected)
        provenance = dict(source["metadata"] or {}).get("scientific_provenance", {})
        _assert_equal(
            "official patient mapping sha256",
            provenance.get("official_patient_mapping_sha256"),
            prepared.source_mapping_sha256,
        )

        identities = dict(connection.execute(text("""
            SELECT source_identifier,id FROM clinical_identities
            WHERE dataset_id=:dataset AND identity_type='PATIENT' AND status='VERIFIED'
        """), {"dataset": source["id"]}).all())
        _assert_equal("verified patient population", set(identities), set(prepared.patients))
        records = connection.execute(text("""
            SELECT r.source_record_key,i.source_identifier patient_id,r.class_index,r.class_name,
                   r.source_file_sha256,r.decoded_pixel_sha256,r.identity_status
            FROM dataset_source_records r JOIN clinical_identities i ON i.id=r.clinical_identity_id
            WHERE r.dataset_id=:dataset
        """), {"dataset": source["id"]}).mappings().all()
        actual_records = {row["source_record_key"]: row for row in records}
        _assert_equal("source record keys", set(actual_records), {
            row["source_record_key"] for row in prepared.records
        })
        for expected in prepared.records:
            actual = actual_records[expected["source_record_key"]]
            for field in (
                "patient_id", "class_index", "class_name", "source_file_sha256",
                "decoded_pixel_sha256",
            ):
                _assert_equal(
                    f"source record {expected['source_record_key']} {field}",
                    actual[field], expected[field],
                )
            _assert_equal(
                f"source record {expected['source_record_key']} identity_status",
                actual["identity_status"], "VERIFIED",
            )

        assignment_count = connection.execute(text("""
            SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id
        """), {"id": version_id}).scalar_one()
        lifecycle_accepted = (
            (version["status"] == "DRAFT" and assignment_count == 0)
            or (version["status"] == "GENERATED" and assignment_count == EXPECTED_RECORDS)
        )
        if not lifecycle_accepted:
            raise BootstrapConflict(
                f"Unsupported bootstrap lifecycle/count: {version['status']}/{assignment_count}"
            )
        return {
            "bootstrap_version_found": True,
            "bootstrap_version_id_match": version["id"] == version_id,
            "bootstrap_scientific_population_match": True,
            "current_lifecycle_status": version["status"],
            "current_assignment_count": assignment_count,
            "lifecycle_state_accepted": True,
            "dry_run_database_writes": 0,
            "result": (
                "ALREADY_BOOTSTRAPPED_AND_ADVANCED"
                if version["status"] == "GENERATED"
                else "ALREADY_BOOTSTRAPPED_DRAFT"
            ),
        }


def apply_scientific_bootstrap(engine: Engine, prepared: PreparedScientificPopulation) -> dict[str, str]:
    """Phase B: verify-or-insert the complete population in one transaction."""
    with engine.begin() as connection:
        repository = ScientificBootstrapRepository(connection)
        connection.execute(text("SELECT pg_advisory_xact_lock(2026081102)"))
        sources = connection.execute(
            text("SELECT * FROM datasets WHERE name=:name FOR UPDATE"), {"name": SOURCE_NAME}
        ).mappings().all()
        if len(sources) != 1:
            raise BootstrapConflict(f"Expected exactly one source {SOURCE_NAME!r}, found {len(sources)}")
        source = sources[0]
        for field, expected in {
            "provider": SOURCE_PROVIDER, "source_type": "medical_image_dataset",
            "source_reference": SOURCE_REFERENCE, "source_version": SOURCE_VERSION,
        }.items():
            if source[field] not in (None, expected):
                raise BootstrapConflict(f"Dataset source {field} conflict")
        source_metadata = dict(source["metadata"] or {})
        provenance = {
            "scientific_provider": SOURCE_PROVIDER,
            "technical_distribution": "TensorFlow Datasets malaria 1.0.0",
            "official_patient_mapping_sha256": prepared.source_mapping_sha256,
        }
        existing_provenance = source_metadata.get("scientific_provenance")
        if existing_provenance not in (None, provenance):
            raise BootstrapConflict("Dataset source provenance conflict")
        source_metadata["scientific_provenance"] = provenance
        connection.execute(text("""
            UPDATE datasets SET provider=:provider,source_type=:source_type,
              source_reference=:reference,source_version=:version,metadata=CAST(:metadata AS jsonb)
            WHERE id=:id
        """), {
            "provider": SOURCE_PROVIDER, "source_type": "medical_image_dataset",
            "reference": SOURCE_REFERENCE, "version": SOURCE_VERSION,
            "metadata": json.dumps(source_metadata, sort_keys=True), "id": source["id"],
        })
        source_id = source["id"]

        existing_identities = repository.rows_by_key(
            "clinical_identities", "id,dataset_id,identity_type,source_identifier,status",
            "source_identifier",
        )
        identity_rows = []
        identity_ids: dict[str, UUID] = {}
        for patient in prepared.patients:
            expected_id = uuid5(ID_NAMESPACE, f"{source_id}:PATIENT:{patient}")
            current = existing_identities.get(patient)
            if current:
                for field, expected in {
                    "id": expected_id, "dataset_id": source_id,
                    "identity_type": "PATIENT", "status": "VERIFIED",
                }.items(): _assert_equal(f"identity {patient} {field}", current[field], expected)
                identity_ids[patient] = current["id"]
            else:
                identity_ids[patient] = expected_id
                identity_rows.append({
                    "id": expected_id, "dataset_id": source_id,
                    "source_identifier": patient,
                    "metadata": json.dumps({"identifier_authority": SOURCE_PROVIDER}),
                })
        if set(existing_identities) - set(prepared.patients):
            raise BootstrapConflict("Unexpected clinical identities already exist")
        repository.insert_many("""
            INSERT INTO clinical_identities (
              id,dataset_id,identity_type,source_identifier,status,metadata
            ) VALUES (:id,:dataset_id,'PATIENT',:source_identifier,'VERIFIED',CAST(:metadata AS jsonb))
        """, identity_rows)

        existing_records = repository.rows_by_key(
            "dataset_source_records",
            "id,dataset_id,clinical_identity_id,source_record_key,tfds_index,source_filename,"
            "class_index,class_name,original_label,project_label,relative_source_key,"
            "source_file_sha256,decoded_pixel_sha256,image_width,image_height,file_size_bytes,identity_status",
            "source_record_key",
        )
        record_rows = []
        record_ids: dict[str, UUID] = {}
        comparable = (
            "dataset_id", "clinical_identity_id", "tfds_index", "source_filename",
            "class_index", "class_name", "original_label", "project_label",
            "relative_source_key", "source_file_sha256", "decoded_pixel_sha256",
            "image_width", "image_height", "file_size_bytes", "identity_status",
        )
        for record in prepared.records:
            key = record["source_record_key"]
            record_id = uuid5(ID_NAMESPACE, f"{source_id}:SOURCE_RECORD:{key}")
            expected = {**record, "dataset_id": source_id,
                        "clinical_identity_id": identity_ids[record["patient_id"]],
                        "identity_status": "VERIFIED"}
            current = existing_records.get(key)
            if current:
                _assert_equal(f"source record {key} id", current["id"], record_id)
                verify_source_record_compatible(dict(current), expected)
                for field in comparable:
                    _assert_equal(f"source record {key} {field}", current[field], expected[field])
            else:
                record_rows.append({**expected, "id": record_id})
            record_ids[key] = record_id
        if set(existing_records) - set(record_ids):
            raise BootstrapConflict("Unexpected dataset source records already exist")
        repository.insert_many("""
            INSERT INTO dataset_source_records (
              id,dataset_id,clinical_identity_id,source_record_key,tfds_index,source_filename,
              class_index,class_name,original_label,project_label,relative_source_key,
              source_file_sha256,decoded_pixel_sha256,image_width,image_height,file_size_bytes,
              identity_status,metadata
            ) VALUES (
              :id,:dataset_id,:clinical_identity_id,:source_record_key,:tfds_index,:source_filename,
              :class_index,:class_name,:original_label,:project_label,:relative_source_key,
              :source_file_sha256,:decoded_pixel_sha256,:image_width,:image_height,:file_size_bytes,
              :identity_status,CAST(:metadata AS jsonb)
            )
        """, record_rows)

        existing_evidence = repository.rows_by_key(
            "identity_evidence",
            "id,source_record_id,clinical_identity_id,evidence_type,evidence_level,mapping_method,"
            "evidence_reference,official_source_reference,evidence_json",
            "source_record_id",
        )
        evidence_rows = []
        for evidence in prepared.evidence:
            record_id = record_ids[evidence["source_record_key"]]
            identity_id = identity_ids[evidence["patient_id"]]
            evidence_id = uuid5(ID_NAMESPACE, f"{record_id}:IDENTITY_EVIDENCE:v1")
            expected = {**evidence, "id": evidence_id, "source_record_id": record_id,
                        "clinical_identity_id": identity_id}
            current = existing_evidence.get(record_id)
            if current:
                for field in (
                    "id", "source_record_id", "clinical_identity_id", "evidence_type",
                    "evidence_level", "mapping_method", "evidence_reference",
                    "official_source_reference",
                ): _assert_equal(f"evidence {record_id} {field}", current[field], expected[field])
                _assert_equal(
                    f"evidence {record_id} evidence_json", current["evidence_json"],
                    json.loads(evidence["evidence_json"]),
                )
            else:
                evidence_rows.append(expected)
        if set(existing_evidence) - set(record_ids.values()):
            raise BootstrapConflict("Unexpected identity evidence already exists")
        repository.insert_many("""
            INSERT INTO identity_evidence (
              id,source_record_id,clinical_identity_id,evidence_type,evidence_level,
              mapping_method,evidence_reference,official_source_reference,evidence_json
            ) VALUES (
              :id,:source_record_id,:clinical_identity_id,:evidence_type,:evidence_level,
              :mapping_method,:evidence_reference,:official_source_reference,
              CAST(:evidence_json AS jsonb)
            )
        """, evidence_rows)

        methodology = expected_methodology()
        version_id = uuid5(ID_NAMESPACE, f"{VERSION_NAME}:{VERSION_SEMVER}")
        versions = connection.execute(text("""
            SELECT * FROM dataset_versions WHERE name=:name AND semantic_version=:version FOR UPDATE
        """), {"name": VERSION_NAME, "version": VERSION_SEMVER}).mappings().all()
        expected_version = {
            "id": version_id, "status": "DRAFT", "grouping_strategy": "patient_group",
            "grouping_field": "patient_id", "stratification_strategy": "patient_group_stratified",
            "split_algorithm": "patient_group_stratified_v1", "split_algorithm_version": "1.0.0",
            "random_seed": 42, "positive_class": "parasitized", "source_record_count": EXPECTED_RECORDS,
            "class_mapping": {"0": "uninfected", "1": "parasitized"},
            "methodology_json": methodology,
        }
        if versions:
            if len(versions) != 1: raise BootstrapConflict("Duplicate v1 dataset versions")
            current = versions[0]
            for field, expected in expected_version.items():
                _assert_equal(f"dataset version {field}", current[field], expected)
            verify_version_methodology(current["methodology_json"], methodology)
            for field, expected in {
                "target_train_ratio": "0.8000000", "target_val_ratio": "0.1000000",
                "target_test_ratio": "0.1000000",
            }.items(): _assert_equal(field, str(current[field]), expected)
        else:
            connection.execute(text("""
                INSERT INTO dataset_versions (
                  id,name,semantic_version,status,grouping_strategy,grouping_field,
                  stratification_strategy,split_algorithm,split_algorithm_version,random_seed,
                  target_train_ratio,target_val_ratio,target_test_ratio,positive_class,class_mapping,
                  source_record_count,methodology_json
                ) VALUES (
                  :id,:name,:version,'DRAFT','patient_group','patient_id',
                  'patient_group_stratified','patient_group_stratified_v1','1.0.0',42,
                  0.80,0.10,0.10,'parasitized',CAST(:class_mapping AS jsonb),27558,
                  CAST(:methodology AS jsonb)
                )
            """), {"id": version_id, "name": VERSION_NAME, "version": VERSION_SEMVER,
                    "class_mapping": json.dumps(expected_version["class_mapping"], sort_keys=True),
                    "methodology": json.dumps(methodology, sort_keys=True)})
        links = connection.execute(text("""
            SELECT dataset_id,role FROM dataset_version_sources WHERE dataset_version_id=:id
        """), {"id": version_id}).mappings().all()
        if links:
            _assert_equal("dataset version source links", [dict(row) for row in links],
                          [{"dataset_id": source_id, "role": "PRIMARY"}])
        else:
            connection.execute(text("""
                INSERT INTO dataset_version_sources(dataset_version_id,dataset_id,role)
                VALUES (:version_id,:dataset_id,'PRIMARY')
            """), {"version_id": version_id, "dataset_id": source_id})

        counts = {
            "patients": repository.scalar("SELECT count(*) FROM clinical_identities"),
            "records": repository.scalar("SELECT count(*) FROM dataset_source_records"),
            "evidence_records": repository.scalar(
                "SELECT count(DISTINCT source_record_id) FROM identity_evidence"
            ),
            "versions": repository.scalar("SELECT count(*) FROM dataset_versions"),
        }
        _assert_equal("transactional counts", counts,
                      {"patients": 201, "records": 27558, "evidence_records": 27558, "versions": 1})
        return {"dataset_source_id": str(source_id), "dataset_version_id": str(version_id)}


def audit_scientific_bootstrap(engine: Engine) -> dict[str, Any]:
    """Independent database audit with no dependence on preparation objects."""
    with engine.connect() as connection:
        version = connection.execute(text("""
            SELECT * FROM dataset_versions WHERE name=:name AND semantic_version=:version
        """), {"name": VERSION_NAME, "version": VERSION_SEMVER}).mappings().one()
        scalar = lambda sql: connection.execute(text(sql), {"version_id": version["id"]}).scalar_one()
        patient_rows = connection.execute(text("""
            SELECT ci.source_identifier,
                   count(*) total,
                   count(*) FILTER (WHERE dsr.class_name='parasitized') parasitized,
                   count(*) FILTER (WHERE dsr.class_name='uninfected') uninfected
            FROM clinical_identities ci JOIN dataset_source_records dsr
              ON dsr.clinical_identity_id=ci.id
            GROUP BY ci.id,ci.source_identifier
        """)).mappings().all()
        class_counts = dict(connection.execute(text(
            "SELECT class_name,count(*) FROM dataset_source_records GROUP BY class_name"
        )).all())
        result = {
            "dataset_source_id": str(scalar("SELECT dataset_id FROM dataset_version_sources WHERE dataset_version_id=:version_id AND role='PRIMARY'")),
            "dataset_version_id": str(version["id"]), "dataset_version_status": version["status"],
            "dataset_version_source_links": scalar("SELECT count(*) FROM dataset_version_sources WHERE dataset_version_id=:version_id"),
            "dataset_version_primary_source_links": scalar("SELECT count(*) FROM dataset_version_sources WHERE dataset_version_id=:version_id AND role='PRIMARY'"),
            "clinical_identity_count": scalar("SELECT count(*) FROM clinical_identities"),
            "patient_identities_verified": scalar("SELECT count(*) FROM clinical_identities WHERE status='VERIFIED'"),
            "patient_identities_unresolved": scalar("SELECT count(*) FROM clinical_identities WHERE status='UNRESOLVED'"),
            "patient_identities_conflict": scalar("SELECT count(*) FROM clinical_identities WHERE status='CONFLICT'"),
            "source_record_count": scalar("SELECT count(*) FROM dataset_source_records"),
            "source_records_with_identity": scalar("SELECT count(*) FROM dataset_source_records WHERE clinical_identity_id IS NOT NULL"),
            "source_records_without_identity": scalar("SELECT count(*) FROM dataset_source_records WHERE clinical_identity_id IS NULL"),
            "identity_evidence_count": scalar("SELECT count(*) FROM identity_evidence"),
            "source_records_with_identity_evidence": scalar("SELECT count(DISTINCT source_record_id) FROM identity_evidence"),
            "source_records_without_identity_evidence": scalar("SELECT count(*) FROM dataset_source_records r WHERE NOT EXISTS (SELECT 1 FROM identity_evidence e WHERE e.source_record_id=r.id)"),
            "source_file_sha256_populated": scalar("SELECT count(*) FROM dataset_source_records WHERE source_file_sha256 IS NOT NULL"),
            "source_file_sha256_null": scalar("SELECT count(*) FROM dataset_source_records WHERE source_file_sha256 IS NULL"),
            "decoded_pixel_sha256_populated": scalar("SELECT count(*) FROM dataset_source_records WHERE decoded_pixel_sha256 IS NOT NULL"),
            "decoded_pixel_sha256_null": scalar("SELECT count(*) FROM dataset_source_records WHERE decoded_pixel_sha256 IS NULL"),
            "unique_patients": len(patient_rows),
            "min_cells_per_patient": min(row["total"] for row in patient_rows),
            "max_cells_per_patient": max(row["total"] for row in patient_rows),
            "patients_only_parasitized": sum(row["parasitized"] > 0 and row["uninfected"] == 0 for row in patient_rows),
            "patients_only_uninfected": sum(row["uninfected"] > 0 and row["parasitized"] == 0 for row in patient_rows),
            "patients_with_both_classes": sum(row["uninfected"] > 0 and row["parasitized"] > 0 for row in patient_rows),
            "class_counts": class_counts,
            "v1_assignment_count": scalar("SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:version_id"),
            "v1_statistics_count": scalar("SELECT count(*) FROM dataset_split_statistics WHERE dataset_version_id=:version_id"),
            "v1_validation_check_count": scalar("SELECT count(*) FROM dataset_split_validation_checks WHERE dataset_version_id=:version_id"),
            "v1_materialization_count": scalar("SELECT count(*) FROM dataset_materializations WHERE dataset_version_id=:version_id"),
            "v1_current_activation_count": scalar("SELECT count(*) FROM dataset_materialization_activations WHERE dataset_version_id=:version_id AND deactivated_at IS NULL"),
        }
        expected = {
            "dataset_version_source_links": 1,
            "dataset_version_primary_source_links": 1, "clinical_identity_count": 201,
            "patient_identities_verified": 201, "patient_identities_unresolved": 0,
            "patient_identities_conflict": 0, "source_record_count": 27558,
            "source_records_with_identity": 27558, "source_records_without_identity": 0,
            "source_records_with_identity_evidence": 27558,
            "source_records_without_identity_evidence": 0,
            "source_file_sha256_populated": 27558, "source_file_sha256_null": 0,
            "decoded_pixel_sha256_populated": 27558, "decoded_pixel_sha256_null": 0,
            "unique_patients": 201, "min_cells_per_patient": 65,
            "max_cells_per_patient": 702, "patients_only_parasitized": 0,
            "patients_only_uninfected": 50, "patients_with_both_classes": 151,
            "class_counts": {"parasitized": 13779, "uninfected": 13779},
            "v1_statistics_count": 0,
            "v1_validation_check_count": 0, "v1_materialization_count": 0,
            "v1_current_activation_count": 0,
        }
        lifecycle_population_consistent = (
            (result["dataset_version_status"] == "DRAFT" and result["v1_assignment_count"] == 0)
            or (result["dataset_version_status"] == "GENERATED" and result["v1_assignment_count"] == 27558)
        )
        result["status"] = "PASS" if (
            lifecycle_population_consistent
            and all(result.get(k) == v for k, v in expected.items())
        ) else "FAIL"
        result["expected"] = expected
        return result
