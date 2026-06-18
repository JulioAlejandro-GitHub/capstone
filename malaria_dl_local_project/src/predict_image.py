import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.config import CLASS_NAMES, OUTPUT_DIR, PROJECT_ROOT
from src.decision import (
    DISCLAIMER,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    build_prediction_response,
)
from src.image_quality import check_image_quality
from src.inference_pipeline import (
    apply_probability_calibration,
    build_structured_clinical_response,
    predict_ensemble_probability,
    predict_model_probability,
    predict_model_probability_with_tta,
    preprocess_external_image,
)
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


EXTERNAL_PREDICTIONS_CSV = OUTPUT_DIR / "predictions" / "external_predictions.csv"
EXTERNAL_EXPLAINABILITY_DIR = OUTPUT_DIR / "explainability" / "external_predictions"


def parse_args():
    parser = argparse.ArgumentParser(description="Evalua una imagen individual con un modelo Keras.")
    parser.add_argument("--checkpoint", default=None, help="Ruta al modelo .keras entrenado.")
    parser.add_argument("--image-path", required=True, help="Ruta a la imagen a evaluar.")
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help=(
            "Modo de preprocesamiento del checkpoint. 'auto' mantiene compatibilidad "
            "con modelos existentes."
        ),
    )
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
        choices=["none", "gradcam", "lime", "shap", "all"],
        default=None,
        help="Generar explicabilidad visual para la imagen externa.",
    )
    parser.add_argument(
        "--tta",
        action="store_true",
        help="Usar Test Time Augmentation para la imagen externa.",
    )
    parser.add_argument("--n-aug", type=int, default=8, help="Cantidad de aumentos para --tta.")
    parser.add_argument("--ensemble", action="store_true", help="Usar ensemble para la imagen externa.")
    parser.add_argument("--models", nargs="+", default=None, help="Modelos .keras para --ensemble.")
    parser.add_argument("--weights", nargs="+", type=float, default=None, help="Pesos del ensemble.")
    parser.add_argument(
        "--explain-model",
        default=None,
        help="Modelo .keras a usar para explicabilidad cuando --ensemble está activo.",
    )
    parser.add_argument(
        "--calibration-method",
        choices=["none", "temperature_scaling"],
        default="none",
        help="Método de calibración de probabilidad.",
    )
    parser.add_argument(
        "--calibration-temperature",
        type=float,
        default=None,
        help="Temperatura opcional para temperature_scaling.",
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta inferencia individual en PostgreSQL.",
    )
    return parser.parse_args()


def load_image(image_path, img_size, preprocessing_mode="rescale_0_1"):
    image_batch, _ = preprocess_external_image(image_path, img_size, preprocessing_mode)
    return image_batch


def model_name_from_checkpoint_path(checkpoint):
    try:
        from src.tracking_integration import model_name_from_checkpoint

        return model_name_from_checkpoint(checkpoint)
    except Exception:
        checkpoint = Path(checkpoint)
        return checkpoint.parent.name or checkpoint.stem


def probability_rows_from_predictions(predictions):
    from src.inference_pipeline import probability_rows_from_predictions as pipeline_probability_rows

    return pipeline_probability_rows(predictions)


def predict_without_tta(model, image_batch):
    return predict_model_probability(model, image_batch)


def predict_with_tta(model, image_batch, n_aug, preprocessing_mode="rescale_0_1", raw_image=None):
    return predict_model_probability_with_tta(
        model,
        image_batch,
        n_aug,
        preprocessing_mode=preprocessing_mode,
        raw_image=raw_image,
    )


def methods_to_run(method):
    if method == "none":
        return []
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


def run_external_explanations(args, model, image_batch, response, preprocessing_mode):
    if not args.explain or args.explain == "none":
        return {
            "requested": False,
            "methods": [],
            "method": None,
            "success": False,
            "image_path": None,
            "last_conv_layer": None,
            "outputs": [],
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
                    preprocessing_mode=preprocessing_mode,
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
                    preprocessing_mode=preprocessing_mode,
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
                    preprocessing_mode=preprocessing_mode,
                )
                item.update({"success": bool(success), "error": error})
        except Exception as exc:
            item["success"] = False
            item["error"] = str(exc)
        items.append(item)

    successful = [item for item in items if item["success"]]
    if len(items) == 1:
        return {
            **items[0],
            "requested": True,
            "methods": methods,
            "outputs": items,
        }

    primary = successful[0] if successful else items[0]
    return {
        "requested": True,
        "methods": methods,
        "method": args.explain,
        "success": bool(successful),
        "image_path": primary.get("image_path") if successful else None,
        "last_conv_layer": primary.get("last_conv_layer"),
        "error": None if successful else "; ".join(item.get("error") or "" for item in items),
        "outputs": items,
        "items": items,
    }


