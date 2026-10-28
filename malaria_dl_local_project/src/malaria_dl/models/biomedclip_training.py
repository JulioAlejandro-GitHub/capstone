"""BiomedCLIP binary classifiers trained over the registered zero-shot origin.

The base image encoder and its local text/tokenizer files are the artifacts of the
biomedclip_zero_shot logical TRAIN named by ``recipe.base_model``; they are resolved from
``artifacts`` and verified byte by byte, never downloaded. A checkpoint stores only the
parameters this RUN trained (head, plus the unfrozen ViT blocks for fine-tuning) and the base
identity they apply to; the rest of the encoder is the unchanged base.
"""
from __future__ import annotations

import os
from pathlib import Path

CHECKPOINT_SCHEMA = "biomedclip_trainable_checkpoint_v1"
EMBEDDING = "openclip_encode_image_l2_v1"
VIT_BLOCKS = 12
# Trained with the last blocks: the final norm and the visual projection feed the head directly.
TOP_PARAMETERS = ("visual.trunk.norm.weight", "visual.trunk.norm.bias", "visual.head.proj.weight")


class BiomedCLIPAdapter:
    """Registry adapter marker: this family is executed by execution.train_torch."""
    framework = "pytorch_openclip"


def base_files(base, connection=None):
    """Verified local paths of the registered base: checkpoint plus its four dependencies."""
    from contextlib import nullcontext

    from sqlalchemy import text

    from ..assessment.openclip import registered_dependencies
    from ..campaigns.contracts import CampaignError
    from ..execution.storage_paths import local_scientific_path
    from ..persistence.database import get_connection
    from ..pretrained.registration import verified_file

    scope = nullcontext(connection) if connection is not None else get_connection()
    with scope as c:
        row = c.execute(text("""
            SELECT a.path, a.checksum, a.file_size_bytes, a.artifact_status
            FROM model_versions mv JOIN artifacts a
              ON a.id=mv.checkpoint_artifact_id AND a.run_id=mv.training_run_id
            WHERE mv.id=CAST(:version AS uuid) AND mv.training_run_id=CAST(:run AS uuid)
              AND mv.status NOT IN ('rejected','retired') AND mv.lineage_status='resolved'
        """), {"version": base["model_version_id"], "run": base["training_run_id"]}).mappings().one_or_none()
        if (row is None or row["artifact_status"] != "available"
                or (row["checksum"], row["file_size_bytes"]) != (base["checkpoint"]["sha256"], base["checkpoint"]["bytes"])):
            raise CampaignError("BASE_MODEL_CHECKPOINT_INVALID")
        dependencies = registered_dependencies(c, base["training_run_id"], {"dependencies": base["dependencies"]})
    try:
        checkpoint = verified_file({"path": str(local_scientific_path(row["path"])),
                                    "sha256": row["checksum"], "bytes": row["file_size_bytes"]})
    except (ValueError, OSError):
        raise CampaignError("BASE_MODEL_CHECKPOINT_INVALID") from None
    return {"checkpoint": checkpoint, "dependencies": dependencies}


def device():
    """Apple GPU only: local TRAIN uses the whole local accelerator, never a silent CPU fallback."""
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "0")
    import torch

    from ..campaigns.contracts import CampaignError

    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") != "0" or not torch.backends.mps.is_available():
        raise CampaignError("TORCH_MPS_REQUIRED")
    return torch.device("mps")


def build(files):
    """(classifier, eval transform) on CPU; the caller moves it to its device."""
    import torch

    from .openclip_inference import create_model

    model, transform, _, _ = create_model(files["checkpoint"]["path"], {"dependencies": files["dependencies"]},
                                          files["checkpoint"]["sha256"])

    class BiomedCLIPBinary(torch.nn.Module):
        def __init__(self, visual):
            super().__init__()
            self.visual = visual
            self.head = torch.nn.Linear(512, 1)

        def embed(self, images):
            return torch.nn.functional.normalize(self.visual(images), dim=-1)

        def forward(self, images):
            return self.head(self.embed(images))  # logits; sigmoid gives the parasitized score

    return BiomedCLIPBinary(model.visual), transform


