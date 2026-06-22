import os
from pathlib import Path

import tensorflow as tf
import tensorflow_datasets as tfds
from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    RAW_MODEL_SCORE_MEANING,
)
from src.preprocessing import (
    PREPROCESSING_RESCALE_0_1,
    PREPROCESSING_VGG16_IMAGENET,
    apply_model_preprocessing,
    preprocess_image_tensor,
    resize_image_tensor,
    resolve_preprocessing_mode,
)


def print_label_mapping_verification():
    print(f"Clases clínicas: {CLASS_NAMES}")
    print(f"Convención de etiquetas: {LABEL_MAPPING_VERSION}")
    print(f"raw_model_score: {RAW_MODEL_SCORE_MEANING}")


def remap_tfds_malaria_label(label):
    """
    TFDS original:
      0 = parasitized
      1 = uninfected

    Proyecto clínico:
      0 = uninfected
      1 = parasitized

    El remapeo es 1 - label.
    """
    label = tf.cast(label, tf.float32)
    return 1.0 - label


def get_tfds_data_dir() -> Path:
    """
    Devuelve la ruta local para TensorFlow Datasets.

    Prioridad:
    1. Variable de entorno TFDS_DATA_DIR.
    2. capstone/data/tensorflow_datasets.
    """
    env_value = os.getenv("TFDS_DATA_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    capstone_root = Path(__file__).resolve().parents[2]
    return capstone_root / "data" / "tensorflow_datasets"


def load_malaria_splits(
    img_size: int = 200,
    batch_size: int = 64,
    seed: int = 42,
    augment: bool = False,
    preprocessing_mode: str = PREPROCESSING_RESCALE_0_1,
):
    """
    Carga NIH/NLM Malaria Cell Images desde TensorFlow Datasets.

    Retorna:
        ds_train, ds_val, ds_test, ds_info
    """
    print_label_mapping_verification()

    (ds_train, ds_val, ds_test), ds_info = tfds.load(
        "malaria",
        split=["train[:80%]", "train[80%:90%]", "train[90%:]"],
        as_supervised=True,
        with_info=True,
        shuffle_files=True,
        data_dir=str(get_tfds_data_dir()),
    )

    preprocessing_mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    augmentation = build_augmentation()

    def preprocess(image, label):
        image = preprocess_image_tensor(image, img_size, preprocessing_mode)
        label = remap_tfds_malaria_label(label)
        return image, label

    def resize_only(image, label):
        image = resize_image_tensor(image, img_size)
        label = remap_tfds_malaria_label(label)
        return image, label

    def apply_preprocessing(image, label):
        image = apply_model_preprocessing(image, preprocessing_mode)
        return image, label

    def augment_fn(image, label):
        image = augmentation(image, training=True)
        return image, label

    if augment and preprocessing_mode == PREPROCESSING_VGG16_IMAGENET:
        ds_train = ds_train.map(resize_only, num_parallel_calls=tf.data.AUTOTUNE)
        ds_train = ds_train.map(augment_fn, num_parallel_calls=tf.data.AUTOTUNE)
        ds_train = ds_train.map(apply_preprocessing, num_parallel_calls=tf.data.AUTOTUNE)
    else:
        ds_train = ds_train.map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
        if augment:
            ds_train = ds_train.map(augment_fn, num_parallel_calls=tf.data.AUTOTUNE)

    ds_train = (
        ds_train
        .shuffle(2000, seed=seed)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )

    ds_val = (
        ds_val
        .map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )

    ds_test = (
        ds_test
        .map(preprocess, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size)
        .prefetch(tf.data.AUTOTUNE)
    )

    return ds_train, ds_val, ds_test, ds_info


def build_augmentation():
    """
    Data augmentation similar al enfoque descrito en el paper:
    rotación, traslación, zoom y contraste.
    """
    return tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal_and_vertical"),
            tf.keras.layers.RandomRotation(0.07),
            tf.keras.layers.RandomTranslation(0.2, 0.2),
            tf.keras.layers.RandomZoom(0.2),
            tf.keras.layers.RandomContrast(0.3),
        ],
        name="data_augmentation",
    )


def load_raw_test_split():
    """
    Carga solo el split de test sin batch ni resize.
    Útil para Test Time Augmentation.
    """
    return tfds.load(
        "malaria",
        split="train[90%:]",
        as_supervised=True,
        shuffle_files=False,
        data_dir=str(get_tfds_data_dir()),
    )


def preprocess_single(
    image,
    label,
    img_size: int = 200,
    preprocessing_mode: str = PREPROCESSING_RESCALE_0_1,
):
    preprocessing_mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    image = preprocess_image_tensor(image, img_size, preprocessing_mode)
    label = remap_tfds_malaria_label(label)
    return image, label
