import statistics
from collections import defaultdict

from .identity_evidence import IdentityStatus, ResolvedClinicalIdentity


def analyze_identities(records: list[ResolvedClinicalIdentity]) -> dict:
    verified = [item for item in records if item.identity_status == IdentityStatus.VERIFIED]
    unresolved = sum(item.identity_status == IdentityStatus.UNRESOLVED for item in records)
    conflicts = sum(item.identity_status == IdentityStatus.CONFLICT for item in records)
    patients: dict[str, dict] = defaultdict(
        lambda: {"total_cells": 0, "parasitized_cells": 0, "uninfected_cells": 0, "splits": defaultdict(int)}
    )
    for item in verified:
        patient = patients[item.patient_id]
        patient["total_cells"] += 1
        patient[f"{item.class_name}_cells"] += 1
        patient["splits"][item.historical_split] += 1
    details = {}
    for patient_id, value in patients.items():
        details[patient_id] = value | {
            "splits": dict(sorted(value["splits"].items())),
            "splits_present": sorted(value["splits"]),
        }
    split_sets = {split: {pid for pid, value in details.items() if split in value["splits"]} for split in ("train", "val", "test")}
    overlapping = {pid for pid, value in details.items() if len(value["splits_present"]) > 1}
    cell_counts = [value["total_cells"] for value in details.values()]
    affected = {split: sum(value["splits"].get(split, 0) for pid, value in details.items() if pid in overlapping) for split in ("train", "val", "test")}
    return {
        "total_records": len(records),
        "patient_verified": len(verified),
        "patient_unresolved": unresolved,
        "patient_conflict": conflicts,
        "patient_id_coverage_percent": 0.0 if not records else len(verified) / len(records) * 100,
        "unique_patients_total": len(details),
        "unique_patients_train": len(split_sets["train"]),
        "unique_patients_val": len(split_sets["val"]),
        "unique_patients_test": len(split_sets["test"]),
        "min_cells_per_patient": min(cell_counts) if cell_counts else None,
        "max_cells_per_patient": max(cell_counts) if cell_counts else None,
        "mean_cells_per_patient": statistics.fmean(cell_counts) if cell_counts else None,
        "median_cells_per_patient": statistics.median(cell_counts) if cell_counts else None,
        "patients_only_parasitized": sum(v["parasitized_cells"] > 0 and v["uninfected_cells"] == 0 for v in details.values()),
        "patients_only_uninfected": sum(v["uninfected_cells"] > 0 and v["parasitized_cells"] == 0 for v in details.values()),
        "patients_with_both_classes": sum(v["uninfected_cells"] > 0 and v["parasitized_cells"] > 0 for v in details.values()),
        "train_val_patient_overlap": len(split_sets["train"] & split_sets["val"]),
        "train_test_patient_overlap": len(split_sets["train"] & split_sets["test"]),
        "val_test_patient_overlap": len(split_sets["val"] & split_sets["test"]),
        "patients_in_one_split": sum(len(v["splits_present"]) == 1 for v in details.values()),
        "patients_in_exactly_two_splits": sum(len(v["splits_present"]) == 2 for v in details.values()),
        "patients_in_all_three_splits": sum(len(v["splits_present"]) == 3 for v in details.values()),
        "cells_from_overlapping_patients": sum(affected.values()),
        "train_cells_from_overlapping_patients": affected["train"],
        "val_cells_from_overlapping_patients": affected["val"],
        "test_cells_from_overlapping_patients": affected["test"],
        "overlapping_patient_cells_percent": 0.0 if not records else sum(affected.values()) / len(records) * 100,
        "patient_leakage_confirmed": bool(overlapping),
        "patients": dict(sorted(details.items())),
    }

