"""Strict parser for NIH/NLM ThinBloodSmearsPf ``Polygon Set`` ground-truth files.

Format verified against the official ReadMe.pdf and all 165 real GT files:

```text
<entry_count>,<image_width>,<image_height>
<cell_no>,<cell_type>,<comment>,Polygon,<n_points>,x1,y1,x2,y2,...
```

The parser preserves the original polygons; it never converts, clips or rasterizes.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


RBC_LABELS = frozenset({"Uninfected", "Parasitized"})
WBC_LABELS = frozenset({"White_Blood_Cell"})
KNOWN_LABELS = RBC_LABELS | WBC_LABELS
POLYGON_SHAPE = "Polygon"


class PolygonParseError(ValueError):
    """A GT file violates the Polygon Set contract; ``code`` is stable for reports."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class PolygonEntry:
    cell_id: str
    label: str
    comment: str
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class PolygonAnnotation:
    declared_count: int
    image_width: int
    image_height: int
    polygons: tuple[PolygonEntry, ...]

    @property
    def label_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.label for item in self.polygons).items()))

    @property
    def rbc_count(self) -> int:
        return sum(item.label in RBC_LABELS for item in self.polygons)

    @property
    def wbc_count(self) -> int:
        return sum(item.label in WBC_LABELS for item in self.polygons)


def _number(value: str, where: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise PolygonParseError("NON_NUMERIC_COORDINATE", f"{where}: {value!r}") from None
    if not math.isfinite(number):
        raise PolygonParseError("NON_NUMERIC_COORDINATE", f"{where}: {value!r}")
    return number


def _integer(value: str, code: str, where: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        raise PolygonParseError(code, f"{where}: {value!r}") from None


def _shoelace_area(points: tuple[tuple[float, float], ...]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def parse_polygon_text(
    content: str, *, image_size: tuple[int, int] | None = None
) -> PolygonAnnotation:
    """Parse GT text; ``image_size`` (width, height) enables header and bounds checks."""
    lines = [line.strip() for line in content.splitlines()]
    if not any(lines):
        raise PolygonParseError("GT_EMPTY", "annotation has no content")
    header = lines[0].split(",")
    if len(header) != 3:
        raise PolygonParseError("INVALID_HEADER", f"expected 3 fields, got {lines[0]!r}")
    declared = _integer(header[0], "INVALID_HEADER", "entry count")
    width = _integer(header[1], "INVALID_HEADER", "image width")
    height = _integer(header[2], "INVALID_HEADER", "image height")
    if declared < 0 or width <= 0 or height <= 0:
        raise PolygonParseError("INVALID_HEADER", lines[0])
    if image_size is not None and (width, height) != tuple(image_size):
        raise PolygonParseError(
            "HEADER_IMAGE_SIZE_MISMATCH", f"header={width}x{height}, image={image_size}"
        )

    polygons: list[PolygonEntry] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(lines[1:], start=2):
        if not line:
            continue
        fields = line.split(",")
        where = f"line {line_number}"
        if len(fields) < 5:
            raise PolygonParseError("INVALID_ROW", f"{where}: too few fields")
        cell_id, label, comment, shape = (item.strip() for item in fields[:4])
        if shape != POLYGON_SHAPE:
            raise PolygonParseError("UNSUPPORTED_SHAPE", f"{where}: {shape!r}")
        if label not in KNOWN_LABELS:
            raise PolygonParseError("UNKNOWN_LABEL", f"{where}: {label!r}")
        if not cell_id or cell_id in seen_ids:
            raise PolygonParseError("DUPLICATE_CELL_ID", f"{where}: {cell_id!r}")
        seen_ids.add(cell_id)
        point_count = _integer(fields[4], "INVALID_ROW", f"{where} point count")
        coordinates = fields[5:]
        if point_count < 0 or len(coordinates) != 2 * point_count:
            raise PolygonParseError(
                "POINT_COUNT_MISMATCH",
                f"{where}: declared {point_count} points, got {len(coordinates)} values",
            )
        values = [_number(value, where) for value in coordinates]
        points = tuple(zip(values[0::2], values[1::2]))
        if len(set(points)) < 3 or _shoelace_area(points) <= 0:
            raise PolygonParseError("DEGENERATE_POLYGON", f"{where}: cell {cell_id}")
        if any(x < 0 or y < 0 or x > width or y > height for x, y in points):
            raise PolygonParseError("COORDINATE_OUT_OF_BOUNDS", f"{where}: cell {cell_id}")
        polygons.append(PolygonEntry(cell_id, label, comment, points))
    if declared != len(polygons):
        raise PolygonParseError(
            "ENTRY_COUNT_MISMATCH", f"header declares {declared}, parsed {len(polygons)}"
        )
    return PolygonAnnotation(declared, width, height, tuple(polygons))


def parse_polygon_file(
    path: Path, *, image_size: tuple[int, int] | None = None
) -> PolygonAnnotation:
    if not path.is_file():
        raise PolygonParseError("GT_MISSING", str(path))
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise PolygonParseError("INVALID_ENCODING", f"{path}: {error}") from None
    return parse_polygon_text(content, image_size=image_size)
