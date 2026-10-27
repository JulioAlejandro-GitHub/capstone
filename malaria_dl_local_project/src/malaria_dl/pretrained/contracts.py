"""Frozen scientific protocol and completion for the original BiomedCLIP.

These contracts describe registration, not training or assessment results.
"""
from copy import deepcopy
from dataclasses import dataclass, asdict
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

from ..campaigns.contracts import CampaignError, canonical, digest
from ..execution.artifacts import file_identity

ARCHITECTURE = "biomedclip_zero_shot"
REPOSITORY = "microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
REVISION = "9f341de24bfb00180f1b847274256e9b65a3a32e"
TEXT_REPOSITORY = "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract"
TEXT_REVISION = "d673b8835373c6fa116d6d8006b33d48734e305d"
ORIGIN = dict(schema="pretrained_origin_v1", kind="pretrained_external", mode="zero_shot",
              training_performed=False, architecture=ARCHITECTURE,
              model_repository=REPOSITORY, revision=REVISION)
COMPONENTS = {
    "open_clip_pytorch_model.bin": {"bytes": 783705670, "sha256": "52cc993c5c5ff962bd0c60931874bc001e7e9b41666a385530f4a036294576be"},
    "open_clip_config.json": {"bytes": 707, "sha256": "9a41f334a8c444678772c0ebb9ab854c97ab350bced3a17b803e258d39c23dc0"},
    "text/config.json": {"bytes": 385, "sha256": "56bab767c02bc792897638feb8addc06d483d9c73769a5f554bbabea1f5507a1"},
    "text/tokenizer_config.json": {"bytes": 28, "sha256": "53b6f42b8b8daddbdc6d3532c324187a92b46c1602bd6e8d4ad5a413b4fc90e1"},
    "text/vocab.txt": {"bytes": 225062, "sha256": "7b36651908a88bc38bda41b728b2a598191e0d3b553cbacf7b1e5f026d5b5b9f"},
}
PROTOCOL = {
    "schema": "biomedclip_zero_shot_inference_v1",
    "architecture": ARCHITECTURE, "model_repository": REPOSITORY, "revision": REVISION,
    "checkpoint": "open_clip_pytorch_model.bin", "format": "open_clip_pytorch_state_dict",
    "open_clip_configuration": "open_clip_config.json",
    "visual_encoder": "vit_base_patch16_224", "visual_projection": "linear",
    "text_encoder": TEXT_REPOSITORY, "text_revision": TEXT_REVISION,
    "text_projection": "mlp", "text_pooling": "cls_last_hidden_state_pooler",
    "tokenizer": {"repository": TEXT_REPOSITORY, "revision": TEXT_REVISION,
                  "context_length": 256, "padding": "max_length", "truncation": True,
                  "clean": "whitespace", "do_lower_case": True, "strip_sep_token": False},
    "transform": {"color": "RGB", "resize_shortest": 224, "interpolation": "bicubic",
                  "antialias": True, "center_crop": [224, 224], "layout": "NCHW",
                  "dtype": "float32", "tensor_scale": "uint8_div_255",
                  "mean": [0.48145466, 0.4578275, 0.40821073],
                  "std": [0.26862954, 0.26130258, 0.27577711]},
    "embedding": {"dimension": 512, "space": "multimodal_projected", "normalization": "L2"},
    "classes": ["uninfected", "parasitized"], "positive_class": 1,
    "prompts": ["a microscopy image of an uninfected red blood cell.",
                "a microscopy image of a red blood cell infected with malaria parasites."],
    "prompt_language": "en", "prompt_ensemble": False,
    "score": {"formula": "softmax(exp(logit_scale) * cosine(image,text))[1]",
              "logit_scale_source": "checkpoint.logit_scale", "exp_logit_scale": 85.2322769165039,
              "semantics": "relative_to_two_prompts", "clinically_calibrated": False},
    "threshold": {"schema": "pretrained_fixed_threshold_v1", "value": 0.5, "comparison": ">=",
                  "source": "protocol_before_test", "calibration": None},
    "components": COMPONENTS,
}
PACKAGES = ("torch", "torchvision", "open_clip_torch", "transformers", "timm", "tokenizers", "numpy")


