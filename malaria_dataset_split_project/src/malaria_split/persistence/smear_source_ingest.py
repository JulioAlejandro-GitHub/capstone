"""Atomic verify-or-insert of the ThinBloodSmearsPf Polygon Set source population.

Writes only ``datasets``, ``clinical_identities``, ``dataset_source_records`` and
``identity_evidence`` rows of the smear source. It never creates Dataset Versions,
assignments, tiles or YOLO artifacts, and never reads or writes other sources' rows.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import Connection, Engine, text

from malaria_split.families import DatasetFamily
from malaria_split.sources.thin_blood_smears_pf import (
    ADAPTER_VERSION,
    SOURCE_NAME,
    SOURCE_PROVIDER,
    SOURCE_REFERENCE,
    SOURCE_SLUG,
    SmearSourceInspection,
    cell_images_candidate_identifier,
)

from .repositories import ScientificBootstrapRepository


ID_NAMESPACE = UUID("6b0c3d3e-7a0e-5f4b-9d55-1f6f0c2a9e11")
ADVISORY_LOCK_KEY = 2026100201
RECORD_CLASS_INDEX = 0
# Schema requires a class; for a full smear it names the unit, not a diagnosis.
RECORD_CLASS_NAME = "full_smear_image"
EVIDENCE_TYPE = "OFFICIAL_DIRECTORY_CONVENTION"
EVIDENCE_LEVEL = "LEVEL_2"
MAPPING_METHOD = "polygon_set_patient_directory_name"


class SmearIngestConflict(RuntimeError):
    pass


def _assert_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise SmearIngestConflict(f"{label} conflict: actual={actual!r}, expected={expected!r}")


def dataset_source_id() -> UUID:
    return uuid5(ID_NAMESPACE, f"DATASET_SOURCE:{SOURCE_NAME}")


def _dataset_metadata(inspection: SmearSourceInspection) -> dict[str, Any]:
    return {
        "dataset_family": DatasetFamily.SMEAR_SEGMENTATION.value,
        "source_slug": SOURCE_SLUG,
        "adapter_version": ADAPTER_VERSION,
        "ground_truth": "polygon_set",
        "source_unit": "full_smear_image",
        "clinical_unit": "patient",
        "population_fingerprint_sha256": inspection.population_fingerprint,
        "provenance_sha256": inspection.provenance_sha256,
        "patient_count": len(inspection.patients),
        "polygon_count": sum(record.polygon_count for record in inspection.records),
    }


def prepare_smear_rows(inspection: SmearSourceInspection) -> dict[str, list[dict[str, Any]]]:
    """Deterministic rows; UUIDs depend only on source name, Patient-ID and relative path."""
    source_id = dataset_source_id()
    readme_sha = inspection.provenance_sha256.get("ReadMe.pdf")
    identities = [{
        "id": uuid5(ID_NAMESPACE, f"{source_id}:PATIENT:{patient}"),
        "dataset_id": source_id, "identity_type": "PATIENT",
        "source_identifier": patient, "status": "VERIFIED",
        "metadata": {
            "identifier_authority": SOURCE_PROVIDER,
            "derivation": "Polygon Set/<Patient ID> directory name (official ReadMe.pdf)",
            "cross_source_hint": {
                "status": "UNVERIFIED",
                "nih_nlm_malaria_cell_images_candidate_patient_id":
                    cell_images_candidate_identifier(patient),
            },
        },
    } for patient in inspection.patients]
    identity_ids = {row["source_identifier"]: row["id"] for row in identities}
    records, evidence = [], []
    for record in inspection.records:
        record_id = uuid5(ID_NAMESPACE, f"{source_id}:SOURCE_RECORD:{record.source_record_key}")
        records.append({
            "id": record_id, "dataset_id": source_id,
            "clinical_identity_id": identity_ids[record.patient_id],
            "source_record_key": record.source_record_key,
            "tfds_index": None, "source_filename": record.image_filename,
            "class_index": RECORD_CLASS_INDEX, "class_name": RECORD_CLASS_NAME,
            "original_label": None, "project_label": None,
            "relative_source_key": record.image_relative_path,
            "source_file_sha256": record.image_sha256, "decoded_pixel_sha256": None,
            "image_width": record.image_width, "image_height": record.image_height,
            "file_size_bytes": record.image_size_bytes, "identity_status": "VERIFIED",
            "metadata": {
                "dataset_family": DatasetFamily.SMEAR_SEGMENTATION.value,
                "record_unit": "full_smear_image",
                "class_semantics": "record_unit_not_diagnostic_label",
                "annotation": {
                    "format": "nih_nlm_polygon_set",
                    "relative_path": record.annotation_relative_path,
                    "sha256": record.annotation_sha256,
                    "size_bytes": record.annotation_size_bytes,
                    "polygon_count": record.polygon_count,
                    "rbc_count": record.rbc_count,
                    "wbc_count": record.wbc_count,
                    "label_counts": record.label_counts,
                },
            },
        })
        evidence.append({
            "id": uuid5(ID_NAMESPACE, f"{record_id}:IDENTITY_EVIDENCE:v1"),
            "source_record_id": record_id,
            "clinical_identity_id": identity_ids[record.patient_id],
            "evidence_type": EVIDENCE_TYPE, "evidence_level": EVIDENCE_LEVEL,
            "mapping_method": MAPPING_METHOD,
            "evidence_reference": f"ReadMe.pdf sha256={readme_sha}",
            "official_source_reference": SOURCE_REFERENCE,
            "evidence_json": {
                "path_template": "Polygon Set/<Patient ID>/Img/<ImageName>.jpg",
                "image_relative_path": record.image_relative_path,
                "annotation_relative_path": record.annotation_relative_path,
                "patient_directory": record.patient_id,
                "image_sha256": record.image_sha256,
                "readme_sha256": readme_sha,
                "mapping_chain": [
                    "official_readme_layout", "patient_directory_name", "patient_id",
                ],
            },
        })
    return {"identities": identities, "records": records, "evidence": evidence}


def _verify_or_insert(
    repository: ScientificBootstrapRepository, *, table: str, key: str,
    expected_rows: list[dict[str, Any]], dataset_id: UUID, insert_sql: str,
) -> int:
    columns = ",".join(expected_rows[0]) if expected_rows else "id," + key
    existing = repository.rows_by_key(table, columns, key, dataset_id=dataset_id)
    expected_keys = {row[key] for row in expected_rows}
    if set(existing) - expected_keys:
        raise SmearIngestConflict(f"Unexpected {table} rows already exist for this source")
    inserts = []
    for row in expected_rows:
        current = existing.get(row[key])
        if current is None:
            inserts.append({name: json.dumps(value, sort_keys=True)
                            if isinstance(value, dict) else value for name, value in row.items()})
            continue
        for name, value in row.items():
            _assert_equal(f"{table} {row[key]} {name}", current[name], value)
    repository.insert_many(insert_sql, inserts)
    return len(inserts)


def ingest_smear_source(connection: Connection, inspection: SmearSourceInspection) -> dict[str, Any]:
    """Verify-or-insert within the caller's transaction; any conflict aborts it."""
    if not inspection.contract_passed:
        raise SmearIngestConflict("Source inspection contract FAIL; nothing persisted")
    repository = ScientificBootstrapRepository(connection)
    connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
    source_id = dataset_source_id()
    metadata = _dataset_metadata(inspection)
    sources = connection.execute(text(
        "SELECT * FROM datasets WHERE name=:name OR id=:id FOR UPDATE"
    ), {"name": SOURCE_NAME, "id": source_id}).mappings().all()
    expected_source = {
        "id": source_id, "name": SOURCE_NAME, "provider": SOURCE_PROVIDER,
        "source_type": "medical_image_dataset", "source_reference": SOURCE_REFERENCE,
        "url": SOURCE_REFERENCE, "total_images": len(inspection.records),
        "checksum": inspection.population_fingerprint, "metadata": metadata,
    }
    if len(sources) > 1:
        raise SmearIngestConflict("Multiple datasets rows match the smear source")
    if sources:
        for field, value in expected_source.items():
            _assert_equal(f"dataset source {field}", sources[0][field], value)
        source_inserted = False
    else:
        connection.execute(text("""
            INSERT INTO datasets (
              id,name,source,description,total_images,license,url,checksum,metadata,
              provider,source_type,source_reference
            ) VALUES (
              :id,:name,'NIH/NLM LHNCBC',:description,:total_images,
              'NLM Data License Agreement (see Data License Agreement.docx)',:url,:checksum,
              CAST(:metadata AS jsonb),:provider,:source_type,:source_reference
            )
        """), {**expected_source, "metadata": json.dumps(metadata, sort_keys=True),
               "description": "Thin blood smear images (P. falciparum) with expert Polygon "
                              "Set ground truth; one record per full smear image."})
        source_inserted = True

    rows = prepare_smear_rows(inspection)
    inserted = {
        "clinical_identities": _verify_or_insert(
            repository, table="clinical_identities", key="source_identifier",
            expected_rows=rows["identities"], dataset_id=source_id, insert_sql="""
            INSERT INTO clinical_identities (
              id,dataset_id,identity_type,source_identifier,status,metadata
            ) VALUES (:id,:dataset_id,:identity_type,:source_identifier,:status,
              CAST(:metadata AS jsonb))
        """),
        "dataset_source_records": _verify_or_insert(
            repository, table="dataset_source_records", key="source_record_key",
            expected_rows=rows["records"], dataset_id=source_id, insert_sql="""
            INSERT INTO dataset_source_records (
              id,dataset_id,clinical_identity_id,source_record_key,tfds_index,source_filename,
              class_index,class_name,original_label,project_label,relative_source_key,
              source_file_sha256,decoded_pixel_sha256,image_width,image_height,file_size_bytes,
              identity_status,metadata
            ) VALUES (
              :id,:dataset_id,:clinical_identity_id,:source_record_key,:tfds_index,
              :source_filename,:class_index,:class_name,:original_label,:project_label,
              :relative_source_key,:source_file_sha256,:decoded_pixel_sha256,:image_width,
              :image_height,:file_size_bytes,:identity_status,CAST(:metadata AS jsonb)
            )
        """),
        "identity_evidence": _verify_or_insert(
            repository, table="identity_evidence", key="source_record_id",
            expected_rows=rows["evidence"], dataset_id=source_id, insert_sql="""
            INSERT INTO identity_evidence (
              id,source_record_id,clinical_identity_id,evidence_type,evidence_level,
              mapping_method,evidence_reference,official_source_reference,evidence_json
            ) VALUES (
              :id,:source_record_id,:clinical_identity_id,:evidence_type,:evidence_level,
              :mapping_method,:evidence_reference,:official_source_reference,
              CAST(:evidence_json AS jsonb)
            )
        """),
    }
    counts = audit_smear_source(connection)
    _assert_equal("persisted smear counts", {
        key: counts[key] for key in ("patients", "source_records", "identity_evidence")
    }, {
        "patients": len(inspection.patients), "source_records": len(inspection.records),
        "identity_evidence": len(inspection.records),
    })
    return {
        "dataset_source_id": str(source_id),
        "result": "INSERTED" if source_inserted or any(inserted.values())
        else "ALREADY_INGESTED_MATCH_NO_OP",
        "inserted": {"datasets": int(source_inserted), **inserted},
        "persisted": counts,
    }


