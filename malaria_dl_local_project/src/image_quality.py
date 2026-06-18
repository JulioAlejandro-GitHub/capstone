from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError


def _blur_score(gray_image):
    gray_image = np.asarray(gray_image, dtype=np.float32)
    if gray_image.shape[0] < 3 or gray_image.shape[1] < 3:
        return 0.0

    laplacian = (
        -4.0 * gray_image[1:-1, 1:-1]
        + gray_image[:-2, 1:-1]
        + gray_image[2:, 1:-1]
        + gray_image[1:-1, :-2]
        + gray_image[1:-1, 2:]
    )
    return float(np.var(laplacian))


def check_image_quality(image_path, min_width=64, min_height=64):
    path = Path(image_path).expanduser()
    result = {
        "passed": False,
        "fatal": False,
        "warnings": [],
        "metrics": {},
    }

    if not path.exists():
        result["fatal"] = True
        result["warnings"].append(f"No existe la imagen: {path}")
        return result
    if not path.is_file():
        result["fatal"] = True
        result["warnings"].append(f"La ruta no corresponde a un archivo: {path}")
        return result

    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            width, height = image.size
            image_array = np.asarray(image, dtype=np.float32) / 255.0
    except (UnidentifiedImageError, OSError) as exc:
        result["fatal"] = True
        result["warnings"].append(f"No se pudo abrir como imagen: {exc}")
        return result

    gray = np.mean(image_array, axis=2)
    brightness_mean = float(np.mean(gray))
    contrast_std = float(np.std(gray))
    blur_score = _blur_score(gray)

    result["metrics"] = {
        "width": int(width),
        "height": int(height),
        "channels": int(image_array.shape[2]),
        "brightness_mean": brightness_mean,
        "contrast_std": contrast_std,
        "blur_score": blur_score,
    }

    if width < min_width or height < min_height:
        result["warnings"].append(
            f"Resolución baja: {width}x{height}. Mínimo recomendado: {min_width}x{min_height}."
        )
    if brightness_mean < 0.08:
        result["warnings"].append("Imagen muy oscura.")
    elif brightness_mean > 0.92:
        result["warnings"].append("Imagen muy brillante.")
    if contrast_std < 0.03:
        result["warnings"].append("Contraste muy bajo.")
    if blur_score < 0.0005:
        result["warnings"].append("Posible desenfoque o falta de detalle.")

    result["passed"] = not result["fatal"]
    return result
