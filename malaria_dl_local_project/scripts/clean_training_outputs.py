import argparse
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_CONFIRMATION = "DELETE_OUTPUTS"
ARTIFACT_SUFFIXES = {
    ".keras",
    ".h5",
    ".joblib",
    ".pkl",
    ".csv",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}
ALWAYS_INCLUDED_DIRS = ["custom_cnn", "vgg16"]
OPTIONAL_DIRS = {
    "include_svm": "cnn_features_svm",
    "include_ensemble": "ensemble",
    "include_explainability": "explainability",
    "include_predictions": "predictions",
}
BASE_STRUCTURE = [
    "custom_cnn",
    "vgg16",
    "cnn_features_svm",
    "ensemble",
    "explainability",
    "explainability/gradcam",
    "explainability/lime",
    "explainability/shap",
    "explainability/external_predictions",
    "explainability/external_predictions/gradcam",
    "predictions",
]


def default_options() -> dict:
    return {
        "include_explainability": True,
        "include_predictions": True,
        "include_svm": True,
        "include_ensemble": True,
    }


def validate_outputs_dir(outputs_dir: Path) -> None:
    if outputs_dir is None or str(outputs_dir).strip() in {"", ".", "..", "/"}:
        raise ValueError(f"outputs-dir peligroso o inválido: {outputs_dir!r}")

    resolved = Path(outputs_dir).expanduser().resolve()
    project_root = PROJECT_ROOT.resolve()

    if resolved == project_root:
        raise ValueError("outputs-dir no puede ser la raíz del proyecto.")
    if resolved == Path("/"):
        raise ValueError("outputs-dir no puede ser '/'.")
    if project_root not in [resolved, *resolved.parents]:
        raise ValueError(f"outputs-dir debe estar dentro del proyecto: {project_root}")
    if not resolved.exists():
        raise FileNotFoundError(f"No existe outputs-dir: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"outputs-dir no es un directorio: {resolved}")
    if resolved.is_symlink():
        raise ValueError(f"outputs-dir no puede ser un symlink: {resolved}")


def target_directories(outputs_dir: Path, options: dict) -> list[Path]:
    selected = [outputs_dir / name for name in ALWAYS_INCLUDED_DIRS]
    for option_name, dirname in OPTIONAL_DIRS.items():
        if options.get(option_name, True):
            selected.append(outputs_dir / dirname)
    return [path for path in selected if path.exists()]


def is_artifact_file(path: Path) -> bool:
    if path.name == ".gitkeep":
        return False
    if path.name == ".DS_Store":
        return True
    return path.suffix.lower() in ARTIFACT_SUFFIXES


def path_is_inside(path: Path, parent: Path) -> bool:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    return resolved_parent == resolved_path or resolved_parent in resolved_path.parents


def collect_training_artifacts(outputs_dir: Path, options: dict) -> list[Path]:
    validate_outputs_dir(outputs_dir)
    outputs_dir = Path(outputs_dir).expanduser().resolve()

    artifacts = set()
    for target_dir in target_directories(outputs_dir, options):
        if target_dir.is_symlink():
            continue

        for root, dirs, files in os.walk(target_dir, topdown=True, followlinks=False):
            root_path = Path(root)
            dirs[:] = [
                dirname
                for dirname in dirs
                if not (root_path / dirname).is_symlink()
            ]

            for filename in files:
                file_path = root_path / filename
                if file_path.is_symlink():
                    continue
                if is_artifact_file(file_path):
                    if not path_is_inside(file_path, outputs_dir):
                        raise ValueError(f"Ruta fuera de outputs detectada: {file_path}")
                    artifacts.add(file_path)

            if root_path != target_dir and path_is_inside(root_path, outputs_dir):
                artifacts.add(root_path)

    return sorted(artifacts, key=lambda path: (path.is_file(), len(path.parts), str(path)))


def create_outputs_backup(outputs_dir: Path, backup_dir: Path) -> Path:
    validate_outputs_dir(outputs_dir)
    outputs_dir = Path(outputs_dir).expanduser().resolve()
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"outputs_before_clean_{timestamp}.tar.gz"

    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(outputs_dir, arcname=outputs_dir.name, recursive=True)

    return backup_path


def delete_artifacts(paths: list[Path], execute: bool) -> dict:
    files_deleted = 0
    dirs_deleted = 0
    skipped = []

    if not execute:
        return {
            "files_deleted": 0,
            "dirs_deleted": 0,
            "skipped": skipped,
        }

    files = [path for path in paths if path.is_file()]
    dirs = sorted(
        [path for path in paths if path.is_dir()],
        key=lambda path: len(path.parts),
        reverse=True,
    )

    for path in files:
        if path.is_symlink():
            skipped.append(str(path))
            continue
        path.unlink()
        files_deleted += 1

    for path in dirs:
        if path.is_symlink():
            skipped.append(str(path))
            continue
        try:
            path.rmdir()
            dirs_deleted += 1
        except OSError:
            skipped.append(str(path))

    return {
        "files_deleted": files_deleted,
        "dirs_deleted": dirs_deleted,
        "skipped": skipped,
    }


def recreate_outputs_structure(outputs_dir: Path) -> None:
    outputs_dir = Path(outputs_dir).expanduser().resolve()
    outputs_dir.mkdir(parents=True, exist_ok=True)
    for relative_dir in BASE_STRUCTURE:
        directory = outputs_dir / relative_dir
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")


def clean_training_outputs(
    outputs_dir: Path,
    execute: bool,
    confirm: str | None,
    backup_before: bool,
    backup_dir: Path,
    keep_directory_structure: bool,
    options: dict | None = None,
    verbose: bool = False,
) -> dict:
    if execute and confirm != SAFE_CONFIRMATION:
        raise ValueError(
            f"Confirmación inválida. Para ejecutar use --confirm {SAFE_CONFIRMATION}."
        )

    options = {**default_options(), **(options or {})}
    outputs_dir = Path(outputs_dir).expanduser().resolve()
    validate_outputs_dir(outputs_dir)
    artifacts = collect_training_artifacts(outputs_dir, options)

    backup_path = None
    if execute and backup_before:
        backup_path = create_outputs_backup(outputs_dir, backup_dir)

    delete_result = delete_artifacts(artifacts, execute=execute)
    if execute and keep_directory_structure:
        recreate_outputs_structure(outputs_dir)

    if verbose:
        for path in artifacts:
            print(path)

    return {
        "mode": "EXECUTE" if execute else "DRY RUN",
        "outputs_dir": str(outputs_dir),
        "backup_path": None if backup_path is None else str(backup_path),
        "artifacts": [str(path) for path in artifacts],
        "artifacts_count": len(artifacts),
        "files_deleted": delete_result["files_deleted"],
        "dirs_deleted": delete_result["dirs_deleted"],
        "skipped": delete_result["skipped"],
        "structure_recreated": bool(execute and keep_directory_structure),
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Elimina entrenamientos, modelos y artefactos generados en outputs/."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Modo seguro por defecto.")
    mode.add_argument("--execute", action="store_true", help="Ejecuta eliminación real.")
    parser.add_argument("--confirm", default=None, help=f"Debe ser {SAFE_CONFIRMATION}.")
    parser.add_argument("--outputs-dir", default="outputs")
    parser.add_argument("--backup-before", action="store_true")
    parser.add_argument("--backup-dir", default="backups/outputs")
    parser.add_argument("--keep-directory-structure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-explainability", dest="include_explainability", action="store_true", default=True)
    parser.add_argument("--no-explainability", dest="include_explainability", action="store_false")
    parser.add_argument("--include-predictions", dest="include_predictions", action="store_true", default=True)
    parser.add_argument("--no-predictions", dest="include_predictions", action="store_false")
    parser.add_argument("--include-svm", dest="include_svm", action="store_true", default=True)
    parser.add_argument("--no-svm", dest="include_svm", action="store_false")
    parser.add_argument("--include-ensemble", dest="include_ensemble", action="store_true", default=True)
    parser.add_argument("--no-ensemble", dest="include_ensemble", action="store_false")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def print_summary(result: dict) -> None:
    print(f"Modo: {result['mode']}")
    print(f"Outputs dir: {result['outputs_dir']}")
    if result.get("backup_path"):
        print(f"Backup: creado en {result['backup_path']}")
    elif result["mode"] == "EXECUTE":
        print("Backup: no solicitado")
    else:
        print("Backup: no creado en dry-run")

    if result["mode"] == "DRY RUN":
        print("Archivos y directorios que serían eliminados:")
        for path in result["artifacts"]:
            print(f"- {path}")
        print("No se eliminó ningún archivo. Para ejecutar realmente:")
        print(f"python scripts/clean_training_outputs.py --execute --confirm {SAFE_CONFIRMATION}")
        return

    print(f"Archivos eliminados: {result['files_deleted']}")
    print(f"Directorios eliminados: {result['dirs_deleted']}")
    print(f"Estructura base recreada: {'sí' if result['structure_recreated'] else 'no'}")
    if result["skipped"]:
        print("Rutas omitidas:")
        for path in result["skipped"]:
            print(f"- {path}")
    print("Estado: limpieza de entrenamientos completada correctamente")


def main():
    args = parse_args()
    options = {
        "include_explainability": args.include_explainability,
        "include_predictions": args.include_predictions,
        "include_svm": args.include_svm,
        "include_ensemble": args.include_ensemble,
    }
    try:
        result = clean_training_outputs(
            outputs_dir=Path(args.outputs_dir),
            execute=bool(args.execute),
            confirm=args.confirm,
            backup_before=bool(args.backup_before),
            backup_dir=Path(args.backup_dir),
            keep_directory_structure=bool(args.keep_directory_structure),
            options=options,
            verbose=bool(args.verbose),
        )
        print_summary(result)
    except Exception as exc:
        print("Error limpiando outputs de entrenamiento.")
        print(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
