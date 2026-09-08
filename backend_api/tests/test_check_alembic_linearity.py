"""Tests unitarios de scripts/db/check_alembic_linearity.py.

Se ejercita contra ScriptDirectory de fixture construidos en tmp_path (no contra el repo
real), cubriendo: caso lineal con un head (pasa), dos heads (falla), un branch point
intermedio (falla) y un merge point (falla). Un único test toca el árbol real del repo
para confirmar que el mecanismo deriva el head sin hardcodeo.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "scripts/db/check_alembic_linearity.py",
    Path("/app/scripts/db/check_alembic_linearity.py"),
)
SCRIPT = next((path for path in _CANDIDATES if path.exists()), _CANDIDATES[0])
if not SCRIPT.exists():
    pytest.skip(
        "scripts/db/check_alembic_linearity.py no disponible (reconstruya la imagen)",
        allow_module_level=True,
    )
SPEC = importlib.util.spec_from_file_location("check_alembic_linearity", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_repo(tmp_path: Path, revisions: dict[str, str | tuple[str, ...] | None]) -> Path:
    """Crea un alembic.ini + alembic/versions/ de fixture y devuelve la ruta del ini.

    `revisions` mapea id -> down_revision (None, un id, o tupla de ids para un merge).
    """
    versions = tmp_path / "alembic" / "versions"
    versions.mkdir(parents=True)
    for rev, down in revisions.items():
        if down is None:
            down_literal = "None"
        elif isinstance(down, tuple):
            down_literal = repr(down)
        else:
            down_literal = repr(down)
        (versions / f"{rev}_fixture.py").write_text(
            f'revision = {rev!r}\n'
            f'down_revision = {down_literal}\n'
            'branch_labels = None\n'
            'depends_on = None\n\n'
            'def upgrade():\n    pass\n\n'
            'def downgrade():\n    pass\n',
            encoding="utf-8",
        )
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = alembic\n", encoding="utf-8")
    return ini


def test_linear_single_head_passes(tmp_path):
    ini = _make_repo(tmp_path, {"r1": None, "r2": "r1", "r3": "r2"})
    assert mod.resolve_linear_head(ini) == "r3"


def test_multiple_heads_fails_and_lists_them(tmp_path):
    # Dos raíces independientes => dos heads sin branch point.
    ini = _make_repo(tmp_path, {"alpha": None, "omega": None})
    with pytest.raises(mod.AlembicLinearityError) as excinfo:
        mod.resolve_linear_head(ini)
    message = str(excinfo.value)
    assert "único head" in message
    assert "alpha" in message and "omega" in message
    assert "alpha_fixture.py" in message


def test_branch_point_fails_and_identifies_revision(tmp_path):
    ini = _make_repo(
        tmp_path,
        {"root": None, "left": "root", "right": "root", "merge": ("left", "right")},
    )
    with pytest.raises(mod.AlembicLinearityError) as excinfo:
        mod.resolve_linear_head(ini)
    message = str(excinfo.value)
    assert "branch point" in message
    assert "root (" in message and "root_fixture.py" in message
    assert "left" in message and "right" in message


def test_merge_point_fails_and_identifies_revision(tmp_path):
    ini = _make_repo(
        tmp_path,
        {"root": None, "left": "root", "right": "root", "merge": ("left", "right")},
    )
    with pytest.raises(mod.AlembicLinearityError) as excinfo:
        mod.resolve_linear_head(ini)
    message = str(excinfo.value)
    assert "merge point" in message
    assert "merge (" in message and "merge_fixture.py" in message


def test_empty_versions_dir_fails(tmp_path):
    ini = _make_repo(tmp_path, {})
    with pytest.raises(mod.AlembicLinearityError):
        mod.resolve_linear_head(ini)


def test_cli_main_reports_ok_on_linear_fixture(tmp_path, capsys):
    ini = _make_repo(tmp_path, {"r1": None, "r2": "r1"})
    assert mod.main([str(ini)]) == 0
    assert "head único r2" in capsys.readouterr().out


def test_cli_main_returns_nonzero_on_branch(tmp_path, capsys):
    ini = _make_repo(tmp_path, {"a": None, "b": "a", "c": "a", "d": ("b", "c")})
    assert mod.main([str(ini)]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_real_repo_history_is_linear_and_head_is_derived():
    """El árbol real del repo pasa y el head sale del ScriptDirectory, sin constante."""
    ini = REPO_ROOT / "alembic.ini"
    script = mod.load_script_directory(ini)
    head = mod.check_linear_history(script)
    assert head == script.get_heads()[0]
    assert head and isinstance(head, str)
