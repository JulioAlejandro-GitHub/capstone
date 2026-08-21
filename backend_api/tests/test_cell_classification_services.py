from __future__ import annotations

import hashlib
import importlib.util
import io
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import sys

import pytest
from PIL import Image

from app.services.cell_classification import (
    CellClassificationError,
    CellClassificationService,
    GradCAMUnsupportedError,
    build_automatic_summary,
    build_revised_summary,
    classification_decision,
    freeze_classification_inputs,
    iter_batches,
    normalize_binary_outputs,
)
from app.services.cell_explanation_storage import CellExplanationStorage
from app.services.local_storage import LocalStorage, StorageError
from app.services.productive_model import (
    EXPECTED_LABEL_MAPPING,
    ProductiveModelError,
    ProductiveModelResolver,
    ResolvedProductiveModel,
)


def _mapping():
    return dict(EXPECTED_LABEL_MAPPING)


def test_sigmoid_and_softmax_are_normalized_with_canonical_mapping():
    sigmoid = normalize_binary_outputs(
        [0.1, 0.9],
        batch_size=2,
        label_mapping=_mapping(),
        output_signature={"shape": [None, 1], "activation": "sigmoid"},
    )
    assert [row["probability_parasitized"] for row in sigmoid] == [0.1, 0.9]
    assert sigmoid[0]["probability_uninfected"] == pytest.approx(0.9)

    softmax = normalize_binary_outputs(
        [[0.8, 0.2], [0.05, 0.95]],
        batch_size=2,
        label_mapping=_mapping(),
        output_signature={"shape": [None, 2], "activation": "softmax"},
    )
    assert [row["probability_parasitized"] for row in softmax] == [0.2, 0.95]
    with pytest.raises(ValueError, match="no suma 1"):
        normalize_binary_outputs(
            [[0.2, 0.2]],
            batch_size=1,
            label_mapping=_mapping(),
            output_signature={"shape": [None, 2], "activation": "softmax"},
        )
    with pytest.raises(ValueError, match="ancho real"):
        normalize_binary_outputs(
            [[0.8], [0.2]],
            batch_size=2,
            label_mapping=_mapping(),
            output_signature={"shape": [None, 2], "activation": "softmax"},
        )
    with pytest.raises(ValueError):
        normalize_binary_outputs(
            [[0.8, 0.2]],
            batch_size=1,
            label_mapping=_mapping(),
            output_signature={"shape": [None, 1], "activation": "sigmoid"},
        )


def test_threshold_is_explicit_and_near_threshold_is_versionable():
    below = classification_decision(0.49, threshold=0.5, review_margin=0.02)
    above = classification_decision(0.50, threshold=0.5, review_margin=0.02)
    assert below["predicted_label"] == "uninfected"
    assert above["predicted_label"] == "parasitized"
    assert below["near_threshold"] is True
    assert above["decision_margin"] == 0.0
    with pytest.raises(TypeError):
        classification_decision(0.9, review_margin=0.05)  # type: ignore[call-arg]


def _detection(index: int, *, review: str = "unreviewed") -> dict:
    return {
        "cell_detection_id": uuid4(),
        "detection_run_id": uuid4(),
        "microscopy_image_id": uuid4(),
        "cell_index": index,
        "cell_code": f"CELL-{index:012X}",
        "image_sequence_number": index,
        "detector_key": "connected_components_v1",
        "detector_version": "1.0.0",
        "detector_algorithm_version": "opencv-1",
        "crop_id": uuid4(),
        "crop_storage_key": f"cell-crops/{uuid4()}/crop.png",
        "crop_sha256": "a" * 64,
        "crop_file_size_bytes": 100,
        "crop_width_px": 20,
        "crop_height_px": 20,
        "detection_review_status": review,
    }


def test_manifest_is_deterministic_and_includes_review_and_physical_exclusions():
    accepted = _detection(2)
    rejected = _detection(1, review="rejected")
    corrupt = _detection(3)
    corrupt["_exclusion_reason"] = "CROP_CHECKSUM_MISMATCH"
    first, first_sha = freeze_classification_inputs([accepted, corrupt, rejected])
    second, second_sha = freeze_classification_inputs([rejected, accepted, corrupt])
    assert first_sha == second_sha
    assert [row["input_order"] for row in first] == [1, 2, 3]
    reasons = {row["exclusion_reason"] for row in first if not row["eligible"]}
    assert reasons == {
        "DETECTION_REJECTED_BY_REVIEW",
        "CROP_CHECKSUM_MISMATCH",
    }
    assert sum(row["eligible"] for row in second) == 1


@pytest.mark.parametrize(
    ("count", "batch_size", "expected"),
    [(1, 32, [1]), (50, 32, [32, 18]), (500, 32, [32] * 15 + [20])],
)
def test_batches_cover_each_input_exactly_once(count, batch_size, expected):
    batches = iter_batches(list(range(count)), batch_size)
    assert [len(batch) for batch in batches] == expected
    assert [item for batch in batches for item in batch] == list(range(count))


def _summary_inputs(count: int) -> list[dict]:
    image_id = uuid4()
    return [
        {
            "id": uuid4(),
            "eligible": True,
            "microscopy_image_id": image_id,
            "image_sequence_number": 1,
        }
        for _ in range(count)
    ]


def test_automatic_and_revised_summaries_keep_distinct_semantics():
    inputs = _summary_inputs(2)
    predictions = [
        {
            "classification_input_id": inputs[0]["id"],
            "prediction_status": "completed",
            "predicted_label": "parasitized",
            "probability_parasitized": 0.8,
            "near_threshold": False,
        },
        {
            "classification_input_id": inputs[1]["id"],
            "prediction_status": "completed",
            "predicted_label": "uninfected",
            "probability_parasitized": 0.1,
            "near_threshold": False,
        },
    ]
    summary = build_automatic_summary(
        classification_run_id=uuid4(),
        analysis_run_id=uuid4(),
        detection_run_id=uuid4(),
        frozen_inputs=inputs,
        predictions=predictions,
    )
    assert summary["outcome"] == "suspicious_cells_detected"
    assert summary["parasitized_candidate_fraction"] == 0.5
    reviewed = build_revised_summary(
        summary,
        [
            {
                "automatic_label": "parasitized",
                "classification_review_status": "corrected",
                "reviewed_label": "uninfected",
                "effective_reviewed_label": "uninfected",
                "detection_review_status": "accepted",
            },
            {
                "automatic_label": "uninfected",
                "classification_review_status": "confirmed",
                "effective_reviewed_label": "uninfected",
                "detection_review_status": "accepted",
            },
        ],
    )
    assert reviewed["outcome"] == "no_suspicious_cells_detected"
    assert reviewed["automatic_summary_unchanged"] is True
    assert summary["outcome"] == "suspicious_cells_detected"