def apply_smear_source_ingest(engine: Engine, inspection: SmearSourceInspection) -> dict[str, Any]:
    with engine.begin() as connection:
        return ingest_smear_source(connection, inspection)


def audit_smear_source(connection: Connection) -> dict[str, Any]:
    """Read-only counts of the smear source population (zero when not yet ingested)."""
    scope = {"dataset_id": dataset_source_id()}
    scalar = lambda sql: connection.execute(text(sql), scope).scalar_one()
    return {
        "patients": scalar("SELECT count(*) FROM clinical_identities WHERE dataset_id=:dataset_id"),
        "source_records": scalar(
            "SELECT count(*) FROM dataset_source_records WHERE dataset_id=:dataset_id"
        ),
        "identity_evidence": scalar("""
            SELECT count(*) FROM identity_evidence e
            JOIN dataset_source_records r ON r.id=e.source_record_id
            WHERE r.dataset_id=:dataset_id
        """),
        "records_without_identity": scalar("""
            SELECT count(*) FROM dataset_source_records
            WHERE dataset_id=:dataset_id AND clinical_identity_id IS NULL
        """),
        "duplicate_image_sha256_groups": scalar("""
            SELECT count(*) FROM (SELECT source_file_sha256 FROM dataset_source_records
            WHERE dataset_id=:dataset_id GROUP BY 1 HAVING count(*)>1) d
        """),
        "dataset_versions": scalar(
            "SELECT count(*) FROM dataset_version_sources WHERE dataset_id=:dataset_id"
        ),
        "split_assignments": scalar("""
            SELECT count(*) FROM dataset_split_assignments a
            JOIN dataset_source_records r ON r.id=a.source_record_id
            WHERE r.dataset_id=:dataset_id
        """),
    }
