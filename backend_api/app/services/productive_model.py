from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db import get_primary_engine


STAGE2_ENVIRONMENT = "stage2"
STAGE2_ALIAS = "default"
EXPECTED_DEPLOYMENT_NAME = "malaria-stage2-classifier"
EXPECTED_LABEL_MAPPING = {
    "0": "uninfected",
    "1": "parasitized",
    "positive_class": 1,
    "positive_label": "parasitized",
}
SUPPORTED_FRAMEWORKS = {
    "keras",
    "tensorflow",
    "tf.keras",
    "tensorflow/keras",
}
SUPPORTED_PREPROCESSING = {"rescale_0_1", "rescale", "vgg16_imagenet"}
PRODUCTIVE_MODEL_UNAVAILABLE = (
    "No existe un modelo productivo válido para Etapa 2. "
    "Publique un modelo desde Modelo IA antes de continuar."
)
LOADER_VERSION = "productive-model-loader-v1"


class ProductiveModelError(ValueError):
    def __init__(
        self,
        code: str,
        detail: str = PRODUCTIVE_MODEL_UNAVAILABLE,
        *,
        reason: str | None = None,
    ):
        self.code = code
        self.detail = detail
        # The reason is intended for controlled logs/tests, never an HTTP response.
        self.reason = reason
        super().__init__(detail)


@dataclass(frozen=True)
class ResolvedProductiveModel:
    deployment_id: str
    deployment_name: str
    publication_id: str
    model_version_id: str
    model_name: str
    model_version: str | None
    source_training_run_id: str
    source_evaluation_run_id: str
    checkpoint_artifact_id: str
    checkpoint_path: Path
    checkpoint_sha256: str
    checkpoint_size_bytes: int
    framework: str
    framework_version: str | None
    architecture: str
    input_width: int
    input_height: int
    input_channels: int
    input_signature: dict[str, Any]
    output_signature: dict[str, Any]
    preprocessing: dict[str, Any]
    label_mapping: dict[str, Any]
    positive_label: str
    positive_class_index: int
    threshold: float
    threshold_source: str
    calibration_metadata: dict[str, Any]
    published_at: Any
    production_status: str
    deployment_metadata: dict[str, Any]

    @property
    def cache_key(self) -> tuple[str, str]:
        return self.model_version_id, self.checkpoint_sha256

    def snapshot(
        self,
        *,
        inference_version: str,
        review_margin: float,
        batch_size: int,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "model_registry_id": self.model_version_id,
            "production_model_id": self.deployment_id,
            "stage2_publication_id": self.publication_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "source_training_run_id": self.source_training_run_id,
            "source_evaluation_run_id": self.source_evaluation_run_id,
            "checkpoint_artifact_id": self.checkpoint_artifact_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_size_bytes": self.checkpoint_size_bytes,
            "framework": self.framework,
            "framework_version": self.framework_version,
            "architecture": self.architecture,
            "input_width": self.input_width,
            "input_height": self.input_height,
            "input_channels": self.input_channels,
            "input_signature": json.loads(json.dumps(self.input_signature)),
            "output_signature": json.loads(json.dumps(self.output_signature)),
            "preprocessing": json.loads(json.dumps(self.preprocessing)),
            "label_mapping": json.loads(json.dumps(self.label_mapping)),
            "positive_label": self.positive_label,
            "positive_class_index": self.positive_class_index,
            "threshold": self.threshold,
            "threshold_source": self.threshold_source,
            "calibration_metadata": json.loads(
                json.dumps(self.calibration_metadata, default=str)
            ),
            "published_at": (
                self.published_at.isoformat()
                if hasattr(self.published_at, "isoformat")
                else str(self.published_at)
            ),
            "production_status": self.production_status,
            "stage2_default": {
                "deployment_name": self.deployment_name,
                "environment": STAGE2_ENVIRONMENT,
                "alias": STAGE2_ALIAS,
                "deployment_id": self.deployment_id,
            },
            "loader_version": LOADER_VERSION,
            "inference_version": inference_version,
            "batch_size": batch_size,
            "review_margin": review_margin,
            "explainability_policy": {
                "version": "cell-gradcam-manual-v1",
                "method": "gradcam",
                "scope": "single_cell_on_demand",
                "automatic_generation": False,
                "manual_retry_required": True,
                "bulk_generation": False,
                "priority_hints": ["parasitized", "near_threshold"],
            },
        }