def test_revised_summary_recomputes_failed_near_and_rejected_population():
    automatic = {
        "failed_prediction_count": 8,
        "near_threshold_count": 9,
    }
    reviewed = build_revised_summary(
        automatic,
        [
            {
                "prediction_status": "completed",
                "automatic_label": "uninfected",
                "near_threshold": False,
                "classification_review_status": "confirmed",
                # An invalid legacy confirmed payload cannot change projection.
                "reviewed_label": "parasitized",
                "detection_review_status": "accepted",
            },
            {
                "prediction_status": "failed",
                "automatic_label": None,
                "near_threshold": False,
                "detection_review_status": "accepted",
            },
            {
                "prediction_status": "completed",
                "automatic_label": "parasitized",
                "near_threshold": True,
                "detection_review_status": "rejected",
            },
        ],
    )
    assert reviewed["eligible_cell_count"] == 2
    assert reviewed["classified_cell_count"] == 1
    assert reviewed["failed_prediction_count"] == 1
    assert reviewed["near_threshold_count"] == 0
    assert reviewed["parasitized_candidate_count"] == 0
    assert reviewed["outcome"] == "inconclusive"


def _candidate(model_path: Path, *, threshold_source: str = "fixed_cli") -> dict:
    payload = model_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    train_id, evaluation_id = uuid4(), uuid4()
    return {
        "deployment_id": str(uuid4()),
        "deployment_name": "malaria-stage2-classifier",
        "environment": "stage2",
        "alias": "default",
        "production_status": "active",
        "model_version_id": str(uuid4()),
        "checkpoint_artifact_id": str(uuid4()),
        "deployment_sha256": digest,
        "deployment_size_bytes": len(payload),
        "threshold_calibration_id": str(uuid4()),
        "threshold_value": 0.5,
        "threshold_profile_snapshot": {
            "value": 0.5,
            "source": threshold_source,
        },
        "preprocessing_profile_snapshot": {"mode": "rescale_0_1"},
        "label_mapping_snapshot": _mapping(),
        "positive_label": "parasitized",
        "score_name": "probability_parasitized",
        "deployment_metadata": {
            "production_scope": "stage2_experimental",
            "stage2": {"eligible": True},
            "technical_smoke_test": {"status": "PASS"},
            "technical_contract": {
                "architecture": "custom_cnn",
                "input_signature": {"shape": [None, 20, 20, 3]},
                "output_signature": {
                    "shape": [None, 1],
                    "activation": "sigmoid",
                },
            }
        },
        "model_name": "custom_cnn",
        "version_number": 1,
        "model_version_status": "candidate",
        "lineage_status": "resolved",
        "source_training_run_id": str(train_id),
        "model_sha256": digest,
        "model_size_bytes": len(payload),
        "framework": "keras",
        "framework_version": "3",
        "input_signature": {"shape": [None, 20, 20, 3]},
        "output_signature": {"shape": [None, 1], "activation": "sigmoid"},
        "model_preprocessing": {"mode": "rescale_0_1"},
        "model_mapping": _mapping(),
        "model_metadata": {"architecture": "custom_cnn"},
        "artifact_path": str(model_path),
        "artifact_checksum": digest,
        "artifact_run_id": str(train_id),
        "artifact_size_bytes": len(payload),
        "artifact_status": "available",
        "publication_id": str(uuid4()),
        "source_evaluation_run_id": str(evaluation_id),
        "publication_status": "active",
        "publication_is_active": True,
        "published_at": datetime.now(UTC),
        "publication_metadata": {},
        "training_status": "completed",
        "training_type": "training",
        "evaluation_status": "completed",
        "evaluation_type": "evaluation",
        "evaluation_lineage_valid": True,
        "calibration_threshold": 0.5,
        "calibration_threshold_source": threshold_source,
        "calibration_threshold_policy": "explicit",
        "calibration_split": "val",
        "calibration_status": "recorded",
        "calibration_score_name": "probability_parasitized",
        "calibration_positive_label": "parasitized",
        "calibration_metadata": {},
    }


def test_productive_resolver_rejects_absent_or_ambiguous_and_accepts_published_half(
    tmp_path: Path,
):
    ml_root = tmp_path / "ml"
    model_path = ml_root / "outputs" / "run" / "model.keras"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"controlled-model")
    candidate = _candidate(model_path)

    resolved = ProductiveModelResolver(
        candidate_loader=lambda: [candidate],
        ml_project_root=ml_root,
    ).resolve()
    assert resolved.threshold == 0.5
    assert resolved.threshold_source == "fixed_cli"
    assert resolved.output_signature["activation"] == "sigmoid"
    assert "checkpoint_path" not in resolved.snapshot(
        inference_version="test", review_margin=0.05, batch_size=32
    )
    xai_policy = resolved.snapshot(
        inference_version="test", review_margin=0.05, batch_size=32
    )["explainability_policy"]
    assert xai_policy == {
        "version": "cell-gradcam-manual-v1",
        "method": "gradcam",
        "scope": "single_cell_on_demand",
        "automatic_generation": False,
        "manual_retry_required": True,
        "bulk_generation": False,
        "priority_hints": ["parasitized", "near_threshold"],
    }

    with pytest.raises(ProductiveModelError) as missing:
        ProductiveModelResolver(
            candidate_loader=lambda: [], ml_project_root=ml_root
        ).resolve()
    assert missing.value.code == "PRODUCTIVE_MODEL_NOT_FOUND"
    assert missing.value.detail == "No existe un modelo Productivo Etapa 2."
    with pytest.raises(ProductiveModelError) as ambiguous:
        ProductiveModelResolver(
            candidate_loader=lambda: [candidate, candidate],
            ml_project_root=ml_root,
        ).resolve()
    assert ambiguous.value.code == "PRODUCTIVE_MODEL_NOT_UNIQUE"
    assert "Existe más de un modelo Productivo Etapa 2" in ambiguous.value.detail
    inconsistent = {**candidate, "calibration_threshold_source": "other"}
    with pytest.raises(ProductiveModelError) as error:
        ProductiveModelResolver(
            candidate_loader=lambda: [inconsistent],
            ml_project_root=ml_root,
        ).resolve()
    assert error.value.code == "PRODUCTIVE_THRESHOLD_INVALID"


