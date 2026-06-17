import argparse
import heapq
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


CASE_TYPES = [
    "true_positive",
    "true_negative",
    "false_positive",
    "false_negative",
    "low_confidence",
]


def get_pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera explicaciones visuales post hoc con LIME y SHAP."
    )
    parser.add_argument("--checkpoint", required=True, help="Ruta al modelo .keras entrenado")
    parser.add_argument("--method", choices=["lime", "shap", "both"], required=True)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-samples", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output-dir", default="outputs/explainability")
    return parser.parse_args()


def predict_positive_scores(model, images):
    predictions = model.predict(images, verbose=0)
    predictions = np.asarray(predictions)

    if predictions.ndim == 2 and predictions.shape[1] == 2:
        scores = predictions[:, 1]
    else:
        scores = predictions.reshape(-1)

    return scores.astype(np.float32)


def binary_predict_proba(model, images):
    images = np.asarray(images, dtype=np.float32)
    images = np.clip(images, 0.0, 1.0)
    p_positive = predict_positive_scores(model, images)
    p_positive = np.clip(p_positive, 0.0, 1.0)
    p_negative = 1.0 - p_positive
    return np.column_stack([p_negative, p_positive])


def get_case_type(true_label, predicted_label):
    if true_label == 1 and predicted_label == 1:
        return "true_positive"
    if true_label == 0 and predicted_label == 0:
        return "true_negative"
    if true_label == 0 and predicted_label == 1:
        return "false_positive"
    return "false_negative"


def case_relevance(case_type, score, threshold):
    if case_type in {"true_positive", "false_positive"}:
        return float(score)
    if case_type in {"true_negative", "false_negative"}:
        return float(1.0 - score)
    return float(-abs(score - threshold))


def push_candidate(heap, relevance, index, image, limit):
    item = (float(relevance), int(index), np.asarray(image, dtype=np.float32).copy())
    if len(heap) < limit:
        heapq.heappush(heap, item)
    elif relevance > heap[0][0]:
        heapq.heapreplace(heap, item)


def collect_prediction_candidates(model, dataset, num_samples, threshold):
    y_true = []
    y_pred = []
    y_score = []

    pool_limit = max(20, min(max(num_samples, 20), 200))
    candidate_heaps = {case_type: [] for case_type in CASE_TYPES}

    sample_index = 0
    for batch_index, (images, labels) in enumerate(dataset, start=1):
        scores = predict_positive_scores(model, images)
        labels_np = labels.numpy().astype(int)
        images_np = images.numpy()
        predictions = (scores >= threshold).astype(int)

        for image, true_label, predicted_label, score in zip(
            images_np, labels_np, predictions, scores
        ):
            true_label = int(true_label)
            predicted_label = int(predicted_label)
            score = float(score)
            case_type = get_case_type(true_label, predicted_label)

            y_true.append(true_label)
            y_pred.append(predicted_label)
            y_score.append(score)

            push_candidate(
                candidate_heaps[case_type],
                case_relevance(case_type, score, threshold),
                sample_index,
                image,
                pool_limit,
            )
            push_candidate(
                candidate_heaps["low_confidence"],
                case_relevance("low_confidence", score, threshold),
                sample_index,
                image,
                pool_limit,
            )

            sample_index += 1

        print(f"Predicciones procesadas: batch {batch_index}, muestras {sample_index}")

    candidate_images = {}
    for heap in candidate_heaps.values():
        for _, index, image in heap:
            candidate_images[index] = image

    return (
        np.asarray(y_true, dtype=int),
        np.asarray(y_pred, dtype=int),
        np.asarray(y_score, dtype=np.float32),
        candidate_images,
    )


def get_image_by_index(images, index):
    if isinstance(images, dict):
        return images.get(int(index))
    if 0 <= int(index) < len(images):
        return images[int(index)]
    return None


