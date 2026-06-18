import argparse
import heapq
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocessing import (
    PREPROCESSING_CHOICES,
    PREPROCESSING_RESCALE_0_1,
    PREPROCESSING_VGG16_IMAGENET,
    apply_model_preprocessing,
    resolve_preprocessing_mode,
)


CASE_TYPES = [
    "true_positive",
    "true_negative",
    "false_positive",
    "false_negative",
    "low_confidence",
]

SUMMARY_COLUMNS = [
    "case_id",
    "case_type",
    "true_label",
    "predicted_label",
    "score_positive_label",
    "positive_label",
    "threshold",
    "method",
    "success",
    "error",
    "image_path",
    "last_conv_layer",
]


def get_pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def get_model_output_tensor(model):
    try:
        return model.output
    except AttributeError:
        outputs = getattr(model, "outputs", None)
        if outputs:
            return outputs[0] if len(outputs) == 1 else outputs
        raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera explicaciones visuales post hoc con LIME, SHAP y Grad-CAM."
    )
    parser.add_argument("--checkpoint", required=True, help="Ruta al modelo .keras entrenado")
    parser.add_argument(
        "--method",
        choices=["lime", "shap", "gradcam", "both", "all"],
        required=True,
        help="'both' ejecuta LIME + SHAP; 'all' ejecuta LIME + SHAP + Grad-CAM.",
    )
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-samples", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--output-dir", default="outputs/explainability")
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help=(
            "Modo de preprocesamiento usado por el checkpoint. 'auto' mantiene "
            "compatibilidad con checkpoints existentes."
        ),
    )
    parser.add_argument(
        "--positive-label",
        default="parasitized",
        help=(
            "Clase clínica interpretada como positiva. Por defecto: parasitized."
        ),
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=200,
        help="Máximo de imágenes candidatas retenidas por tipo de caso.",
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args()


def methods_to_run(method):
    if method == "both":
        return ["lime", "shap"]
    if method == "all":
        return ["lime", "shap", "gradcam"]
    return [method]


def resolve_positive_label(class_names, positive_label):
    if len(class_names) != 2:
        raise ValueError(f"Se esperaban 2 clases, pero se encontraron: {class_names}")

    if positive_label is None:
        positive_idx = 1
        positive_label = class_names[positive_idx]
    else:
        if positive_label not in class_names:
            raise ValueError(
                f"--positive-label debe ser una de estas clases: {class_names}. "
                f"Valor recibido: {positive_label}"
            )
        positive_idx = class_names.index(positive_label)

    negative_idx = 1 - positive_idx
    return positive_idx, negative_idx, positive_label


def raw_model_predictions(model, images):
    predictions = model.predict(images, verbose=0)
    return np.asarray(predictions, dtype=np.float32)


def scores_from_predictions(predictions, positive_idx):
    predictions = np.asarray(predictions, dtype=np.float32)
    if predictions.ndim == 2 and predictions.shape[1] == 2:
        scores = predictions[:, positive_idx]
    else:
        scores = predictions.reshape(-1)
        if int(positive_idx) == 0:
            scores = 1.0 - scores
    return np.clip(scores.astype(np.float32), 0.0, 1.0)


def predict_positive_scores(model, images, positive_idx):
    return scores_from_predictions(raw_model_predictions(model, images), positive_idx)


def model_image_to_display(image, preprocessing_mode=PREPROCESSING_RESCALE_0_1):
    mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    image = np.asarray(image, dtype=np.float32)

    if mode == PREPROCESSING_VGG16_IMAGENET:
        bgr_image = image.copy()
        bgr_image[..., 0] += 103.939
        bgr_image[..., 1] += 116.779
        bgr_image[..., 2] += 123.68
        rgb_image = bgr_image[..., ::-1]
        return np.clip(rgb_image / 255.0, 0.0, 1.0).astype(np.float32)

    return np.clip(image, 0.0, 1.0).astype(np.float32)


def display_images_to_model_inputs(images, preprocessing_mode=PREPROCESSING_RESCALE_0_1):
    mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    images = np.asarray(images, dtype=np.float32)
    images = np.clip(images, 0.0, 1.0)

    if mode == PREPROCESSING_VGG16_IMAGENET:
        return apply_model_preprocessing(images * 255.0, mode).numpy().astype(np.float32)

    return images.astype(np.float32)


def binary_predict_proba(
    model,
    images,
    positive_idx,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
):
    images = np.asarray(images, dtype=np.float32)
    model_images = display_images_to_model_inputs(images, preprocessing_mode)
    predictions = raw_model_predictions(model, model_images)

    if predictions.ndim == 2 and predictions.shape[1] == 2:
        return np.clip(predictions, 0.0, 1.0)

    p_positive = scores_from_predictions(predictions, positive_idx)
    probabilities = np.zeros((len(p_positive), 2), dtype=np.float32)
    probabilities[:, positive_idx] = p_positive
    probabilities[:, 1 - positive_idx] = 1.0 - p_positive
    return probabilities


def predicted_labels_from_scores(y_score, positive_idx, negative_idx, threshold):
    return np.where(y_score >= threshold, positive_idx, negative_idx).astype(int)


def get_case_type(true_label, predicted_label, positive_idx, negative_idx):
    if true_label == positive_idx and predicted_label == positive_idx:
        return "true_positive"
    if true_label == negative_idx and predicted_label == negative_idx:
        return "true_negative"
    if true_label == negative_idx and predicted_label == positive_idx:
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


def collect_prediction_candidates(
    model,
    dataset,
    num_samples,
    threshold,
    positive_idx,
    negative_idx,
    max_candidates,
):
    y_true = []
    y_pred = []
    y_score = []

    pool_limit = max(1, int(max_candidates))
    if pool_limit < num_samples:
        print(
            f"Advertencia: --max-candidates ({pool_limit}) es menor que "
            f"--num-samples ({num_samples}); podrían seleccionarse menos casos."
        )

    candidate_heaps = {case_type: [] for case_type in CASE_TYPES}

    sample_index = 0
    for batch_index, (images, labels) in enumerate(dataset, start=1):
        scores = predict_positive_scores(model, images, positive_idx)
        labels_np = labels.numpy().astype(int)
        images_np = images.numpy()
        predictions = predicted_labels_from_scores(
            scores,
            positive_idx=positive_idx,
            negative_idx=negative_idx,
            threshold=threshold,
        )

        for image, true_label, predicted_label, score in zip(
            images_np, labels_np, predictions, scores
        ):
            true_label = int(true_label)
            predicted_label = int(predicted_label)
            score = float(score)
            case_type = get_case_type(
                true_label,
                predicted_label,
                positive_idx=positive_idx,
                negative_idx=negative_idx,
            )

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


def sorted_indices_for_case(
    case_type,
    y_true,
    y_pred,
    y_score,
    threshold,
    positive_idx,
    negative_idx,
):
    if case_type == "true_positive":
        indices = np.where((y_true == positive_idx) & (y_pred == positive_idx))[0]
        order = np.argsort(-y_score[indices])
    elif case_type == "true_negative":
        indices = np.where((y_true == negative_idx) & (y_pred == negative_idx))[0]
        order = np.argsort(y_score[indices])
    elif case_type == "false_positive":
        indices = np.where((y_true == negative_idx) & (y_pred == positive_idx))[0]
        order = np.argsort(-y_score[indices])
    elif case_type == "false_negative":
        indices = np.where((y_true == positive_idx) & (y_pred == negative_idx))[0]
        order = np.argsort(y_score[indices])
    elif case_type == "low_confidence":
        indices = np.arange(len(y_score))
        order = np.argsort(np.abs(y_score - threshold))
    else:
        raise ValueError(f"Tipo de caso no soportado: {case_type}")

    return indices[order]


def select_cases(
    images,
    y_true,
    y_pred,
    y_score,
    positive_idx,
    negative_idx,
    num_samples,
    threshold,
    class_names=None,
    positive_label=None,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
):
    if num_samples <= 0:
        raise ValueError("--num-samples debe ser mayor que cero")

    if class_names is None:
        class_names = [str(idx) for idx in range(2)]
    if positive_label is None:
        positive_label = class_names[positive_idx]

    selected = []
    selected_indices = set()
    target_per_type = max(1, math.ceil(num_samples / len(CASE_TYPES)))

    def add_case(index, case_type):
        if len(selected) >= num_samples or int(index) in selected_indices:
            return False

        image = get_image_by_index(images, int(index))
        if image is None:
            return False

        true_label_idx = int(y_true[index])
        predicted_label_idx = int(y_pred[index])
        score = float(y_score[index])

        model_image = np.asarray(image, dtype=np.float32).copy()
        display_image = model_image_to_display(model_image, preprocessing_mode)

        selected.append(
            {
                "case_id": int(index),
                "case_type": case_type,
                "true_label": class_names[true_label_idx],
                "predicted_label": class_names[predicted_label_idx],
                "true_label_idx": true_label_idx,
                "predicted_label_idx": predicted_label_idx,
                "score_positive_label": score,
                "positive_label": positive_label,
                "threshold": float(threshold),
                "image": model_image,
                "display_image": display_image,
                "preprocessing_mode": resolve_preprocessing_mode(
                    requested=preprocessing_mode
                ),
            }
        )
        selected_indices.add(int(index))
        return True

    for case_type in CASE_TYPES:
        added_for_type = 0
        for index in sorted_indices_for_case(
            case_type,
            y_true,
            y_pred,
            y_score,
            threshold,
            positive_idx,
            negative_idx,
        ):
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
            case_type = get_case_type(
                int(y_true[index]),
                int(y_pred[index]),
                positive_idx=positive_idx,
                negative_idx=negative_idx,
            )
            add_case(index, case_type)
            if len(selected) >= num_samples:
                break

    return selected


def select_explanation_cases(
    y_true,
    y_pred,
    y_score,
    images,
    class_names,
    num_samples,
    threshold,
    positive_idx=1,
    negative_idx=0,
    positive_label=None,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
):
    return select_cases(
        images=images,
        y_true=y_true,
        y_pred=y_pred,
        y_score=y_score,
        positive_idx=positive_idx,
        negative_idx=negative_idx,
        num_samples=num_samples,
        threshold=threshold,
        class_names=class_names,
        positive_label=positive_label,
        preprocessing_mode=preprocessing_mode,
    )


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
        f"score-{case['score_positive_label']:.4f}.png"
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
    positive_idx=1,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
):
    try:
        from lime import lime_image
        from skimage.segmentation import mark_boundaries, slic
    except ImportError as exc:
        raise ImportError(
            "LIME requiere instalar las dependencias: lime y scikit-image."
        ) from exc

    plt = get_pyplot()
    display_image = model_image_to_display(image, preprocessing_mode)

    def predict_fn(images):
        return binary_predict_proba(
            model,
            images,
            positive_idx=positive_idx,
            preprocessing_mode=preprocessing_mode,
        )

    probabilities = predict_fn(np.expand_dims(display_image, axis=0))[0]
    label_to_explain = predicted_class_index(class_names, predicted_label, probabilities)

    explainer = lime_image.LimeImageExplainer(random_state=42)
    explanation = explainer.explain_instance(
        display_image.astype(np.double),
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
    axes[0].imshow(display_image)
    axes[0].set_title("Imagen original")
    axes[0].axis("off")

    axes[1].imshow(boundary_image)
    axes[1].set_title("Superpixeles LIME")
    axes[1].axis("off")

    axes[2].imshow(display_image)
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
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
):
    try:
        import shap

        plt = get_pyplot()
        background_images = np.asarray(background_images, dtype=np.float32)
        model_image = np.asarray(image, dtype=np.float32)
        display_image = model_image_to_display(model_image, preprocessing_mode)

        if background_images.ndim != 4 or len(background_images) == 0:
            raise ValueError("SHAP requiere al menos una imagen de background.")

        try:
            explainer = shap.GradientExplainer(model, background_images)
        except Exception as first_error:
            print(f"SHAP GradientExplainer con modelo Keras fallo: {first_error}")
            explainer = shap.GradientExplainer(
                (model.inputs, get_model_output_tensor(model)),
                background_images,
            )

        shap_values = explainer.shap_values(np.expand_dims(model_image, axis=0))
        shap_array = extract_shap_array(shap_values)

        signed_map = np.mean(shap_array, axis=-1)
        max_abs = float(np.max(np.abs(signed_map)))
        if max_abs > 0:
            signed_map = signed_map / max_abs

        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        axes[0].imshow(display_image)
        axes[0].set_title("Imagen original")
        axes[0].axis("off")

        im = axes[1].imshow(signed_map, cmap="coolwarm", vmin=-1, vmax=1)
        axes[1].set_title("Mapa SHAP")
        axes[1].axis("off")
        fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

        axes[2].imshow(display_image)
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


