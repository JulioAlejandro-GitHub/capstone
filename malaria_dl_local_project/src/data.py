import tensorflow as tf
import tensorflow_datasets as tfds


def load_malaria_splits(
    img_size: int = 200,
    batch_size: int = 64,
    seed: int = 42,
    augment: bool = False,
):
    """
    Carga NIH/NLM Malaria Cell Images desde TensorFlow Datasets.

    Retorna:
        ds_train, ds_val, ds_test, ds_info
    """
    (ds_train, ds_val, ds_test), ds_info = tfds.load(
        "malaria",
        split=["train[:80%]", "train[80%:90%]", "train[90%:]"],
        as_supervised=True,
        with_info=True,
        shuffle_files=True,
    )

    augmentation = build_augmentation()

    def preprocess(image, label):
        image = tf.image.resize(image, (img_size, img_size))
        image = tf.cast(image, tf.float32) / 255.0
        label = tf.cast(label, tf.float32)
        return image, label

    def augment_fn(image, label):
        image = augmentation(image, training=True)
        return image, label

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
    )


def preprocess_single(image, label, img_size: int = 200):
    image = tf.image.resize(image, (img_size, img_size))
    image = tf.cast(image, tf.float32) / 255.0
    label = tf.cast(label, tf.float32)
    return image, label
