from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

from src.calibration import calibrate_probability
from src.config import CLASS_NAMES, LABEL_MAPPING_VERSION, RAW_MODEL_SCORE_MEANING, label_mapping_metadata
from src.decision import (
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    build_clinical_inference_response,
    probabilities_by_class_from_prediction,
)
from src.model_metadata import resolve_threshold_for_checkpoint
from src.preprocessing import (
    PREPROCESSING_RESCALE_0_1,
    PREPROCESSING_VGG16_IMAGENET,
    apply_model_preprocessing,
    preprocessing_description,
    preprocess_numpy_image,
    resize_image_tensor,
    resolve_preprocessing_mode,
)


def preprocess_external_image(
    image_path,
    img_size,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
    return_raw=False,
):
    preprocessing_mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    image = Image.open(image_path).convert("RGB")
    raw_image = resize_image_tensor(np.asarray(image, dtype=np.float32), img_size)
    raw_image = raw_image.numpy().astype(np.float32)
    image = preprocess_numpy_image(raw_image, img_size, preprocessing_mode)
    image_batch = np.expand_dims(image, axis=0).astype(np.float32)
    if return_raw:
        return image_batch, image, raw_image
    return image_batch, image


def probability_rows_from_predictions(predictions, label_mapping_version=LABEL_MAPPING_VERSION):
    predictions = np.asarray(predictions, dtype=np.float32)
    if predictions.ndim == 2 and predictions.shape[1] == len(CLASS_NAMES):
        return [
            probabilities_by_class_from_prediction(
                row.reshape(1, -1),
                CLASS_NAMES,
                label_mapping_version=label_mapping_version,
            )
            for row in predictions
        ]

    return [
        probabilities_by_class_from_prediction(
            np.asarray([score], dtype=np.float32),
            CLASS_NAMES,
            label_mapping_version=label_mapping_version,
        )
        for score in predictions.reshape(-1)
    ]


def predict_model_probability(model, image_batch, label_mapping_version=LABEL_MAPPING_VERSION):
    prediction = model.predict(image_batch, verbose=0)
    probabilities = probabilities_by_class_from_prediction(
        prediction,
        CLASS_NAMES,
        label_mapping_version=label_mapping_version,
    )
    prediction_array = np.asarray(prediction, dtype=np.float32)
    raw_model_score = (
        float(probabilities[POSITIVE_LABEL])
        if prediction_array.ndim == 2 and prediction_array.shape[1] == len(CLASS_NAMES)
        else float(prediction_array.reshape(-1)[0])
    )
    return {
        "raw_model_output": prediction_array.tolist(),
        "raw_model_score": raw_model_score,
        "raw_model_score_meaning": (
            RAW_MODEL_SCORE_MEANING
            if label_mapping_version == LABEL_MAPPING_VERSION
            else "probability_uninfected"
        ),
        "probability_parasitized": probabilities[POSITIVE_LABEL],
        "probability_uninfected": probabilities[NEGATIVE_LABEL],
        "label_mapping_version": label_mapping_version,
        "label_mapping": label_mapping_metadata(label_mapping_version),
        "tta_predictions": None,
    }