def layer_has_rank4_output(layer):
    try:
        output = layer.output
    except (AttributeError, ValueError):
        return False

    if isinstance(output, (list, tuple)):
        if not output:
            return False
        output = output[0]

    shape = getattr(output, "shape", None)
    if shape is None:
        return False

    try:
        return len(shape) == 4
    except TypeError:
        return False


def iter_conv_layer_candidates(model, tf, include_rank4_fallback=False):
    for layer in reversed(model.layers):
        if isinstance(layer, tf.keras.Model):
            yield from iter_conv_layer_candidates(layer, tf, include_rank4_fallback)

        if isinstance(layer, tf.keras.layers.Conv2D):
            yield layer
        elif include_rank4_fallback and layer_has_rank4_output(layer):
            yield layer


def build_gradcam_model(model, target_layer, tf):
    if isinstance(model, tf.keras.Sequential) and target_layer in model.layers:
        try:
            x = model.inputs[0] if len(model.inputs) == 1 else model.inputs
            target_output = None

            for layer in model.layers:
                x = layer(x)
                if layer is target_layer:
                    target_output = x

            if target_output is not None:
                return tf.keras.models.Model(
                    inputs=model.inputs,
                    outputs=[target_output, x],
                )
        except Exception:
            pass

    try:
        return tf.keras.models.Model(
            inputs=model.inputs,
            outputs=[target_layer.output, get_model_output_tensor(model)],
        )
    except Exception as standard_error:
        raise standard_error


