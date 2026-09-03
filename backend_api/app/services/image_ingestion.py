from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Request, UploadFile
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.audit import audit_transaction_connection, record_event
from app.schemas.scientific import _assert_no_pii
from app.security import Principal
from app.services.image_validation import ImageValidationError, validate_image
from app.services.local_storage import LocalStorage, StagedUpload, StorageError, UploadTooLarge
from app.services.serialization import to_jsonable
from app.services.scientific import ScientificError


NIH_SOURCE = "nih_nlm_thin_blood_smears_pf"
IGNORED_NAMES = {"thumbs.db", ".ds_store"}
CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,119}$")


def _code(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def normalize_subject_code(value: str) -> str:
    normalized = value.strip().upper()
    if not CODE_PATTERN.fullmatch(normalized) or ".." in normalized:
        raise ScientificError(422, "ID de paciente inválido.")
    return normalized


def _row(connection, sql: str, params: dict) -> dict | None:
    value = connection.execute(text(sql), params).mappings().first()
    return dict(value) if value else None


def _event(connection, request, principal, event_type, resource_type, row, after=None):
    record_event(
        event_type=event_type, action=event_type, principal=principal, request=request,
        success=True, connection=connection, resource_type=resource_type,
        resource_id=str(row["id"]), after_state=to_jsonable(after or dict(row)),
    )


def _upload_response(connection, batch_id, ignored: int) -> dict:
    lineage = _row(connection, """
      SELECT b.*,rs.subject_code,rs.status subject_status,c.case_code,
        bs.sample_code,bs.status sample_status,ss.slide_code
      FROM image_ingestion_batches b
      JOIN research_subjects rs ON rs.id=b.subject_id
      JOIN scientific_cases c ON c.id=b.case_id
      JOIN blood_samples bs ON bs.id=b.sample_id
      JOIN smear_slides ss ON ss.id=b.slide_id
      WHERE b.id=:id
    """, {"id": batch_id})
    assert lineage is not None
    images = connection.execute(text("""
      SELECT id,original_filename,sha256,width_px,height_px
      FROM microscopy_images
      WHERE ingestion_batch_id=:id
      ORDER BY image_sequence_number,id
    """), {"id": batch_id}).mappings().all()
    return {
        "subject": {
            "id": lineage["subject_id"],
            "subject_code": lineage["subject_code"],
            "status": lineage["subject_status"],
        },
        "case": {"id": lineage["case_id"], "case_code": lineage["case_code"]},
        "sample": {
            "id": lineage["sample_id"],
            "sample_code": lineage["sample_code"],
            "status": lineage["sample_status"],
        },
        "slide": {"id": lineage["slide_id"], "slide_code": lineage["slide_code"]},
        "ingestion_batch": {
            key: lineage[key]
            for key in (
                "id",
                "status",
                "acquisition_origin",
                "source_system",
                "received_image_count",
                "expected_image_count",
                "created_at",
                "completed_at",
            )
        },
        "images": [{
            **dict(image),
            "content_url": f"/api/v1/scientific/images/{image['id']}/content",
        } for image in images],
        "counts": {
            "received": lineage["received_image_count"],
            "expected": lineage["expected_image_count"],
            "ignored": ignored,
        },
        "status": lineage["status"],
    }


class ImageIngestionService:
    @staticmethod
    def lookup_subject(subject_code: str) -> dict:
        from app.db import get_primary_engine
        code = normalize_subject_code(subject_code)
        with get_primary_engine().connect() as connection:
            subject = _row(connection, """
              SELECT id,subject_code,status,source_system,external_patient_id
              FROM research_subjects WHERE upper(subject_code)=:code
            """, {"code": code})
        if not subject:
            raise ScientificError(404, "No se encontró el paciente ingresado.")
        return subject

    @staticmethod
    def samples_for_subject(subject_id: str, sample_code: str | None = None) -> list[dict]:
        from app.db import get_primary_engine
        with get_primary_engine().connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM research_subjects WHERE id=CAST(:id AS uuid)"),
                {"id": subject_id},
            ).scalar()
            if not exists:
                raise ScientificError(404, "Paciente no encontrado.")
            params = {"id": subject_id}
            exact = ""
            if sample_code:
                params["code"] = sample_code.strip().upper()
                exact = " AND bs.sample_code=:code"
            rows = connection.execute(text(f"""
              SELECT bs.id,bs.sample_code,bs.case_id,bs.status,bs.sample_identity_origin
              FROM blood_samples bs JOIN scientific_cases c ON c.id=bs.case_id
              WHERE c.subject_id=CAST(:id AS uuid){exact}
              ORDER BY bs.created_at DESC
            """), params).mappings().all()
        return [dict(row) for row in rows]

    def auto_subject(self, principal: Principal, request: Request) -> dict:
        connection = audit_transaction_connection.get()
        assert connection is not None
        return self._create_subject(connection, principal, request, None, None)

    def auto_sample(self, subject_id: str, principal: Principal, request: Request) -> dict:
        connection = audit_transaction_connection.get()
        assert connection is not None
        subject = _row(connection, "SELECT * FROM research_subjects WHERE id=CAST(:id AS uuid)", {"id": subject_id})
        if not subject:
            raise ScientificError(404, "Paciente no encontrado.")
        if subject["status"] != "active":
            raise ScientificError(409, "No se puede reutilizar un paciente archivado.")
        case = self._resolve_case(connection, subject, "manual_upload", None, principal, request)
        return self._create_sample(connection, subject, case, None, None, None, principal, request)

    def _create_subject(self, connection, principal, request, source_system, external_patient_id):
        for _ in range(5):
            try:
                row = _row(connection, """
                  INSERT INTO research_subjects(
                    id,subject_code,status,source_system,external_patient_id,created_by
                  ) VALUES(
                    :id,:code,'active',:source,:external,CAST(:actor AS uuid)
                  ) RETURNING *
                """, {"id": uuid4(), "code": _code("PAT"), "source": source_system,
                      "external": external_patient_id, "actor": principal.user_id})
                _event(connection, request, principal, "scientific.subject.auto_created", "research_subject", row)
                return row
            except IntegrityError:
                continue
        raise ScientificError(409, "No fue posible generar un ID único de paciente.")

    def _resolve_case(self, connection, subject, origin, source_system, principal, request):
        source_type = {
            "manual_upload": "imported_image",
            "research_dataset_import": "research_dataset",
            "external_capture_system": "physical_microscope",
        }[origin]
        case = _row(connection, """
          SELECT * FROM scientific_cases
          WHERE subject_id=:subject AND source_type=:source_type
            AND status IN ('registered','ready')
          ORDER BY CASE status WHEN 'ready' THEN 0 ELSE 1 END,created_at LIMIT 1
        """, {"subject": subject["id"], "source_type": source_type})
        if case:
            return case
        case = _row(connection, """
          INSERT INTO scientific_cases(
            id,case_code,subject_id,source_type,status,priority,metadata_json,created_by
          ) VALUES(:id,:code,:subject,:source_type,'registered','normal','{}',CAST(:actor AS uuid))
          RETURNING *
        """, {"id": uuid4(), "code": _code("CAS"), "subject": subject["id"],
              "source_type": source_type, "actor": principal.user_id})
        _event(connection, request, principal, "scientific.case.auto_created", "scientific_case", case)
        return case

    def _create_sample(self, connection, subject, case, source_system, external_sample_id,
                       source_group_key, principal, request):
        sample = _row(connection, """
          INSERT INTO blood_samples(
            id,case_id,sample_code,specimen_type,status,source_system,external_sample_id,
            sample_identity_origin,source_group_key,ingestion_status,expected_image_count,created_by
          ) VALUES(
            :id,:case,:code,'peripheral_blood','registered',:source,:external,
            :identity_origin,:group_key,'pending',:expected,CAST(:actor AS uuid)
          ) RETURNING *
        """, {
            "id": uuid4(), "case": case["id"], "code": _code("SMP"), "source": source_system,
            "external": external_sample_id,
            "identity_origin": "external_system" if external_sample_id else "generated_by_capstone",
            "group_key": source_group_key, "expected": 5 if source_system == NIH_SOURCE else None,
            "actor": principal.user_id,
        })
        _event(connection, request, principal, "scientific.sample.auto_created", "blood_sample", sample)
        return sample

    async def upload(
        self, *, files: list[UploadFile], subject_mode: str, subject_code: str | None,
        sample_mode: str, sample_id: str | None, acquisition_origin: str,
        source_system: str | None, external_patient_id: str | None,
        external_sample_id: str | None, source_component_id: str | None,
        source_group_key: str | None, captured_at: datetime | None, metadata_json: dict,
        principal: Principal, request: Request,
    ) -> dict:
        connection = audit_transaction_connection.get()
        assert connection is not None
        if subject_mode not in {"existing", "automatic_new"} or sample_mode not in {"existing", "automatic_new"}:
            raise ScientificError(422, "Modo de identidad inválido.")
        if (subject_mode == "existing") != bool(subject_code):
            raise ScientificError(422, "subject_code debe enviarse solo para un paciente existente.")
        if (sample_mode == "existing") != bool(sample_id):
            raise ScientificError(422, "sample_id debe enviarse solo para una muestra existente.")
        if acquisition_origin not in {"manual_upload", "research_dataset_import", "external_capture_system"}:
            raise ScientificError(422, "acquisition_origin inválido.")
        if acquisition_origin != "manual_upload" and not source_system:
            raise ScientificError(422, "source_system es obligatorio para este origen.")
        is_nih = source_system == NIH_SOURCE
        if is_nih and (acquisition_origin != "research_dataset_import" or not external_patient_id):
            raise ScientificError(422, "El perfil NIH-NLM requiere external_patient_id.")
        _assert_no_pii(metadata_json)
        external_patient_id = external_patient_id.strip() if external_patient_id else None
        source_group_key = (
            (external_sample_id or external_patient_id) if is_nih else source_group_key
        )
        selected = [
            upload for upload in files
            if (upload.filename or "").lower() not in IGNORED_NAMES
            and not (upload.filename or "").startswith(".")
        ]
        if not selected:
            raise ScientificError(422, "No se recibieron imágenes científicas válidas.")

        client_request_id = metadata_json.get("client_request_id")
        if client_request_id is not None:
            try:
                client_request_id = str(UUID(str(client_request_id)))
            except (TypeError, ValueError, AttributeError) as exc:
                raise ScientificError(422, "client_request_id inválido.") from exc
            metadata_json["client_request_id"] = client_request_id
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"{principal.user_id}:{client_request_id}"},
            )
            existing_batch_id = connection.execute(text("""
              SELECT id
              FROM image_ingestion_batches
              WHERE created_by=CAST(:actor AS uuid)
                AND metadata_json->>'client_request_id'=:request_id
              ORDER BY created_at,id
              LIMIT 1
            """), {
                "actor": principal.user_id,
                "request_id": client_request_id,
            }).scalar()
            if existing_batch_id:
                return _upload_response(
                    connection,
                    existing_batch_id,
                    len(files) - len(selected),
                )

        if subject_mode == "existing":
            subject = _row(connection, "SELECT * FROM research_subjects WHERE upper(subject_code)=:code",
                           {"code": normalize_subject_code(subject_code or "")})
            if not subject:
                raise ScientificError(404, "No se encontró el paciente ingresado.")
            if subject["status"] != "active":
                raise ScientificError(409, "No se puede reutilizar un paciente archivado.")
        else:
            subject = None
            if source_system and external_patient_id:
                subject = _row(connection, """
                  SELECT * FROM research_subjects
                  WHERE source_system=:source AND external_patient_id=:external
                """, {"source": source_system, "external": external_patient_id})
                if subject and subject["status"] != "active":
                    raise ScientificError(
                        409, "La identidad externa corresponde a un paciente archivado."
                    )
            subject = subject or self._create_subject(
                connection, principal, request, source_system, external_patient_id,
            )

        if sample_mode == "existing":
            sample = _row(connection, """
              SELECT bs.* FROM blood_samples bs JOIN scientific_cases c ON c.id=bs.case_id
              WHERE bs.id=CAST(:id AS uuid) AND c.subject_id=:subject
            """, {"id": sample_id, "subject": subject["id"]})
            if not sample:
                raise ScientificError(409, "La muestra no pertenece al paciente.")
            if sample["status"] == "archived":
                raise ScientificError(409, "No se puede reutilizar una muestra archivada.")
            case = _row(
                connection,
                "SELECT * FROM scientific_cases WHERE id=:id",
                {"id": sample["case_id"]},
            )
            if not case or case["status"] not in {"registered", "ready"}:
                raise ScientificError(
                    409, "La muestra pertenece a un caso no reutilizable."
                )
        else:
            case = self._resolve_case(
                connection, subject, acquisition_origin, source_system,
                principal, request,
            )
            sample = None
            if source_system and source_group_key:
                sample = _row(connection, """
                  SELECT bs.* FROM blood_samples bs
                  WHERE bs.case_id=:case AND bs.source_system=:source
                    AND (bs.external_sample_id=:external OR
                         (bs.external_sample_id IS NULL AND bs.source_group_key=:group_key))
                  ORDER BY bs.created_at LIMIT 1
                """, {"case": case["id"], "source": source_system,
                      "external": external_sample_id, "group_key": source_group_key})
                if sample and sample["status"] == "archived":
                    raise ScientificError(
                        409, "La identidad externa corresponde a una muestra archivada."
                    )
            sample = sample or self._create_sample(
                connection, subject, case, source_system, external_sample_id,
                source_group_key, principal, request,
            )

        batch = None
        if source_system and source_group_key:
            batch = _row(connection, """
              SELECT * FROM image_ingestion_batches
              WHERE source_system=:source AND source_group_key=:group_key FOR UPDATE
            """, {"source": source_system, "group_key": source_group_key})
        if batch:
            slide = _row(connection, "SELECT * FROM smear_slides WHERE id=:id", {"id": batch["slide_id"]})
            same_lineage = (
                str(batch["subject_id"]) == str(subject["id"])
                and str(batch["case_id"]) == str(case["id"])
                and str(batch["sample_id"]) == str(sample["id"])
            )
            if not same_lineage:
                raise ScientificError(
                    409, "El grupo de origen ya pertenece a otro linaje científico."
                )
            if not slide or slide["status"] == "archived":
                raise ScientificError(409, "No se puede reutilizar un frotis archivado.")
        else:
            slide = _row(connection, """
              INSERT INTO smear_slides(id,sample_id,slide_code,smear_type,status,created_by)
              VALUES(:id,:sample,:code,:smear,'registered',CAST(:actor AS uuid)) RETURNING *
            """, {"id": uuid4(), "sample": sample["id"], "code": _code("SLD"),
                  "smear": "thin" if is_nih else "unknown", "actor": principal.user_id})
            _event(connection, request, principal, "scientific.slide.auto_created", "smear_slide", slide)
            batch = _row(connection, """
              INSERT INTO image_ingestion_batches(
                id,subject_id,case_id,sample_id,slide_id,acquisition_origin,source_system,
                source_group_key,expected_image_count,created_by,metadata_json
              ) VALUES(
                :id,:subject,:case,:sample,:slide,:origin,:source,:group_key,:expected,
                CAST(:actor AS uuid),CAST(:metadata AS jsonb)
              ) RETURNING *
            """, {"id": uuid4(), "subject": subject["id"], "case": case["id"],
                  "sample": sample["id"], "slide": slide["id"], "origin": acquisition_origin,
                  "source": source_system, "group_key": source_group_key,
                  "expected": 5 if is_nih else None, "actor": principal.user_id,
                  "metadata": json.dumps(metadata_json)})
            _event(connection, request, principal, "scientific.ingestion_batch.created",
                   "image_ingestion_batch", batch)

        storage = LocalStorage()
        staged: list[tuple[StagedUpload, object, UploadFile]] = []
        final_paths: list[Path] = []
        request.state.storage_compensation = final_paths
        request.state.storage_compensation_storage = storage
        try:
            for upload in sorted(selected, key=lambda item: (item.filename or "").casefold()):
                item = await storage.stage(upload)
                staged.append((item, validate_image(item.path), upload))
            next_sequence = connection.execute(text("""
              SELECT COALESCE(max(image_sequence_number),0)
              FROM microscopy_images WHERE ingestion_batch_id=:batch
            """), {"batch": batch["id"]}).scalar_one()
            images = []
            for item, technical, _ in staged:
                source_name = item.original_filename if source_system else None
                relative_path = (
                    f"{external_patient_id}/Img/{source_name}" if is_nih else
                    (f"{source_group_key}/{source_name}" if source_system and source_name else None)
                )
                existing = None
                if source_system and relative_path:
                    existing = _row(connection, """
                      SELECT * FROM microscopy_images
                      WHERE source_system=:source AND source_relative_path=:path
                    """, {"source": source_system, "path": relative_path})
                if existing:
                    if existing["sha256"] != item.sha256:
                        raise ScientificError(409, "La ruta externa ya existe con contenido diferente.")
                    storage.cleanup(
                        [item.path],
                        boundaries=(storage.staging / "uploads",),
                    )
                    images.append(existing)
                    continue
                duplicate = _row(connection, """
                  SELECT id FROM microscopy_images WHERE slide_id=:slide AND sha256=:sha
                """, {"slide": slide["id"], "sha": item.sha256})
                if duplicate:
                    raise ScientificError(409, "La misma imagen ya existe en el frotis.")
                next_sequence += 1
                image_id = uuid4()
                key = storage.build_key(
                    UUID(str(subject["id"])), UUID(str(sample["id"])), UUID(str(slide["id"])),
                    image_id, item.sha256, technical.extension,
                )
                image = _row(connection, """
                  INSERT INTO microscopy_images(
                    id,slide_id,image_code,storage_provider,storage_key,original_filename,mime_type,
                    file_size_bytes,sha256,width_px,height_px,bit_depth,status,metadata_json,created_by,
                    acquisition_origin,source_system,source_component_id,source_image_name,
                    source_relative_path,image_sequence_number,detected_format,channel_count,
                    color_space,orientation,ingestion_batch_id,captured_at
                  ) VALUES(
                    :id,:slide,:code,'local',:key,:filename,:mime,:size,:sha,:width,:height,:depth,
                    'available',CAST(:metadata AS jsonb),CAST(:actor AS uuid),:origin,:source,
                    :component,:source_name,:relative_path,:sequence,:format,:channels,:color,
                    :orientation,:batch,:captured_at
                  ) RETURNING *
                """, {
                    "id": image_id, "slide": slide["id"], "code": _code("IMG"), "key": key,
                    "filename": item.original_filename, "mime": technical.mime_type, "size": item.size,
                    "sha": item.sha256, "width": technical.width_px, "height": technical.height_px,
                    "depth": technical.bit_depth, "metadata": json.dumps(metadata_json),
                    "actor": principal.user_id, "origin": acquisition_origin, "source": source_system,
                    "component": source_component_id, "source_name": source_name,
                    "relative_path": relative_path, "sequence": next_sequence,
                    "format": technical.detected_format, "channels": technical.channel_count,
                    "color": technical.color_space, "orientation": technical.orientation,
                    "batch": batch["id"], "captured_at": captured_at,
                })
                final = storage.promote(
                    item.path,
                    key,
                    expected_size_bytes=item.size,
                    expected_sha256=item.sha256,
                )
                final_paths.append(final)
                after = {
                    "image_id": str(image_id), "subject_id": str(subject["id"]),
                    "case_id": str(case["id"]), "sample_id": str(sample["id"]),
                    "slide_id": str(slide["id"]), "ingestion_batch_id": str(batch["id"]),
                    "subject_code": subject["subject_code"], "sample_code": sample["sample_code"],
                    "acquisition_origin": acquisition_origin, "source_system": source_system,
                    "external_patient_id": external_patient_id,
                    "external_sample_id": external_sample_id, "source_group_key": source_group_key,
                    "source_image_name": source_name, "image_sequence_number": next_sequence,
                    "sha256": item.sha256, "file_size_bytes": item.size,
                    "width_px": technical.width_px, "height_px": technical.height_px,
                    "status": "available",
                }
                _event(connection, request, principal,
                       "scientific.image.imported" if is_nih else "scientific.image.uploaded",
                       "microscopy_image", image, after)
                images.append(image)
            received = connection.execute(text("""
              SELECT count(*) FROM microscopy_images WHERE ingestion_batch_id=:batch
            """), {"batch": batch["id"]}).scalar_one()
            expected = 5 if is_nih else batch["expected_image_count"]
            status = (
                "complete" if expected is None or received == expected else
                "incomplete" if received < expected else "inconsistent"
            )
            batch = _row(connection, """
              UPDATE image_ingestion_batches SET received_image_count=:received,status=:status,
                updated_at=NOW(),completed_at=CASE WHEN CAST(:status AS varchar)='complete' THEN NOW() ELSE NULL END
              WHERE id=:id RETURNING *
            """, {"received": received, "status": status, "id": batch["id"]})
            connection.execute(text("""
              UPDATE blood_samples SET ingestion_status=:status,expected_image_count=:expected,
                updated_at=NOW() WHERE id=:id
            """), {"status": status, "expected": expected, "id": sample["id"]})
            _event(connection, request, principal, "scientific.ingestion_batch.updated",
                   "image_ingestion_batch", batch)
            return _upload_response(
                connection,
                batch["id"],
                len(files) - len(selected),
            )
        except UploadTooLarge as exc:
            raise ScientificError(413, str(exc)) from exc
        except (StorageError, ImageValidationError) as exc:
            raise ScientificError(422, str(exc)) from exc
        finally:
            storage.cleanup(
                [item.path for item, _, _ in staged],
                boundaries=(storage.staging / "uploads",),
            )