def test_productive_resolver_accepts_canonical_tensorflow_keras_framework(tmp_path: Path):
    ml_root = tmp_path / "ml"
    model_path = ml_root / "outputs" / "run" / "model.keras"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"controlled-model")
    candidate = {**_candidate(model_path), "framework": "tensorflow.keras"}

    resolved = ProductiveModelResolver(
        candidate_loader=lambda: [candidate],
        ml_project_root=ml_root,
    ).resolve_current_stage2_productive_model()

    assert resolved.framework == "tensorflow.keras"


def test_productive_resolver_query_starts_from_active_publication_and_uses_real_fk():
    captured: dict[str, object] = {}

    class EmptyMappings:
        @staticmethod
        def all():
            return []

    class EmptyResult:
        @staticmethod
        def mappings():
            return EmptyMappings()

    class RecordingConnection:
        @staticmethod
        def execute(statement, params):
            captured["sql"] = str(statement)
            captured["params"] = params
            return EmptyResult()

    resolver = ProductiveModelResolver()
    assert resolver._fetch_candidates(connection=RecordingConnection()) == []

    sql = " ".join(str(captured["sql"]).split()).lower()
    assert "from stage2_model_publications publication" in sql
    assert (
        "left join deployed_model_versions d on "
        "d.model_version_id=publication.model_version_id and "
        "d.checkpoint_artifact_id=publication.checkpoint_artifact_id"
    ) in sql
    assert "publication.is_active=true" in sql
    assert "d.is_active" not in sql
    assert captured["params"] == {
        "historical": False,
        "environment": "stage2",
        "alias": "default",
        "production_scope": "stage2_experimental",
        "deployment_id": None,
        "model_version_id": None,
        "artifact_id": None,
        "publication_id": None,
        "checkpoint_sha256": None,
    }


def test_active_publication_is_not_reinterpreted_by_inference_lifecycle_checks(
    tmp_path: Path,
):
    ml_root = tmp_path / "ml"
    model_path = ml_root / "outputs" / "run" / "model.keras"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"controlled-model")
    candidate = _candidate(model_path)
    candidate.update(
        training_status="failed",
        evaluation_status="failed",
        evaluation_lineage_valid=False,
        model_version_status="retired",
        lineage_status="unresolved",
        deployment_metadata={"technical_contract": candidate["deployment_metadata"]["technical_contract"]},
    )

    resolved = ProductiveModelResolver(
        candidate_loader=lambda: [candidate],
        ml_project_root=ml_root,
    ).resolve_current_stage2_productive_model()

    assert resolved.publication_id == candidate["publication_id"]


def test_historical_snapshot_resolves_exact_identity_without_current_default_fallback(
    tmp_path: Path,
):
    ml_root = tmp_path / "ml"
    historical_path = ml_root / "outputs" / "old" / "model.keras"
    current_path = ml_root / "outputs" / "new" / "model.keras"
    historical_path.parent.mkdir(parents=True)
    current_path.parent.mkdir(parents=True)
    historical_path.write_bytes(b"historical-model")
    current_path.write_bytes(b"current-model")
    historical = _candidate(historical_path)
    current = _candidate(current_path)
    historical.update(
        production_status="inactive",
        publication_status="inactive",
        publication_is_active=False,
        model_version_status="retired",
    )
    historical_resolver = ProductiveModelResolver(
        snapshot_loader=lambda _snapshot: [historical],
        candidate_loader=lambda: [current],
        ml_project_root=ml_root,
    )
    frozen = ProductiveModelResolver(
        candidate_loader=lambda: [{**historical, "production_status": "active",
                                   "publication_status": "active",
                                   "publication_is_active": True,
                                   "model_version_status": "candidate"}],
        ml_project_root=ml_root,
    ).resolve().snapshot(
        inference_version="test",
        review_margin=0.05,
        batch_size=32,
    )
    resolved = historical_resolver.resolve_snapshot(frozen)
    assert resolved.deployment_id == historical["deployment_id"]
    assert resolved.deployment_id != current["deployment_id"]
    malformed = {**frozen, "checkpoint_size_bytes": "not-a-number"}
    with pytest.raises(ProductiveModelError) as error:
        historical_resolver.resolve_snapshot(malformed)
    assert error.value.code == "FROZEN_MODEL_SNAPSHOT_INVALID"


def test_productive_metadata_conversion_errors_are_typed(tmp_path: Path):
    ml_root = tmp_path / "ml"
    model_path = ml_root / "outputs" / "run" / "model.keras"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"controlled-model")
    invalid = {**_candidate(model_path), "deployment_size_bytes": "bad"}
    with pytest.raises(ProductiveModelError) as error:
        ProductiveModelResolver(
            candidate_loader=lambda: [invalid],
            ml_project_root=ml_root,
        ).resolve()
    assert error.value.code == "MODEL_SIZE_MISMATCH"


def test_model_loader_uses_private_verified_copy_not_reopened_checkpoint(
    tmp_path: Path,
):
    ml_root = tmp_path / "ml"
    checkpoint = ml_root / "outputs" / "run" / "model.keras"
    checkpoint.parent.mkdir(parents=True)
    original = b"verified-checkpoint"
    checkpoint.write_bytes(original)
    candidate = _candidate(checkpoint)
    observed: dict[str, object] = {}

    def loader(private_path: Path):
        observed["path"] = private_path
        assert private_path != checkpoint
        assert private_path.suffix == checkpoint.suffix
        checkpoint.write_bytes(b"mutated-original")
        observed["payload"] = private_path.read_bytes()
        return observed["payload"]

    resolver = ProductiveModelResolver(
        candidate_loader=lambda: [candidate],
        model_loader=loader,
        ml_project_root=ml_root,
    )
    resolved = resolver.resolve()
    assert resolver.load(resolved) == original
    assert observed["payload"] == original
    assert not Path(observed["path"]).exists()
    assert checkpoint.read_bytes() == b"mutated-original"

    checkpoint.write_bytes(original)
    second = ProductiveModelResolver(
        candidate_loader=lambda: [candidate],
        model_loader=lambda _path: object(),
        ml_project_root=ml_root,
    )
    frozen = second.resolve()
    checkpoint.write_bytes(b"tampered-before-load")
    with pytest.raises(ProductiveModelError) as error:
        second.load(frozen)
    assert error.value.code in {"MODEL_SIZE_MISMATCH", "MODEL_CHECKSUM_MISMATCH"}