def layer_is_connected_to_model(model, layer, tf):
    try:
        build_gradcam_model(model, layer, tf)
        return True
    except Exception:
        return False


def find_last_conv_layer(model):
    import tensorflow as tf

    for include_rank4_fallback in (False, True):
        for layer in iter_conv_layer_candidates(
            model,
            tf,
            include_rank4_fallback=include_rank4_fallback,
        ):
            if layer_is_connected_to_model(model, layer, tf):
                return layer

    raise ValueError("No se encontró una capa convolucional compatible para Grad-CAM.")


def explain_with_gradcam(
    model,
    image,
    pred_idx,
    output_path,
    title,
    last_conv_layer_name=None,
    invert_scalar_output=False,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
):
    import tensorflow as tf

    plt = get_pyplot()
    model_image = np.asarray(image, dtype=np.float32)
    display_image = model_image_to_display(model_image, preprocessing_mode)

    if last_conv_layer_name is None:
        last_conv_layer = find_last_conv_layer(model)
    else:
        last_conv_layer = model.get_layer(last_conv_layer_name)

    print("Última capa convolucional usada para Grad-CAM:", last_conv_layer.name)

    grad_model = build_gradcam_model(model, last_conv_layer, tf)

    image_batch = tf.convert_to_tensor(np.expand_dims(model_image, axis=0), dtype=tf.float32)
    with tf.GradientTape() as tape:
        conv_outputs, model_output = grad_model(image_batch, training=False)
        if len(model_output.shape) >= 2 and model_output.shape[-1] == 1:
            class_channel = 1.0 - model_output[:, 0] if invert_scalar_output else model_output[:, 0]
        elif len(model_output.shape) == 1:
            class_channel = 1.0 - model_output if invert_scalar_output else model_output
        else:
            class_channel = model_output[:, pred_idx]

    grads = tape.gradient(class_channel, conv_outputs)
    if grads is None:
        raise ValueError(
            f"No se pudieron calcular gradientes para la capa {last_conv_layer.name}."
        )

    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)
    heatmap = tf.maximum(heatmap, 0)

    max_value = tf.reduce_max(heatmap)
    heatmap = tf.cond(
        max_value > 0,
        lambda: heatmap / max_value,
        lambda: tf.zeros_like(heatmap),
    )
    heatmap = tf.image.resize(
        heatmap[..., tf.newaxis],
        model_image.shape[:2],
        method="bilinear",
    )
    heatmap = heatmap.numpy().squeeze()

    heatmap_rgb = plt.get_cmap("jet")(heatmap)[..., :3].astype(np.float32)
    overlay = np.clip((0.6 * display_image) + (0.4 * heatmap_rgb), 0.0, 1.0)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(display_image)
    axes[0].set_title("Imagen original")
    axes[0].axis("off")

    im = axes[1].imshow(heatmap, cmap="jet", vmin=0, vmax=1)
    axes[1].set_title("Heatmap Grad-CAM")
    axes[1].axis("off")
    fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)

    axes[2].imshow(overlay)
    axes[2].set_title("Overlay Grad-CAM")
    axes[2].axis("off")

    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    return True, None, last_conv_layer.name