def sorted_indices_for_case(case_type, y_true, y_pred, y_score, threshold):
    if case_type == "true_positive":
        indices = np.where((y_true == 1) & (y_pred == 1))[0]
        order = np.argsort(-y_score[indices])
    elif case_type == "true_negative":
        indices = np.where((y_true == 0) & (y_pred == 0))[0]
        order = np.argsort(y_score[indices])
    elif case_type == "false_positive":
        indices = np.where((y_true == 0) & (y_pred == 1))[0]
        order = np.argsort(-y_score[indices])
    elif case_type == "false_negative":
        indices = np.where((y_true == 1) & (y_pred == 0))[0]
        order = np.argsort(y_score[indices])
    elif case_type == "low_confidence":
        indices = np.arange(len(y_score))
        order = np.argsort(np.abs(y_score - threshold))
    else:
        raise ValueError(f"Tipo de caso no soportado: {case_type}")

    return indices[order]


def select_explanation_cases(
    y_true,
    y_pred,
    y_score,
    images,
    class_names,
    num_samples,
    threshold,
):
    """
    Selecciona casos balanceados entre aciertos, errores y baja confianza.

    Para no cargar todo el dataset en memoria, `images` puede ser un diccionario
    con solo las imagenes candidatas retenidas durante la prediccion.
    """
    if num_samples <= 0:
        raise ValueError("--num-samples debe ser mayor que cero")

    selected = []
    selected_indices = set()
    target_per_type = max(1, math.ceil(num_samples / len(CASE_TYPES)))

    def add_case(index, case_type):
        if len(selected) >= num_samples or int(index) in selected_indices:
            return False

        image = get_image_by_index(images, int(index))
        if image is None:
            return False

        true_label = int(y_true[index])
        predicted_label = int(y_pred[index])
        score = float(y_score[index])

        selected.append(
            {
                "case_id": int(index),
                "case_type": case_type,
                "true_label": class_names[true_label],
                "predicted_label": class_names[predicted_label],
                "score": score,
                "threshold": float(threshold),
                "image": np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0),
            }
        )
        selected_indices.add(int(index))
        return True

    for case_type in CASE_TYPES:
        added_for_type = 0
        for index in sorted_indices_for_case(case_type, y_true, y_pred, y_score, threshold):
            if add_case(index, case_type):
                added_for_type += 1
            if added_for_type >= target_per_type or len(selected) >= num_samples:
                break

    if len(selected) < num_samples:
        remaining_indices = sorted(
            [idx for idx in images if int(idx) not in selected_indices],
            key=lambda idx: abs(float(y_score[int(idx)]) - threshold),
        )
        for index in remaining_indices:
            case_type = get_case_type(int(y_true[index]), int(y_pred[index]))
            add_case(index, case_type)
            if len(selected) >= num_samples:
                break

    return selected


def collect_background_images(dataset, max_images=20):
    background_images = []
    for images, _ in dataset:
        for image in images.numpy():
            background_images.append(np.asarray(image, dtype=np.float32))
            if len(background_images) >= max_images:
                return np.asarray(background_images, dtype=np.float32)
    return np.asarray(background_images, dtype=np.float32)


def sanitize_label(label):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(label)).strip("-")


def build_output_path(output_dir, method, case):
    method_dir = Path(output_dir) / method / case["case_type"]
    method_dir.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{case['case_id']:04d}_"
        f"real-{sanitize_label(case['true_label'])}_"
        f"pred-{sanitize_label(case['predicted_label'])}_"
        f"score-{case['score']:.4f}.png"
    )
    return method_dir / filename


def build_title(method, true_label=None, predicted_label=None, score=None):
    parts = [method]
    if true_label is not None:
        parts.append(f"real: {true_label}")
    if predicted_label is not None:
        parts.append(f"pred: {predicted_label}")
    if score is not None:
        parts.append(f"score: {score:.4f}")
    return " | ".join(parts)


def predicted_class_index(class_names, predicted_label, probabilities):
    if predicted_label in class_names:
        return class_names.index(predicted_label)
    return int(np.argmax(probabilities))


