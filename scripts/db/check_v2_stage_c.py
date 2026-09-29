"""Reproduce C using fixed offline commands and synthetic fixtures. No DB/Docker."""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from adoption_v2.core import (
    CATALOG_HASH,
    CONTRACT_HASH,
    MANIFEST_HASH,
    contract,
    digest,
    target,
)
from adoption_v2.ddl import delta
from adoption_v2.execute import certified_catalog

EVIDENCE = ROOT / "docs/audits/e10_10_5c_evidence"


def write(name, value):
    (EVIDENCE / name).write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"
    )


def mapping():
    spec = contract()
    manifest, _ = target()
    tables = {
        e["name"]: e["columns"] for e in manifest["statements"] if e["kind"] == "table"
    }
    primary = {
        e["table"]: e["keys"]
        for e in manifest["statements"]
        if e["kind"] == "constraint" and e.get("constraint_type") == "CONSTR_PRIMARY"
    }
    rules = {
        "runs": "Preservar fila; proyectar training_results.validation antes de retirar training_results; original completo en archivo privado",
        "run_clinical_metrics": "Preservar PK; contexto explícito; métricas binary_nullable_v2 verificadas contra counts; AUC original",
        "run_metrics": "Consolidar sólo métricas clínicas reservadas con igualdad demostrada; preservar extensiones con namespace",
        "run_threshold_calibration": "Preservar PK y valores; enlace explícito a pareja VAL con población/checkpoint idénticos",
        "training_history": "Preservar PK; aliases compatibles; unir epochs del ledger sólo con identidad y valores concordantes",
        "confusion_matrices": "Verificar labels y counts contra medición única; PK y payload íntegros en archivo; vista certificada",
        "classification_reports": "Verificar clase/support/ratios contra medición única; PK y payload íntegros en archivo; vista certificada",
        "alembic_version": "Conservar revisión legacy en archivo; transición condicionada por reconciliación y catálogo, dentro de transacción",
        "run_configurations": "Una por TRAIN desde configuración congelada + canonical/hash originales referenciados",
        "evaluations": "Contexto de evidencia explícita; cardinalidad única; UUID original o uuid5 determinista",
        "evaluation_ensemble_members": "Miembros referenciados explícitamente; pesos y linaje verificados",
        "xai_evidence": "Proyección con procedencia, input/checkpoint hashes y padre explícitos; sin ejecutar algoritmos",
        "xai_artifacts": "Metadatos originales referenciados; sin leer ni regenerar artefactos",
        "xai_quantitative_evaluations": "Vacío: no generar evaluaciones sin evidencia aprobada",
        "xai_interpretations": "Vacío: no inventar interpretaciones",
        "xai_specialist_reviews": "Vacío: no inventar revisiones de especialistas",
    }
    entries = []
    for name in sorted(set(spec["tables"]) | set(tables)):
        legacy = spec["tables"].get(name)
        entries.append(
            {
                "source_table": name if legacy else "",
                "target_table": legacy["target"] if legacy else name,
                "action": legacy["action"] if legacy else "NEW",
                "source_primary_key": "|".join(spec["primary_keys"].get(name, [])),
                "target_primary_key": "|".join(primary.get(name, [])),
                "identity_policy": "Head anterior archivado; transición explícita"
                if name == "alembic_version"
                else "PK original en tabla y archivo"
                if legacy and legacy["action"] != "MERGE"
                else "PK original en archivo + vínculo a evaluación"
                if legacy
                else "FK existente o uuid5; nunca UUID aleatorio",
                "rule": rules.get(
                    name,
                    "Preservar todas las columnas originales; columnas nuevas sólo según contrato; FK/checks finales obligatorios",
                ),
                "original_payload": "Archivo privado íntegro y hash por tabla/fila; no publicar credenciales",
                "blocker": "Cualquier deriva de esquema, conflicto, evidencia incompleta o catálogo final distinto",
            }
        )
    path = ROOT / "docs/audits/e10_10_5_legacy_mapping.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(entries[0]))
        writer.writeheader()
        writer.writerows(entries)
    columns = {}
    for name, cols in tables.items():
        original = [
            r["column_name"]
            for r in sorted(
                spec["expected_schema"]["columns"], key=lambda r: r["ordinal_position"]
            )
            if r["table_name"] == name
        ]
        if original:
            assert original + [k for k in cols if k not in original] == list(cols), name
        columns[name] = {
            "original_columns": original,
            "target_columns": list(cols),
            "added_columns": [k for k in cols if k not in original],
        }
    write("column_mapping.json", columns)
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alembic-python", default=sys.executable)
    parser.add_argument("--ruff", default="ruff")
    args = parser.parse_args()
    EVIDENCE.mkdir(exist_ok=True)
    paths = ["adoption_v2", "tests/adoption_v2", "scripts/db/check_v2_stage_c.py"]
    commands = [
        [sys.executable, "scripts/db/build_v2_baseline.py", "--check"],
        [
            sys.executable,
            "scripts/db/validate_v2_static.py",
            "--report",
            str(EVIDENCE / "baseline_static.json"),
        ],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests/adoption_v2", "-v"],
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/db_v2",
            "-p",
            "test_static_baseline.py",
            "-v",
        ],
        [
            args.alembic_python,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/db_v2",
            "-p",
            "test_alembic_envelope.py",
            "-v",
        ],
        [args.ruff, "check", *paths],
        [args.ruff, "format", "--check", *paths],
        [
            sys.executable,
            "-c",
            "from pathlib import Path; paths=list(Path('adoption_v2').glob('*.py'))+list(Path('tests/adoption_v2').glob('*.py'))+[Path('scripts/db/check_v2_stage_c.py')]; [compile(p.read_text(),str(p),'exec') for p in paths]; print(len(paths),'modules compiled in memory')",
        ],
    ]
    report = {
        "stage": "E10.10.5C",
        "scope": "offline only; synthetic fixtures; no PostgreSQL/Docker/network",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "commands": [],
    }
    for command in commands:
        run = subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=False
        )
        report["commands"].append(
            {
                "command": command,
                "exit_code": run.returncode,
                "stdout": run.stdout,
                "stderr": run.stderr,
            }
        )
        print(command[1:3], run.returncode, flush=True)
    report["passed"] = all(c["exit_code"] == 0 for c in report["commands"])
    write("commands.json", report)
    immutable = json.loads(
        (ROOT / "docs/audits/e10_10_5a_history_manifest.json").read_text()
    )["files"]
    for path, h in immutable.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == h, path
    certified_catalog()
    for path, info in json.loads((EVIDENCE / "inputs.json").read_text()).items():
        assert (
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == info["sha256"]
        ), path
    phases = delta()
    write("ddl_plan.json", phases)
    count = mapping()
    sys.path.insert(0, str(ROOT / "tests/adoption_v2"))
    from fixtures import calibrated, explained, rich

    from adoption_v2.planner import build_plan

    fixture_results = {}
    for name, fixture in [
        ("scientific", rich),
        ("calibration", calibrated),
        ("xai", explained),
    ]:
        source, bindings = fixture()
        a = build_plan(source, bindings)
        b = build_plan(source, bindings)
        assert digest(a) == digest(b)
        fixture_results[name] = {
            "plan_sha256": a["plan_sha256"],
            "source_inventory_sha256": a["source_inventory_sha256"],
            "preserved_tables": a["preserved_tables"],
            "counts": {k: len(v) for k, v in a["rows"].items()},
            "deterministic": True,
            "database_execution": False,
        }
    write("synthetic_reconciliation.json", fixture_results)
    result = {
        "stage": "E10.10.5C",
        "passed": report["passed"],
        "source_tables": len(contract()["tables"]),
        "target_tables": len(fixture_results["scientific"]["counts"]),
        "mapping_rows": count,
        "actions": dict(Counter(v["action"] for v in contract()["tables"].values())),
        "ddl_statements": {k: len(v) for k, v in phases.items()},
        "historical_files_unchanged": len(immutable),
        "historical_sql_checksums": len(contract()["historical_ledger"]),
        "legacy_contract_sha256": CONTRACT_HASH,
        "target_manifest_sha256": MANIFEST_HASH,
        "route_a_catalog_canonical_sha256": CATALOG_HASH,
        "server_execution": "NOT EXECUTED — requires Gate C and stage D",
    }
    write("static_results.json", result)
    print(json.dumps(result, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
