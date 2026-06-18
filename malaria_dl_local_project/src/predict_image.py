import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

from src.config import CLASS_NAMES, OUTPUT_DIR, PROJECT_ROOT
from src.decision import (
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    build_prediction_response,
    probabilities_by_class_from_prediction,
)


EXTERNAL_PREDICTIONS_CSV = OUTPUT_DIR / "predictions" / "external_predictions.csv"
EXTERNAL_EXPLAINABILITY_DIR = OUTPUT_DIR / "explainability" / "external_predictions"


def parse_args():
    parser = argparse.ArgumentParser(description="Evalua una imagen individual con un modelo Keras.")
    parser.add_argument("--checkpoint", required=True, help="Ruta al modelo .keras entrenado.")
    parser.add_argument("--image-path", required=True, help="Ruta a la imagen a evaluar.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--positive-label",
        default=POSITIVE_LABEL,
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
        "--explain",
        choices=["gradcam", "lime", "shap", "all"],
        default=None,
        help="Generar explicabilidad visual para la imagen externa.",
    )
    parser.add_argument(
        "--tta",
        action="store_true",
        help="Usar Test Time Augmentation para la imagen externa.",
    )
    parser.add_argument("--n-aug", type=int, default=8, help="Cantidad de aumentos para --tta.")
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


def model_name_from_checkpoint_path(checkpoint):
    try:
        from src.tracking_integration import model_name_from_checkpoint

        return model_name_from_checkpoint(checkpoint)
    except Exception:
        checkpoint = Path(checkpoint)
        return checkpoint.parent.name or checkpoint.stem


def probability_rows_from_predictions(predictions):
    predictions = np.asarray(predictions, dtype=np.float32)
    if predictions.ndim == 2 and predictions.shape[1] == len(CLASS_NAMES):
        return [
            probabilities_by_class_from_prediction(row.reshape(1, -1), CLASS_NAMES)
            for row in predictions
        ]

    return [
        probabilities_by_class_from_prediction(np.asarray([score], dtype=np.float32), CLASS_NAMES)
        for score in predictions.reshape(-1)
    ]


def predict_without_tta(model, image_batch):
    prediction = model.predict(image_batch, verbose=0)
    probabilities_by_class = probabilities_by_class_from_prediction(prediction, CLASS_NAMES)
    return {
        "raw_model_output": np.asarray(prediction).tolist(),
        "probability_parasitized": probabilities_by_class[POSITIVE_LABEL],
        "probability_uninfected": probabilities_by_class[NEGATIVE_LABEL],
        "tta_predictions": None,
    }


def predict_with_tta(model, image_batch, n_aug):
    from src.data import build_augmentation

    augmentation = build_augmentation()
    image = image_batch[0]
    augmented_images = [image]

    for _ in range(int(n_aug)):
        augmented = augmentation(image, training=True)
        augmented_images.append(np.asarray(augmented, dtype=np.float32))

    tta_batch = np.asarray(augmented_images, dtype=np.float32)
    predictions = model.predict(tta_batch, verbose=0)
    probability_rows = probability_rows_from_predictions(predictions)
    probability_parasitized = float(
        np.mean([row[POSITIVE_LABEL] for row in probability_rows])
    )
    probability_uninfected = float(1.0 - probability_parasitized)

    return {
        "raw_model_output": np.asarray(predictions).tolist(),
        "probability_parasitized": probability_parasitized,
        "probability_uninfected": probability_uninfected,
        "tta_predictions": probability_rows,
    }


def methods_to_run(method):
    if method == "all":
        return ["gradcam", "lime", "shap"]
    return [method] if method else []


