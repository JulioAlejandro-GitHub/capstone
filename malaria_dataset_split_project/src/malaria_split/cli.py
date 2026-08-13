import argparse
import json
import os
from pathlib import Path
import sys

from sqlalchemy import text

from malaria_split.discovery import audit_database, scan_current_physical_split
from malaria_split.identity import (
    IdentityStatus,
    analyze_identities,
    build_source_identity_index,
    resolve_physical_manifest,
)
from malaria_split.persistence.bootstrap import (
    apply_scientific_bootstrap,
    audit_existing_scientific_bootstrap,
    audit_scientific_bootstrap,
    prepare_scientific_population,
)
from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.splitting import (
    build_seeded_greedy_baseline,
    evaluate_candidate,
    load_patient_profiles,
    randomized_patient_sequence,
)
from malaria_split.splitting.patient_profiles import PatientClassProfile
from malaria_split.splitting.optimizer import optimize_patient_split
from malaria_split.splitting.reporting import candidate_composition
from malaria_split.splitting.candidate import candidate_sort_key
from malaria_split.persistence.split_generation import (
    PersistenceMode,
    prepare_split_generation,
    persist_split_generation,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _capstone_root() -> Path:
    return _project_root().parent


def _read_simple_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def audit_current_split(config_path: Path, root_override: str | None = None) -> int:
    config = _read_simple_config(config_path)
    configured_root = root_override or os.getenv("MALARIA_CURRENT_SPLIT_ROOT") or config[
        "current_physical_split_root"
    ]
    root = Path(configured_root).expanduser()
    if not root.is_absolute():
        root = _capstone_root() / root
    result = scan_current_physical_split(
        root,
        _csv_tuple(config.get("expected_splits", "train,val,test")),
        _csv_tuple(config.get("expected_classes", "parasitized,uninfected")),
        _csv_tuple(config.get("expected_extensions", ".png,.jpg,.jpeg")),
    )
    payload = result.to_dict()
    payload["inspected_root"] = str(root.resolve())
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not result.structural_errors else 1


def _configured_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else _capstone_root() / path


def _spot_check(records, limit: int = 10) -> list[dict]:
    """Deterministic diverse sample for human evidence review."""
    selected = []
    seen = set()
    for item in records:
        if item.identity_status != IdentityStatus.VERIFIED:
            continue
        dimension = (item.historical_split, item.class_name, item.patient_id)
        if dimension in seen:
            continue
        selected.append(item.to_dict())
        seen.add(dimension)
        if len(selected) == limit:
            break
    return selected


def audit_patient_identity(config_path: Path) -> int:
    config = _read_simple_config(config_path)
    physical_root = _configured_path(config["current_physical_split_root"])
    original_root = _configured_path(config["tfds_original_images_root"])
    mappings = [
        _configured_path(config["patient_mapping_parasitized"]),
        _configured_path(config["patient_mapping_uninfected"]),
    ]
    source_index, index_diagnostics = build_source_identity_index(original_root, mappings)
    records = resolve_physical_manifest(
        physical_root / "files_manifest.csv", physical_root, source_index
    )
    analysis = analyze_identities(records)
    spot_check = _spot_check(records)
    output = _configured_path(config["identity_audit_output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_classification": "DERIVED AUDIT ARTIFACT",
        "source_index": index_diagnostics,
        "summary": {key: value for key, value in analysis.items() if key != "patients"},
        "patients": analysis["patients"],
        "manual_spot_check_sample": spot_check,
        "records": [item.to_dict() for item in records],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "artifact_classification": payload["artifact_classification"],
        "output": str(output.resolve()),
        "source_index": index_diagnostics,
        "summary": payload["summary"],
        "spot_check_records": len(spot_check),
    }, ensure_ascii=False, indent=2))
    return 0 if len(records) == 27558 and not index_diagnostics["mapping_errors"] else 1


def audit_system_contracts(config_path: Path) -> int:
    config = _read_simple_config(config_path)
    malaria_project = _configured_path(config.get("malaria_project_root", "malaria_dl_local_project"))
    sys.path.insert(0, str(malaria_project))
    try:
        from src.malaria_dl.persistence.database import get_engine

        payload = audit_database(get_engine(), schema=config.get("database_schema", "public"))
    finally:
        if sys.path and sys.path[0] == str(malaria_project):
            sys.path.pop(0)
    output = _configured_path(config.get(
        "system_contract_audit_output",
        "malaria_dataset_split_project/var/audit/system_contract_audit.json",
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"artifact_classification": "DERIVED AUDIT ARTIFACT", **payload}, indent=2), encoding="utf-8")
    print(json.dumps({
        "artifact_classification": "DERIVED AUDIT ARTIFACT",
        "output": str(output.resolve()),
        "database": payload["database"],
        "schema_fingerprint_sha256": payload["schema_fingerprint_sha256"],
        "migration_state": payload["migration_state"],
        "table_row_counts": {name: value["row_count"] for name, value in payload["tables"].items()},
        "checksum_counts": payload["checksum_counts"],
    }, indent=2))
    return 0