def test_loaded_model_shapes_must_match_frozen_contract(tmp_path: Path):
    resolved = _resolved(tmp_path)
    CellClassificationService._validate_loaded_model_contract(object(), resolved)
    CellClassificationService._validate_loaded_model_contract(
        SimpleNamespace(
            input_shape=(None, 20, 20, 3),
            output_shape=(None, 1),
        ),
        resolved,
    )
    with pytest.raises(CellClassificationError) as error:
        CellClassificationService._validate_loaded_model_contract(
            SimpleNamespace(
                input_shape=(None, 32, 32, 3),
                output_shape=(None, 1),
            ),
            resolved,
        )
    assert error.value.code == "LOADED_MODEL_INPUT_SIGNATURE_MISMATCH"
    with pytest.raises(CellClassificationError) as error:
        CellClassificationService._validate_loaded_model_contract(
            SimpleNamespace(
                input_shape=(None, 20, 20, 3),
                output_shape=(None, 2),
            ),
            resolved,
        )
    assert error.value.code == "LOADED_MODEL_OUTPUT_SIGNATURE_MISMATCH"


def _storage(tmp_path: Path) -> CellExplanationStorage:
    settings = SimpleNamespace(
        storage_provider="local",
        storage_root=tmp_path / "storage",
        max_upload_size_bytes=1_000_000,
        upload_chunk_size_bytes=1024,
    )
    return CellExplanationStorage(LocalStorage(settings))


def _png(mode: str, size=(12, 10)) -> bytes:
    output = io.BytesIO()
    Image.new(mode, size, 127 if mode == "L" else (1, 2, 3)).save(
        output, format="PNG"
    )
    return output.getvalue()


def test_explanation_storage_stages_promotes_hashes_and_never_touches_crop(
    tmp_path: Path,
):
    storage = _storage(tmp_path)
    ids = [uuid4() for _ in range(4)]
    crop = tmp_path / "storage" / "cell-crops" / "crop.png"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(_png("L"))
    before = crop.read_bytes()
    staged = storage.stage(
        analysis_run_id=ids[0],
        classification_run_id=ids[1],
        cell_detection_id=ids[2],
        explanation_id=ids[3],
        heatmap_png=_png("L"),
        overlay_png=_png("RGB"),
        expected_width_px=12,
        expected_height_px=10,
    )
    heatmap, overlay = storage.promote(staged)
    assert heatmap.read_bytes() == _png("L")
    assert overlay.read_bytes() == _png("RGB")
    assert not staged.heatmap.path.parent.exists()
    assert crop.read_bytes() == before
    assert staged.heatmap.sha256 == hashlib.sha256(_png("L")).hexdigest()
    with pytest.raises(StorageError, match="no se sobrescribe"):
        storage.promote(
            storage.stage(
                analysis_run_id=ids[0],
                classification_run_id=ids[1],
                cell_detection_id=ids[2],
                explanation_id=uuid4(),
                heatmap_png=_png("L"),
                overlay_png=_png("RGB"),
                expected_width_px=12,
                expected_height_px=10,
            )
        )


class _FakeEngine:
    @contextmanager
    def begin(self):
        yield object()

    @contextmanager
    def connect(self):
        yield object()


class _EligibilityRepository:
    def __init__(self):
        self.run_id = uuid4()

    def eligible_detection_runs(self, **_kwargs):
        return {
            "items": [{"id": self.run_id, "detection_run_code": "DET-00000001"}],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }

    def detection_run_input(self, _run_id):
        detection = _detection(1)
        detection["detection_run_id"] = self.run_id
        detection["crop_storage_key"] = None
        return {
            "id": self.run_id,
            "status": "completed",
            "ready_for_analysis": True,
            "detector_key": "connected_components_v1",
            "detector_version": "1.0.0",
            "algorithm_version": "opencv-1",
            "detection_count": 1,
            "crop_count": 1,
            "detections": [detection],
        }


def test_eligible_runs_explain_productive_model_block_without_exposing_paths():
    repository = _EligibilityRepository()

    def unavailable():
        raise ProductiveModelError("PRODUCTIVE_MODEL_NOT_UNIQUE")

    service = CellClassificationService(
        engine=_FakeEngine(),
        repository_factory=lambda _connection: repository,
        model_resolver=SimpleNamespace(resolve=unavailable),
    )
    result = service.eligible_detection_runs(limit=50, offset=0)
    item = result["items"][0]
    assert item["eligible"] is False
    assert item["reason"] == "PRODUCTIVE_MODEL_NOT_UNIQUE"
    assert item["productive_model"] is None
    assert "No existe un modelo productivo válido" in item["message"]
    assert all("path" not in key for key in item)


@pytest.mark.parametrize(
    ("ready", "status", "detection_count", "expected"),
    [
        (False, "completed", 1, "ANALYSIS_NOT_READY"),
        (True, "processing", 1, "DETECTION_RUN_NOT_COMPLETED"),
        (True, "completed", 0, "NO_DETECTIONS"),
    ],
)
def test_targeted_eligibility_returns_block_reason_instead_of_empty(
    tmp_path: Path,
    ready: bool,
    status: str,
    detection_count: int,
    expected: str,
):
    run_id = uuid4()
    detections = []
    if detection_count:
        detection = _detection(1)
        detection["detection_run_id"] = run_id
        detections = [detection]

    class Repository:
        def eligible_detection_runs(self, **_kwargs):
            return {
                "items": [{"id": run_id, "detection_run_code": "DET-00000001"}],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }

        def detection_run_input(self, _run_id):
            return {
                "id": run_id,
                "status": status,
                "ready_for_analysis": ready,
                "detector_key": "connected_components_v1",
                "detector_version": "1.0.0",
                "algorithm_version": "opencv-1",
                "detection_count": detection_count,
                "crop_count": detection_count,
                "detections": detections,
            }

    service = CellClassificationService(
        engine=_FakeEngine(),
        repository_factory=lambda _connection: Repository(),
        model_resolver=SimpleNamespace(resolve=lambda: _resolved(tmp_path)),
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]
    result = service.eligible_detection_runs(
        detection_run_id=str(run_id),
        limit=50,
        offset=0,
    )
    assert result["total"] == 1
    assert result["items"][0]["eligible"] is False
    assert result["items"][0]["reason_code"] == expected