def make_summary_row(
    case,
    method,
    image_path,
    success,
    error=None,
    last_conv_layer=None,
):
    return {
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "true_label": case["true_label"],
        "predicted_label": case["predicted_label"],
        "score_positive_label": case["score_positive_label"],
        "positive_label": case["positive_label"],
        "threshold": case["threshold"],
        "method": method,
        "success": bool(success),
        "error": "" if error is None else str(error),
        "image_path": str(image_path) if success else "",
        "last_conv_layer": "" if last_conv_layer is None else str(last_conv_layer),
    }


def write_summary(rows, output_dir):
    summary_path = Path(output_dir) / "explanation_summary.csv"
    pd.DataFrame(rows, columns=SUMMARY_COLUMNS).to_csv(summary_path, index=False)
    print(f"Resumen guardado en: {summary_path}")


def run_lime(model, class_names, positive_idx, output_dir, case):
    output_path = build_output_path(output_dir, "lime", case)
    try:
        explain_with_lime(
            model=model,
            image=case["image"],
            class_names=class_names,
            output_path=output_path,
            true_label=case["true_label"],
            predicted_label=case["predicted_label"],
            score=case["score_positive_label"],
            positive_idx=positive_idx,
            preprocessing_mode=case.get("preprocessing_mode", PREPROCESSING_RESCALE_0_1),
        )
        return make_summary_row(case, "lime", output_path, success=True)
    except Exception as exc:
        print(f"LIME no pudo ejecutarse para {output_path.name}: {exc}")
        return make_summary_row(case, "lime", output_path, success=False, error=exc)