def explain_with_lime(
    model,
    image,
    class_names,
    output_path,
    true_label=None,
    predicted_label=None,
    score=None,
):
    try:
        from lime import lime_image
        from skimage.segmentation import mark_boundaries, slic
    except ImportError as exc:
        raise ImportError(
            "LIME requiere instalar las dependencias: lime y scikit-image."
        ) from exc

    plt = get_pyplot()
    image = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)

    def predict_fn(images):
        return binary_predict_proba(model, images)

    probabilities = predict_fn(np.expand_dims(image, axis=0))[0]
    label_to_explain = predicted_class_index(class_names, predicted_label, probabilities)

    explainer = lime_image.LimeImageExplainer(random_state=42)
    explanation = explainer.explain_instance(
        image.astype(np.double),
        predict_fn,
        labels=(label_to_explain,),
        hide_color=0,
        num_samples=1000,
        segmentation_fn=lambda x: slic(
            x,
            n_segments=50,
            compactness=10,
            sigma=1,
            start_label=1,
        ),
    )

    highlighted_image, mask = explanation.get_image_and_mask(
        label_to_explain,
        positive_only=True,
        num_features=8,
        hide_rest=False,
    )
    boundary_image = mark_boundaries(highlighted_image, mask)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(image)
    axes[0].set_title("Imagen original")
    axes[0].axis("off")

    axes[1].imshow(boundary_image)
    axes[1].set_title("Superpixeles LIME")
    axes[1].axis("off")

    axes[2].imshow(image)
    axes[2].imshow(mask, cmap="jet", alpha=0.35)
    axes[2].set_title("Overlay LIME")
    axes[2].axis("off")

    fig.suptitle(build_title("LIME", true_label, predicted_label, score))
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def extract_shap_array(shap_values):
    if isinstance(shap_values, list):
        if not shap_values:
            raise ValueError("SHAP retorno una lista vacia de valores.")
        shap_array = np.asarray(shap_values[-1])
    else:
        shap_array = np.asarray(shap_values)

    if shap_array.ndim == 5:
        shap_array = shap_array[0]
        if shap_array.shape[-1] == 1:
            shap_array = shap_array[..., 0]
        else:
            shap_array = shap_array[..., -1]
    elif shap_array.ndim == 4:
        shap_array = shap_array[0]

    if shap_array.ndim != 3:
        raise ValueError(f"Forma SHAP no soportada: {shap_array.shape}")

    return shap_array.astype(np.float32)


def explain_with_shap(
    model,
    background_images,
    image,
    class_names,
    output_path,
    true_label=None,
    predicted_label=None,
    score=None,
):
    try:
        import shap

        plt = get_pyplot()
        background_images = np.asarray(background_images, dtype=np.float32)
        image = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)

        if background_images.ndim != 4 or len(background_images) == 0:
            raise ValueError("SHAP requiere al menos una imagen de background.")

        try:
            explainer = shap.GradientExplainer(model, background_images)
        except Exception as first_error:
            print(f"SHAP GradientExplainer con modelo Keras fallo: {first_error}")
            explainer = shap.GradientExplainer((model.input, model.output), background_images)

        shap_values = explainer.shap_values(np.expand_dims(image, axis=0))
        shap_array = extract_shap_array(shap_values)

        signed_map = np.mean(shap_array, axis=-1)
        max_abs = float(np.max(np.abs(signed_map)))
        if max_abs > 0:
            signed_map = signed_map / max_abs

        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        axes[0].imshow(image)
        axes[0].set_title("Imagen original")
        axes[0].axis("off")

        im = axes[1].imshow(signed_map, cmap="coolwarm", vmin=-1, vmax=1)
        axes[1].set_title("Mapa SHAP")
        axes[1].axis("off")
        fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

        axes[2].imshow(image)
        axes[2].imshow(signed_map, cmap="coolwarm", alpha=0.45, vmin=-1, vmax=1)
        axes[2].set_title("Overlay SHAP")
        axes[2].axis("off")

        fig.suptitle(build_title("SHAP", true_label, predicted_label, score))
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True, None
    except Exception as exc:
        print(f"SHAP no pudo ejecutarse para {output_path.name}: {exc}")
        return False, str(exc)