class _ExecutionRepository:
    def __init__(self, detections):
        self.detection_run_id = uuid4()
        self.analysis_run_id = uuid4()
        self.detections = [
            {
                **row,
                "detection_run_id": self.detection_run_id,
            }
            for row in detections
        ]
        self.run = None
        self.inputs = []
        self.predictions = []
        self.summary = None
        self.event_rows = []

    def detection_run_input(self, _run_id, *, for_update=False):
        return {
            "id": self.detection_run_id,
            "analysis_run_id": self.analysis_run_id,
            "status": "completed",
            "ready_for_analysis": True,
            "detector_key": "connected_components_v1",
            "detector_version": "1.0.0",
            "algorithm_version": "opencv-1",
            "detection_count": len(self.detections),
            "crop_count": sum(bool(row.get("crop_id")) for row in self.detections),
            "detections": self.detections,
        }

    def find_equivalent(self, **_kwargs):
        return None

    def find_failed_equivalent(self, **_kwargs):
        return None

    def create_run(self, **values):
        self.run = {
            **values,
            "id": values["run_id"],
            "status": "created",
            "processed_count": 0,
            "parasitized_count": 0,
            "uninfected_count": 0,
            "near_threshold_count": 0,
            "failed_count": 0,
        }
        return self.run

    def insert_inputs(self, _run_id, items):
        self.inputs = list(items)
        return self.inputs

    def add_event(self, **values):
        self.event_rows.append(values)
        return values

    def start_run(self, _run_id):
        self.run["status"] = "processing"
        return self.run

    def insert_prediction(self, values):
        self.predictions.append(dict(values))
        return values

    def update_counts(self, _run_id, **counts):
        self.run.update(counts)
        return self.run

    def complete_run(self, _run_id, *, status, **counts):
        self.run.update(counts)
        self.run["status"] = status
        return self.run

    def fail_run(self, _run_id, *, error_code, error_message):
        self.run.update(
            status="failed",
            error_code=error_code,
            error_message=error_message,
        )
        return self.run

    def create_summary(self, values):
        self.summary = dict(values)
        return self.summary

    def get_run(self, _run_id):
        return self.run

    def events(self, _run_id):
        return self.event_rows


class _CountingResolver:
    def __init__(self, resolved):
        self.resolved = resolved
        self.load_count = 0

    def resolve(self):
        return self.resolved

    def revalidate(self, _resolved, *, connection):
        return self.resolved

    def resolve_snapshot(self, _snapshot):
        return self.resolved

    def load(self, _resolved):
        self.load_count += 1
        return object()


class _MissingTensorFlowResolver(_CountingResolver):
    def load(self, _resolved):
        self.load_count += 1
        raise ModuleNotFoundError("No module named 'tensorflow'")


def test_missing_tensorflow_during_model_loading_is_terminal_and_structured(
    tmp_path: Path,
    caplog,
):
    repository = _ExecutionRepository([_detection(1)])
    resolver = _MissingTensorFlowResolver(_resolved(tmp_path))
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(
            cell_classification_batch_size=2,
            cell_classification_review_margin=0.01,
        ),
        repository_factory=lambda _connection: repository,
        model_resolver=resolver,
        auditor=lambda **_kwargs: None,
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]

    with pytest.raises(CellClassificationError) as error:
        service.execute_classification(
            str(repository.detection_run_id),
            SimpleNamespace(user_id=str(uuid4())),
            SimpleNamespace(),
        )

    assert error.value.status_code == 500
    assert error.value.code == "CELL_CLASSIFICATION_EXECUTION_FAILED"
    assert error.value.detail == "La clasificación celular no pudo completarse."
    assert error.value.classification_run_id == str(repository.run["id"])
    assert error.value.stage == "model_loading"
    assert error.value.retryable is True
    assert repository.run["status"] == "failed"
    assert repository.run["error_code"] == "CELL_CLASSIFICATION_EXECUTION_FAILED"
    assert any(
        event["event_type"] == "cell_classification.run.failed"
        for event in repository.event_rows
    )
    assert "No module named 'tensorflow'" in caplog.text


def test_execution_loads_once_batches_and_persists_thresholded_partial_records(
    tmp_path: Path,
):
    detections = [_detection(index) for index in (1, 2, 3)]
    repository = _ExecutionRepository(detections)
    resolved = _resolved(tmp_path)
    resolver = _CountingResolver(resolved)
    scores = {1: 0.1, 2: 0.5, 3: 0.9}
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(
            cell_classification_batch_size=2,
            cell_classification_review_margin=0.01,
        ),
        repository_factory=lambda _connection: repository,
        model_resolver=resolver,
        preprocessor=lambda item, _resolved: item["cell_index"],
        predictor=lambda _model, values: [scores[int(value)] for value in values],
        auditor=lambda **_kwargs: None,
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]
    result = service.execute_classification(
        str(repository.detection_run_id),
        SimpleNamespace(user_id=str(uuid4())),
        SimpleNamespace(),
    )
    assert resolver.load_count == 1
    assert result["status"] == "completed"
    assert result["processed_count"] == 3
    assert result["parasitized_count"] == 2
    assert result["uninfected_count"] == 1
    assert len(repository.predictions) == 3
    assert all(
        prediction["threshold_used"] == 0.5
        and prediction["threshold_source"] == "fixed_cli"
        for prediction in repository.predictions
    )
    assert sum(
        event["event_type"] == "cell_classification.batch.started"
        for event in repository.event_rows
    ) == 2


