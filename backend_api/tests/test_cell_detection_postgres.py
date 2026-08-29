from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from PIL import Image, ImageDraw
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from app.config import Settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url
from app.observability import correlation_id_context
from app.security import Principal
from app.services.cell_analysis import (
    CellAnalysisError,
    CellAnalysisService,
    frozen_manifest,
)
from app.services.cell_crop_storage import CellCropStorage
from app.services.detectors.connected_components_v1 import (
    ALGORITHM_VERSION,
    COORDINATE_SPACE,
    DETECTOR_KEY,
    DETECTOR_VERSION,
)
from app.services.local_storage import LocalStorage


pytestmark = pytest.mark.requires_docker_postgres

CELL_CODE = re.compile(r"^CELL-[A-F0-9]{12}$")
CROP_KEY = re.compile(
    r"^cell-crops/"
    r"[0-9a-f-]{36}/[0-9a-f-]{36}/[0-9a-f-]{36}/[0-9a-f-]{36}/crop[.]png$"
)


@pytest.fixture(autouse=True)
def require_docker_gate():
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL Docker explícito")


class TransactionEngine:
    """Expose service-style transactions as savepoints of one test transaction."""

    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1),
            "scheme": "http",
        }
    )


def _synthetic_png(seed: int) -> bytes:
    image = Image.new("RGB", (160, 120), "white")
    drawing = ImageDraw.Draw(image)
    shift = seed % 5
    for box in (
        (18 + shift, 16, 42 + shift, 40),
        (68, 22 + shift, 94, 48 + shift),
        (105 - shift, 67, 133 - shift, 95),
    ):
        drawing.ellipse(box, fill=(12, 12, 12))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@dataclass(frozen=True)
class AnalysisFixture:
    analysis_run_id: UUID
    analysis_run_image_id: UUID
    microscopy_image_id: UUID
    storage_key: str
    source_path: Path
    source_bytes: bytes
    sha256: str
    width_px: int
    height_px: int


