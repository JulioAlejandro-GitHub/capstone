import hashlib
import mimetypes
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError


CAPSTONE_ROOT = Path(__file__).resolve().parents[2]
PREDICTION_UPLOAD_DIR = CAPSTONE_ROOT / "data" / "prediction_uploads"
ALLOWED_IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


@dataclass(frozen=True)
class StoredPredictionImage:
    source_path: Path
    stored_path: Path
    relative_path: str
    image_id: str
    original_filename: str
    stored_filename: str
    checksum_sha256: str
    mime_type: str | None
    file_size_bytes: int


def get_prediction_upload_dir():
    PREDICTION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return PREDICTION_UPLOAD_DIR


def relative_to_capstone(path):
    return path.resolve().relative_to(CAPSTONE_ROOT).as_posix()


def normalize_filename_part(value, default="image"):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_value).strip("._-")
    return cleaned or default


def validate_image_file(image_path):
    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")
    if not image_path.is_file():
        raise ValueError(f"La ruta no corresponde a un archivo: {image_path}")

    suffix = image_path.suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            "Extension de imagen no soportada. Usa una de estas: "
            f"{sorted(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    try:
        with Image.open(image_path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"El archivo no es una imagen valida: {image_path}") from exc


def compute_file_checksum(path):
    checksum = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def build_prediction_image_name(source_path, checksum_sha256):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_short = checksum_sha256[:6]
    stem = normalize_filename_part(source_path.stem)
    suffix = source_path.suffix.lower()
    return f"{timestamp}_{hash_short}_{stem}{suffix}"


def unique_destination_path(upload_dir, filename):
    destination = upload_dir / filename
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 1
    while True:
        candidate = upload_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def store_prediction_image(image_path, image_id=None):
    source_path = Path(image_path).expanduser().resolve()
    validate_image_file(source_path)

    checksum_sha256 = compute_file_checksum(source_path)
    upload_dir = get_prediction_upload_dir()
    filename = build_prediction_image_name(source_path, checksum_sha256)
    destination = unique_destination_path(upload_dir, filename)
    shutil.copy2(source_path, destination)

    stored_image_id = image_id or destination.stem
    stored_image_id = normalize_filename_part(stored_image_id, default=destination.stem)

    return StoredPredictionImage(
        source_path=source_path,
        stored_path=destination,
        relative_path=relative_to_capstone(destination),
        image_id=stored_image_id,
        original_filename=source_path.name,
        stored_filename=destination.name,
        checksum_sha256=checksum_sha256,
        mime_type=mimetypes.guess_type(destination.name)[0],
        file_size_bytes=destination.stat().st_size,
    )