def trainable_names(model, fine_tune_layers):
    """Head always; the last ``fine_tune_layers`` ViT blocks (12 = total) with norm and projection."""
    from ..campaigns.contracts import CampaignError

    if type(fine_tune_layers) is not int or not 0 <= fine_tune_layers <= VIT_BLOCKS:
        raise CampaignError("INVALID_FINE_TUNE_LAYERS")
    blocks = {f"visual.trunk.blocks.{i}." for i in range(VIT_BLOCKS - fine_tune_layers, VIT_BLOCKS)}
    names = [n for n, _ in model.named_parameters()
             if n.startswith("head.") or (fine_tune_layers and (n in TOP_PARAMETERS or any(n.startswith(b) for b in blocks)))]
    if fine_tune_layers == VIT_BLOCKS:  # total: patch embedding, tokens and positions as well
        names = [n for n, _ in model.named_parameters()]
    return names


def set_trainable(model, names):
    selected = set(names)
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(name in selected)
    return [n for n, p in model.named_parameters() if p.requires_grad]


def save_checkpoint(path, model, names, identity):
    """Exclusive creation and fsync, then an atomic link; never overwrites an epoch artifact."""
    import torch

    from ..campaigns.contracts import CampaignError

    path = Path(path)
    if path.exists():
        raise CampaignError("ARTIFACT_ALREADY_EXISTS")
    partial = path.with_name(path.name + ".partial")
    parameters = dict(model.named_parameters())
    payload = {"schema": CHECKPOINT_SCHEMA, "identity": identity,
               "state": {n: parameters[n].detach().to("cpu").clone() for n in names}}
    with partial.open("xb") as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(partial, path)  # refuses an existing destination, unlike rename
    partial.unlink()


def load_classifier(path, contract, connection=None):
    """Base plus the trained parameters of a checkpoint, in eval mode on CPU."""
    import torch

    from ..campaigns.contracts import CampaignError

    payload = torch.load(Path(path), map_location="cpu", weights_only=True)
    base = contract["external"]["base_model"]
    if (payload.get("schema") != CHECKPOINT_SCHEMA or payload["identity"].get("base_model") != base
            or payload["identity"].get("architecture") != contract["architecture"]):
        raise CampaignError("CHECKPOINT_IDENTITY_CONFLICT")
    model, transform = build(base_files(base, connection))
    parameters = dict(model.named_parameters())
    state = payload["state"]
    if not any(n.startswith("head.") for n in state) or not set(state) <= set(parameters):
        raise CampaignError("CHECKPOINT_OUTPUT_CONTRACT_CONFLICT")
    with torch.no_grad():
        for name, value in state.items():
            if parameters[name].shape != value.shape:
                raise CampaignError("CHECKPOINT_OUTPUT_CONTRACT_CONFLICT")
            parameters[name].copy_(value)
    return model.eval(), transform


def torch_loader(path, contract):
    """verify_session loader: the selected checkpoint reconstructs a (N, 1) parasitized score."""
    import torch

    from ..campaigns.contracts import CampaignError

    model, _ = load_classifier(path, contract)
    height, width = contract["input"]["shape"][1:3]
    with torch.inference_mode():
        output = torch.sigmoid(model(torch.zeros((1, 3, height, width))))
    if tuple(output.shape) != (1, 1) or not torch.isfinite(output).all():
        raise CampaignError("CHECKPOINT_OUTPUT_CONTRACT_CONFLICT")


class BiomedCLIPClassifier:
    """Cell-classification predict interface: (N, 1) sigmoid parasitized score on CPU."""

    def __init__(self, checkpoint, preprocessing, architecture):
        contract = {"architecture": architecture, "external": preprocessing}
        self.model, self.transform = load_classifier(checkpoint, contract)
        self.input_shape = (None, 224, 224, 3)
        self.output_shape = (None, 1)
        self.device = "cpu"

    def predict(self, batch, verbose=0):
        import numpy as np
        import torch

        values = np.asarray(batch, dtype=np.float32)
        if values.ndim != 4:
            raise ValueError("Expected a batch of cell images")
        if values.shape[-1] == 3:  # technical smoke input: NHWC, through the same original transform
            from PIL import Image
            tensors = torch.stack([self.transform(Image.fromarray(np.uint8(value))) for value in values])
        else:
            tensors = torch.from_numpy(values)
        with torch.inference_mode():
            result = torch.sigmoid(self.model(tensors)).numpy()
        if result.shape != (len(values), 1) or not np.isfinite(result).all():
            raise ValueError("Invalid BiomedCLIP head scores")
        return result