@pytest.mark.parametrize(
    ("ready", "reviews", "expected_code"),
    [
        (False, ["unreviewed"], "ANALYSIS_NOT_READY"),
        (True, ["rejected"], "NO_ELIGIBLE_CROPS"),
    ],
)
def test_post_rejects_not_ready_or_zero_eligible_before_create(
    tmp_path: Path,
    ready: bool,
    reviews: list[str],
    expected_code: str,
):
    detections = [
        _detection(index, review=review)
        for index, review in enumerate(reviews, 1)
    ]
    repository = _ExecutionRepository(detections)
    original = repository.detection_run_input

    def detection_run_input(run_id, *, for_update=False):
        row = original(run_id, for_update=for_update)
        row["ready_for_analysis"] = ready
        return row

    repository.detection_run_input = detection_run_input
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(
            cell_classification_batch_size=2,
            cell_classification_review_margin=0.01,
        ),
        repository_factory=lambda _connection: repository,
        model_resolver=_CountingResolver(_resolved(tmp_path)),
        auditor=lambda **_kwargs: None,
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]
    with pytest.raises(CellClassificationError) as error:
        service.execute_classification(
            str(repository.detection_run_id),
            SimpleNamespace(user_id=str(uuid4())),
            SimpleNamespace(),
        )
    assert error.value.status_code == 409
    assert error.value.code == expected_code
    assert repository.run is None


class _StaleExecutionRepository(_ExecutionRepository):
    def __init__(self, detections):
        super().__init__(detections)
        self.original_stale_id = uuid4()
        self.run = {
            "id": self.original_stale_id,
            "status": "processing",
            "updated_at": datetime.now(UTC) - timedelta(hours=2),
        }
        self.create_count = 0
        self.retry_of = None

    def find_equivalent(self, **_kwargs):
        return self.run if self.run["status"] in {"created", "processing"} else None

    def find_failed_equivalent(self, **_kwargs):
        return self.run if self.run["status"] == "failed" else None

    def create_run(self, **values):
        self.create_count += 1
        self.retry_of = values.get("retry_of_run_id")
        return super().create_run(**values)


def test_stale_active_run_is_terminalized_without_retrying_same_post(tmp_path: Path):
    repository = _StaleExecutionRepository([_detection(1)])
    resolver = _CountingResolver(_resolved(tmp_path))
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(
            cell_classification_batch_size=2,
            cell_classification_review_margin=0.01,
        ),
        repository_factory=lambda _connection: repository,
        model_resolver=resolver,
        preprocessor=lambda item, _resolved: item["cell_index"],
        predictor=lambda _model, _values: [0.9],
        auditor=lambda **_kwargs: None,
        active_run_stale_after_seconds=60,
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]
    with pytest.raises(CellClassificationError) as error:
        service.execute_classification(
            str(repository.detection_run_id),
            SimpleNamespace(user_id=str(uuid4())),
            SimpleNamespace(),
        )
    assert error.value.status_code == 409
    assert error.value.code == "STALE_ACTIVE_RUN_TERMINATED"
    assert repository.run["status"] == "failed"
    assert repository.create_count == 0

    result = service.execute_classification(
        str(repository.detection_run_id),
        SimpleNamespace(user_id=str(uuid4())),
        SimpleNamespace(),
    )
    assert result["status"] == "completed"
    assert repository.create_count == 1
    assert repository.retry_of == repository.original_stale_id


class _StartFailureRepository(_ExecutionRepository):
    def start_run(self, _run_id):
        return None


def test_failure_after_create_terminalizes_created_run(tmp_path: Path):
    repository = _StartFailureRepository([_detection(1)])
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(
            cell_classification_batch_size=2,
            cell_classification_review_margin=0.01,
        ),
        repository_factory=lambda _connection: repository,
        model_resolver=_CountingResolver(_resolved(tmp_path)),
        auditor=lambda **_kwargs: None,
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]
    with pytest.raises(CellClassificationError) as error:
        service.execute_classification(
            str(repository.detection_run_id),
            SimpleNamespace(user_id=str(uuid4())),
            SimpleNamespace(),
        )
    assert error.value.code == "RUN_START_STATE_CONFLICT"
    assert repository.run["status"] == "failed"


def test_warning_run_keeps_completed_event_and_warning_event(tmp_path: Path):
    repository = _ExecutionRepository([_detection(1), _detection(2)])
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(
            cell_classification_batch_size=2,
            cell_classification_review_margin=0.01,
        ),
        repository_factory=lambda _connection: repository,
        model_resolver=_CountingResolver(_resolved(tmp_path)),
        preprocessor=lambda item, _resolved: (
            (_ for _ in ()).throw(ValueError("bad crop"))
            if item["cell_index"] == 2
            else item["cell_index"]
        ),
        predictor=lambda _model, _values: [0.9],
        auditor=lambda **_kwargs: None,
    )
    service._preflight_detections = lambda rows: [dict(row) for row in rows]
    result = service.execute_classification(
        str(repository.detection_run_id),
        SimpleNamespace(user_id=str(uuid4())),
        SimpleNamespace(),
    )
    assert result["status"] == "completed_with_warnings"
    event_types = {event["event_type"] for event in repository.event_rows}
    assert "cell_classification.run.completed" in event_types
    assert "cell_classification.run.completed_with_warnings" in event_types


class _ExplanationRepository:
    def __init__(self, prediction, explanation):
        self.prediction = prediction
        self.explanation = explanation
        self.fail_count = 0

    def prediction_for_explanation(self, *_args, **_kwargs):
        return self.prediction

    def find_explanation(self, *_args, **_kwargs):
        return self.explanation

    def create_explanation(self, **values):
        self.explanation = {
            "id": values["explanation_id"],
            "cell_prediction_id": values["cell_prediction_id"],
            "status": "not_requested",
        }
        return self.explanation

    def start_explanation(self, explanation_id, *, retry):
        self.explanation = {**self.explanation, "id": explanation_id, "status": "pending"}
        return self.explanation

    def fail_explanation(self, explanation_id, *, error_code, error_message, unsupported):
        self.fail_count += 1
        self.explanation = {
            **self.explanation,
            "id": explanation_id,
            "status": "unsupported" if unsupported else "failed",
            "error_code": error_code,
            "error_message": error_message,
        }
        return self.explanation

    def add_event(self, **_values):
        return {"id": uuid4()}


