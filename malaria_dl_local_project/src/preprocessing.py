from __future__ import annotations

import numpy as np
import tensorflow as tf


PREPROCESSING_AUTO = "auto"
PREPROCESSING_RESCALE_0_1 = "rescale_0_1"
PREPROCESSING_VGG16_IMAGENET = "vgg16_imagenet"

PREPROCESSING_CHOICES = [
    PREPROCESSING_AUTO,
    PREPROCESSING_RESCALE_0_1,
    PREPROCESSING_VGG16_IMAGENET,
]

PREPROCESSING_DESCRIPTIONS = {
    PREPROCESSING_RESCALE_0_1: "resize + cast float32 + normalización [0, 1]",
    PREPROCESSING_VGG16_IMAGENET: (
        "resize + cast float32 + tf.keras.applications.vgg16.preprocess_input"
    ),
}


def resolve_preprocessing_mode(model_name=None, requested=PREPROCESSING_AUTO):
    requested = requested or PREPROCESSING_AUTO
    if requested not in PREPROCESSING_CHOICES:
        raise ValueError(
            f"Preprocesamiento no soportado: {requested}. "
            f"Opciones: {PREPROCESSING_CHOICES}"
        )

    if requested != PREPROCESSING_AUTO:
        return requested

    # Default conservador: mantiene compatibilidad con checkpoints ya entrenados.
    return PREPROCESSING_RESCALE_0_1


def recommended_preprocessing_mode(model_name):
    model_name = (model_name or "").lower()
    if "vgg16" in model_name:
        return PREPROCESSING_VGG16_IMAGENET
    return PREPROCESSING_RESCALE_0_1


def preprocessing_description(preprocessing_mode):
    mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    return PREPROCESSING_DESCRIPTIONS[mode]


def resize_image_tensor(image, img_size):
    image = tf.image.resize(image, (img_size, img_size))
    return tf.cast(image, tf.float32)


def apply_model_preprocessing(image, preprocessing_mode):
    mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    image = tf.cast(image, tf.float32)

    if mode == PREPROCESSING_RESCALE_0_1:
        return image / 255.0
    if mode == PREPROCESSING_VGG16_IMAGENET:
        return tf.keras.applications.vgg16.preprocess_input(image)

    raise ValueError(f"Preprocesamiento no soportado: {mode}")


def preprocess_image_tensor(image, img_size, preprocessing_mode=PREPROCESSING_RESCALE_0_1):
    resized = resize_image_tensor(image, img_size)
    return apply_model_preprocessing(resized, preprocessing_mode)


def preprocess_numpy_image(image, img_size, preprocessing_mode=PREPROCESSING_RESCALE_0_1):
    image = np.asarray(image, dtype=np.float32)
    preprocessed = preprocess_image_tensor(image, img_size, preprocessing_mode)
    return preprocessed.numpy().astype(np.float32)


def preprocessing_metadata(preprocessing_mode):
    mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    return {
        "mode": mode,
        "description": PREPROCESSING_DESCRIPTIONS[mode],
    }