class ProductiveModelCache:
    """Small thread-safe cache keyed by immutable model identity."""

    def __init__(self, maxsize: int = 2):
        if maxsize < 1:
            raise ValueError("maxsize debe ser positivo")
        self.maxsize = maxsize
        self._items: OrderedDict[tuple[str, str], Any] = OrderedDict()
        self._lock = RLock()

    def get_or_load(
        self,
        resolved: ResolvedProductiveModel,
        loader: Callable[[ResolvedProductiveModel], Any],
    ) -> Any:
        key = resolved.cache_key
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key]
            model = loader(resolved)
            self._items[key] = model
            while len(self._items) > self.maxsize:
                self._items.popitem(last=False)
            return model

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    result = {str(key): item for key, item in value.items()}
    if "positive_class" in result:
        try:
            result["positive_class"] = int(result["positive_class"])
        except (TypeError, ValueError):
            pass
    return result


def _json_object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _signature_shape(signature: Mapping[str, Any], *, output: bool = False) -> list[Any]:
    candidates: Sequence[Any] = (
        signature.get("shape"),
        signature.get("input_shape"),
        signature.get("output_shape"),
    )
    for candidate in candidates:
        if isinstance(candidate, (list, tuple)):
            return list(candidate)
    tensors = signature.get("inputs" if not output else "outputs")
    if isinstance(tensors, list) and len(tensors) == 1 and isinstance(tensors[0], Mapping):
        return _signature_shape(tensors[0], output=output)
    return []


def parse_input_signature(signature: Mapping[str, Any]) -> tuple[int, int, int]:
    shape = _signature_shape(signature)
    if len(shape) == 4:
        shape = shape[1:]
    if len(shape) != 3:
        raise ProductiveModelError(
            "MODEL_INPUT_SIGNATURE_INVALID", reason="input shape ausente o no rank-3/4"
        )
    try:
        height, width, channels = (int(value) for value in shape)
    except (TypeError, ValueError) as exc:
        raise ProductiveModelError(
            "MODEL_INPUT_SIGNATURE_INVALID", reason="dimensiones no enteras"
        ) from exc
    if height < 1 or width < 1 or channels not in {1, 3}:
        raise ProductiveModelError(
            "MODEL_INPUT_SIGNATURE_INVALID", reason="dimensiones incompatibles"
        )
    return width, height, channels


def validate_output_signature(signature: Mapping[str, Any]) -> None:
    shape = _signature_shape(signature, output=True)
    if not shape:
        raise ProductiveModelError(
            "MODEL_OUTPUT_SIGNATURE_INVALID", reason="output shape ausente"
        )
    last = shape[-1]
    try:
        width = int(last)
    except (TypeError, ValueError) as exc:
        raise ProductiveModelError(
            "MODEL_OUTPUT_SIGNATURE_INVALID", reason="output shape no numérico"
        ) from exc
    if width not in {1, 2}:
        raise ProductiveModelError(
            "MODEL_OUTPUT_SIGNATURE_INVALID", reason="solo se admite salida binaria"
        )