def _bootstrap_paths(config_path: Path) -> tuple[Path, Path, list[Path]]:
    config = _read_simple_config(config_path)
    return (
        _configured_path(config["current_physical_split_root"]),
        _configured_path(config["tfds_original_images_root"]),
        [
            _configured_path(config["patient_mapping_parasitized"]),
            _configured_path(config["patient_mapping_uninfected"]),
        ],
    )


def bootstrap_malaria_v1(config_path: Path, dry_run: bool) -> int:
    physical_root, original_root, mappings = _bootstrap_paths(config_path)
    prepared = prepare_scientific_population(
        physical_root=physical_root, original_root=original_root, mapping_paths=mappings
    )
    summary_keys = (
        "total_records", "patient_verified", "patient_unresolved", "patient_conflict",
        "unique_patients_total", "min_cells_per_patient", "max_cells_per_patient",
        "patients_only_parasitized", "patients_only_uninfected",
        "patients_with_both_classes", "class_counts",
    )
    payload = {
        "mode": "DRY_RUN" if dry_run else "APPLY",
        "scientific_preparation": {key: prepared.summary[key] for key in summary_keys},
        "source_mapping_sha256": prepared.source_mapping_sha256,
        "source_file_sha256_populated": len(prepared.records),
        "decoded_pixel_sha256_populated": len(prepared.records),
        "source_record_keys_unique": len({row["source_record_key"] for row in prepared.records}),
        "identity_evidence_available": len(prepared.evidence),
        "status": "PASS",
    }
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for bootstrap database recognition")
    if dry_run:
        engine = create_postgresql_engine(database_url)
        try:
            payload["database_recognition"] = audit_existing_scientific_bootstrap(engine, prepared)
        finally:
            engine.dispose()
    else:
        engine = create_postgresql_engine(database_url)
        try:
            payload["database_apply"] = apply_scientific_bootstrap(engine, prepared)
        finally:
            engine.dispose()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def audit_bootstrap_persistence() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for persistence audit")
    engine = create_postgresql_engine(database_url)
    try:
        payload = audit_scientific_bootstrap(engine)
    finally:
        engine.dispose()
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0 if payload["status"] == "PASS" else 1


