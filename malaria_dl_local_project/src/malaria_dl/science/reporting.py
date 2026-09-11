"""Human-readable view of a canonical persisted report; no CSV fallback."""

import json
from pathlib import Path

from ..campaigns.contracts import digest
from .protocol import require


def markdown(report):
    lines = [
        "# Comparación científica E7",
        "",
        f"Protocolo: `{report['protocol']['version']}` / `{report['protocol_hash']}`.",
        f"Reporte SHA-256: `{digest(report)}`.",
        f"Estado: {report['state']}. Partición: {report['split']}.",
        "",
        "La sensibilidad objetivo es estrictamente > 0,98. VALIDATION compartida es exploratoria; no acredita validación clínica.",
        "",
        "| Arquitectura | Semilla | EVALUATE attempt | Sensibilidad | Especificidad | F2 | Estado |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for item in report["items"]:
        m = item["metrics"]
        lines.append(
            f"| {item['architecture']} | {item['seed']} | {item['evaluation_id']} | {m['sensitivity']} | {m['specificity']} | {m['f2']} | {item['status']} |"
        )
    if not report["items"]:
        lines += ["", "Sin resultados acreditados: no hay cifras, ranking ni ganador."]
    lines += [
        "",
        "## Decisión",
        "",
        json.dumps(report["selection"], ensure_ascii=False, sort_keys=True),
        "",
        "## Exclusiones",
        "",
    ]
    lines += [
        f"- {e['evaluation_id']}: {e['reason']}" for e in report["exclusions"]
    ] or ["Ninguna referencia excluida."]
    lines += [
        "",
        "## Alcance y procedencia",
        "",
        f"Dataset: `{report['dataset'].get('dataset_version_id')}`. Snapshot SHA-256: `{digest(report['dataset'])}`.",
        f"Pendientes de matriz: {sum(r['state'] != 'evaluated' for r in report['matrix'])}.",
        "El JSON asociado conserva configuración, soporte, pacientes, matrices de confusión, curvas, IC por paciente, variabilidad entre semillas, contrastes pareados y referencias exactas a predicciones y EXPLAIN.",
        "Los IC son puntuales, condicionados al modelo entrenado; no se concatenan semillas. Metadatos ausentes permanecen ausentes.",
        "TEST previo: alcance histórico no acreditado como intacto. EXPLAIN no demuestra causalidad.",
        "",
    ]
    lines += [f"- {v}" for v in report["limitations"]]
    lines += ["", "## Métricas, curvas e incertidumbre por repetición", ""]
    for item in report["items"]:
        lines += [
            f"### {item['architecture']} · semilla {item['seed']} · {item['evaluation_id']}",
            "",
            "Filas reales [0,1], columnas predichas [0,1]; PR-AUC = average precision no interpolada.",
            "",
            "```json",
            json.dumps(
                {
                    "metrics": item["metrics"],
                    "patient_sampling": item["uncertainty"],
                    "threshold_proposal": item["threshold_proposal_val_only"],
                    "baseline_always_parasitized": item["baseline_always_parasitized"],
                    "limitations": item["limitations"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
            "Las coordenadas exactas de curvas y su referencia de predicciones están en el JSON del reporte.",
            "",
        ]
    lines += [
        "## Variabilidad entre semillas y contrastes pareados",
        "",
        "Las diferencias son izquierda menos derecha; IC puntuales por pacientes, no significancia ni réplicas independientes entre semillas.",
        "",
        "```json",
        json.dumps(
            {
                "between_seeds": report["seed_summaries"],
                "paired": report["paired_contrasts"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
    ]

    return "\n".join(lines) + "\n"


def export_report(repository, report_id, destination):
    # The only scientific export path starts from a successful database read.
    report = repository.read_report(report_id)
    require(report is not None, "PERSISTED_REPORT_REQUIRED")
    root = Path(destination)
    if root.exists() and any(root.iterdir()):
        existing = root / "report.json"
        require(
            existing.is_file() and json.loads(existing.read_text()) == report,
            "EXPORT_DESTINATION_CONFLICT",
        )
    root.mkdir(parents=True, exist_ok=True)
    (root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    (root / "report.md").write_text(markdown(report))
    plot_curves(report, root)
    return digest(report)


def plot_curves(report, root):
    """Standalone figures from persisted coordinates, never new inference or metrics."""
    available = [item for item in report["items"] if item["curves"]["roc"] is not None]
    if not available:
        return
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(12, 5), layout="constrained")
    FigureCanvasAgg(figure)
    roc, pr = figure.subplots(1, 2)
    for item in available:
        label = f"{item['architecture']} s={item['seed']} {item['configuration_hash'][:8] if item['configuration_hash'] else 'historical'}"
        c = item["curves"]
        roc.plot(c["roc"]["fpr"], c["roc"]["tpr"], label=label, alpha=0.7)
        pr.step(
            c["precision_recall"]["recall"],
            c["precision_recall"]["precision"],
            where="post",
            label=label,
            alpha=0.7,
        )
    roc.plot([0, 1], [0, 1], linestyle="--", color="grey")
    roc.set(
        xlabel="False positive rate",
        ylabel="Sensitivity (parasitized)",
        xlim=(0, 1),
        ylim=(0, 1.01),
        title="ROC",
    )
    pr.set(
        xlabel="Recall (parasitized)",
        ylabel="Precision (parasitized)",
        xlim=(0, 1),
        ylim=(0, 1.01),
        title="Precision–recall; area = average precision",
    )
    roc.legend(fontsize=6)
    pr.legend(fontsize=6)
    figure.suptitle(
        f"{report['split'].upper()} · {'exploratory' if report['split'] == 'val' else 'historical final results'} · {digest(report)[:12]}"
    )
    figure.savefig(root / "curves.png", dpi=180)
    from matplotlib import rc_context

    with rc_context({"svg.hashsalt": digest(report)}):
        figure.savefig(root / "curves.svg", metadata={"Date": None})
    figure.clear()