@dataclass
class PostgresContext:
    connection: object
    shared_engine: TransactionEngine
    local_storage: LocalStorage
    crop_storage: CellCropStorage
    actor: Principal
    actor_id: UUID
    suffix: str
    sequence: int = 0

    @property
    def service(self) -> CellAnalysisService:
        return CellAnalysisService(
            engine=self.shared_engine,
            local_storage=self.local_storage,
            crop_storage=self.crop_storage,
        )

    def create_analysis(
        self,
        *,
        gate_status: str = "pass",
        ready_for_analysis: bool = True,
        approve_warning: bool = False,
    ) -> AnalysisFixture:
        self.sequence += 1
        token = f"{self.suffix}{self.sequence:02d}"
        subject_id = uuid4()
        case_id = uuid4()
        sample_id = uuid4()
        slide_id = uuid4()
        ingestion_batch_id = uuid4()
        microscopy_image_id = uuid4()
        analysis_run_id = uuid4()
        analysis_run_image_id = uuid4()
        payload = _synthetic_png(self.sequence)
        digest = hashlib.sha256(payload).hexdigest()
        storage_key = (
            f"microscopy-images/{subject_id}/{sample_id}/{slide_id}/"
            f"{microscopy_image_id}/{digest}.png"
        )
        source_path = self.local_storage.resolve(storage_key)
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(payload)

        self.connection.execute(
            text(
                """
                INSERT INTO research_subjects(
                  id,subject_code,status,created_by,updated_by
                ) VALUES(:id,:code,'active',:actor,:actor)
                """
            ),
            {"id": subject_id, "code": f"SUB-CELL-{token}", "actor": self.actor_id},
        )
        self.connection.execute(
            text(
                """
                INSERT INTO scientific_cases(
                  id,case_code,subject_id,source_type,status,created_by,updated_by
                ) VALUES(
                  :id,:code,:subject,'synthetic','ready',:actor,:actor
                )
                """
            ),
            {
                "id": case_id,
                "code": f"CASE-CELL-{token}",
                "subject": subject_id,
                "actor": self.actor_id,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO blood_samples(
                  id,case_id,sample_code,status,created_by,updated_by
                ) VALUES(:id,:case_id,:code,'prepared',:actor,:actor)
                """
            ),
            {
                "id": sample_id,
                "case_id": case_id,
                "code": f"SAMPLE-CELL-{token}",
                "actor": self.actor_id,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO smear_slides(
                  id,sample_id,slide_code,smear_type,status,created_by,updated_by
                ) VALUES(
                  :id,:sample_id,:code,'thin','ready_for_capture',:actor,:actor
                )
                """
            ),
            {
                "id": slide_id,
                "sample_id": sample_id,
                "code": f"SLIDE-CELL-{token}",
                "actor": self.actor_id,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO image_ingestion_batches(
                  id,subject_id,case_id,sample_id,slide_id,acquisition_origin,
                  expected_image_count,received_image_count,status,created_by,
                  completed_at
                ) VALUES(
                  :id,:subject,:case_id,:sample,:slide,'manual_upload',
                  1,1,'complete',:actor,now()
                )
                """
            ),
            {
                "id": ingestion_batch_id,
                "subject": subject_id,
                "case_id": case_id,
                "sample": sample_id,
                "slide": slide_id,
                "actor": self.actor_id,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO microscopy_images(
                  id,slide_id,image_code,storage_provider,storage_key,
                  original_filename,mime_type,file_size_bytes,sha256,width_px,
                  height_px,status,created_by,updated_by,acquisition_origin,
                  ingestion_batch_id,detected_format,channel_count,color_space
                ) VALUES(
                  :id,:slide,:code,'local',:storage_key,
                  'patient-private-name.png','image/png',:size,:sha,160,120,
                  'available',:actor,:actor,'manual_upload',:batch,'PNG',3,'RGB'
                )
                """
            ),
            {
                "id": microscopy_image_id,
                "slide": slide_id,
                "code": f"IMG-CELL-{token}",
                "storage_key": storage_key,
                "size": len(payload),
                "sha": digest,
                "actor": self.actor_id,
                "batch": ingestion_batch_id,
            },
        )
        manifest = frozen_manifest(
            [
                {
                    "microscopy_image_id": microscopy_image_id,
                    "input_sha256": digest,
                    "input_file_size_bytes": len(payload),
                    "input_width_px": 160,
                    "input_height_px": 120,
                    "sequence_number": 1,
                }
            ]
        )
        self.connection.execute(
            text(
                """
                INSERT INTO microscopy_analysis_runs(
                  id,ingestion_batch_id,subject_id,case_id,sample_id,slide_id,
                  run_code,run_status,active_stage,quality_gate_status,
                  ready_for_analysis,quality_profile_key,quality_profile_version,
                  quality_algorithm_version,quality_profile_snapshot,
                  input_manifest_sha256,input_image_count,requested_by,
                  started_at,completed_at
                ) VALUES(
                  :id,:batch,:subject,:case_id,:sample,:slide,:run_code,
                  'ready_for_analysis','completed',:gate_status,:ready,
                  'technical_quality_v1','1.0.0','quality-1.0.0',
                  CAST(:profile AS jsonb),:manifest,1,:actor,now(),now()
                )
                """
            ),
            {
                "id": analysis_run_id,
                "batch": ingestion_batch_id,
                "subject": subject_id,
                "case_id": case_id,
                "sample": sample_id,
                "slide": slide_id,
                "run_code": f"ANA-{token}"[:20],
                "gate_status": gate_status,
                "ready": ready_for_analysis,
                "profile": json.dumps({"test_fixture": True}),
                "manifest": manifest,
                "actor": self.actor_id,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO microscopy_analysis_run_images(
                  id,analysis_run_id,microscopy_image_id,sequence_number,
                  input_sha256,input_file_size_bytes,input_width_px,input_height_px,
                  image_status_at_creation,quality_status
                ) VALUES(
                  :id,:run_id,:image_id,1,:sha,:size,160,120,'available',
                  :quality_status
                )
                """
            ),
            {
                "id": analysis_run_image_id,
                "run_id": analysis_run_id,
                "image_id": microscopy_image_id,
                "sha": digest,
                "size": len(payload),
                "quality_status": gate_status,
            },
        )
        if approve_warning:
            self.connection.execute(
                text(
                    """
                    INSERT INTO quality_gate_decisions(
                      id,analysis_run_id,decision,comment,actor_user_id
                    ) VALUES(
                      :id,:run_id,'approve_with_warnings',
                      'Aprobación técnica de fixture.',:actor
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "run_id": analysis_run_id,
                    "actor": self.actor_id,
                },
            )
        return AnalysisFixture(
            analysis_run_id=analysis_run_id,
            analysis_run_image_id=analysis_run_image_id,
            microscopy_image_id=microscopy_image_id,
            storage_key=storage_key,
            source_path=source_path,
            source_bytes=payload,
            sha256=digest,
            width_px=160,
            height_px=120,
        )


@pytest.fixture()
def postgres_context(tmp_path):
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    connection = engine.connect()
    outer = connection.begin()
    assert_capstone_database(
        settings,
        connection.execute(text("SELECT current_database()")).scalar_one(),
    )
    assert connection.execute(
        text(
            """
            SELECT version_num='20260810_05'
            FROM alembic_version
            """
        )
    ).scalar_one(), "la migración 20260810_05 debe estar aplicada"

    actor_id = uuid4()
    suffix = uuid4().hex[:10]
    username = f"cell_pg_{suffix}"
    connection.execute(
        text(
            """
            INSERT INTO users(id,username,email,password_hash,status)
            VALUES(:id,:username,:email,'test-not-used','active')
            """
        ),
        {
            "id": actor_id,
            "username": username,
            "email": f"{username}@invalid.test",
        },
    )
    test_settings = replace(
        settings,
        storage_root=tmp_path / "storage",
        storage_provider="local",
    )
    local = LocalStorage(test_settings)
    crops = CellCropStorage(local)
    token = correlation_id_context.set(f"cell-pg-{suffix}")
    try:
        yield PostgresContext(
            connection=connection,
            shared_engine=TransactionEngine(connection),
            local_storage=local,
            crop_storage=crops,
            actor=Principal(
                user_id=str(actor_id),
                username=username,
                roles=("administrator",),
                permissions=frozenset(),
            ),
            actor_id=actor_id,
            suffix=suffix,
        )
    finally:
        correlation_id_context.reset(token)
        outer.rollback()
        residue = connection.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM users WHERE id=:actor_id),
                  (SELECT count(*) FROM cell_detection_runs
                    WHERE requested_by=:actor_id),
                  (SELECT count(*) FROM audit_events
                    WHERE actor_user_id=:actor_id)
                """
            ),
            {"actor_id": actor_id},
        ).one()
        assert residue == (0, 0, 0)
        connection.close()
        engine.dispose()


def test_eligibility_requires_pass_or_an_approved_warning(postgres_context):
    context = postgres_context
    passed = context.create_analysis(gate_status="pass")
    warning_blocked = context.create_analysis(gate_status="warning")
    warning_approved = context.create_analysis(
        gate_status="warning", approve_warning=True
    )
    not_ready = context.create_analysis(
        gate_status="pass", ready_for_analysis=False
    )

    result = context.service.eligible_analysis_runs(limit=500, offset=0)
    ids = {UUID(str(item["id"])) for item in result["items"]}
    assert passed.analysis_run_id in ids
    assert warning_approved.analysis_run_id in ids
    assert warning_blocked.analysis_run_id not in ids
    assert not_ready.analysis_run_id not in ids

    with pytest.raises(CellAnalysisError) as rejected:
        context.service.execute_detection(
            str(warning_blocked.analysis_run_id),
            context.actor,
            _request("/api/v1/cell-analysis/detection-runs"),
        )
    assert rejected.value.code == "QUALITY_GATE_NOT_APPROVED"
    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM cell_detection_runs
            WHERE analysis_run_id=:run_id
            """
        ),
        {"run_id": warning_blocked.analysis_run_id},
    ).scalar_one() == 0


