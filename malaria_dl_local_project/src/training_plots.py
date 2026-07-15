"""Matplotlib plots for combined base and fine-tuning histories."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


REQUIRED_HISTORY_COLUMNS = {
    "epoch",
    "phase",
    "accuracy",
    "val_accuracy",
    "loss",
    "val_loss",
    "learning_rate",
}


def _load_history(history_csv: str | Path) -> pd.DataFrame:
    history_path = Path(history_csv)
    if not history_path.is_file():
        raise FileNotFoundError(f"No existe el historial de entrenamiento: {history_path}")

    history = pd.read_csv(history_path)
    missing_columns = sorted(REQUIRED_HISTORY_COLUMNS.difference(history.columns))
    if missing_columns:
        raise ValueError(
            "El historial de entrenamiento no contiene las columnas requeridas: "
            + ", ".join(missing_columns)
        )
    if history.empty:
        raise ValueError("El historial de entrenamiento está vacío.")

    numeric_columns = ["epoch", "accuracy", "val_accuracy", "loss", "val_loss"]
    try:
        history[numeric_columns] = history[numeric_columns].apply(
            pd.to_numeric,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Las columnas de época y métricas deben contener valores numéricos."
        ) from exc

    return history


def _add_fine_tuning_marker(axis, fine_tuning_start_epoch: int | None) -> None:
    if fine_tuning_start_epoch is None:
        return
    axis.axvline(
        x=fine_tuning_start_epoch,
        color="tab:red",
        linestyle="--",
        linewidth=1.5,
        label="Start Fine-Tuning",
    )


def _plot_metric(
    axis,
    *,
    history: pd.DataFrame,
    model_name: str,
    metric: str,
    validation_metric: str,
    train_label: str,
    validation_label: str,
    title_prefix: str,
    y_label: str,
    fine_tuning_start_epoch: int | None,
) -> None:
    axis.plot(
        history["epoch"],
        history[metric],
        marker="o",
        markersize=4,
        label=train_label,
    )
    axis.plot(
        history["epoch"],
        history[validation_metric],
        marker="o",
        markersize=4,
        label=validation_label,
    )
    _add_fine_tuning_marker(axis, fine_tuning_start_epoch)
    axis.set_xlabel("Epoch")
    axis.set_ylabel(y_label)
    axis.set_title(f"{title_prefix} ({model_name})")
    axis.grid(True, linestyle=":", alpha=0.6)
    axis.legend()


def _save_single_plot(
    *,
    history: pd.DataFrame,
    model_name: str,
    output_path: Path,
    metric: str,
    validation_metric: str,
    train_label: str,
    validation_label: str,
    title_prefix: str,
    y_label: str,
    fine_tuning_start_epoch: int | None,
) -> None:
    figure, axis = plt.subplots(figsize=(9, 5))
    try:
        _plot_metric(
            axis,
            history=history,
            model_name=model_name,
            metric=metric,
            validation_metric=validation_metric,
            train_label=train_label,
            validation_label=validation_label,
            title_prefix=title_prefix,
            y_label=y_label,
            fine_tuning_start_epoch=fine_tuning_start_epoch,
        )
        figure.tight_layout()
        figure.savefig(output_path, dpi=150, bbox_inches="tight")
    finally:
        plt.close(figure)


def plot_combined_training_curves(
    history_csv: str,
    model_name: str,
    output_dir: str,
    fine_tuning_start_epoch: int | None = None,
) -> dict:
    """Generate individual and two-panel plots from a combined history CSV."""
    history = _load_history(history_csv)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "combined_accuracy": destination / "combined_accuracy.png",
        "combined_loss": destination / "combined_loss.png",
        "combined_training_curves": destination / "combined_training_curves.png",
    }

    _save_single_plot(
        history=history,
        model_name=model_name,
        output_path=output_paths["combined_accuracy"],
        metric="accuracy",
        validation_metric="val_accuracy",
        train_label="Train Accuracy",
        validation_label="Val Accuracy",
        title_prefix="Combined Accuracy",
        y_label="Accuracy",
        fine_tuning_start_epoch=fine_tuning_start_epoch,
    )
    _save_single_plot(
        history=history,
        model_name=model_name,
        output_path=output_paths["combined_loss"],
        metric="loss",
        validation_metric="val_loss",
        train_label="Train Loss",
        validation_label="Val Loss",
        title_prefix="Combined Loss",
        y_label="Loss",
        fine_tuning_start_epoch=fine_tuning_start_epoch,
    )

    figure, axes = plt.subplots(1, 2, figsize=(15, 5))
    try:
        _plot_metric(
            axes[0],
            history=history,
            model_name=model_name,
            metric="accuracy",
            validation_metric="val_accuracy",
            train_label="Train Accuracy",
            validation_label="Val Accuracy",
            title_prefix="Combined Accuracy",
            y_label="Accuracy",
            fine_tuning_start_epoch=fine_tuning_start_epoch,
        )
        _plot_metric(
            axes[1],
            history=history,
            model_name=model_name,
            metric="loss",
            validation_metric="val_loss",
            train_label="Train Loss",
            validation_label="Val Loss",
            title_prefix="Combined Loss",
            y_label="Loss",
            fine_tuning_start_epoch=fine_tuning_start_epoch,
        )
        figure.tight_layout()
        figure.savefig(
            output_paths["combined_training_curves"],
            dpi=150,
            bbox_inches="tight",
        )
    finally:
        plt.close(figure)

    return {name: str(path) for name, path in output_paths.items()}