def audit_patient_profiles_v1(dataset_version_id: str) -> int:
    """Read-only 3A.1 audit; baseline is evaluated but never persisted or selected."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for patient profile audit")
    engine = create_postgresql_engine(database_url)
    try:
        with engine.connect() as connection:
            from uuid import UUID

            version_id = UUID(dataset_version_id)
            profiles = load_patient_profiles(connection, version_id)
            sequence = randomized_patient_sequence(profiles)
            baseline = build_seeded_greedy_baseline(profiles)
            evaluation = evaluate_candidate(profiles, baseline)
            duplicate_groups = connection.execute(text("""
                SELECT count(*) FROM (
                  SELECT source_file_sha256 FROM dataset_source_records
                  GROUP BY source_file_sha256 HAVING count(*) > 1
                ) duplicates
            """)).scalar_one()
    finally:
        engine.dispose()
    profile_counts = {
        kind.value: sum(item.patient_class_profile == kind for item in profiles)
        for kind in PatientClassProfile
    }
    sizes = sorted(item.total_records for item in profiles)
    payload = {
        "mode": "READ_ONLY_PATIENT_PROFILE_AUDIT",
        "dataset_version_id": dataset_version_id,
        "patients": len(profiles),
        "records": sum(item.total_records for item in profiles),
        "classes": {
            "parasitized": sum(item.parasitized_records for item in profiles),
            "uninfected": sum(item.uninfected_records for item in profiles),
        },
        "patient_class_profiles": profile_counts,
        "patient_size_distribution": {
            "min": sizes[0], "median": sizes[len(sizes) // 2], "max": sizes[-1]
        },
        "exact_duplicate_hash_groups": duplicate_groups,
        "canonical_order_first_patient": profiles[0].source_identifier,
        "seeded_sequence_first_patient": sequence[0].source_identifier,
        "random_seed": 42,
        "baseline_is_official_candidate": False,
        "baseline_valid": evaluation.valid,
        "baseline_hard_constraint_violations": evaluation.hard_constraint_violations,
        "baseline_objective_tuple": evaluation.objective_tuple,
        "baseline_digest": evaluation.canonical_assignment_digest,
        "database_assignments_written": 0,
        "status": "PASS" if (
            len(profiles) == 201
            and sum(item.total_records for item in profiles) == 27558
            and profile_counts == {
                "BOTH_CLASSES": 151,
                "UNINFECTED_ONLY": 50,
                "PARASITIZED_ONLY": 0,
            }
            and duplicate_groups == 0
        ) else "FAIL",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0 if payload["status"] == "PASS" else 1


def generate_patient_split_v1(dataset_version_id: str, dry_run: bool) -> int:
    if not dry_run:
        raise RuntimeError("SPLIT 3A.2 only permits --dry-run")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    from uuid import UUID

    version_id = UUID(dataset_version_id)

    def run_from_postgresql(seed: int):
        engine = create_postgresql_engine(database_url)
        try:
            with engine.connect() as connection:
                status = connection.execute(
                    text("SELECT status FROM dataset_versions WHERE id=:id"), {"id": version_id}
                ).scalar_one()
                assignment_count = connection.execute(text("""
                    SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id
                """), {"id": version_id}).scalar_one()
                if status != "DRAFT" or assignment_count != 0:
                    raise RuntimeError("SPLIT 3A.2 precondition failed")
                profiles = load_patient_profiles(connection, version_id)
            return profiles, optimize_patient_split(profiles, seed)
        finally:
            engine.dispose()

    profiles_a, run_a = run_from_postgresql(42)
    profiles_b, run_b = run_from_postgresql(42)
    _, seed_43 = run_from_postgresql(43)
    winner = run_a.winner
    composition = candidate_composition(profiles_a, winner.assignments)
    baseline_key = candidate_sort_key(run_a.baseline.evaluation)
    winner_key = candidate_sort_key(winner.evaluation)
    comparison = "BETTER" if winner_key < baseline_key else "EQUIVALENT" if winner_key == baseline_key else "WORSE"
    payload = {
        "mode": "NON_AUTHORITATIVE_DRY_RUN",
        "dataset_version_id": dataset_version_id,
        "algorithm": "patient_group_stratified_v1",
        "algorithm_version": "1.0.0",
        "seed": 42,
        "initial_candidates": run_a.initial_candidates,
        "candidates_evaluated": run_a.candidates_evaluated,
        "local_search_iterations": run_a.local_search_iterations,
        "winner": {
            "candidate_id": winner.candidate_id,
            "assignment_digest": winner.evaluation.canonical_assignment_digest,
            "objective": winner.evaluation.objective.__dict__ if hasattr(winner.evaluation.objective, "__dict__") else {
                field: getattr(winner.evaluation.objective, field)
                for field in winner.evaluation.objective.__dataclass_fields__
            },
            "objective_tuple": winner.evaluation.objective_tuple,
            "hard_constraint_violations": winner.evaluation.hard_constraint_violations,
            "composition": composition,
        },
        "baseline": {
            "assignment_digest": run_a.baseline.evaluation.canonical_assignment_digest,
            "objective_tuple": run_a.baseline.evaluation.objective_tuple,
        },
        "winner_vs_baseline": comparison,
        "reproducibility": {
            "run_a_digest": winner.evaluation.canonical_assignment_digest,
            "run_b_digest": run_b.winner.evaluation.canonical_assignment_digest,
            "run_a_objective": winner.evaluation.objective_tuple,
            "run_b_objective": run_b.winner.evaluation.objective_tuple,
            "deterministic": (
                winner.evaluation.canonical_assignment_digest
                == run_b.winner.evaluation.canonical_assignment_digest
                and winner.evaluation.objective_tuple == run_b.winner.evaluation.objective_tuple
            ),
            "seed_43_digest": seed_43.winner.evaluation.canonical_assignment_digest,
        },
        "database_assignments_written": 0,
    }
    payload["status"] = "PASS" if (
        winner.evaluation.valid
        and comparison in ("BETTER", "EQUIVALENT")
        and payload["reproducibility"]["deterministic"]
    ) else "FAIL"
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0 if payload["status"] == "PASS" else 1


def persist_patient_split_v1(rehearse: bool, apply: bool) -> int:
    if rehearse == apply:
        raise RuntimeError("Choose exactly one of --rehearse or --apply")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    engine = create_postgresql_engine(database_url)
    try:
        with engine.connect() as preparation_connection:
            prepared = prepare_split_generation(preparation_connection)
        mode = PersistenceMode.REHEARSE if rehearse else PersistenceMode.APPLY
        result = persist_split_generation(engine, prepared, mode)
        with engine.connect() as verification:
            after = {
                "status": verification.execute(text(
                    "SELECT status FROM dataset_versions WHERE id=:id"
                ), {"id": prepared.dataset_version_id}).scalar_one(),
                "assignments": verification.execute(text(
                    "SELECT count(*) FROM dataset_split_assignments WHERE dataset_version_id=:id"
                ), {"id": prepared.dataset_version_id}).scalar_one(),
                "generated_at": verification.execute(text(
                    "SELECT generated_at FROM dataset_versions WHERE id=:id"
                ), {"id": prepared.dataset_version_id}).scalar_one(),
            }
    finally:
        engine.dispose()
    audit_payload = dict(result.audit)
    for key in ("class_counts", "profile_counts"):
        audit_payload[key] = {
            "|".join(item): value for item, value in result.audit[key].items()
        }
    payload = {
        "mode": "REHEARSE_ROLLBACK" if rehearse else "APPLY_COMMIT",
        "dataset_version_id": str(prepared.dataset_version_id),
        "regenerated_assignment_digest": result.regenerated_digest,
        "patient_assignments_prepared": len(prepared.optimization.winner.assignments),
        "assignment_rows_prepared": len(prepared.assignment_rows),
        "dataset_version_write_lock": "SELECT_FOR_UPDATE_NOWAIT",
        "bulk_insert_method": "SQLALCHEMY_EXECUTEMANY_BATCH_1000_SINGLE_TRANSACTION",
        "audit_inside_transaction": audit_payload,
        "persisted_assignment_digest": result.persisted_assignment_digest,
        "persisted_record_assignment_digest": result.persisted_record_assignment_digest,
        "methodology_metadata_prepared": True,
        "rollback_executed": result.rolled_back,
        "already_applied": result.already_applied,
        "after_rollback": after,
        "status": "PASS" if (
            (rehearse and result.rolled_back and after["status"] == "DRAFT" and after["assignments"] == 0)
            or (apply and after["status"] == "GENERATED" and after["assignments"] == 27558)
        ) else "FAIL",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0 if payload["status"] == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoría read-only del split físico")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit-current-split")
    audit.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    audit.add_argument("--root", help="Override explícito de la ruta auditada")
    identity = subparsers.add_parser("audit-patient-identity")
    identity.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    contracts = subparsers.add_parser("audit-system-contracts")
    contracts.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    bootstrap = subparsers.add_parser("bootstrap-malaria-v1")
    bootstrap.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    bootstrap.add_argument("--dry-run", action="store_true")
    subparsers.add_parser("audit-scientific-bootstrap")
    profiles = subparsers.add_parser("audit-patient-profiles-v1")
    profiles.add_argument(
        "--dataset-version-id",
        default="d8c0cab5-09dd-597f-9de7-7ca01aee2ec2",
    )
    generate = subparsers.add_parser("generate-patient-split-v1")
    generate.add_argument("--dry-run", action="store_true")
    generate.add_argument(
        "--dataset-version-id",
        default="d8c0cab5-09dd-597f-9de7-7ca01aee2ec2",
    )
    persistence = subparsers.add_parser("persist-patient-split-v1")
    persistence.add_argument("--rehearse", action="store_true")
    persistence.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "audit-current-split":
        return audit_current_split(args.config, args.root)
    if args.command == "audit-patient-identity":
        return audit_patient_identity(args.config)
    if args.command == "audit-system-contracts":
        return audit_system_contracts(args.config)
    if args.command == "bootstrap-malaria-v1":
        return bootstrap_malaria_v1(args.config, args.dry_run)
    if args.command == "audit-scientific-bootstrap":
        return audit_bootstrap_persistence()
    if args.command == "audit-patient-profiles-v1":
        return audit_patient_profiles_v1(args.dataset_version_id)
    if args.command == "generate-patient-split-v1":
        return generate_patient_split_v1(args.dataset_version_id, args.dry_run)
    if args.command == "persist-patient-split-v1":
        return persist_patient_split_v1(args.rehearse, args.apply)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