def make_summary_row(case, method, image_path):
    return {
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "true_label": case["true_label"],
        "predicted_label": case["predicted_label"],
        "score": case["score"],
        "threshold": case["threshold"],
        "method": method,
        "image_path": str(image_path),
    }


def write_summary(rows, output_dir):
    columns = [
        "case_id",
        "case_type",
        "true_label",
        "predicted_label",
        "score",
        "threshold",
        "method",
        "image_path",
    ]
    summary_path = Path(output_dir) / "explanation_summary.csv"
    pd.DataFrame(rows, columns=columns).to_csv(summary_path, index=False)
    print(f"Resumen guardado en: {summary_path}")


def methods_to_run(method):
    if method == "both":
        return ["lime", "shap"]
    return [method]


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    output_dir = Path(args.output_dir)

    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    output_dir.mkdir(parents=True, exist_ok=True)

    import tensorflow as tf

    from src.data import load_malaria_splits

    print(f"Cargando modelo: {checkpoint}")
    model = tf.keras.models.load_model(checkpoint)

    print("Cargando splits de malaria desde TensorFlow Datasets...")
    ds_train, _, ds_test, ds_info = load_malaria_splits(
        img_size=args.img_size,
        batch_size=args.batch_size,
        augment=False,
    )

    class_names = list(ds_info.features["label"].names)
    if len(class_names) != 2:
        raise ValueError(f"Se esperaban 2 clases, pero se encontraron: {class_names}")
    if class_names != ["parasitized", "uninfected"]:
        print(f"Orden de clases detectado desde TFDS: {class_names}")
    else:
        print("Orden de clases: ['parasitized', 'uninfected']")

    for method in methods_to_run(args.method):
        for case_type in CASE_TYPES:
            (output_dir / method / case_type).mkdir(parents=True, exist_ok=True)

    print("Calculando predicciones y reteniendo candidatos para explicabilidad...")
    y_true, y_pred, y_score, candidate_images = collect_prediction_candidates(
        model=model,
        dataset=ds_test,
        num_samples=args.num_samples,
        threshold=args.threshold,
    )

    cases = select_explanation_cases(
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_score,
        images=candidate_images,
        class_names=class_names,
        num_samples=args.num_samples,
        threshold=args.threshold,
    )
    print(f"Casos seleccionados: {len(cases)}")

    background_images = None
    if "shap" in methods_to_run(args.method):
        print("Preparando background de entrenamiento para SHAP...")
        background_images = collect_background_images(ds_train, max_images=20)
        print(f"Imagenes de background SHAP: {len(background_images)}")

    summary_rows = []
    for case_number, case in enumerate(cases, start=1):
        print(
            f"Explicando caso {case_number}/{len(cases)} "
            f"({case['case_type']}, real={case['true_label']}, "
            f"pred={case['predicted_label']}, score={case['score']:.4f})"
        )

        if args.method in {"lime", "both"}:
            output_path = build_output_path(output_dir, "lime", case)
            explain_with_lime(
                model=model,
                image=case["image"],
                class_names=class_names,
                output_path=output_path,
                true_label=case["true_label"],
                predicted_label=case["predicted_label"],
                score=case["score"],
            )
            summary_rows.append(make_summary_row(case, "lime", output_path))

        if args.method in {"shap", "both"}:
            output_path = build_output_path(output_dir, "shap", case)
            success, _ = explain_with_shap(
                model=model,
                background_images=background_images,
                image=case["image"],
                class_names=class_names,
                output_path=output_path,
                true_label=case["true_label"],
                predicted_label=case["predicted_label"],
                score=case["score"],
            )
            if success:
                summary_rows.append(make_summary_row(case, "shap", output_path))

    write_summary(summary_rows, output_dir)
    print("Explicabilidad finalizada.")


if __name__ == "__main__":
    main()