def explanation_output_path(method, image_id):
    from src.prediction_uploads import normalize_filename_part

    method_dir = EXTERNAL_EXPLAINABILITY_DIR / method
    method_dir.mkdir(parents=True, exist_ok=True)
    safe_id = normalize_filename_part(image_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return method_dir / f"{timestamp}_{safe_id}_{method}.png"


def relative_to_project(path):
    path = Path(path)
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def run_external_explanations(args, model, image_batch, response):
    if not args.explain:
        return {
            "method": None,
            "success": False,
            "image_path": None,
            "last_conv_layer": None,
            "error": None,
        }

    image = image_batch[0]
    image_id = response.get("image_id") or Path(response["image_path"]).stem
    methods = methods_to_run(args.explain)
    items = []

    for method in methods:
        output_path = explanation_output_path(method, image_id)
        item = {
            "method": method,
            "success": False,
            "image_path": relative_to_project(output_path),
            "last_conv_layer": None,
            "error": None,
        }
        try:
            if method == "gradcam":
                from src.explain import build_title, explain_with_gradcam

                pred_idx = CLASS_NAMES.index(response["predicted_label"])
                success, error, last_conv_layer = explain_with_gradcam(
                    model=model,
                    image=image,
                    pred_idx=pred_idx,
                    output_path=output_path,
                    title=build_title(
                        "Grad-CAM",
                        true_label=response.get("true_label"),
                        predicted_label=response["predicted_label"],
                        score=response["probability_parasitized"],
                    ),
                    invert_scalar_output=response["predicted_label"] == POSITIVE_LABEL,
                )
                item.update(
                    {
                        "success": bool(success),
                        "error": error,
                        "last_conv_layer": last_conv_layer,
                    }
                )
            elif method == "lime":
                from src.explain import explain_with_lime

                explain_with_lime(
                    model=model,
                    image=image,
                    class_names=CLASS_NAMES,
                    output_path=output_path,
                    true_label=response.get("true_label"),
                    predicted_label=response["predicted_label"],
                    score=response["probability_parasitized"],
                    positive_idx=CLASS_NAMES.index(POSITIVE_LABEL),
                )
                item["success"] = True
            elif method == "shap":
                from src.explain import explain_with_shap

                background = np.stack([np.zeros_like(image), image], axis=0)
                success, error = explain_with_shap(
                    model=model,
                    background_images=background,
                    image=image,
                    class_names=CLASS_NAMES,
                    output_path=output_path,
                    true_label=response.get("true_label"),
                    predicted_label=response["predicted_label"],
                    score=response["probability_parasitized"],
                )
                item.update({"success": bool(success), "error": error})
        except Exception as exc:
            item["success"] = False
            item["error"] = str(exc)
        items.append(item)

    successful = [item for item in items if item["success"]]
    if len(items) == 1:
        return items[0]

    primary = successful[0] if successful else items[0]
    return {
        "method": args.explain,
        "success": bool(successful),
        "image_path": primary.get("image_path") if successful else None,
        "last_conv_layer": primary.get("last_conv_layer"),
        "error": None if successful else "; ".join(item.get("error") or "" for item in items),
        "items": items,
    }


def build_result(args, image_path, stored_image, checkpoint, prediction_result):
    stored_image_path = stored_image.relative_path if stored_image is not None else None
    response_image_path = stored_image_path or str(image_path)
    model_name = model_name_from_checkpoint_path(checkpoint)
    probability_parasitized = prediction_result["probability_parasitized"]
    probability_uninfected = prediction_result["probability_uninfected"]
    predicted_label = (
        POSITIVE_LABEL
        if probability_parasitized >= float(args.threshold)
        else NEGATIVE_LABEL
    )

    is_correct = None
    if args.true_label is not None:
        if args.true_label not in CLASS_NAMES:
            raise ValueError(f"--true-label debe ser una de estas clases: {CLASS_NAMES}")
        is_correct = args.true_label == predicted_label

    extra = {
        "checkpoint": str(checkpoint),
        "image_id": args.image_id
        or (stored_image.image_id if stored_image is not None else Path(image_path).stem),
        "class_names": CLASS_NAMES,
        "positive_label": args.positive_label,
        "true_label": args.true_label,
        "is_correct": is_correct,
        "score_positive_label": probability_parasitized,
        "scores_by_class": {
            POSITIVE_LABEL: probability_parasitized,
            NEGATIVE_LABEL: probability_uninfected,
        },
        "raw_model_output": prediction_result["raw_model_output"],
        "tta": bool(args.tta),
        "n_aug": int(args.n_aug) if args.tta else 0,
        "tta_predictions": prediction_result["tta_predictions"],
    }

    if stored_image is not None:
        extra.update(
            {
                "original_image_path": str(stored_image.source_path),
                "stored_image_path": stored_image.relative_path,
                "original_filename": stored_image.original_filename,
                "stored_filename": stored_image.stored_filename,
                "checksum_sha256": stored_image.checksum_sha256,
                "mime_type": stored_image.mime_type,
                "file_size_bytes": stored_image.file_size_bytes,
            }
        )

    response = build_prediction_response(
        image_path=str(image_path),
        stored_image_path=stored_image_path,
        model_checkpoint=str(checkpoint),
        model_name=model_name,
        probability_parasitized=probability_parasitized,
        threshold=args.threshold,
        extra=extra,
    )
    response["predicted_label"] = predicted_label
    return response


def print_result(result):
    print(f"Imagen evaluada: {result['image_path']}")
    if result.get("stored_image_path"):
        print(f"Imagen almacenada: {result['stored_image_path']}")
    print(f"Modelo: {result['model_checkpoint']}")
    print(f"Probabilidad parasitized: {result['probability_parasitized']:.6f}")
    print(f"Probabilidad uninfected: {result['probability_uninfected']:.6f}")
    print(f"Umbral: {result['threshold']:.2f}")
    print(f"Predicción: {result['predicted_label']}")
    print(f"Confianza: {result['confidence_level']}")
    print(f"Respuesta: {result['human_readable_response']}")
    explanation = result.get("explainability") or {}
    explanation_path = explanation.get("image_path")
    print(f"Explicabilidad: {explanation_path or 'no solicitada'}")
    tracking = result.get("tracking") or {}
    if tracking.get("track_db"):
        print("Tracking DB: registrado" if tracking.get("registered") else "Tracking DB: no registrado")
    else:
        print("Tracking DB: no solicitado")


def save_json(result, output_json):
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resultado JSON guardado en: {output_path}")


def flatten_explainability_for_csv(explainability):
    if not explainability:
        return None, None
    if explainability.get("method") == "all":
        items = explainability.get("items") or []
        methods = ",".join(item.get("method", "") for item in items)
        paths = ",".join(
            item.get("image_path", "")
            for item in items
            if item.get("success") and item.get("image_path")
        )
        return methods or "all", paths or None
    return explainability.get("method"), explainability.get("image_path")


def append_external_prediction_csv(result):
    EXTERNAL_PREDICTIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    explainability_method, explainability_path = flatten_explainability_for_csv(
        result.get("explainability")
    )
    tracking = result.get("tracking") or {}
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "image_path": result["image_path"],
        "stored_image_path": result.get("stored_image_path"),
        "model_checkpoint": result["model_checkpoint"],
        "predicted_label": result["predicted_label"],
        "probability_parasitized": result["probability_parasitized"],
        "probability_uninfected": result["probability_uninfected"],
        "threshold": result["threshold"],
        "confidence_level": result["confidence_level"],
        "decision": result["decision"],
        "explainability_method": explainability_method,
        "explainability_path": explainability_path,
        "track_db": tracking.get("track_db", False),
        "prediction_id": tracking.get("prediction_id"),
    }

    write_header = not EXTERNAL_PREDICTIONS_CSV.exists()
    with EXTERNAL_PREDICTIONS_CSV.open("a", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def explainability_items(explainability):
    if not explainability:
        return []
    if not explainability.get("method"):
        return []
    if explainability.get("method") == "all":
        return explainability.get("items") or []
    return [explainability]


def track_prediction(args, result, checkpoint):
    context = None
    tracking_result = {
        "track_db": bool(args.track_db),
        "registered": False,
        "run_id": None,
        "prediction_id": None,
        "error": None,
    }
    if not args.track_db:
        return tracking_result

    try:
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
            run_name=f"uploaded_prediction:{result['image_id']}",
            parameters=args_to_parameters(
                args,
                extra={
                    "checkpoint": str(checkpoint),
                    "image_path": result["image_path"],
                    "stored_image_path": result.get("stored_image_path"),
                    "original_image_path": result.get("original_image_path"),
                    "stored_filename": result.get("stored_filename"),
                    "class_names": CLASS_NAMES,
                    "prediction_source": "uploaded_for_prediction",
                    "probability_parasitized": result["probability_parasitized"],
                    "probability_uninfected": result["probability_uninfected"],
                    "confidence_level": result["confidence_level"],
                    "decision": result["decision"],
                    "explainability_method": args.explain,
                    "explainability": result.get("explainability"),
                    "tta": bool(args.tta),
                    "n_aug": int(args.n_aug) if args.tta else 0,
                },
            ),
        )

        tracker = context["tracker"]
        run_id = context.get("run_id")
        tracking_result["run_id"] = run_id
        if not run_id:
            tracking_result["error"] = "No se pudo iniciar run en PostgreSQL."
            return tracking_result

        case_type = "unknown"
        if result["true_label"] is not None:
            case_type = tracker.compute_case_type(
                result["true_label"],
                result["predicted_label"],
                positive_label=POSITIVE_LABEL,
            )

        prediction_id = tracker.safe_track(
            tracker.log_prediction,
            run_id,
            dataset_id=context.get("dataset_id"),
            image_id=result["image_id"],
            image_path=result.get("stored_image_path") or result["image_path"],
            true_label=result["true_label"],
            predicted_label=result["predicted_label"],
            score=result["probability_parasitized"],
            score_positive_label=result["probability_parasitized"],
            threshold=result["threshold"],
            is_correct=result["is_correct"],
            case_type=case_type,
            metadata={
                "source": "uploaded_for_prediction",
                "original_image_path": result.get("original_image_path"),
                "original_filename": result.get("original_filename"),
                "stored_filename": result.get("stored_filename"),
                "checksum_sha256": result.get("checksum_sha256"),
                "probability_parasitized": result["probability_parasitized"],
                "probability_uninfected": result["probability_uninfected"],
                "confidence_level": result["confidence_level"],
                "decision": result["decision"],
                "scores_by_class": result["scores_by_class"],
                "raw_model_output": result["raw_model_output"],
                "tta": bool(args.tta),
                "n_aug": int(args.n_aug) if args.tta else 0,
            },
        )
        tracking_result["prediction_id"] = prediction_id

        if result.get("stored_image_path"):
            tracker.safe_track(
                tracker.log_artifact,
                run_id,
                artifact_type="uploaded_input_image",
                name=result.get("stored_filename"),
                path=result["stored_image_path"],
                mime_type=result.get("mime_type"),
                file_size_bytes=result.get("file_size_bytes"),
                checksum=result.get("checksum_sha256"),
                metadata={
                    "source": "uploaded_for_prediction",
                    "original_image_path": result.get("original_image_path"),
                    "original_filename": result.get("original_filename"),
                    "stored_filename": result.get("stored_filename"),
                    "image_id": result["image_id"],
                },
            )

        for item in explainability_items(result.get("explainability")):
            output_path = item.get("image_path") if item.get("success") else None
            tracker.safe_track(
                tracker.log_explainability_result,
                run_id,
                prediction_id=prediction_id,
                method=item.get("method"),
                image_path=result.get("stored_image_path") or result["image_path"],
                output_path=output_path,
                true_label=result.get("true_label"),
                predicted_label=result["predicted_label"],
                score=result["probability_parasitized"],
                case_type=case_type,
                last_conv_layer=item.get("last_conv_layer"),
                explanation_parameters={
                    "source": "external_prediction",
                    "output_dir": str(EXTERNAL_EXPLAINABILITY_DIR),
                },
                success=bool(item.get("success")),
                error_message=item.get("error"),
                metadata={"source": "uploaded_for_prediction"},
            )
            if output_path and Path(output_path).exists():
                tracker.safe_track(
                    tracker.log_artifact,
                    run_id,
                    artifact_type=f"{item.get('method')}_image",
                    name=Path(output_path).name,
                    path=str(output_path),
                    mime_type="image/png",
                    metadata={"source": "external_prediction_explainability"},
                )

        finish_tracking_run(
            context,
            metadata={
                "status_detail": "single image inference completed",
                "confidence_level": result["confidence_level"],
                "decision": result["decision"],
                "probability_parasitized": result["probability_parasitized"],
                "probability_uninfected": result["probability_uninfected"],
            },
        )
        tracking_result["registered"] = prediction_id is not None
        return tracking_result
    except Exception as exc:
        tracking_result["error"] = str(exc)
        try:
            fail_tracking_run(context, exc, script_name="src.predict_image")
        except Exception:
            pass
        print(f"Warning: tracking PostgreSQL no disponible: {exc}")
        return tracking_result


