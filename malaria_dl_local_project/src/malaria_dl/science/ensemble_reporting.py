"""E8 scientific comparison reuses E7 metric, seed and curve conventions."""

import json
from collections import defaultdict
from pathlib import Path

from ..campaigns.contracts import digest
from ..campaigns.repository import identifier
from .comparison import safe_reason
from .ensemble import experimental_matrix, validate_evaluation
from .protocol import load_protocol, require
from .reporting import plot_curves
from .statistics import seed_summary


def compare_results(evaluation_ids, reader):
    evaluation_ids = [identifier(eid) for eid in evaluation_ids]
    require(
        len(set(evaluation_ids)) == len(evaluation_ids),
        "ENSEMBLE_COMPARISON_REFERENCES_AMBIGUOUS",
    )
    selected = []
    excluded = []
    for eid in sorted(evaluation_ids):
        try:
            value = reader(eid)
            validate_evaluation(value)
            selected.append((eid, value))
        except Exception as exc:  # noqa: BLE001 -- public diagnostic never includes driver text
            excluded.append(
                {"evaluation_id": eid, "status": "excluded", "reason": safe_reason(exc)}
            )
    # An explicit population, not an intersection or majority vote, defines each stratum.
    groups = defaultdict(list)
    items = []
    for eid, v in selected:
        b = v["configuration"]["configuration"]
        key = digest(
            {
                "strategy": b["strategy"],
                "weights": [m["weight"] for m in b["members"]],
                "configurations": [m["configuration_hash"] for m in b["members"]],
                "dataset": b["dataset"],
                "sample_hash": b["sample_hash"],
                "code": {"configuration": b["code"], "execution": v["execution_code"]},
            }
        )
        item = {
            "evaluation_id": eid,
            "architecture": "ensemble_" + b["strategy"],
            "seed": b["repetition"]["seed"],
            "configuration_hash": key,
            "metrics": v["metrics"],
            "curves": v["curves"],
            "result": v,
        }
        groups[key].append(item)
        items.append(item)
    duplicates = {
        i["evaluation_id"]
        for rs in groups.values()
        if len({r["seed"] for r in rs}) != len(rs)
        for i in rs
    }
    excluded += [
        {
            "evaluation_id": eid,
            "status": "excluded",
            "reason": "AMBIGUOUS_ENSEMBLE_REPETITION",
        }
        for eid in sorted(duplicates)
    ]
    items = [i for i in items if i["evaluation_id"] not in duplicates]
    summaries = []
    for key, rs in sorted(groups.items()):
        rs = [r for r in rs if r["evaluation_id"] not in duplicates]
        if rs:
            summaries.append(
                {
                    "comparison_group": key,
                    "seeds": sorted(r["seed"] for r in rs),
                    "missing_seeds": sorted(
                        set(load_protocol()["seeds"]) - {r["seed"] for r in rs}
                    ),
                    "metrics": seed_summary(rs),
                }
            )
    planned = experimental_matrix()
    for row in planned:
        observed = []
        for item in items:
            b = item["result"]["configuration"]["configuration"]
            if (
                row["entity_type"] == "ensemble"
                and row["strategy"] == b["strategy"]
                and row["seed"] == b["repetition"]["seed"]
                and row["optimizer"] == b["repetition"]["optimizer"]
            ):
                observed.append(item["evaluation_id"])
            elif (
                row["entity_type"] == "individual"
                and row["condition"] == "original"
                and row["seed"] == b["repetition"]["seed"]
            ):
                observed.extend(
                    ref["evaluation_id"]
                    for member, ref in zip(b["members"], b["validation_references"])
                    if member["configuration_hash"] == row["configuration_hash"]
                )
        if observed:
            row.update(
                state="evaluated_explicit_references",
                reason=None,
                evaluation_ids=sorted(set(observed)),
            )
    return {
        "schema": "ensemble_comparison_e8_v1",
        "split": "val",
        "protocol_hash": digest(load_protocol()),
        "references": sorted(evaluation_ids),
        "items": items,
        "exclusions": excluded,
        "seed_summaries": summaries,
        "matrix": planned,
        "state": "exploratory" if items else "preparation_missing_evidence",
        "selection": None,
        "limitations": [
            "Each group has one exact population; no cross-group ranking",
            "Individual reference selected on VAL within each explicit repetition",
            "No best TEST member or superiority claim",
            "No seed pooling; original E7 matrix stays frozen",
            "Matrix execution state is not inferred for unselected experiments",
        ],
    }


def validate_comparison(value):
    require(
        value["schema"] == "ensemble_comparison_e8_v1"
        and value["split"] == "val"
        and value["protocol_hash"] == digest(load_protocol()),
        "ENSEMBLE_COMPARISON_INVALID",
    )
    for item in value["items"]:
        validate_evaluation(item["result"])
        require(
            item["metrics"] == item["result"]["metrics"]
            and item["curves"] == item["result"]["curves"]
            and item["seed"]
            == item["result"]["configuration"]["configuration"]["repetition"]["seed"],
            "ENSEMBLE_COMPARISON_RESULT_CONFLICT",
        )
    require(
        set(value["references"])
        == {i["evaluation_id"] for i in value["items"]}
        | {e["evaluation_id"] for e in value["exclusions"]},
        "ENSEMBLE_COMPARISON_REFERENCE_CONFLICT",
    )


def export(repository, report_id, destination):
    report = repository.read_report(report_id)
    validate_comparison(report)
    root = Path(destination)
    if root.exists() and any(root.iterdir()):
        require(
            (root / "report.json").is_file()
            and json.loads((root / "report.json").read_text()) == report,
            "EXPORT_DESTINATION_CONFLICT",
        )
    root.mkdir(parents=True, exist_ok=True)
    (root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    lines = [
        "# Ensembles E8 — comparación exploratoria VAL",
        "",
        f"Reporte SHA-256: `{digest(report)}`.",
        "Sin afirmación de superioridad ni validación clínica.",
        "",
        "| Estrategia | Semilla | Sensibilidad | Especificidad | F2 |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in report["items"]:
        m = item["metrics"]
        lines.append(
            f"| {item['architecture']} | {item['seed']} | {m['sensitivity']} | {m['specificity']} | {m['f2']} |"
        )
    for item in report["items"]:
        lines += [
            "",
            "```json",
            json.dumps(
                {
                    "members_weights_threshold": item["result"]["configuration"],
                    "ensemble_vs_members": item["result"]["member_comparisons"],
                    "baseline": item["result"]["baseline"],
                    "uncertainty": item["result"]["uncertainty"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
        ]
    if not report["items"]:
        lines += ["", "Sin resultados comparables: no hay cifras ni ganador."]
    lines += [
        "",
        "## Exclusiones, repeticiones y límites",
        "",
        "```json",
        json.dumps(
            {k: report[k] for k in ("exclusions", "seed_summaries", "limitations")},
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "El JSON conserva contribuciones por muestra, desacuerdo y errores corregidos/introducidos. No son mapas espaciales ni incertidumbre clínica calibrada.",
    ]
    (root / "report.md").write_text("\n".join(lines) + "\n")
    plot_curves(report, root)
    return digest(report)
