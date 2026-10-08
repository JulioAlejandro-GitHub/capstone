"""Authenticated, bounded HTTP transport for the local execution plane."""
from __future__ import annotations

import io
import os
import secrets
import warnings
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from .inference import DEFAULT_CHECKPOINT, RUNTIME_VERSION, DetectionResponse, InferenceOptions, YoloRuntime


class RuntimeSettings(BaseModel):
    token: str = Field(min_length=32, repr=False)
    checkpoint: Path = DEFAULT_CHECKPOINT
    max_upload_bytes: int = Field(default=20_971_520, gt=0)
    max_image_pixels: int = Field(default=25_000_000, gt=0)

    @classmethod
    def from_env(cls) -> RuntimeSettings:
        return cls(token=os.environ.get("YOLO_RUNTIME_TOKEN", ""),
                   checkpoint=Path(os.environ.get("YOLO_RUNTIME_CHECKPOINT", str(DEFAULT_CHECKPOINT))),
                   max_upload_bytes=int(os.environ.get("YOLO_RUNTIME_MAX_UPLOAD_BYTES", "20971520")),
                   max_image_pixels=int(os.environ.get("YOLO_RUNTIME_MAX_IMAGE_PIXELS", "25000000")))


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str
    runtime_version: str
    checkpoint_sha256: str


def decode_image(data: bytes, max_pixels: int) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > max_pixels:
                    raise HTTPException(413, "IMAGE_PIXEL_LIMIT_EXCEEDED")
                if source.format not in {"JPEG", "PNG", "TIFF"} or getattr(source, "n_frames", 1) != 1:
                    raise HTTPException(415, "UNSUPPORTED_IMAGE_FORMAT")
                source.load()
                return source.copy()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(413, "IMAGE_PIXEL_LIMIT_EXCEEDED") from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(422, "INVALID_IMAGE") from None


def create_app(settings: RuntimeSettings | None = None,
               runtime_factory: Callable[[Path], YoloRuntime] = YoloRuntime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        selected = settings or RuntimeSettings.from_env()
        app.state.settings = selected
        app.state.runtime = runtime_factory(selected.checkpoint)
        yield
        del app.state.runtime

    app = FastAPI(title="Capstone YOLO Runtime", version=RUNTIME_VERSION, lifespan=lifespan)

    def authenticate(request: Request) -> None:
        expected = "Bearer " + request.app.state.settings.token
        supplied = request.headers.get("authorization", "")
        if not secrets.compare_digest(supplied.encode(), expected.encode()):
            raise HTTPException(401, "INVALID_RUNTIME_TOKEN", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        runtime = request.app.state.runtime
        return HealthResponse(status="ready", model_loaded=True, device="mps",
                              runtime_version=RUNTIME_VERSION, checkpoint_sha256=runtime.checkpoint_sha256)

    @app.post("/v1/detect", response_model=DetectionResponse, dependencies=[Depends(authenticate)],
              openapi_extra={"requestBody": {"required": True, "content": {
                  "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
    async def detect(request: Request, options: Annotated[InferenceOptions, Query()]) -> DetectionResponse:
        selected = request.app.state.settings
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > selected.max_upload_bytes:
                raise HTTPException(413, "IMAGE_UPLOAD_LIMIT_EXCEEDED")
            data.extend(chunk)
        image = await run_in_threadpool(decode_image, bytes(data), selected.max_image_pixels)
        try:
            return await run_in_threadpool(request.app.state.runtime.detect, image, options)
        except Exception:
            # Never expose image paths, tokens, or model internals in error bodies/logs.
            raise HTTPException(503, "YOLO_INFERENCE_FAILED") from None
        finally:
            image.close()

    return app