def _resolved(tmp_path: Path) -> ResolvedProductiveModel:
    model = tmp_path / "model.keras"
    model.write_bytes(b"x")
    return ResolvedProductiveModel(
        deployment_id=str(uuid4()),
        deployment_name="malaria-stage2-classifier",
        publication_id=str(uuid4()),
        model_version_id=str(uuid4()),
        model_name="custom_cnn",
        model_version="1",
        source_training_run_id=str(uuid4()),
        source_evaluation_run_id=str(uuid4()),
        checkpoint_artifact_id=str(uuid4()),
        checkpoint_path=model,
        checkpoint_sha256=hashlib.sha256(b"x").hexdigest(),
        checkpoint_size_bytes=1,
        framework="keras",
        framework_version="3",
        architecture="custom_cnn",
        input_width=20,
        input_height=20,
        input_channels=3,
        input_signature={"shape": [None, 20, 20, 3]},
        output_signature={"shape": [None, 1], "activation": "sigmoid"},
        preprocessing={"mode": "rescale_0_1"},
        label_mapping=_mapping(),
        positive_label="parasitized",
        positive_class_index=1,
        threshold=0.5,
        threshold_source="fixed_cli",
        calibration_metadata={},
        published_at=datetime.now(UTC),
        production_status="active",
        deployment_metadata={},
    )


def test_manual_gradcam_unsupported_is_terminal_without_changing_prediction(
    tmp_path: Path,
):
    resolved = _resolved(tmp_path)
    prediction_id = uuid4()
    prediction = {
        "id": prediction_id,
        "prediction_status": "completed",
        "predicted_class_index": 1,
        "classification_run_id": uuid4(),
        "cell_detection_id": uuid4(),
        "analysis_run_id": uuid4(),
        "crop_storage_key": "cell-crops/fake.png",
        "crop_sha256": "a" * 64,
        "crop_file_size_bytes": 10,
        "crop_width_px": 20,
        "crop_height_px": 20,
        "preprocessing_snapshot": {"mode": "rescale_0_1"},
        "model_snapshot": resolved.snapshot(
            inference_version="test",
            review_margin=0.05,
            batch_size=32,
        ),
    }
    repository = _ExplanationRepository(prediction, None)
    resolver = SimpleNamespace(
        resolve_snapshot=lambda _snapshot: resolved,
        load=lambda _resolved: object(),
    )
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(),
        repository_factory=lambda _connection: repository,
        model_resolver=resolver,
        preprocessor=lambda _item, _resolved: [[[0.0, 0.0, 0.0]]],
        gradcam=lambda **_kwargs: (_ for _ in ()).throw(
            GradCAMUnsupportedError("no conv layer")
        ),
        auditor=lambda **_kwargs: None,
    )
    result = service.generate_explanation(
        str(prediction_id),
        False,
        SimpleNamespace(user_id=str(uuid4())),
        SimpleNamespace(),
    )
    assert result["status"] == "unsupported"
    assert result["error_code"] == "GRADCAM_UNSUPPORTED"
    assert prediction["prediction_status"] == "completed"


def test_plain_gradcam_value_error_is_failed_not_unsupported(tmp_path: Path):
    resolved = _resolved(tmp_path)
    prediction_id = uuid4()
    prediction = {
        "id": prediction_id,
        "prediction_status": "completed",
        "predicted_class_index": 1,
        "classification_run_id": uuid4(),
        "cell_detection_id": uuid4(),
        "analysis_run_id": uuid4(),
        "crop_storage_key": "cell-crops/fake.png",
        "crop_sha256": "a" * 64,
        "crop_file_size_bytes": 10,
        "crop_width_px": 20,
        "crop_height_px": 20,
        "preprocessing_snapshot": {"mode": "rescale_0_1"},
        "model_snapshot": resolved.snapshot(
            inference_version="test",
            review_margin=0.05,
            batch_size=32,
        ),
    }
    repository = _ExplanationRepository(prediction, None)
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(),
        repository_factory=lambda _connection: repository,
        model_resolver=SimpleNamespace(
            resolve_snapshot=lambda _snapshot: resolved,
            load=lambda _resolved: object(),
        ),
        preprocessor=lambda _item, _resolved: [[[0.0, 0.0, 0.0]]],
        gradcam=lambda **_kwargs: (_ for _ in ()).throw(
            ValueError("operational value error")
        ),
        auditor=lambda **_kwargs: None,
    )
    result = service.generate_explanation(
        str(prediction_id),
        False,
        SimpleNamespace(user_id=str(uuid4())),
        SimpleNamespace(),
    )
    assert result["status"] == "failed"
    assert result["error_code"] == "GRADCAM_GENERATION_FAILED"


def test_stale_pending_explanation_terminalizes_only_on_authorized_post():
    prediction_id = uuid4()
    prediction = {
        "id": prediction_id,
        "prediction_status": "completed",
        "classification_run_id": uuid4(),
        "cell_detection_id": uuid4(),
    }
    pending = {
        "id": uuid4(),
        "cell_prediction_id": prediction_id,
        "status": "pending",
        "started_at": datetime.now(UTC) - timedelta(hours=1),
    }
    repository = _ExplanationRepository(prediction, pending)
    service = CellClassificationService(
        engine=_FakeEngine(),
        settings=SimpleNamespace(),
        repository_factory=lambda _connection: repository,
        model_resolver=SimpleNamespace(),
        auditor=lambda **_kwargs: None,
        pending_explanation_stale_after_seconds=60,
    )
    observed = service.get_prediction_explanation(str(prediction_id))
    assert observed["status"] == "pending"
    assert repository.fail_count == 0
    recovered = service.generate_explanation(
        str(prediction_id),
        True,
        SimpleNamespace(user_id=str(uuid4())),
        SimpleNamespace(),
    )
    assert recovered["status"] == "failed"
    assert recovered["error_code"] == "STALE_EXPLANATION_TERMINATED"
    assert repository.fail_count == 1


def test_default_wrapper_maps_real_ml_gradcam_unsupported_type(monkeypatch):
    pytest.importorskip("numpy")
    pytest.importorskip("tensorflow")
    ml_root = Path(__file__).resolve().parents[2] / "malaria_dl_local_project"
    if str(ml_root) not in sys.path:
        sys.path.insert(0, str(ml_root))
    from src.malaria_dl.explainability import gradcam as ml_gradcam

    def unsupported(**_kwargs):
        raise ml_gradcam.GradCAMUnsupportedError("incompatible")

    monkeypatch.setattr(ml_gradcam, "compute_gradcam_artifacts", unsupported)
    call = CellClassificationService(
        engine=_FakeEngine(),
        model_resolver=SimpleNamespace(),
    )._gradcam_callable()
    with pytest.raises(GradCAMUnsupportedError):
        call()