def predict_model_probability_with_tta(
    model,
    image_batch,
    n_aug,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
    raw_image=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    from src.data import build_augmentation

    preprocessing_mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    augmentation = build_augmentation()
    image = image_batch[0]

    if preprocessing_mode == PREPROCESSING_VGG16_IMAGENET and raw_image is not None:
        augmented_raw_images = [np.asarray(raw_image, dtype=np.float32)]
        for _ in range(int(n_aug)):
            augmented = augmentation(raw_image, training=True)
            augmented_raw_images.append(np.asarray(augmented, dtype=np.float32))
        tta_batch = apply_model_preprocessing(
            np.asarray(augmented_raw_images, dtype=np.float32),
            preprocessing_mode,
        ).numpy()
    else:
        augmented_images = [image]
        for _ in range(int(n_aug)):
            augmented = augmentation(image, training=True)
            augmented_images.append(np.asarray(augmented, dtype=np.float32))
        tta_batch = np.asarray(augmented_images, dtype=np.float32)

    predictions = model.predict(tta_batch, verbose=0)
    prediction_array = np.asarray(predictions, dtype=np.float32)
    probability_rows = probability_rows_from_predictions(
        predictions,
        label_mapping_version=label_mapping_version,
    )
    probability_parasitized = float(
        np.mean([row[POSITIVE_LABEL] for row in probability_rows])
    )
    probability_uninfected = float(1.0 - probability_parasitized)
    raw_model_score = (
        probability_parasitized
        if (
            label_mapping_version == LABEL_MAPPING_VERSION
            or (
                prediction_array.ndim == 2
                and prediction_array.shape[1] == len(CLASS_NAMES)
            )
        )
        else float(np.mean(prediction_array.reshape(-1)))
    )

    return {
        "raw_model_output": prediction_array.tolist(),
        "raw_model_score": raw_model_score,
        "raw_model_score_meaning": (
            RAW_MODEL_SCORE_MEANING
            if label_mapping_version == LABEL_MAPPING_VERSION
            else "probability_uninfected"
        ),
        "probability_parasitized": probability_parasitized,
        "probability_uninfected": probability_uninfected,
        "label_mapping_version": label_mapping_version,
        "label_mapping": label_mapping_metadata(label_mapping_version),
        "tta_predictions": probability_rows,
    }


def normalize_ensemble_weights(num_models, weights=None):
    if weights is None:
        return np.ones(num_models, dtype=float) / float(num_models)

    weights = np.asarray(weights, dtype=float)
    if len(weights) != num_models:
        raise ValueError("La cantidad de pesos debe coincidir con la cantidad de modelos.")
    total = float(np.sum(weights))
    if total <= 0:
        raise ValueError("La suma de pesos del ensemble debe ser mayor que cero.")
    return weights / total


def predict_ensemble_probability(
    models,
    image_batch,
    weights=None,
    tta=False,
    n_aug=8,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
    raw_image=None,
    label_mapping_version=LABEL_MAPPING_VERSION,
):
    weights = normalize_ensemble_weights(len(models), weights)
    model_results = []

    for model in models:
        if tta:
            model_results.append(
                predict_model_probability_with_tta(
                    model,
                    image_batch,
                    n_aug,
                    preprocessing_mode=preprocessing_mode,
                    raw_image=raw_image,
                    label_mapping_version=label_mapping_version,
                )
            )
        else:
            model_results.append(
                predict_model_probability(
                    model,
                    image_batch,
                    label_mapping_version=label_mapping_version,
                )
            )

    probability_parasitized = float(
        np.average(
            [item["probability_parasitized"] for item in model_results],
            weights=weights,
        )
    )
    probability_uninfected = float(1.0 - probability_parasitized)

    return {
        "raw_model_output": [item["raw_model_output"] for item in model_results],
        "raw_model_score": float(
            np.average([item["raw_model_score"] for item in model_results], weights=weights)
        ),
        "raw_model_score_meaning": (
            RAW_MODEL_SCORE_MEANING
            if label_mapping_version == LABEL_MAPPING_VERSION
            else "probability_uninfected"
        ),
        "probability_parasitized": probability_parasitized,
        "probability_uninfected": probability_uninfected,
        "label_mapping_version": label_mapping_version,
        "label_mapping": label_mapping_metadata(label_mapping_version),
        "ensemble_model_results": model_results,
        "ensemble_weights": weights.tolist(),
        "tta_predictions": None,
    }


def apply_probability_calibration(prediction_result, method="none", calibration_params=None):
    calibration = calibrate_probability(
        prediction_result["probability_parasitized"],
        method=method,
        calibration_params=calibration_params,
    )
    calibrated_probability = calibration["calibrated_probability"]
    return {
        **prediction_result,
        "uncalibrated_probability_parasitized": prediction_result["probability_parasitized"],
        "probability_parasitized": calibrated_probability,
        "probability_uninfected": float(1.0 - calibrated_probability),
        "calibration": calibration,
    }


def resolve_inference_threshold(threshold, checkpoint_path):
    return resolve_threshold_for_checkpoint(threshold, checkpoint_path)


def model_name_from_path(path):
    path = Path(path)
    return path.parent.name or path.stem


def build_structured_clinical_response(
    flat_result,
    quality_result,
    img_size,
    input_shape,
    model_info,
    probabilities,
    threshold,
    preprocessing_mode=PREPROCESSING_RESCALE_0_1,
    explainability=None,
    tracking=None,
):
    image_info = {
        "original_path": flat_result["image_path"],
        "stored_path": flat_result.get("stored_image_path"),
        "quality": quality_result,
    }
    preprocessing = {
        "img_size": int(img_size),
        "mode": resolve_preprocessing_mode(requested=preprocessing_mode),
        "description": preprocessing_description(preprocessing_mode),
        "normalization": preprocessing_description(preprocessing_mode),
        "input_shape": list(input_shape),
    }
    return build_clinical_inference_response(
        image=image_info,
        preprocessing=preprocessing,
        model=model_info,
        probabilities=probabilities,
        threshold=threshold,
        explainability=explainability,
        tracking=tracking,
    )