def require(condition, code):
    if not condition:
        raise CampaignError(code)


def framework_versions():
    return {name: version(name) for name in PACKAGES}


def configuration(dataset, frameworks):
    value = {"schema": "pretrained_configuration_v1", "scientific_origin": deepcopy(ORIGIN),
             "inference": deepcopy(PROTOCOL), "target_dataset": deepcopy(dataset),
             "framework": "pytorch/open_clip", "framework_versions": dict(frameworks)}
    validate_configuration(value)
    return value


def validate_configuration(value):
    require(isinstance(value, dict) and set(value) == {
        "schema", "scientific_origin", "inference", "target_dataset", "framework", "framework_versions"
    }, "PRETRAINED_CONFIGURATION_INCOMPLETE")
    require(value["schema"] == "pretrained_configuration_v1" and canonical(value["scientific_origin"]) == canonical(ORIGIN),
            "PRETRAINED_ORIGIN_INVALID")
    require(canonical(value["inference"]) == canonical(PROTOCOL), "PRETRAINED_PROTOCOL_INVALID")
    require(value["framework"] == "pytorch/open_clip" and set(value["framework_versions"]) == set(PACKAGES)
            and all(isinstance(v, str) and v.strip() for v in value["framework_versions"].values()),
            "PRETRAINED_FRAMEWORK_INVALID")
    d = value["target_dataset"]
    require(isinstance(d, dict) and set(d) == {
        "dataset_version_id", "dataset_materialization_id", "dataset_root", "patient_assignment_fingerprint",
        "record_assignment_fingerprint", "source_population_fingerprint", "clinical_identity_fingerprint",
        "counts", "selection_unit"}, "PRETRAINED_DATASET_INCOMPLETE")
    try:
        UUID(d["dataset_version_id"])
        UUID(d["dataset_materialization_id"])
    except (ValueError, TypeError):
        raise CampaignError("PRETRAINED_DATASET_INVALID") from None
    require(d["selection_unit"] == "dataset_version_id", "PRETRAINED_DATASET_INVALID")


def verify_components(root):
    """Hash actual bytes; no cache, manifest-only, symlink or name-based trust."""
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), "PRETRAINED_ROOT_INVALID")
    for name, expected in COMPONENTS.items():
        path = root / name
        require(not any(p.is_symlink() for p in (path, *path.parents)), "PRETRAINED_SYMLINK_FORBIDDEN")
        require(file_identity(path) == expected, "PRETRAINED_COMPONENT_IDENTITY_MISMATCH:" + name)
    return deepcopy(COMPONENTS)


@dataclass(frozen=True)
class PretrainedCompletionContractV1:
    schema: str
    run_id: str
    owner: str
    model_id: str
    dataset_version_id: str
    artifact_id: str
    model_version_id: str
    configuration_hash: str
    components_hash: str

    @classmethod
    def create(cls, *, run_id, owner, model_id, artifact_id, model_version_id, config):
        validate_configuration(config)
        return cls("pretrained_completion_v1", run_id, owner, model_id,
                   config["target_dataset"]["dataset_version_id"], artifact_id, model_version_id,
                   digest(config), digest(COMPONENTS))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        require(isinstance(value, dict) and set(value) == set(cls.__dataclass_fields__),
                "PRETRAINED_COMPLETION_INVALID")
        result = cls(**value)
        require(result.schema == "pretrained_completion_v1", "PRETRAINED_COMPLETION_INVALID")
        for key in ("run_id", "owner", "model_id", "dataset_version_id", "artifact_id", "model_version_id"):
            try:
                UUID(value[key])
            except (ValueError, TypeError):
                raise CampaignError("PRETRAINED_COMPLETION_INVALID") from None
        require(result.components_hash == digest(COMPONENTS)
                and isinstance(result.configuration_hash, str)
                and len(result.configuration_hash) == 64
                and all(ch in "0123456789abcdef" for ch in result.configuration_hash),
                "PRETRAINED_COMPLETION_INVALID")
        return result