def main():
    args = parse_args()
    checkpoint = Path(args.checkpoint).expanduser()
    image_path = Path(args.image_path).expanduser()
    stored_image = None

    if args.positive_label != POSITIVE_LABEL:
        raise ValueError(
            f"Este flujo estructurado usa {POSITIVE_LABEL!r} como clase positiva clínica."
        )
    if not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")
    if not image_path.exists():
        raise FileNotFoundError(f"No existe la imagen: {image_path}")

    model = tf.keras.models.load_model(checkpoint)

    prediction_image_path = image_path
    if args.track_db:
        from src.prediction_uploads import store_prediction_image

        stored_image = store_prediction_image(image_path, image_id=args.image_id)
        prediction_image_path = stored_image.stored_path

    image_batch = load_image(prediction_image_path, args.img_size)
    prediction_result = (
        predict_with_tta(model, image_batch, args.n_aug)
        if args.tta
        else predict_without_tta(model, image_batch)
    )
    result = build_result(args, image_path, stored_image, checkpoint, prediction_result)
    result["explainability"] = run_external_explanations(args, model, image_batch, result)
    result["tracking"] = track_prediction(args, result, checkpoint)

    print_result(result)

    if args.output_json:
        save_json(result, args.output_json)

    append_external_prediction_csv(result)
    print(f"Predicción acumulada en: {EXTERNAL_PREDICTIONS_CSV}")


if __name__ == "__main__":
    main()