def test_real_execution_is_idempotent_traceable_and_file_backed(postgres_context):
    context = postgres_context
    fixture = context.create_analysis()
    service = context.service
    request = _request("/api/v1/cell-analysis/detection-runs")

    first = service.execute_detection(
        str(fixture.analysis_run_id), context.actor, request
    )
    assert first["idempotent"] is False
    assert first["status"] == "completed"
    assert first["detector_key"] == DETECTOR_KEY
    assert first["detector_version"] == DETECTOR_VERSION
    assert first["algorithm_version"] == ALGORITHM_VERSION
    assert first["profile_snapshot"]["coordinate_space"] == COORDINATE_SPACE
    assert first["image_count"] == first["processed_image_count"] == 1
    assert first["component_count"] >= 3
    assert first["detection_count"] == first["crop_count"] >= 3
    assert first["warning_count"] == 0
    detection_run_id = UUID(str(first["id"]))

    persisted_counts = context.connection.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM image_connected_components
                WHERE detection_run_id=:id) components,
              (SELECT count(*) FROM cell_detections
                WHERE detection_run_id=:id) detections,
              (SELECT count(*) FROM cell_crops crop
                JOIN cell_detections cell ON cell.id=crop.cell_detection_id
                WHERE cell.detection_run_id=:id) crops,
              (SELECT count(*) FROM cell_detection_events
                WHERE detection_run_id=:id) events,
              (SELECT count(*) FROM audit_events
                WHERE resource_type='cell_detection_run'
                  AND resource_id=CAST(:id AS text)) audit_events
            """
        ),
        {"id": detection_run_id},
    ).mappings().one()
    assert persisted_counts["components"] == first["component_count"]
    assert persisted_counts["detections"] == first["detection_count"]
    assert persisted_counts["crops"] == first["crop_count"]
    assert persisted_counts["events"] == 4
    assert persisted_counts["audit_events"] == 3

    events = context.connection.execute(
        text(
            """
            SELECT event_type,status,metadata_json
            FROM cell_detection_events
            WHERE detection_run_id=:id
            ORDER BY created_at,id
            """
        ),
        {"id": detection_run_id},
    ).mappings().all()
    assert {row["event_type"] for row in events} == {
        "cell_detection.run.created",
        "cell_detection.run.started",
        "cell_detection.image.completed",
        "cell_detection.run.completed",
    }
    image_event = next(
        row for row in events
        if row["event_type"] == "cell_detection.image.completed"
    )
    assert image_event["metadata_json"]["raw_width_px"] == fixture.width_px
    assert image_event["metadata_json"]["raw_height_px"] == fixture.height_px
    assert image_event["metadata_json"]["oriented_width_px"] == fixture.width_px
    assert image_event["metadata_json"]["oriented_height_px"] == fixture.height_px

    detections = context.connection.execute(
        text(
            """
            SELECT
              cell.id,cell.cell_code,cell.coordinate_space,
              cell.bbox_x,cell.bbox_y,cell.bbox_width,cell.bbox_height,
              component.component_status,component.bbox_x component_bbox_x,
              component.bbox_y component_bbox_y,
              component.bbox_width component_bbox_width,
              component.bbox_height component_bbox_height,
              crop.relative_storage_key,crop.sha256,crop.file_size_bytes,
              crop.width_px crop_width_px,crop.height_px crop_height_px,
              crop.format
            FROM cell_detections cell
            JOIN image_connected_components component
              ON component.id=cell.connected_component_id
            JOIN cell_crops crop ON crop.cell_detection_id=cell.id
            WHERE cell.detection_run_id=:id
            ORDER BY cell.cell_index
            """
        ),
        {"id": detection_run_id},
    ).mappings().all()
    assert len(detections) == first["detection_count"]
    for row in detections:
        assert CELL_CODE.fullmatch(row["cell_code"])
        assert row["coordinate_space"] == COORDINATE_SPACE
        assert row["component_status"] == "accepted"
        assert (
            row["bbox_x"],
            row["bbox_y"],
            row["bbox_width"],
            row["bbox_height"],
        ) == (
            row["component_bbox_x"],
            row["component_bbox_y"],
            row["component_bbox_width"],
            row["component_bbox_height"],
        )
        assert 0 <= row["bbox_x"] < fixture.width_px
        assert 0 <= row["bbox_y"] < fixture.height_px
        assert row["bbox_x"] + row["bbox_width"] <= fixture.width_px
        assert row["bbox_y"] + row["bbox_height"] <= fixture.height_px
        assert CROP_KEY.fullmatch(row["relative_storage_key"])
        crop_path = context.crop_storage.resolve(
            row["relative_storage_key"], must_exist=True
        )
        crop_bytes = crop_path.read_bytes()
        assert len(crop_bytes) == row["file_size_bytes"]
        assert hashlib.sha256(crop_bytes).hexdigest() == row["sha256"]
        with Image.open(crop_path) as crop_image:
            assert crop_image.format == row["format"] == "PNG"
            assert crop_image.size == (
                row["crop_width_px"],
                row["crop_height_px"],
            )

    # The detector is derived-only: no original byte or frozen metadata changes.
    assert fixture.source_path.read_bytes() == fixture.source_bytes
    original = context.connection.execute(
        text(
            """
            SELECT storage_key,sha256,file_size_bytes,width_px,height_px,status
            FROM microscopy_images WHERE id=:id
            """
        ),
        {"id": fixture.microscopy_image_id},
    ).mappings().one()
    assert original == {
        "storage_key": fixture.storage_key,
        "sha256": fixture.sha256,
        "file_size_bytes": len(fixture.source_bytes),
        "width_px": fixture.width_px,
        "height_px": fixture.height_px,
        "status": "available",
    }

    audit_before_retry = context.connection.execute(
        text(
            """
            SELECT count(*) FROM audit_events
            WHERE resource_type='cell_detection_run'
              AND resource_id=CAST(:id AS text)
            """
        ),
        {"id": detection_run_id},
    ).scalar_one()
    second = service.execute_detection(
        str(fixture.analysis_run_id), context.actor, request
    )
    assert second["id"] == detection_run_id
    assert second["idempotent"] is True
    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM cell_detection_runs
            WHERE analysis_run_id=:analysis_run_id
              AND detector_key=:detector_key
              AND detector_version=:detector_version
              AND algorithm_version=:algorithm_version
            """
        ),
        {
            "analysis_run_id": fixture.analysis_run_id,
            "detector_key": DETECTOR_KEY,
            "detector_version": DETECTOR_VERSION,
            "algorithm_version": ALGORITHM_VERSION,
        },
    ).scalar_one() == 1
    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM audit_events
            WHERE resource_type='cell_detection_run'
              AND resource_id=CAST(:id AS text)
            """
        ),
        {"id": detection_run_id},
    ).scalar_one() == audit_before_retry

    audit_payload = json.dumps(
        [
            dict(row)
            for row in context.connection.execute(
                text(
                    """
                    SELECT before_state,after_state,metadata
                    FROM audit_events
                    WHERE resource_type='cell_detection_run'
                      AND resource_id=CAST(:id AS text)
                    """
                ),
                {"id": detection_run_id},
            ).mappings()
        ],
        default=str,
    ).lower()
    assert "patient-private-name" not in audit_payload
    assert fixture.storage_key.lower() not in audit_payload
    assert "relative_storage_key" not in audit_payload


def test_review_effective_state_is_append_only_and_terminal_rows_are_guarded(
    postgres_context,
):
    context = postgres_context
    fixture = context.create_analysis()
    service = context.service
    run = service.execute_detection(
        str(fixture.analysis_run_id),
        context.actor,
        _request("/api/v1/cell-analysis/detection-runs"),
    )
    detection_run_id = UUID(str(run["id"]))
    detection_id = context.connection.execute(
        text(
            """
            SELECT id FROM cell_detections
            WHERE detection_run_id=:id ORDER BY cell_index LIMIT 1
            """
        ),
        {"id": detection_run_id},
    ).scalar_one()

    accepted = service.create_review(
        cell_detection_id=str(detection_id),
        decision="accepted",
        comment=None,
        principal=context.actor,
        request=_request(
            f"/api/v1/cell-analysis/detections/{detection_id}/reviews"
        ),
    )
    assert accepted["effective_review_status"] == "accepted"
    comment_only = service.create_review(
        cell_detection_id=str(detection_id),
        decision="comment_only",
        comment="Observación técnica sin cambiar la decisión.",
        principal=context.actor,
        request=_request(
            f"/api/v1/cell-analysis/detections/{detection_id}/reviews"
        ),
    )
    assert comment_only["effective_review_status"] == "accepted"

    detail = service.get_detection(str(detection_id))
    assert detail["review_status"] == "accepted"
    assert len(detail["review_history"]) == 2
    assert {row["decision"] for row in detail["review_history"]} == {
        "accepted",
        "comment_only",
    }
    summary = service.get_run(str(detection_run_id))
    assert summary["review_counts"]["reviewed"] == 1
    assert summary["review_counts"]["accepted"] == 1
    assert (
        summary["review_counts"]["unreviewed"]
        == summary["detection_count"] - 1
    )

    review_audit = context.connection.execute(
        text(
            """
            SELECT after_state FROM audit_events
            WHERE event_type='scientific.cell_review.created'
              AND resource_id=CAST(:id AS text)
            ORDER BY created_at,id
            """
        ),
        {"id": detection_id},
    ).scalars().all()
    assert len(review_audit) == 2
    assert all("comment" not in state for state in review_audit)
    by_decision = {state["decision"]: state for state in review_audit}
    assert by_decision["accepted"]["comment_present"] is False
    assert by_decision["comment_only"]["comment_present"] is True
    assert by_decision["comment_only"]["comment_length"] > 0

    component_id = context.connection.execute(
        text(
            "SELECT connected_component_id FROM cell_detections WHERE id=:id"
        ),
        {"id": detection_id},
    ).scalar_one()
    crop_id = context.connection.execute(
        text("SELECT id FROM cell_crops WHERE cell_detection_id=:id"),
        {"id": detection_id},
    ).scalar_one()
    review_id = UUID(str(accepted["id"]))
    guarded_statements = (
        (
            "UPDATE image_connected_components SET area_px=area_px+1 WHERE id=:id",
            component_id,
        ),
        ("DELETE FROM cell_detections WHERE id=:id", detection_id),
        ("UPDATE cell_crops SET padding_px=padding_px+1 WHERE id=:id", crop_id),
        ("DELETE FROM scientific_reviews WHERE id=:id", review_id),
        (
            "UPDATE cell_detection_runs SET detector_version='9.9.9' WHERE id=:id",
            detection_run_id,
        ),
        ("DELETE FROM cell_detection_runs WHERE id=:id", detection_run_id),
    )
    for statement, entity_id in guarded_statements:
        with pytest.raises(DBAPIError) as rejected:
            with context.connection.begin_nested():
                context.connection.execute(text(statement), {"id": entity_id})
        sqlstate = getattr(rejected.value.orig, "sqlstate", None) or getattr(
            rejected.value.orig, "pgcode", None
        )
        assert sqlstate == "55000"

    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM scientific_reviews
            WHERE entity_id=:id
            """
        ),
        {"id": detection_id},
    ).scalar_one() == 2


