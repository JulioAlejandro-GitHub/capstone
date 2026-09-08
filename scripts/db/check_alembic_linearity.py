#!/usr/bin/env python3
"""Verifica que el árbol de revisiones Alembic del repo sea una única línea recta.

Todo se deriva del ScriptDirectory en disco (alembic/versions/): no hay ningún head
hardcodeado, ni aquí ni en el YAML de CI. El check protege exactamente dos propiedades,
las mismas que protegía el assert inline anterior en .github/workflows/ci.yml:

  1. Un único head (no hay heads divergentes / múltiples puntas).
  2. Historial lineal: ningún branch point ni merge point en todo el árbol.

Si alguien introduce una bifurcación real (dos heads simultáneos, un branch point o un
merge point), el check falla con un mensaje accionable: lista los heads con su archivo, o
identifica la revisión exacta (id + archivo) que rompe la linealidad.

Uso:
  * CLI:      python scripts/db/check_alembic_linearity.py
  * Makefile: make check-alembic-linearity
  * import:   from check_alembic_linearity import resolve_linear_head
              (lo usan scripts/db/purge.py y scripts/storage/reset_smear_analysis.py
               para derivar el head esperado en runtime en vez de hardcodearlo)
"""
from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import Script, ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALEMBIC_INI = REPO_ROOT / "alembic.ini"


class AlembicLinearityError(RuntimeError):
    """El árbol de revisiones no es una única línea recta."""


def load_script_directory(alembic_ini: Path | None = None) -> ScriptDirectory:
    """Construye un ScriptDirectory a partir de un alembic.ini, independiente del cwd."""
    ini_path = Path(alembic_ini) if alembic_ini is not None else DEFAULT_ALEMBIC_INI
    config = Config(str(ini_path))
    script_location = config.get_main_option("script_location") or "alembic"
    if not Path(script_location).is_absolute():
        script_location = str((ini_path.parent / script_location).resolve())
    config.set_main_option("script_location", script_location)
    return ScriptDirectory.from_config(config)


def _describe(script: ScriptDirectory, revision: str) -> str:
    """'20260901_01 (alembic/versions/20260901_01_....py)' para mensajes accionables."""
    try:
        obj = script.get_revision(revision)
    except Exception:  # revisión colgante referenciada pero inexistente
        return f"{revision} (archivo no encontrado)"
    try:
        rel = Path(obj.path).resolve().relative_to(REPO_ROOT)
        location = str(rel)
    except ValueError:
        location = obj.path
    return f"{revision} ({location})"


def check_linear_history(script: ScriptDirectory) -> str:
    """Devuelve el head único si el historial es lineal; si no, lanza AlembicLinearityError.

    Deriva el head del propio ScriptDirectory. No compara contra ningún valor esperado:
    la garantía es "un único head lineal", no "el head es tal valor".
    """
    revisions: list[Script] = list(script.walk_revisions())
    if not revisions:
        raise AlembicLinearityError(
            "No se encontraron revisiones Alembic en alembic/versions/."
        )

    heads = list(script.get_heads())
    if len(heads) != 1:
        listed = "\n".join(f"  - {_describe(script, head)}" for head in sorted(heads))
        raise AlembicLinearityError(
            f"Se esperaba un único head Alembic; se encontraron {len(heads)}:\n{listed}\n"
            "Hay ramas divergentes. Reconcilia el historial a una sola línea "
            "(rebase de las migraciones nuevas sobre el head real) antes de continuar."
        )

    branch_points = [rev for rev in revisions if rev.is_branch_point]
    merge_points = [rev for rev in revisions if rev.is_merge_point]

    problems: list[str] = []
    for rev in branch_points:
        children = ", ".join(_describe(script, child) for child in sorted(rev.nextrev))
        problems.append(
            f"branch point: {_describe(script, rev.revision)} es down_revision de "
            f"{len(rev.nextrev)} revisiones: [{children}]"
        )
    for rev in merge_points:
        down = rev.down_revision
        parents = down if isinstance(down, (tuple, list)) else (down,)
        listed = ", ".join(_describe(script, parent) for parent in parents)
        problems.append(
            f"merge point: {_describe(script, rev.revision)} desciende de "
            f"{len(parents)} revisiones: [{listed}]"
        )

    if problems:
        raise AlembicLinearityError(
            "El historial Alembic no es lineal:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
        )

    return heads[0]


def resolve_linear_head(alembic_ini: Path | None = None) -> str:
    """Carga el ScriptDirectory del repo y devuelve el head único lineal.

    Punto de entrada para consumidores que necesitan "el head del repo" derivado en
    runtime (guards de operaciones destructivas). Lanza AlembicLinearityError si el
    historial no es una única línea recta.
    """
    return check_linear_history(load_script_directory(alembic_ini))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    alembic_ini = Path(args[0]) if args else None
    try:
        script = load_script_directory(alembic_ini)
        head = check_linear_history(script)
    except AlembicLinearityError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # ini ausente, script_location inválido, etc.
        print(f"FAIL: no se pudo cargar el ScriptDirectory de Alembic: {error}", file=sys.stderr)
        return 1
    count = len(list(script.walk_revisions()))
    print(f"OK: historial Alembic lineal, {count} revisiones, head único {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
