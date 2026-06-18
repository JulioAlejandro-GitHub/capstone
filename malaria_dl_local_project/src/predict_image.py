import argparse
import json
import mimetypes
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

from src.config import CLASS_NAMES


def parse_args():
    parser = argparse.ArgumentParser(description="Evalua una imagen individual con un modelo Keras.")
    parser.add_argument("--checkpoint", required=True, help="Ruta al modelo .keras entrenado.")
    parser.add_argument("--image-path", required=True, help="Ruta a la imagen a evaluar.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--positive-label",
        default="parasitized",
        help="Clase clinicamente positiva para reportar score y decision.",
    )
    parser.add_argument(
        "--true-label",
        default=None,
        help="Clase real opcional. Si se informa, calcula tipo de caso TP/TN/FP/FN.",
    )
    parser.add_argument("--image-id", default=None, help="ID opcional para registrar la imagen.")
    parser.add_argument("--output-json", default=None, help="Ruta opcional para guardar el resultado JSON.")
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta inferencia individual en PostgreSQL.",
    )
    return parser.parse_args()


def load_image(image_path, img_size):
    image = Image.open(image_path).convert("RGB")
    image = np.asarray(image, dtype=np.float32)
    image = tf.image.resize(image, (img_size, img_size))
    image = image.numpy().astype(np.float32) / 255.0
    return np.expand_dims(image, axis=0)


def probabilities_from_prediction(prediction, class_names):
    prediction = np.asarray(prediction, dtype=np.float32)

    if prediction.ndim == 2 and prediction.shape[1] == len(class_names):
        probabilities = prediction[0]
    elif prediction.size == 1 and len(class_names) == 2:
        score_class_1 = float(prediction.reshape(-1)[0])
        probabilities = np.asarray([1.0 - score_class_1, score_class_1], dtype=np.float32)
    else:
        raise ValueError(
            f"Salida de modelo no soportada para {len(class_names)} clases: shape={prediction.shape}"
        )

    return np.clip(probabilities, 0.0, 1.0)


def predict_label(probabilities, class_names, positive_label, threshold):
    if positive_label not in class_names:
        raise ValueError(f"--positive-label debe ser una de estas clases: {class_names}")
    if len(class_names) != 2:
        raise ValueError("Este script soporta clasificacion binaria.")

    positive_idx = class_names.index(positive_label)
    negative_idx = 1 - positive_idx
    score_positive_label = float(probabilities[positive_idx])
    predicted_idx = positive_idx if score_positive_label >= threshold else negative_idx

    return {
        "predicted_label": class_names[predicted_idx],
        "predicted_index": int(predicted_idx),
        "positive_label": positive_label,
        "score_positive_label": score_positive_label,
        "threshold": float(threshold),
    }


def build_result(args, image_path, checkpoint, prediction, probabilities):
    decision = predict_label(
        probabilities=probabilities,
        class_names=CLASS_NAMES,
        positive_label=args.positive_label,
        threshold=args.threshold,
    )
    scores_by_class = {
        class_name: float(probabilities[index])
        for index, class_name in enumerate(CLASS_NAMES)
    }
    result = {
        "checkpoint": str(checkpoint),
        "image_path": str(image_path),
        "image_id": args.image_id or image_path.stem,
        "class_names": CLASS_NAMES,
        "scores_by_class": scores_by_class,
        "raw_model_output": np.asarray(prediction).tolist(),
        **decision,
    }

    if args.true_label is not None:
        if args.true_label not in CLASS_NAMES:
            raise ValueError(f"--true-label debe ser una de estas clases: {CLASS_NAMES}")
        result["true_label"] = args.true_label
        result["is_correct"] = args.true_label == result["predicted_label"]
    else:
        result["true_label"] = None
        result["is_correct"] = None

    return result


def print_result(result):
    print("Resultado de inferencia individual")
    print(f"  imagen: {result['image_path']}")
    print(f"  checkpoint: {result['checkpoint']}")
    print(f"  clase positiva: {result['positive_label']}")
    print(f"  prediccion: {result['predicted_label']}")
    print(f"  score positivo: {result['score_positive_label']:.6f}")
    print(f"  threshold: {result['threshold']:.6f}")
    print("  scores por clase:")
    for class_name, score in result["scores_by_class"].items():
        print(f"    {class_name}: {score:.6f}")
    if result["true_label"] is not None:
        print(f"  clase real: {result['true_label']}")
        print(f"  correcto: {result['is_correct']}")


def save_json(result, output_json):
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resultado JSON guardado en: {output_path}")


def track_prediction(args, result, checkpoint, image_path):
    from src.tracking_integration import (
        args_to_parameters,
        fail_tracking_run,
        finish_tracking_run,
        model_name_from_checkpoint,
        start_tracking_run,
    )

    context = start_tracking_run(
        args=args,
        run_type="inference",
        script_name="src.predict_image",
        model_name=model_name_from_checkpoint(checkpoint),
        run_name=f"predict_image:{image_path.stem}",
        parameters=args_to_parameters(
            args,
            extra={
                "checkpoint": str(checkpoint),
                "image_path": str(image_path),
                "class_names": CLASS_NAMES,
            },
        ),
    )

    try:
        tracker = context["tracker"]
        run_id = context.get("run_id")
        if run_id:
            case_type = "unknown"
            if result["true_label"] is not None:
                case_type = tracker.compute_case_type(
                    result["true_label"],
                    result["predicted_label"],
                    positive_label=result["positive_label"],
                )

            tracker.safe_track(
                tracker.log_prediction,
                run_id,
                dataset_id=context.get("dataset_id"),
                image_id=result["image_id"],
                image_path=str(image_path),
                true_label=result["true_label"],
                predicted_label=result["predicted_label"],
                score=result["score_positive_label"],
                score_positive_label=result["score_positive_label"],
                threshold=result["threshold"],
                is_correct=result["is_correct"],
                case_type=case_type,
                metadata={
                    "source": "external_image",
                    "scores_by_class": result["scores_by_class"],
                    "raw_model_output": result["raw_model_output"],
                },
            )
            tracker.safe_track(
                tracker.log_artifact,
                run_id,
                artifact_type="input_image",
                name=image_path.name,
                path=str(image_path),
                mime_type=mimetypes.guess_type(image_path)[0],
            )
            finish_tracking_run(context, metadata={"status_detail": "single image inference completed"})
    except Exception as exc:
        fail_tracking_run(context, exc, script_name="src.predict_image")
        raise


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint)
    image_path = Path(args.image_path)

    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")
    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    model = tf.keras.models.load_model(checkpoint)
    image_batch = load_image(image_path, args.img_size)
    prediction = model.predict(image_batch, verbose=0)
    probabilities = probabilities_from_prediction(prediction, CLASS_NAMES)
    result = build_result(args, image_path, checkpoint, prediction, probabilities)

    print_result(result)

    if args.output_json:
        save_json(result, args.output_json)

    if args.track_db:
        track_prediction(args, result, checkpoint, image_path)


if __name__ == "__main__":
    main()