def build_result(args, image_path, stored_image, checkpoint, prediction_result):
    stored_image_path = stored_image.relative_path if stored_image is not None else None
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
        "raw_model_score": prediction_result.get("raw_model_score"),
        "uncalibrated_probability_parasitized": prediction_result.get(
            "uncalibrated_probability_parasitized",
            probability_parasitized,
        ),
        "calibration": prediction_result.get("calibration", {"method": "none", "applied": False}),
        "preprocessing_mode": prediction_result.get("preprocessing_mode"),
        "tta": bool(args.tta),
        "n_aug": int(args.n_aug) if args.tta else 0,
        "tta_predictions": prediction_result["tta_predictions"],
        "ensemble_applied": bool(args.ensemble),
        "ensemble_model_results": prediction_result.get("ensemble_model_results"),
        "ensemble_weights": prediction_result.get("ensemble_weights"),
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
    response["decision_code"] = response["decision"]
    return response


def format_optional_probability(value):
    if value is None:
        return "no disponible"
    return f"{float(value):.6f}"


def get_decision_dict(result):
    decision = result.get("decision")
    return decision if isinstance(decision, dict) else {}


def print_result(result):
    model_info = result.get("model") or {}
    image_info = result.get("image") or {}
    quality = image_info.get("quality") or {}
    probabilities = result.get("probabilities") or {}
    print(f"Imagen evaluada: {result['image_path']}")
    if result.get("stored_image_path"):
        print(f"Imagen almacenada: {result['stored_image_path']}")
    print("Flujo: inferencia clínica experimental")
    print("Control de calidad:", "aprobado" if quality.get("passed", True) else "observado")
    if quality.get("warnings"):
        print("Advertencias de calidad:", "; ".join(quality["warnings"]))
    print(f"Modelo: {result.get('model_checkpoint') or 'no cargado'}")
    print("TTA:", "sí" if model_info.get("tta_applied") else "no")
    print("Ensemble:", "sí" if model_info.get("ensemble_applied") else "no")
    print(f"Probabilidad parasitized: {format_optional_probability(result.get('probability_parasitized'))}")
    print(f"Probabilidad uninfected: {format_optional_probability(result.get('probability_uninfected'))}")
    print(f"Calibración: {(probabilities.get('calibration') or {}).get('method', 'none')}")
    print(f"Umbral clínico experimental: {result['threshold']:.2f}")
    print(f"Predicción: {result.get('predicted_label') or 'no disponible'}")
    print(f"Confianza: {result.get('confidence_level') or 'no disponible'}")
    print(f"Respuesta: {result.get('human_readable_response') or 'no disponible'}")
    explanation = result.get("explainability") or {}
    explanation_path = explanation.get("image_path")
    print(f"Explicabilidad: {explanation_path or 'no solicitada'}")
    tracking = result.get("tracking") or {}
    if tracking.get("track_db"):
        print("Tracking DB: registrado" if tracking.get("registered") else "Tracking DB: no registrado")
    else:
        print("Tracking DB: no solicitado")
    print(f"Advertencia: {result.get('disclaimer', DISCLAIMER)}")


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