def test_shared_gradcam_helper_generates_compatible_artifacts():
    numpy = pytest.importorskip("numpy")
    tensorflow = pytest.importorskip("tensorflow")
    ml_root = Path(__file__).resolve().parents[2] / "malaria_dl_local_project"
    if str(ml_root) not in sys.path:
        sys.path.insert(0, str(ml_root))
    from src.malaria_dl.explainability.gradcam import compute_gradcam_artifacts

    model = tensorflow.keras.Sequential(
        [
            tensorflow.keras.layers.Input(shape=(20, 20, 3)),
            tensorflow.keras.layers.Conv2D(
                4, 3, activation="relu", name="conv_for_test"
            ),
            tensorflow.keras.layers.GlobalAveragePooling2D(),
            tensorflow.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    image = numpy.random.default_rng(7).random(
        (20, 20, 3), dtype=numpy.float32
    )
    heatmap, overlay, layer = compute_gradcam_artifacts(
        model,
        image,
        1,
        preprocessing_mode="rescale_0_1",
    )
    assert heatmap.shape == (20, 20)
    assert overlay.shape == (20, 20, 3)
    assert layer == "conv_for_test"
    assert numpy.isfinite(heatmap).all()
    assert numpy.isfinite(overlay).all()


def test_public_serialization_never_exposes_storage_keys():
    payload = CellClassificationService._public_record(
        {
            "id": "p",
            "crop_storage_key": "cell-crops/internal.png",
            "nested": {"overlay_storage_key": "secret", "sha256": "a" * 64},
        }
    )
    assert "crop_storage_key" not in payload
    assert "overlay_storage_key" not in payload["nested"]
    assert payload["nested"]["sha256"] == "a" * 64


def test_public_snapshot_is_allowlisted_and_strips_nested_sensitive_metadata():
    snapshot = {
        "schema_version": 1,
        "model_registry_id": str(uuid4()),
        "model_name": "custom_cnn",
        "checkpoint_sha256": "a" * 64,
        "input_signature": {
            "shape": [None, 20, 20, 3],
            "dataset_path": "/private/dataset",
            "token": "secret",
        },
        "preprocessing": {
            "mode": "rescale_0_1",
            "dataset_uri": "s3://private",
        },
        "calibration_metadata": {
            "threshold_calibration_id": str(uuid4()),
            "calibration_status": "recorded",
            "metadata": {
                "password": "hidden",
                "artifact_path": "/private/model",
            },
        },
        "deployment_metadata": {
            "secret": "hidden",
            "dataset_path": "/private/dataset",
        },
    }
    payload = CellClassificationService._public_record(
        {"model_snapshot": snapshot}
    )["model_snapshot"]
    encoded = repr(payload)
    assert payload["input_signature"] == {"shape": [None, 20, 20, 3]}
    assert payload["preprocessing"] == {"mode": "rescale_0_1"}
    assert payload["calibration_metadata"]["calibration_status"] == "recorded"
    assert "deployment_metadata" not in payload
    assert "/private" not in encoded
    assert "secret" not in encoded
    assert "password" not in encoded


class _ReviewRepository:
    def __init__(self, *, label="uninfected", status="completed"):
        self.prediction = {
            "id": uuid4(),
            "predicted_label": label,
            "prediction_status": status,
            "classification_run_id": uuid4(),
            "cell_detection_id": uuid4(),
        }
        self.created = 0

    def prediction_for_review(self, _prediction_id):
        return self.prediction

    def create_review(self, **values):
        self.created += 1
        return {**values, **self.prediction, "id": uuid4()}

    def add_event(self, **values):
        return values


def test_review_blocks_failed_and_confirmed_opposite_label():
    principal = SimpleNamespace(user_id=str(uuid4()))
    for repository, reviewed_label, expected_code in (
        (
            _ReviewRepository(status="failed"),
            None,
            "PREDICTION_NOT_REVIEWABLE",
        ),
        (
            _ReviewRepository(label="uninfected"),
            "parasitized",
            "CONFIRMED_LABEL_MISMATCH",
        ),
    ):
        service = CellClassificationService(
            engine=_FakeEngine(),
            repository_factory=lambda _connection, repo=repository: repo,
            model_resolver=SimpleNamespace(),
            auditor=lambda **_kwargs: None,
        )
        with pytest.raises(CellClassificationError) as error:
            service.create_review(
                str(repository.prediction["id"]),
                "confirmed",
                reviewed_label,
                None,
                principal,
                SimpleNamespace(),
            )
        assert error.value.code == expected_code
        assert repository.created == 0


def test_verified_explanation_content_returns_bytes_not_reopened_path(
    tmp_path: Path,
):
    storage = _storage(tmp_path)
    payload = _png("L")
    key = "cell-explanations/a/b/c/gradcam_heatmap.png"
    path = storage.local.resolve(key)
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)
    explanation = {
        "id": uuid4(),
        "status": "generated",
        "heatmap_storage_key": key,
        "heatmap_sha256": hashlib.sha256(payload).hexdigest(),
        "heatmap_file_size_bytes": len(payload),
    }

    class Repository:
        def get_explanation(self, _explanation_id):
            return explanation

    service = CellClassificationService(
        engine=_FakeEngine(),
        repository_factory=lambda _connection: Repository(),
        model_resolver=SimpleNamespace(),
        explanation_storage=storage,
    )
    metadata, content = service.explanation_content(
        str(explanation["id"]), "heatmap"
    )
    assert content == payload
    assert isinstance(content, bytes)
    assert "heatmap_storage_key" not in metadata
    assert metadata["heatmap_sha256"] == hashlib.sha256(payload).hexdigest()


def test_reconciler_reports_empty_staging_directories(tmp_path: Path):
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "storage"
        / "reconcile_cell_explanations.py"
    )
    spec = importlib.util.spec_from_file_location("reconcile_xai_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    empty = (
        tmp_path
        / ".staging"
        / "cell-explanations"
        / "classification"
        / "empty"
    )
    empty.mkdir(parents=True)
    issues = module.reconcile(root=tmp_path, rows=[])
    assert (
        "staging_residue",
        ".staging/cell-explanations/classification/empty",
    ) in issues
