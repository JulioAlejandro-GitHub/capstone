import pytest

from malaria_split.sources.polygon_set import (
    PolygonParseError,
    parse_polygon_file,
    parse_polygon_text,
)
from tests.smear_fixtures import gt_text

# Verbatim example row from the official ReadMe.pdf.
README_ROW = (
    "1-1,Uninfected,No_comment,Polygon,11,2414.05,1707,2416.4,1669.85,2431.5,1646.55,"
    "2455.9,1630.3,2488.45,1629.05,2516.4,1644.25,2537.3,1681.45,2533.8,1715.2,"
    "2505.9,1743.05,2455.9,1745.4,2425.7,1725.65"
)


def _code(content, **kwargs):
    with pytest.raises(PolygonParseError) as error:
        parse_polygon_text(content, **kwargs)
    return error.value.code


def test_valid_official_example_is_preserved_exactly():
    annotation = parse_polygon_text(f"1,5312,2988\n{README_ROW}", image_size=(5312, 2988))
    assert (annotation.declared_count, annotation.image_width, annotation.image_height) == (
        1, 5312, 2988
    )
    polygon = annotation.polygons[0]
    assert polygon.cell_id == "1-1" and polygon.label == "Uninfected"
    assert len(polygon.points) == 11
    assert polygon.points[0] == (2414.05, 1707.0)
    assert polygon.points[-1] == (2425.7, 1725.65)


def test_label_counts_distinguish_rbc_and_wbc():
    annotation = parse_polygon_text(
        gt_text(["Uninfected", "Parasitized", "Parasitized", "White_Blood_Cell"])
    )
    assert annotation.label_counts == {
        "Parasitized": 2, "Uninfected": 1, "White_Blood_Cell": 1
    }
    assert (annotation.rbc_count, annotation.wbc_count) == (3, 1)


def test_missing_file(tmp_path):
    with pytest.raises(PolygonParseError) as error:
        parse_polygon_file(tmp_path / "absent.txt")
    assert error.value.code == "GT_MISSING"


@pytest.mark.parametrize("content", ["", "\n\n", "   \n"])
def test_empty_file(content):
    assert _code(content) == "GT_EMPTY"


@pytest.mark.parametrize("header", ["1,64", "x,64,48", "1,0,48", "1,64,48,9"])
def test_corrupt_header(header):
    assert _code(f"{header}\n" + gt_text(["Uninfected"]).split("\n", 1)[1]) == "INVALID_HEADER"


def test_corrupt_row_and_unsupported_values():
    assert _code("1,64,48\n1-1,Uninfected") == "INVALID_ROW"
    assert _code("1,64,48\n1-1,Uninfected,No_comment,Point,1,3,4") == "UNSUPPORTED_SHAPE"
    assert _code("1,64,48\n1-1,Platelet,No_comment,Polygon,3,1,1,5,1,5,5") == "UNKNOWN_LABEL"
    assert _code("1,64,48\n1-1,Uninfected,No_comment,Polygon,4,1,1,5,1,5,5") == (
        "POINT_COUNT_MISMATCH"
    )


def test_non_numeric_coordinates():
    assert _code("1,64,48\n1-1,Uninfected,No_comment,Polygon,3,1,a,5,1,5,5") == (
        "NON_NUMERIC_COORDINATE"
    )
    assert _code("1,64,48\n1-1,Uninfected,No_comment,Polygon,3,1,nan,5,1,5,5") == (
        "NON_NUMERIC_COORDINATE"
    )


@pytest.mark.parametrize("points", [
    "2,1,1,5,5",              # fewer than three vertices
    "3,1,1,1,1,5,5",          # repeated vertex leaves two distinct points
    "3,1,1,2,2,3,3",          # collinear: zero area
])
def test_degenerate_polygon(points):
    assert _code(f"1,64,48\n1-1,Uninfected,No_comment,Polygon,{points}") == "DEGENERATE_POLYGON"


def test_coordinates_outside_image():
    assert _code("1,64,48\n1-1,Uninfected,No_comment,Polygon,3,1,1,65,1,5,5") == (
        "COORDINATE_OUT_OF_BOUNDS"
    )
    assert _code("1,64,48\n1-1,Uninfected,No_comment,Polygon,3,-0.5,1,5,1,5,5") == (
        "COORDINATE_OUT_OF_BOUNDS"
    )


def test_header_must_match_image_and_entry_count():
    assert _code(gt_text(["Uninfected"]), image_size=(65, 48)) == "HEADER_IMAGE_SIZE_MISMATCH"
    content = gt_text(["Uninfected", "Uninfected"]).replace("2,64,48", "3,64,48")
    assert _code(content) == "ENTRY_COUNT_MISMATCH"


def test_duplicate_cell_id_is_ambiguous():
    row = "1-1,Uninfected,No_comment,Polygon,3,1,1,5,1,5,5"
    assert _code(f"2,64,48\n{row}\n{row}") == "DUPLICATE_CELL_ID"