def ensure_external_predictions_csv_columns(fieldnames):
    if not EXTERNAL_PREDICTIONS_CSV.exists():
        return fieldnames

    with EXTERNAL_PREDICTIONS_CSV.open("r", newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        existing_fieldnames = reader.fieldnames or []
        rows = list(reader)

    merged_fieldnames = list(existing_fieldnames)
    for fieldname in fieldnames:
        if fieldname not in merged_fieldnames:
            merged_fieldnames.append(fieldname)

    if merged_fieldnames == existing_fieldnames:
        return merged_fieldnames

    with EXTERNAL_PREDICTIONS_CSV.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=merged_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return merged_fieldnames


def append_external_prediction_csv(result):
    EXTERNAL_PREDICTIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    explainability_method, explainability_path = flatten_explainability_for_csv(
        result.get("explainability")
    )
    tracking = result.get("tracking") or {}
    image_info = result.get("image") or {}
    quality = image_info.get("quality") or {}
    model_info = result.get("model") or {}
    probabilities = result.get("probabilities") or {}
    decision = get_decision_dict(result)
    explainability = result.get("explainability") or {}
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
        "decision": result.get("decision_code"),
        "explainability_method": explainability_method,
        "explainability_path": explainability_path,
        "track_db": tracking.get("track_db", False),
        "prediction_id": tracking.get("prediction_id"),
        "workflow": result.get("workflow"),
        "image_original_path": image_info.get("original_path", result["image_path"]),
        "image_stored_path": image_info.get("stored_path", result.get("stored_image_path")),
        "quality_passed": quality.get("passed"),
        "quality_warnings": json.dumps(quality.get("warnings", []), ensure_ascii=False),
        "img_size": (result.get("preprocessing") or {}).get("img_size"),
        "model_mode": model_info.get("mode"),
        "model_name": model_info.get("model_name", result.get("model_name")),
        "tta_applied": model_info.get("tta_applied", result.get("tta")),
        "n_aug": model_info.get("n_aug", result.get("n_aug")),
        "ensemble_applied": model_info.get("ensemble_applied"),
        "ensemble_models": json.dumps(model_info.get("ensemble_models", []), ensure_ascii=False),
        "ensemble_weights": json.dumps(model_info.get("ensemble_weights", []), ensure_ascii=False),
        "raw_model_score": probabilities.get("raw_model_score"),
        "calibration_method": (probabilities.get("calibration") or {}).get("method"),
        "decision_code": decision.get("decision_code", result.get("decision_code")),
        "human_readable_response": decision.get(
            "human_readable_response",
            result.get("human_readable_response"),
        ),
        "explainability_requested": explainability.get("requested", bool(explainability_method)),
        "explainability_methods": json.dumps(explainability.get("methods", []), ensure_ascii=False),
        "explainability_paths": explainability_path,
        "run_id": tracking.get("run_id"),
    }

    fieldnames = ensure_external_predictions_csv_columns(list(row.keys()))
    write_header = not EXTERNAL_PREDICTIONS_CSV.exists()
    with EXTERNAL_PREDICTIONS_CSV.open("a", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
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

        tracked_model_name = (
            "ensemble" if result.get("ensemble_applied") else model_name_from_checkpoint(checkpoint)
        )
        context = start_tracking_run(
            args=args,
            run_type="inference",
            script_name="src.predict_image",
            model_name=tracked_model_name,
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
                    "decision": result.get("decision_code"),
                    "human_readable_response": result.get("human_readable_response"),
                    "workflow": result.get("workflow"),
                    "quality": (result.get("image") or {}).get("quality"),
                    "raw_model_score": result.get("raw_model_score"),
                    "calibration": result.get("calibration"),
                    "ensemble_applied": result.get("ensemble_applied"),
                    "ensemble_models": (result.get("model") or {}).get("ensemble_models"),
                    "ensemble_weights": result.get("ensemble_weights"),
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
                "decision": result.get("decision_code"),
                "human_readable_response": result.get("human_readable_response"),
                "workflow": result.get("workflow"),
                "quality": (result.get("image") or {}).get("quality"),
                "raw_model_score": result.get("raw_model_score"),
                "calibration": result.get("calibration"),
                "ensemble_applied": result.get("ensemble_applied"),
                "ensemble_models": (result.get("model") or {}).get("ensemble_models"),
                "ensemble_weights": result.get("ensemble_weights"),
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
                "decision": result.get("decision_code"),
                "workflow": result.get("workflow"),
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


def resolve_model_paths(args):
    checkpoint = Path(args.checkpoint).expanduser() if args.checkpoint else None
    if checkpoint is not None and not checkpoint.exists():
        raise FileNotFoundError(f"No existe el checkpoint: {checkpoint}")

    if args.ensemble:
        model_paths = [Path(path).expanduser() for path in (args.models or [])]
        if not model_paths and checkpoint is not None:
            model_paths = [checkpoint]
        if not model_paths:
            raise ValueError("--ensemble requiere --models o --checkpoint.")
        for path in model_paths:
            if not path.exists():
                raise FileNotFoundError(f"No existe el modelo del ensemble: {path}")
        primary_checkpoint = checkpoint or model_paths[0]
    else:
        if checkpoint is None:
            raise ValueError("--checkpoint es requerido si no usas --ensemble.")
        model_paths = [checkpoint]
        primary_checkpoint = checkpoint

    explain_model_path = Path(args.explain_model).expanduser() if args.explain_model else primary_checkpoint
    if args.explain and args.explain != "none" and not explain_model_path.exists():
        raise FileNotFoundError(f"No existe el modelo para explicabilidad: {explain_model_path}")

    return primary_checkpoint, model_paths, explain_model_path


def load_explain_model(explain_model_path, loaded_models):
    for path, model in loaded_models:
        if Path(path).resolve() == Path(explain_model_path).resolve():
            return model
    return tf.keras.models.load_model(explain_model_path)


def model_info_from_args(args, primary_checkpoint, model_paths, weights, preprocessing_mode):
    return {
        "mode": "ensemble" if args.ensemble else "single_model",
        "checkpoint": str(primary_checkpoint),
        "model_name": "ensemble" if args.ensemble else model_name_from_checkpoint_path(primary_checkpoint),
        "preprocessing_mode": preprocessing_mode,
        "tta_applied": bool(args.tta),
        "n_aug": int(args.n_aug) if args.tta else 0,
        "ensemble_applied": bool(args.ensemble),
        "ensemble_models": [str(path) for path in model_paths] if args.ensemble else [],
        "ensemble_weights": None if weights is None else [float(value) for value in weights],
    }


def quality_failure_response(args, image_path, quality_result):
    checkpoint = args.checkpoint or ""
    result = {
        "workflow": "clinical_inference_experimental",
        "image_path": str(image_path),
        "stored_image_path": None,
        "model_checkpoint": str(checkpoint),
        "model_name": None,
        "predicted_label": None,
        "probability_parasitized": None,
        "probability_uninfected": None,
        "threshold": float(args.threshold),
        "confidence_level": None,
        "decision_code": "image_quality_failed",
        "human_readable_response": "No fue posible evaluar la imagen por falla de calidad o lectura.",
        "recommendation": "Resultado experimental. Requiere revisión de la imagen de entrada.",
        "disclaimer": DISCLAIMER,
        "image": {
            "original_path": str(image_path),
            "stored_path": None,
            "quality": quality_result,
        },
        "preprocessing": {
            "img_size": int(args.img_size),
            "mode": args.preprocessing,
            "normalization": args.preprocessing,
            "input_shape": None,
        },
        "model": {
            "mode": "ensemble" if args.ensemble else "single_model",
            "checkpoint": str(checkpoint),
            "model_name": None,
            "tta_applied": bool(args.tta),
            "n_aug": int(args.n_aug) if args.tta else 0,
            "ensemble_applied": bool(args.ensemble),
            "ensemble_models": args.models or [],
            "ensemble_weights": args.weights or [],
        },
        "probabilities": {
            "probability_parasitized": None,
            "probability_uninfected": None,
            "raw_model_score": None,
            "calibration": {"method": args.calibration_method, "applied": False},
        },
        "decision": {
            "threshold": float(args.threshold),
            "predicted_label": None,
            "confidence_level": None,
            "decision_code": "image_quality_failed",
            "human_readable_response": "No fue posible evaluar la imagen por falla de calidad o lectura.",
        },
        "explainability": {
            "requested": bool(args.explain and args.explain != "none"),
            "methods": methods_to_run(args.explain),
            "success": False,
            "outputs": [],
            "error": "Imagen no evaluada por falla de calidad.",
        },
        "tracking": {
            "track_db": bool(args.track_db),
            "registered": False,
            "run_id": None,
            "prediction_id": None,
            "error": "Imagen no evaluada por falla de calidad.",
        },
    }
    return result


def main():
    args = parse_args()
    image_path = Path(args.image_path).expanduser()
    stored_image = None

    if args.positive_label != POSITIVE_LABEL:
        raise ValueError(
            f"Este flujo estructurado usa {POSITIVE_LABEL!r} como clase positiva clínica."
        )

    quality_result = check_image_quality(image_path)
    if quality_result.get("fatal"):
        result = quality_failure_response(args, image_path, quality_result)
        print_result(result)
        if args.output_json:
            save_json(result, args.output_json)
        return

    primary_checkpoint, model_paths, explain_model_path = resolve_model_paths(args)
    preprocessing_mode = resolve_preprocessing_mode(
        "ensemble" if args.ensemble else primary_checkpoint.parent.name,
        args.preprocessing,
    )
    loaded_models = [(path, tf.keras.models.load_model(path)) for path in model_paths]
    explain_model = (
        load_explain_model(explain_model_path, loaded_models)
        if args.explain and args.explain != "none"
        else None
    )

    prediction_image_path = image_path
    if args.track_db:
        from src.prediction_uploads import store_prediction_image

        stored_image = store_prediction_image(image_path, image_id=args.image_id)
        prediction_image_path = stored_image.stored_path

    image_batch, _, raw_image = preprocess_external_image(
        prediction_image_path,
        args.img_size,
        preprocessing_mode=preprocessing_mode,
        return_raw=True,
    )

    if args.ensemble:
        weights = args.weights
        prediction_result = predict_ensemble_probability(
            [model for _, model in loaded_models],
            image_batch,
            weights=weights,
            tta=args.tta,
            n_aug=args.n_aug,
            preprocessing_mode=preprocessing_mode,
            raw_image=raw_image,
        )
        normalized_weights = prediction_result.get("ensemble_weights")
    else:
        model = loaded_models[0][1]
        prediction_result = (
            predict_with_tta(
                model,
                image_batch,
                args.n_aug,
                preprocessing_mode=preprocessing_mode,
                raw_image=raw_image,
            )
            if args.tta
            else predict_without_tta(model, image_batch)
        )
        normalized_weights = None
    prediction_result["preprocessing_mode"] = preprocessing_mode

    calibration_params = {}
    if args.calibration_temperature is not None:
        calibration_params["temperature"] = args.calibration_temperature
    prediction_result = apply_probability_calibration(
        prediction_result,
        method=args.calibration_method,
        calibration_params=calibration_params,
    )

    result = build_result(args, image_path, stored_image, primary_checkpoint, prediction_result)
    result["model_checkpoint"] = str(primary_checkpoint)
    result["model_name"] = "ensemble" if args.ensemble else model_name_from_checkpoint_path(primary_checkpoint)
    result["explainability"] = run_external_explanations(
        args,
        explain_model,
        image_batch,
        result,
        preprocessing_mode,
    )
    model_info = model_info_from_args(
        args,
        primary_checkpoint,
        model_paths,
        normalized_weights,
        preprocessing_mode,
    )
    probabilities = {
        "probability_parasitized": result["probability_parasitized"],
        "probability_uninfected": result["probability_uninfected"],
        "raw_model_score": result.get("raw_model_score"),
        "calibration": result.get("calibration"),
    }
    result.update(
        build_structured_clinical_response(
            flat_result=result,
            quality_result=quality_result,
            img_size=args.img_size,
            input_shape=image_batch.shape,
            model_info=model_info,
            probabilities=probabilities,
            threshold=args.threshold,
            preprocessing_mode=preprocessing_mode,
            explainability=result["explainability"],
            tracking={"track_db": bool(args.track_db), "registered": False, "run_id": None, "prediction_id": None},
        )
    )
    result["decision_code"] = result["decision"]["decision_code"]
    result["confidence_level"] = result["decision"]["confidence_level"]
    result["human_readable_response"] = result["decision"]["human_readable_response"]
    result["tracking"] = track_prediction(args, result, primary_checkpoint)
    result["tracking"]["track_db"] = bool(args.track_db)

    print_result(result)

    if args.output_json:
        save_json(result, args.output_json)

    append_external_prediction_csv(result)
    print(f"Predicción acumulada en: {EXTERNAL_PREDICTIONS_CSV}")


if __name__ == "__main__":
    main()