def run_shap(model, background_images, class_names, output_dir, case):
    output_path = build_output_path(output_dir, "shap", case)
    success, error = explain_with_shap(
        model=model,
        background_images=background_images,
        image=case["image"],
        class_names=class_names,
        output_path=output_path,
        true_label=case["true_label"],
        predicted_label=case["predicted_label"],
        score=case["score_positive_label"],
        preprocessing_mode=case.get("preprocessing_mode", PREPROCESSING_RESCALE_0_1),
    )
    return make_summary_row(
        case,
        "shap",
        output_path,
        success=success,
        error=error,
    )


def run_gradcam(model, output_dir, case):
    output_path = build_output_path(output_dir, "gradcam", case)
    title = build_title(
        "Grad-CAM",
        case["true_label"],
        case["predicted_label"],
        case["score_positive_label"],
    )
    try:
        success, error, last_conv_layer = explain_with_gradcam(
            model=model,
            image=case["image"],
            pred_idx=case["predicted_label_idx"],
            output_path=output_path,
            title=title,
            invert_scalar_output=case["predicted_label_idx"] == 0,
            preprocessing_mode=case.get("preprocessing_mode", PREPROCESSING_RESCALE_0_1),
        )
        return make_summary_row(
            case,
            "gradcam",
            output_path,
            success=success,
            error=error,
            last_conv_layer=last_conv_layer,
        )
    except Exception as exc:
        print(f"Grad-CAM no pudo ejecutarse para {output_path.name}: {exc}")
        return make_summary_row(
            case,
            "gradcam",
            output_path,
            success=False,
            error=exc,
        )


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    output_dir = Path(args.output_dir)
    selected_methods = methods_to_run(args.method)
    run_context = None

    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    preprocessing_mode = resolve_preprocessing_mode(checkpoint.parent.name, args.preprocessing)

    if args.track_db:
        from src.tracking_integration import (
            args_to_parameters,
            model_name_from_checkpoint,
            start_tracking_run,
        )

        run_context = start_tracking_run(
            args=args,
            run_type="explainability",
            script_name="src.explain",
            model_name=model_name_from_checkpoint(checkpoint),
            run_name=f"explain:{checkpoint.stem}:{args.method}",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "selected_methods": selected_methods,
                    "output_dir": str(output_dir),
                    "preprocessing_mode": preprocessing_mode,
                },
            ),
        )

    try:
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
            preprocessing_mode=preprocessing_mode,
        )

        class_names = list(ds_info.features["label"].names)
        positive_idx, negative_idx, positive_label = resolve_positive_label(
            class_names,
            args.positive_label,
        )

        print(f"Orden de clases detectado desde TFDS: {class_names}")
        print(f"Preprocesamiento: {preprocessing_mode}")
        print(
            f"Clase positiva para score sigmoid: {positive_label} "
            f"(índice {positive_idx}); umbral={args.threshold}"
        )

        for method in selected_methods:
            for case_type in CASE_TYPES:
                (output_dir / method / case_type).mkdir(parents=True, exist_ok=True)

        print("Calculando predicciones y reteniendo candidatos para explicabilidad...")
        y_true, y_pred, y_score, candidate_images = collect_prediction_candidates(
            model=model,
            dataset=ds_test,
            num_samples=args.num_samples,
            threshold=args.threshold,
            positive_idx=positive_idx,
            negative_idx=negative_idx,
            max_candidates=args.max_candidates,
        )

        cases = select_explanation_cases(
            y_true=y_true,
            y_pred=y_pred,
            y_score=y_score,
            images=candidate_images,
            class_names=class_names,
            num_samples=args.num_samples,
            threshold=args.threshold,
            positive_idx=positive_idx,
            negative_idx=negative_idx,
            positive_label=positive_label,
            preprocessing_mode=preprocessing_mode,
        )
        print(f"Casos seleccionados: {len(cases)}")

        background_images = None
        if "shap" in selected_methods:
            print("Preparando background de entrenamiento para SHAP...")
            background_images = collect_background_images(ds_train, max_images=20)
            print(f"Imagenes de background SHAP: {len(background_images)}")

        summary_rows = []
        for case_number, case in enumerate(cases, start=1):
            print(
                f"Explicando caso {case_number}/{len(cases)} "
                f"({case['case_type']}, real={case['true_label']}, "
                f"pred={case['predicted_label']}, "
                f"score_{case['positive_label']}={case['score_positive_label']:.4f})"
            )

            for method in selected_methods:
                if method == "lime":
                    summary_rows.append(
                        run_lime(
                            model=model,
                            class_names=class_names,
                            positive_idx=positive_idx,
                            output_dir=output_dir,
                            case=case,
                        )
                    )
                elif method == "shap":
                    summary_rows.append(
                        run_shap(
                            model=model,
                            background_images=background_images,
                            class_names=class_names,
                            output_dir=output_dir,
                            case=case,
                        )
                    )
                elif method == "gradcam":
                    summary_rows.append(
                        run_gradcam(
                            model=model,
                            output_dir=output_dir,
                            case=case,
                        )
                    )
                else:
                    raise ValueError(f"Método no soportado: {method}")

        write_summary(summary_rows, output_dir)

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_explainability_outputs,
            )

            log_explainability_outputs(run_context, cases, summary_rows, output_dir)
            finish_tracking_run(run_context, metadata={"status_detail": "explainability completed"})

        print("Explicabilidad finalizada.")
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.explain")
        raise


if __name__ == "__main__":
    main()