def test_integrity_failure_finishes_failed_without_partial_results(postgres_context):
    context = postgres_context
    fixture = context.create_analysis()
    modified = bytearray(fixture.source_bytes)
    modified[-1] ^= 1
    fixture.source_path.write_bytes(modified)

    with pytest.raises(CellAnalysisError) as rejected:
        context.service.execute_detection(
            str(fixture.analysis_run_id),
            context.actor,
            _request("/api/v1/cell-analysis/detection-runs"),
        )
    assert rejected.value.code == "CHECKSUM_MISMATCH"
    assert rejected.value.status_code == 409

    failed = context.connection.execute(
        text(
            """
            SELECT id,status,error_code,error_message,started_at,failed_at,
              component_count,detection_count,crop_count
            FROM cell_detection_runs WHERE analysis_run_id=:analysis_run_id
            """
        ),
        {"analysis_run_id": fixture.analysis_run_id},
    ).mappings().one()
    assert failed["status"] == "failed"
    assert failed["error_code"] == "CHECKSUM_MISMATCH"
    assert failed["error_message"] == (
        "La integridad de una imagen original no pudo verificarse."
    )
    assert failed["started_at"] is not None
    assert failed["failed_at"] is not None
    assert (
        failed["component_count"],
        failed["detection_count"],
        failed["crop_count"],
    ) == (0, 0, 0)
    assert context.connection.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM image_connected_components
                WHERE detection_run_id=:id),
              (SELECT count(*) FROM cell_detections
                WHERE detection_run_id=:id),
              (SELECT count(*) FROM cell_crops crop
                JOIN cell_detections cell ON cell.id=crop.cell_detection_id
                WHERE cell.detection_run_id=:id)
            """
        ),
        {"id": failed["id"]},
    ).one() == (0, 0, 0)
    failure_events = context.connection.execute(
        text(
            """
            SELECT event_type
            FROM cell_detection_events WHERE detection_run_id=:id
            """
        ),
        {"id": failed["id"]},
    ).scalars().all()
    assert set(failure_events) == {
        "cell_detection.run.created",
        "cell_detection.run.started",
        "cell_detection.run.failed",
    }
    assert len(failure_events) == 3
    failure_audit = context.connection.execute(
        text(
            """
            SELECT success,error_code,after_state
            FROM audit_events
            WHERE event_type='scientific.cell_detection.failed'
              AND resource_id=CAST(:id AS text)
            """
        ),
        {"id": failed["id"]},
    ).mappings().one()
    assert failure_audit["success"] is False
    assert failure_audit["error_code"] == "CHECKSUM_MISMATCH"
    assert failure_audit["after_state"]["status"] == "failed"
    crop_root = context.local_storage.root / "cell-crops"
    assert not crop_root.exists() or not list(crop_root.rglob("crop.png"))


def test_schema_uses_metadata_not_bytea_and_declares_expected_constraints(
    postgres_context,
):
    connection = postgres_context.connection
    inspector = inspect(connection)
    tables = {
        "cell_detection_runs",
        "image_connected_components",
        "cell_detections",
        "cell_crops",
        "cell_detection_events",
        "scientific_reviews",
    }
    assert tables <= set(inspector.get_table_names())
    bytea_columns = connection.execute(
        text(
            """
            SELECT table_name,column_name
            FROM information_schema.columns
            WHERE table_schema=current_schema()
              AND table_name IN (
                'cell_detection_runs','image_connected_components',
                'cell_detections','cell_crops','cell_detection_events',
                'scientific_reviews'
              )
              AND data_type='bytea'
            """
        )
    ).all()
    assert bytea_columns == []
    assert {"relative_storage_key", "sha256", "file_size_bytes"} <= {
        column["name"] for column in inspector.get_columns("cell_crops")
    }
    detection_constraints = {
        item["name"] for item in inspector.get_unique_constraints("cell_detections")
    }
    assert {
        "uq_cell_detections_component",
        "uq_cell_detections_run_index",
        "uq_cell_detections_cell_code",
    } <= detection_constraints
    review_checks = {
        item["name"] for item in inspector.get_check_constraints("scientific_reviews")
    }
    assert "ck_scientific_review_comment" in review_checks
