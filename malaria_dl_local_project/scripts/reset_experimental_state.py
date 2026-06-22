import argparse
from pathlib import Path

from clean_training_outputs import clean_training_outputs
from purge_db_data import purge_database_data


SAFE_CONFIRMATION = "RESET_EXPERIMENTS"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reinicia estado experimental: purga DB y limpia outputs/."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Modo seguro por defecto.")
    mode.add_argument("--execute", action="store_true", help="Ejecuta el reset real.")
    parser.add_argument("--confirm", default=None, help=f"Debe ser {SAFE_CONFIRMATION}.")
    parser.add_argument("--skip-db", action="store_true")
    parser.add_argument("--skip-outputs", action="store_true")
    parser.add_argument("--backup-before", action="store_true")
    parser.add_argument("--schema", default="public")
    parser.add_argument("--outputs-dir", default="outputs")
    parser.add_argument("--db-backup-dir", default="backups/db")
    parser.add_argument("--outputs-backup-dir", default="backups/outputs")
    parser.add_argument("--reseed", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def reset_experimental_state(
    execute: bool,
    confirm: str | None,
    skip_db: bool,
    skip_outputs: bool,
    backup_before: bool,
    schema: str,
    outputs_dir: Path,
    db_backup_dir: Path,
    outputs_backup_dir: Path,
    reseed: bool,
    verbose: bool = False,
) -> dict:
    if execute and confirm != SAFE_CONFIRMATION:
        raise ValueError(
            f"Confirmación inválida. Para ejecutar use --confirm {SAFE_CONFIRMATION}."
        )
    if skip_db and skip_outputs:
        raise ValueError("No hay acciones que ejecutar: --skip-db y --skip-outputs están activos.")

    results = {"mode": "EXECUTE" if execute else "DRY RUN"}
    if not skip_db:
        results["db"] = purge_database_data(
            execute=execute,
            confirm="PURGE_DB" if execute else None,
            schema=schema,
            backup_before=backup_before,
            backup_dir=db_backup_dir,
            reseed=reseed,
            verbose=verbose,
        )

    if not skip_outputs:
        results["outputs"] = clean_training_outputs(
            outputs_dir=outputs_dir,
            execute=execute,
            confirm="DELETE_OUTPUTS" if execute else None,
            backup_before=backup_before,
            backup_dir=outputs_backup_dir,
            keep_directory_structure=True,
            verbose=verbose,
        )

    return results


def print_summary(results: dict) -> None:
    print(f"Modo: {results['mode']}")
    if "db" in results:
        db = results["db"]
        print("DB:")
        print(f"- base: {db['database']}")
        print(f"- schema: {db['schema']}")
        print(f"- tablas: {db['tables_count']}")
        print(f"- backup: {db.get('backup_path') or 'no creado'}")
    else:
        print("DB: omitida")

    if "outputs" in results:
        outputs = results["outputs"]
        print("Outputs:")
        print(f"- ruta: {outputs['outputs_dir']}")
        print(f"- artefactos detectados: {outputs['artifacts_count']}")
        print(f"- archivos eliminados: {outputs['files_deleted']}")
        print(f"- directorios eliminados: {outputs['dirs_deleted']}")
        print(f"- backup: {outputs.get('backup_path') or 'no creado'}")
    else:
        print("Outputs: omitidos")

    if results["mode"] == "DRY RUN":
        print("No se ejecutó ningún cambio. Para ejecutar realmente:")
        print(
            "python scripts/reset_experimental_state.py "
            f"--execute --confirm {SAFE_CONFIRMATION} --backup-before"
        )
    else:
        print("Estado: reset experimental completado correctamente")


def main():
    args = parse_args()
    try:
        results = reset_experimental_state(
            execute=bool(args.execute),
            confirm=args.confirm,
            skip_db=bool(args.skip_db),
            skip_outputs=bool(args.skip_outputs),
            backup_before=bool(args.backup_before),
            schema=args.schema,
            outputs_dir=Path(args.outputs_dir),
            db_backup_dir=Path(args.db_backup_dir),
            outputs_backup_dir=Path(args.outputs_backup_dir),
            reseed=bool(args.reseed),
            verbose=bool(args.verbose),
        )
        print_summary(results)
    except Exception as exc:
        print("Error reiniciando estado experimental.")
        print(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