class ProductiveModelResolver:
    """Resolve only the unique active Stage 2 default deployment.

    A publication is a catalog authorization, never a fallback. The resolver
    consequently starts at the active ``stage2/default`` deployment and then
    requires one matching active publication.
    """

    def __init__(
        self,
        *,
        engine: Engine | None = None,
        candidate_loader: Callable[[], Sequence[Mapping[str, Any]]] | None = None,
        snapshot_loader: Callable[
            [Mapping[str, Any]], Sequence[Mapping[str, Any]]
        ]
        | None = None,
        model_loader: Callable[[Path], Any] | None = None,
        cache: ProductiveModelCache | None = None,
        ml_project_root: Path | None = None,
        allowed_roots: Sequence[Path] | None = None,
    ):
        self.engine = engine
        self.candidate_loader = candidate_loader
        self.snapshot_loader = snapshot_loader
        self.model_loader = model_loader or self._keras_loader
        self.cache = cache or ProductiveModelCache()
        capstone_root = Path(__file__).resolve().parents[3]
        self.ml_project_root = (
            ml_project_root or capstone_root / "malaria_dl_local_project"
        ).resolve()
        roots = allowed_roots or (
            self.ml_project_root / "releases",
            self.ml_project_root / "outputs",
        )
        self.allowed_roots = tuple(Path(root).resolve() for root in roots)

    @staticmethod
    def _keras_loader(path: Path) -> Any:
        import tensorflow as tf

        return tf.keras.models.load_model(path, compile=False)

    def _engine(self) -> Engine:
        return self.engine or get_primary_engine()

    def _fetch_candidates(
        self,
        *,
        snapshot: Mapping[str, Any] | None = None,
        connection: Any | None = None,
    ) -> list[dict[str, Any]]:
        # environment+alias are authoritative. Querying every active row in the
        # context lets us reject ambiguity across differing deployment names.
        historical = snapshot is not None
        statement = text(
            """
            SELECT
              d.id::text deployment_id,d.deployment_name,d.environment,d.alias,
              d.status production_status,d.model_version_id::text,
              d.checkpoint_artifact_id::text,d.artifact_sha256 deployment_sha256,
              d.artifact_size_bytes deployment_size_bytes,
              d.threshold_calibration_id::text,d.threshold_value,
              d.threshold_profile_snapshot,d.preprocessing_profile_snapshot,
              d.label_mapping_snapshot,d.positive_label,d.score_name,
              d.metadata deployment_metadata,
              mv.model_name,mv.version_number,mv.status model_version_status,
              mv.lineage_status,mv.training_run_id::text source_training_run_id,
              mv.artifact_sha256 model_sha256,
              mv.artifact_size_bytes model_size_bytes,mv.framework,
              mv.framework_version,mv.input_signature,mv.output_signature,
              mv.preprocessing_profile_snapshot model_preprocessing,
              mv.class_mapping model_mapping,mv.metadata model_metadata,
              artifact.path artifact_path,artifact.checksum artifact_checksum,
              artifact.run_id::text artifact_run_id,
              artifact.file_size_bytes artifact_size_bytes,
              artifact.artifact_status,
              publication.id::text publication_id,
              publication.evaluation_run_id::text source_evaluation_run_id,
              publication.status publication_status,
              publication.is_active publication_is_active,
              publication.published_at,publication.metadata publication_metadata,
              training.status training_status,training.run_type training_type,
              evaluation.status evaluation_status,evaluation.run_type evaluation_type,
              calibration.threshold_selected calibration_threshold,
              calibration.threshold_source calibration_threshold_source,
              calibration.threshold_policy calibration_threshold_policy,
              calibration.calibration_split,
              calibration.calibration_status,
              calibration.score_name calibration_score_name,
              calibration.positive_label calibration_positive_label,
              calibration.metadata calibration_metadata,
              EXISTS(
                SELECT 1
                FROM run_lineage lineage
                WHERE lineage.parent_run_id=mv.training_run_id
                  AND lineage.child_run_id=publication.evaluation_run_id
                  AND lineage.model_version_id=mv.id
                  AND lineage.checkpoint_artifact_id=d.checkpoint_artifact_id
                  AND lineage.relationship_type='evaluates_checkpoint_from'
              ) evaluation_lineage_valid
            FROM deployed_model_versions d
            JOIN model_versions mv ON mv.id=d.model_version_id
            JOIN artifacts artifact ON artifact.id=d.checkpoint_artifact_id
            JOIN runs training ON training.id=mv.training_run_id
            LEFT JOIN stage2_model_publications publication
              ON publication.model_version_id=d.model_version_id
             AND publication.training_run_id=mv.training_run_id
             AND publication.checkpoint_artifact_id=d.checkpoint_artifact_id
             AND publication.scope='stage2'
             AND (
               :historical
               OR (
                 publication.status='active'
                 AND publication.is_active=true
               )
             )
            LEFT JOIN runs evaluation ON evaluation.id=publication.evaluation_run_id
            LEFT JOIN run_threshold_calibration calibration
              ON calibration.run_threshold_calibration_id=d.threshold_calibration_id
             AND calibration.model_version_id=d.model_version_id
            WHERE (
              (
                NOT :historical
                AND d.environment=:environment
                AND d.alias=:alias
                AND d.status='active'
              )
              OR
              (
                :historical
                AND d.id=CAST(:deployment_id AS uuid)
                AND d.model_version_id=CAST(:model_version_id AS uuid)
                AND d.checkpoint_artifact_id=CAST(:artifact_id AS uuid)
                AND publication.id=CAST(:publication_id AS uuid)
                AND artifact.checksum=:checkpoint_sha256
              )
            )
            ORDER BY d.created_at,d.id
            """
        )
        params = {
            "historical": historical,
            "environment": STAGE2_ENVIRONMENT,
            "alias": STAGE2_ALIAS,
            "deployment_id": (
                str(snapshot.get("production_model_id")) if snapshot else None
            ),
            "model_version_id": (
                str(snapshot.get("model_registry_id")) if snapshot else None
            ),
            "artifact_id": (
                str(snapshot.get("checkpoint_artifact_id")) if snapshot else None
            ),
            "publication_id": (
                str(snapshot.get("stage2_publication_id")) if snapshot else None
            ),
            "checkpoint_sha256": (
                str(snapshot.get("checkpoint_sha256")).lower()
                if snapshot
                else None
            ),
        }
        if connection is not None:
            rows = connection.execute(statement, params).mappings().all()
        else:
            with self._engine().connect() as owned_connection:
                rows = owned_connection.execute(
                    statement,
                    params,
                ).mappings().all()
        return [dict(row) for row in rows]

    def _artifact_path(self, raw_path: Any) -> Path:
        if not raw_path:
            raise ProductiveModelError(
                "MODEL_ARTIFACT_MISSING", reason="artifact path ausente"
            )
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = self.ml_project_root / path
        lexical = Path(path.absolute())
        current = Path(lexical.anchor)
        for part in lexical.parts[1:]:
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError as exc:
                raise ProductiveModelError(
                    "MODEL_ARTIFACT_MISSING", reason="artifact inexistente"
                ) from exc
            if stat.S_ISLNK(info.st_mode):
                raise ProductiveModelError(
                    "MODEL_ARTIFACT_UNSAFE", reason="symlink en artifact path"
                )
        resolved = lexical.resolve(strict=True)
        if not any(
            resolved == root or resolved.is_relative_to(root)
            for root in self.allowed_roots
        ):
            raise ProductiveModelError(
                "MODEL_ARTIFACT_UNSAFE", reason="artifact fuera de roots autorizados"
            )
        if not stat.S_ISREG(resolved.lstat().st_mode):
            raise ProductiveModelError(
                "MODEL_ARTIFACT_MISSING", reason="artifact no regular"
            )
        return resolved

    def _validate(
        self,
        row: Mapping[str, Any],
        *,
        require_active: bool,
    ) -> ResolvedProductiveModel:
        if row.get("environment") != STAGE2_ENVIRONMENT or row.get("alias") != STAGE2_ALIAS:
            raise ProductiveModelError(
                "PRODUCTIVE_SLOT_INVALID", reason="contexto no es stage2/default"
            )
        if require_active and row.get("production_status") != "active":
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_INACTIVE", reason="deployment inactivo"
            )
        if not str(row.get("deployment_name") or "").strip():
            raise ProductiveModelError(
                "PRODUCTIVE_SLOT_INVALID", reason="deployment_name vacío"
            )
        if require_active and (
            row.get("publication_status") != "active"
            or row.get("publication_is_active") is not True
        ):
            raise ProductiveModelError(
                "PRODUCTIVE_PUBLICATION_INACTIVE", reason="publicación no activa"
            )
        if row.get("training_type") != "training" or row.get("training_status") != "completed":
            raise ProductiveModelError(
                "PRODUCTIVE_TRAIN_INCOMPLETE", reason="TRAIN no completed"
            )
        if (
            row.get("evaluation_type") != "evaluation"
            or row.get("evaluation_status") != "completed"
            or row.get("evaluation_lineage_valid") is not True
        ):
            raise ProductiveModelError(
                "PRODUCTIVE_EVALUATION_INCOMPLETE", reason="EVALUATE no completed"
            )
        if require_active and row.get("model_version_status") not in {
            "candidate",
            "validated",
            "approved",
            "deployed",
        }:
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_STATUS_INVALID",
                reason="model version no utilizable",
            )
        if row.get("lineage_status") != "resolved":
            raise ProductiveModelError(
                "PRODUCTIVE_LINEAGE_INVALID", reason="lineage no resolved"
            )
        framework = str(row.get("framework") or "").strip().lower()
        if framework not in SUPPORTED_FRAMEWORKS:
            raise ProductiveModelError(
                "PRODUCTIVE_FRAMEWORK_UNSUPPORTED", reason="framework no soportado"
            )
        if row.get("artifact_status") != "available":
            raise ProductiveModelError(
                "MODEL_ARTIFACT_UNAVAILABLE", reason="artifact no available"
            )
        if str(row.get("artifact_run_id") or "") != str(
            row.get("source_training_run_id") or ""
        ):
            raise ProductiveModelError(
                "MODEL_ARTIFACT_LINEAGE_INVALID",
                reason="artifact no pertenece al TRAIN publicado",
            )

        deployment_metadata = _json_object(row.get("deployment_metadata"))
        stage2 = _json_object(deployment_metadata.get("stage2"))
        smoke = _json_object(
            deployment_metadata.get("technical_smoke_test")
            or deployment_metadata.get("stage2_smoke_test")
        )
        if stage2.get("eligible") is not True or smoke.get("status") != "PASS":
            raise ProductiveModelError(
                "PRODUCTIVE_STAGE2_EVIDENCE_MISSING",
                reason="stage2 eligibility/smoke PASS ausente",
            )
        technical = _json_object(deployment_metadata.get("technical_contract"))
        input_signature = _json_object(
            technical.get("input_signature") or row.get("input_signature")
        )
        output_signature = _json_object(
            technical.get("output_signature") or row.get("output_signature")
        )
        input_width, input_height, input_channels = parse_input_signature(input_signature)
        validate_output_signature(output_signature)

        preprocessing = _json_object(row.get("preprocessing_profile_snapshot"))
        if not preprocessing:
            preprocessing = _json_object(technical.get("preprocessing"))
        mode = str(
            preprocessing.get("mode") or preprocessing.get("preprocessing") or ""
        ).strip()
        if mode not in SUPPORTED_PREPROCESSING:
            raise ProductiveModelError(
                "PRODUCTIVE_PREPROCESSING_INVALID",
                reason="preprocessing ausente, auto o no soportado",
            )
        if mode == "rescale":
            mode = "rescale_0_1"
        preprocessing["mode"] = mode

        mapping = _mapping(row.get("label_mapping_snapshot"))
        if not mapping:
            mapping = _mapping(technical.get("class_mapping"))
        if any(mapping.get(key) != value for key, value in EXPECTED_LABEL_MAPPING.items()):
            raise ProductiveModelError(
                "PRODUCTIVE_LABEL_MAPPING_INVALID", reason="mapping no canónico"
            )
        if (
            row.get("positive_label") != "parasitized"
            or row.get("score_name") != "probability_parasitized"
        ):
            raise ProductiveModelError(
                "PRODUCTIVE_LABEL_MAPPING_INVALID", reason="convención de score inválida"
            )

        threshold_snapshot = _json_object(row.get("threshold_profile_snapshot"))
        if not row.get("threshold_calibration_id") or not threshold_snapshot:
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_MISSING", reason="threshold snapshot ausente"
            )
        try:
            threshold = float(row["threshold_value"])
            calibrated = float(row["calibration_threshold"])
        except (TypeError, ValueError) as exc:
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_MISSING", reason="threshold no numérico"
            ) from exc
        if not (
            math.isfinite(threshold)
            and 0.0 <= threshold <= 1.0
            and math.isclose(threshold, calibrated, abs_tol=1e-12)
        ):
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_INVALID", reason="threshold/calibración no coinciden"
            )
        snapshot_value = threshold_snapshot.get(
            "value", threshold_snapshot.get("threshold")
        )
        try:
            frozen_threshold = float(snapshot_value)
        except (TypeError, ValueError) as exc:
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_INVALID",
                reason="threshold snapshot no numérico",
            ) from exc
        if snapshot_value is None or not math.isclose(
            frozen_threshold, threshold, abs_tol=1e-12
        ):
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_INVALID", reason="threshold snapshot no coincide"
            )
        threshold_source = str(
            threshold_snapshot.get("source")
            or threshold_snapshot.get("threshold_source")
            or row.get("calibration_threshold_source")
            or ""
        ).strip()
        if (
            not threshold_source
            or row.get("calibration_status") not in {"recorded", "validated"}
            or row.get("calibration_positive_label") != "parasitized"
            or row.get("calibration_score_name") != "probability_parasitized"
        ):
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_INVALID",
                reason="fuente/calibración de threshold inválida",
            )
        calibration_source = str(
            row.get("calibration_threshold_source") or ""
        ).strip()
        if not calibration_source or threshold_source != calibration_source:
            raise ProductiveModelError(
                "PRODUCTIVE_THRESHOLD_INVALID",
                reason="fuente del threshold snapshot/calibración no coincide",
            )

        expected_sha = str(row.get("deployment_sha256") or "").lower()
        checksums = {
            expected_sha,
            str(row.get("model_sha256") or "").lower(),
            str(row.get("artifact_checksum") or "").lower(),
        }
        if len(checksums) != 1 or len(expected_sha) != 64:
            raise ProductiveModelError(
                "MODEL_CHECKSUM_MISMATCH", reason="SHA de registros no coincide"
            )
        expected_size = row.get("deployment_size_bytes")
        try:
            sizes = {
                int(value)
                for value in (
                    expected_size,
                    row.get("model_size_bytes"),
                    row.get("artifact_size_bytes"),
                )
                if value is not None
            }
            parsed_expected_size = int(expected_size)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ProductiveModelError(
                "MODEL_SIZE_MISMATCH", reason="tamaño no numérico"
            ) from exc
        if (
            expected_size is None
            or len(sizes) != 1
            or parsed_expected_size < 1
        ):
            raise ProductiveModelError(
                "MODEL_SIZE_MISMATCH", reason="tamaños de registros no coinciden"
            )
        path = self._artifact_path(row.get("artifact_path"))
        if path.stat().st_size != parsed_expected_size:
            raise ProductiveModelError(
                "MODEL_SIZE_MISMATCH", reason="tamaño físico no coincide"
            )
        if sha256_file(path) != expected_sha:
            raise ProductiveModelError(
                "MODEL_CHECKSUM_MISMATCH", reason="SHA físico no coincide"
            )

        model_metadata = _json_object(row.get("model_metadata"))
        architecture = str(
            technical.get("architecture")
            or model_metadata.get("architecture")
            or row.get("model_name")
            or ""
        ).strip()
        if not architecture:
            raise ProductiveModelError(
                "PRODUCTIVE_ARCHITECTURE_MISSING", reason="architecture ausente"
            )
        calibration_metadata = {
            "threshold_calibration_id": str(row["threshold_calibration_id"]),
            "threshold_policy": row.get("calibration_threshold_policy"),
            "calibration_split": row.get("calibration_split"),
            "calibration_status": row.get("calibration_status"),
            "metadata": _json_object(row.get("calibration_metadata")),
        }
        return ResolvedProductiveModel(
            deployment_id=str(row["deployment_id"]),
            deployment_name=str(row["deployment_name"]),
            publication_id=str(row["publication_id"]),
            model_version_id=str(row["model_version_id"]),
            model_name=str(row["model_name"]),
            model_version=(
                str(row["version_number"])
                if row.get("version_number") is not None
                else None
            ),
            source_training_run_id=str(row["source_training_run_id"]),
            source_evaluation_run_id=str(row["source_evaluation_run_id"]),
            checkpoint_artifact_id=str(row["checkpoint_artifact_id"]),
            checkpoint_path=path,
            checkpoint_sha256=expected_sha,
            checkpoint_size_bytes=parsed_expected_size,
            framework=framework,
            framework_version=(
                str(row["framework_version"]) if row.get("framework_version") else None
            ),
            architecture=architecture,
            input_width=input_width,
            input_height=input_height,
            input_channels=input_channels,
            input_signature=input_signature,
            output_signature=output_signature,
            preprocessing=preprocessing,
            label_mapping=mapping,
            positive_label="parasitized",
            positive_class_index=1,
            threshold=threshold,
            threshold_source=threshold_source,
            calibration_metadata=calibration_metadata,
            published_at=row["published_at"],
            production_status=str(row["production_status"]),
            deployment_metadata=deployment_metadata,
        )

    def _safe_validate(
        self,
        row: Mapping[str, Any],
        *,
        require_active: bool,
    ) -> ResolvedProductiveModel:
        try:
            return self._validate(row, require_active=require_active)
        except ProductiveModelError:
            raise
        except (KeyError, OSError, TypeError, ValueError, OverflowError) as exc:
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_METADATA_INVALID",
                reason=f"metadata productiva inválida: {type(exc).__name__}",
            ) from exc

    @staticmethod
    def _same_identity(
        left: ResolvedProductiveModel,
        right: ResolvedProductiveModel,
    ) -> bool:
        return (
            left.deployment_id,
            left.publication_id,
            left.model_version_id,
            left.checkpoint_artifact_id,
            left.checkpoint_sha256,
        ) == (
            right.deployment_id,
            right.publication_id,
            right.model_version_id,
            right.checkpoint_artifact_id,
            right.checkpoint_sha256,
        )

    @staticmethod
    def _snapshot_identity(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
        keys = (
            "production_model_id",
            "stage2_publication_id",
            "model_registry_id",
            "checkpoint_artifact_id",
            "checkpoint_sha256",
        )
        values = tuple(str(snapshot.get(key) or "").strip() for key in keys)
        if any(not value for value in values):
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_INVALID",
                reason="IDs/SHA obligatorios ausentes del snapshot",
            )
        try:
            identifiers = tuple(str(UUID(value)) for value in values[:-1])
        except (ValueError, AttributeError) as exc:
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_INVALID",
                reason="identificadores congelados inválidos",
            ) from exc
        if len(values[-1]) != 64 or any(
            character not in "0123456789abcdef" for character in values[-1].lower()
        ):
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_INVALID",
                reason="checkpoint_sha256 congelado inválido",
            )
        return (*identifiers, values[-1].lower())

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )

    def _validate_snapshot_contract(
        self,
        snapshot: Mapping[str, Any],
        resolved: ResolvedProductiveModel,
    ) -> None:
        expected_identity = self._snapshot_identity(snapshot)
        actual_identity = (
            resolved.deployment_id,
            resolved.publication_id,
            resolved.model_version_id,
            resolved.checkpoint_artifact_id,
            resolved.checkpoint_sha256,
        )
        if expected_identity != actual_identity:
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_MISMATCH",
                reason="la identidad histórica no coincide",
            )
        try:
            scalar_pairs = (
                (str(snapshot["model_name"]), resolved.model_name),
                (
                    (
                        str(snapshot["model_version"])
                        if snapshot.get("model_version") is not None
                        else None
                    ),
                    resolved.model_version,
                ),
                (
                    str(snapshot["source_training_run_id"]),
                    resolved.source_training_run_id,
                ),
                (
                    str(snapshot["source_evaluation_run_id"]),
                    resolved.source_evaluation_run_id,
                ),
                (str(snapshot["framework"]).lower(), resolved.framework),
                (
                    (
                        str(snapshot["framework_version"])
                        if snapshot.get("framework_version") is not None
                        else None
                    ),
                    resolved.framework_version,
                ),
                (str(snapshot["architecture"]), resolved.architecture),
                (int(snapshot["checkpoint_size_bytes"]), resolved.checkpoint_size_bytes),
                (int(snapshot["input_width"]), resolved.input_width),
                (int(snapshot["input_height"]), resolved.input_height),
                (int(snapshot["input_channels"]), resolved.input_channels),
                (str(snapshot["positive_label"]), resolved.positive_label),
                (
                    int(snapshot["positive_class_index"]),
                    resolved.positive_class_index,
                ),
                (str(snapshot["threshold_source"]), resolved.threshold_source),
            )
            frozen_threshold = float(snapshot["threshold"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_INVALID",
                reason="contrato congelado incompleto o no numérico",
            ) from exc
        if (
            any(left != right for left, right in scalar_pairs)
            or not math.isfinite(frozen_threshold)
            or not math.isclose(
                frozen_threshold, resolved.threshold, abs_tol=1e-12
            )
        ):
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_MISMATCH",
                reason="campos escalares congelados no coinciden",
            )
        json_pairs = (
            (snapshot.get("input_signature"), resolved.input_signature),
            (snapshot.get("output_signature"), resolved.output_signature),
            (snapshot.get("preprocessing"), resolved.preprocessing),
            (snapshot.get("label_mapping"), resolved.label_mapping),
            (snapshot.get("calibration_metadata"), resolved.calibration_metadata),
        )
        if any(
            self._canonical(left) != self._canonical(right)
            for left, right in json_pairs
        ):
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_MISMATCH",
                reason="contrato JSON congelado no coincide",
            )
        stage2 = snapshot.get("stage2_default")
        if not isinstance(stage2, Mapping) or (
            str(stage2.get("environment")) != STAGE2_ENVIRONMENT
            or str(stage2.get("alias")) != STAGE2_ALIAS
            or str(stage2.get("deployment_id")) != resolved.deployment_id
            or str(stage2.get("deployment_name")) != resolved.deployment_name
        ):
            raise ProductiveModelError(
                "FROZEN_MODEL_SNAPSHOT_MISMATCH",
                reason="slot stage2/default congelado no coincide",
            )

    def resolve(self) -> ResolvedProductiveModel:
        rows = list(
            self.candidate_loader()
            if self.candidate_loader is not None
            else self._fetch_candidates()
        )
        if len(rows) != 1:
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_NOT_UNIQUE",
                reason=f"stage2/default resolvió {len(rows)} filas",
            )
        return self._safe_validate(rows[0], require_active=True)

    def resolve_snapshot(
        self,
        snapshot: Mapping[str, Any],
    ) -> ResolvedProductiveModel:
        identity = self._snapshot_identity(snapshot)
        if self.snapshot_loader is not None:
            rows = list(self.snapshot_loader(snapshot))
        elif self.candidate_loader is not None:
            rows = [
                row
                for row in self.candidate_loader()
                if (
                    str(row.get("deployment_id") or ""),
                    str(row.get("publication_id") or ""),
                    str(row.get("model_version_id") or ""),
                    str(row.get("checkpoint_artifact_id") or ""),
                    str(row.get("deployment_sha256") or "").lower(),
                )
                == identity
            ]
        else:
            rows = self._fetch_candidates(snapshot=snapshot)
        if len(rows) != 1:
            raise ProductiveModelError(
                "FROZEN_MODEL_UNAVAILABLE",
                reason=f"snapshot histórico resolvió {len(rows)} filas",
            )
        resolved = self._safe_validate(rows[0], require_active=False)
        self._validate_snapshot_contract(snapshot, resolved)
        return resolved

    def revalidate(
        self,
        resolved: ResolvedProductiveModel,
        *,
        connection: Any,
    ) -> ResolvedProductiveModel:
        """Lock and revalidate the active slot immediately before run creation."""

        if self.candidate_loader is not None:
            current = self.resolve()
            if not self._same_identity(resolved, current):
                raise ProductiveModelError(
                    "PRODUCTIVE_MODEL_CHANGED",
                    reason="stage2/default cambió antes de congelar la ejecución",
                )
            return current
        locked = connection.execute(
            text(
                """
                SELECT d.id
                FROM deployed_model_versions d
                JOIN model_versions mv ON mv.id=d.model_version_id
                JOIN artifacts artifact ON artifact.id=d.checkpoint_artifact_id
                JOIN stage2_model_publications publication
                  ON publication.id=CAST(:publication_id AS uuid)
                 AND publication.model_version_id=d.model_version_id
                 AND publication.training_run_id=mv.training_run_id
                 AND publication.checkpoint_artifact_id=d.checkpoint_artifact_id
                 AND publication.scope='stage2'
                JOIN run_threshold_calibration calibration
                  ON calibration.run_threshold_calibration_id=
                    d.threshold_calibration_id
                 AND calibration.model_version_id=d.model_version_id
                JOIN runs training ON training.id=mv.training_run_id
                JOIN runs evaluation
                  ON evaluation.id=publication.evaluation_run_id
                JOIN run_lineage lineage
                  ON lineage.parent_run_id=mv.training_run_id
                 AND lineage.child_run_id=publication.evaluation_run_id
                 AND lineage.model_version_id=mv.id
                 AND lineage.checkpoint_artifact_id=d.checkpoint_artifact_id
                 AND lineage.relationship_type='evaluates_checkpoint_from'
                WHERE d.id=CAST(:deployment_id AS uuid)
                  AND d.model_version_id=CAST(:model_version_id AS uuid)
                  AND d.checkpoint_artifact_id=CAST(:artifact_id AS uuid)
                  AND d.environment=:environment
                  AND d.alias=:alias
                  AND d.status='active'
                  AND publication.status='active'
                  AND publication.is_active=true
                  AND mv.status IN (
                    'candidate','validated','approved','deployed'
                  )
                  AND mv.lineage_status='resolved'
                  AND artifact.artifact_status='available'
                  AND artifact.checksum=:checkpoint_sha256
                  AND artifact.file_size_bytes=:checkpoint_size_bytes
                  AND d.artifact_sha256=:checkpoint_sha256
                  AND d.artifact_size_bytes=:checkpoint_size_bytes
                  AND training.run_type='training'
                  AND training.status='completed'
                  AND evaluation.run_type='evaluation'
                  AND evaluation.status='completed'
                  AND calibration.calibration_status IN ('recorded','validated')
                  AND calibration.threshold_selected=:threshold
                  AND calibration.threshold_source=:threshold_source
                FOR SHARE OF
                  d,mv,artifact,publication,calibration,training,evaluation,lineage
                """
            ),
            {
                "deployment_id": resolved.deployment_id,
                "publication_id": resolved.publication_id,
                "model_version_id": resolved.model_version_id,
                "artifact_id": resolved.checkpoint_artifact_id,
                "environment": STAGE2_ENVIRONMENT,
                "alias": STAGE2_ALIAS,
                "checkpoint_sha256": resolved.checkpoint_sha256,
                "checkpoint_size_bytes": resolved.checkpoint_size_bytes,
                "threshold": resolved.threshold,
                "threshold_source": resolved.threshold_source,
            },
        ).first()
        if not locked:
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_CHANGED",
                reason="stage2/default ya no conserva la identidad/status congelados",
            )
        rows = self._fetch_candidates(connection=connection)
        if len(rows) != 1:
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_NOT_UNIQUE",
                reason=f"revalidación stage2/default resolvió {len(rows)} filas",
            )
        current = self._safe_validate(rows[0], require_active=True)
        if not self._same_identity(resolved, current):
            raise ProductiveModelError(
                "PRODUCTIVE_MODEL_CHANGED",
                reason="stage2/default cambió antes de congelar la ejecución",
            )
        return current

    @staticmethod
    def _verified_checkpoint_bytes(
        resolved: ResolvedProductiveModel,
    ) -> bytes:
        descriptor: int | None = None
        try:
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(resolved.checkpoint_path, flags)
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size != resolved.checkpoint_size_bytes
            ):
                raise ProductiveModelError(
                    "MODEL_SIZE_MISMATCH",
                    reason="checkpoint cambió antes de la carga",
                )
            chunks: list[bytes] = []
            remaining = resolved.checkpoint_size_bytes + 1
            while remaining > 0:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            after = os.fstat(descriptor)
            if (
                len(payload) != resolved.checkpoint_size_bytes
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise ProductiveModelError(
                    "MODEL_ARTIFACT_CHANGED",
                    reason="checkpoint cambió durante la lectura",
                )
            if hashlib.sha256(payload).hexdigest() != resolved.checkpoint_sha256:
                raise ProductiveModelError(
                    "MODEL_CHECKSUM_MISMATCH",
                    reason="SHA físico cambió antes de la carga",
                )
            return payload
        except ProductiveModelError:
            raise
        except (FileNotFoundError, OSError) as exc:
            raise ProductiveModelError(
                "MODEL_ARTIFACT_UNAVAILABLE",
                reason="checkpoint no disponible durante la carga",
            ) from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _load_verified_copy(
        self,
        resolved: ResolvedProductiveModel,
    ) -> Any:
        payload = self._verified_checkpoint_bytes(resolved)
        descriptor: int | None = None
        temporary_path: Path | None = None
        try:
            descriptor, raw_path = tempfile.mkstemp(
                prefix="capstone-model-",
                suffix=resolved.checkpoint_path.suffix,
            )
            temporary_path = Path(raw_path)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as destination:
                descriptor = None
                destination.write(payload)
                destination.flush()
                os.fsync(destination.fileno())
            return self.model_loader(temporary_path)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def load(self, resolved: ResolvedProductiveModel) -> Any:
        return self.cache.get_or_load(resolved, self._load_verified_copy)
