import json
import os
from pathlib import Path

import tensorflow as tf
import tensorflow_datasets as tfds
from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    PHYSICAL_DATASET_DIR,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    PROJECT_ROOT,
    RAW_MODEL_SCORE_MEANING,
    TFDS_ORIGINAL_CLASS_NAMES,
)
from src.preprocessing import (
    PREPROCESSING_RESCALE_0_1,
    PREPROCESSING_VGG16_IMAGENET,
    apply_model_preprocessing,
    preprocess_image_tensor,
    resize_image_tensor,
    resolve_preprocessing_mode,
)


DATA_SOURCE_PHYSICAL = "physical"
DATA_SOURCE_TFDS = "tfds"
DATA_SOURCE_CHOICES = [DATA_SOURCE_PHYSICAL, DATA_SOURCE_TFDS]
SPLIT_NAMES = ["train", "val", "test"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}


def print_label_mapping_verification():
    print(f"Clases clínicas: {CLASS_NAMES}")
    print(f"Convención de etiquetas: {LABEL_MAPPING_VERSION}")
    print(f"raw_model_score: {RAW_MODEL_SCORE_MEANING}")


def resolve_physical_dataset_dir(dataset_dir: Path | str | None = None) -> Path:
    if dataset_dir is None:
        return PHYSICAL_DATASET_DIR
    dataset_dir = Path(dataset_dir).expanduser()
    if dataset_dir.is_absolute():
        return dataset_dir
    return PROJECT_ROOT / dataset_dir


def physical_split_exists(dataset_dir: Path | str | None = None) -> bool:
    dataset_dir = resolve_physical_dataset_dir(dataset_dir)
    return all((dataset_dir / split).is_dir() for split in SPLIT_NAMES)


def _relative_path(path):
    try:
        return Path(path).resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def count_images_in_directory(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(
        1
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def count_physical_split_images(dataset_dir: Path | str | None = None) -> dict:
    dataset_dir = resolve_physical_dataset_dir(dataset_dir)
    counts = {}
    total = 0
    for split in SPLIT_NAMES:
        split_counts = {}
        split_total = 0
        for class_name in CLASS_NAMES:
            count = count_images_in_directory(dataset_dir / split / class_name)
            split_counts[class_name] = count
            split_total += count
        split_counts["total"] = split_total
        counts[split] = split_counts
        total += split_total
    counts["total"] = total
    return counts


def load_physical_split_metadata(dataset_dir: Path | str | None = None) -> dict:
    dataset_dir = resolve_physical_dataset_dir(dataset_dir)
    metadata_path = dataset_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"No existe metadata.json en {dataset_dir}. "
            "Regenera el split físico con: "
            "python scripts/create_physical_dataset_split.py --overwrite"
        )
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def validate_physical_split(dataset_dir: Path | str | None = None) -> dict:
    dataset_dir = resolve_physical_dataset_dir(dataset_dir)
    if not dataset_dir.exists():
        raise FileNotFoundError(
            f"No existe {dataset_dir}.\n"
            "Ejecute:\n"
            "python scripts/create_physical_dataset_split.py"
        )

    missing = []
    for split in SPLIT_NAMES:
        split_dir = dataset_dir / split
        if not split_dir.is_dir():
            missing.append(str(split_dir))
        for class_name in CLASS_NAMES:
            class_dir = split_dir / class_name
            if not class_dir.is_dir():
                missing.append(str(class_dir))
    if missing:
        raise FileNotFoundError(
            "El split físico está incompleto. Faltan rutas:\n"
            + "\n".join(f"- {path}" for path in missing)
        )

    metadata = load_physical_split_metadata(dataset_dir)
    expected_metadata = {
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "class_names": CLASS_NAMES,
        "negative_class_index": NEGATIVE_CLASS_INDEX,
        "negative_class_name": NEGATIVE_LABEL,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "positive_class_name": POSITIVE_LABEL,
    }
    mismatches = []
    for key, expected_value in expected_metadata.items():
        if metadata.get(key) != expected_value:
            mismatches.append(
                f"{key}: esperado {expected_value!r}, recibido {metadata.get(key)!r}"
            )
    if mismatches:
        raise ValueError(
            "metadata.json no coincide con la convención clínica del proyecto:\n"
            + "\n".join(f"- {item}" for item in mismatches)
        )

    project_mapping = metadata.get("project_mapping") or {}
    if project_mapping.get("0") != NEGATIVE_LABEL or project_mapping.get("1") != POSITIVE_LABEL:
        raise ValueError(
            "metadata.json tiene project_mapping inválido. "
            "Debe ser {'0': 'uninfected', '1': 'parasitized'}."
        )

    counts = count_physical_split_images(dataset_dir)
    empty_splits = [
        split
        for split in SPLIT_NAMES
        if counts.get(split, {}).get("total", 0) <= 0
    ]
    if empty_splits:
        raise ValueError(
            "El split físico contiene splits vacíos: " + ", ".join(empty_splits)
        )

    metadata_counts = metadata.get("counts") or {}
    for split in SPLIT_NAMES:
        if metadata_counts.get(split, {}).get("total") != counts[split]["total"]:
            raise ValueError(
                "metadata.json no coincide con los archivos físicos para "
                f"{split}: metadata={metadata_counts.get(split, {}).get('total')}, "
                f"archivos={counts[split]['total']}"
            )

    return {**metadata, "counts": counts, "dataset_dir": str(dataset_dir)}


def print_physical_split_summary(dataset_dir, metadata):
    counts = metadata["counts"]
    print("Dataset source: physical")
    print(f"Dataset dir: {_relative_path(dataset_dir)}")
    print_label_mapping_verification()
    print("Split:")
    for split in SPLIT_NAMES:
        print(f"  {split}: {counts[split]['total']} imágenes")


def build_dataset_info(data_source, dataset_dir=None, metadata=None):
    if data_source == DATA_SOURCE_PHYSICAL:
        metadata = metadata or validate_physical_split(dataset_dir)
        dataset_dir = resolve_physical_dataset_dir(dataset_dir)
        return {
            "dataset_source": "physical_split",
            "data_source": DATA_SOURCE_PHYSICAL,
            "dataset_dir": str(dataset_dir),
            "split_seed": metadata.get("seed"),
            "train_ratio": metadata.get("train_ratio"),
            "val_ratio": metadata.get("val_ratio"),
            "test_ratio": metadata.get("test_ratio"),
            "label_mapping_version": LABEL_MAPPING_VERSION,
            "class_names": CLASS_NAMES,
            "counts": metadata.get("counts"),
        }
    if data_source == DATA_SOURCE_TFDS:
        return {
            "dataset_source": "tfds_dynamic_split",
            "data_source": DATA_SOURCE_TFDS,
            "dataset_dir": str(get_tfds_data_dir()),
            "split_seed": None,
            "train_ratio": 0.8,
            "val_ratio": 0.1,
            "test_ratio": 0.1,
            "label_mapping_version": LABEL_MAPPING_VERSION,
            "class_names": CLASS_NAMES,
            "legacy_or_experimental": True,
        }
    raise ValueError(f"data_source no soportado: {data_source}")


def dataset_tracking_metadata(data_source=DATA_SOURCE_PHYSICAL, dataset_dir=None):
    return build_dataset_info(data_source, dataset_dir)


def add_data_source_args(parser):
    parser.add_argument(
        "--data-source",
        choices=DATA_SOURCE_CHOICES,
        default=DATA_SOURCE_PHYSICAL,
        help=(
            "Fuente de datos. Default oficial: physical. "
            "Usa tfds solo como fallback explícito/legacy."
        ),
    )
    parser.add_argument(
        "--dataset-dir",
        default=str(PHYSICAL_DATASET_DIR.relative_to(PHYSICAL_DATASET_DIR.parents[1])),
        help="Ruta del split físico. Default: data/malaria_physical_split.",
    )
    return parser


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
    data_source: str = DATA_SOURCE_PHYSICAL,
    dataset_dir: Path | str | None = None,
):
    """
    Carga NIH/NLM Malaria Cell Images.

    Por defecto usa el split físico persistente:
      data/malaria_physical_split/{train,val,test}

    TFDS queda disponible solo con data_source="tfds".

    Retorna:
        ds_train, ds_val, ds_test, ds_info
    """
    if data_source == DATA_SOURCE_PHYSICAL:
        return load_physical_split(
            img_size=img_size,
            batch_size=batch_size,
            dataset_dir=dataset_dir,
            augment=augment,
            preprocessing_mode=preprocessing_mode,
            seed=seed,
        )
    if data_source != DATA_SOURCE_TFDS:
        raise ValueError(f"data_source no soportado: {data_source}")

    print("Dataset source: tfds")
    print(f"Dataset dir: {_relative_path(get_tfds_data_dir())}")
    print("WARNING: usando split dinámico TFDS legacy/experimental.")
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


def make_image_dataset_from_directory(
    directory,
    img_size: int,
    batch_size,
    shuffle: bool,
    seed: int = 42,
):
    kwargs = {}
    if shuffle:
        kwargs["seed"] = seed
    return tf.keras.utils.image_dataset_from_directory(
        directory=directory,
        labels="inferred",
        label_mode="binary",
        class_names=CLASS_NAMES,
        image_size=(img_size, img_size),
        batch_size=batch_size,
        shuffle=shuffle,
        **kwargs,
    )


def preprocess_physical_dataset(
    dataset,
    preprocessing_mode: str,
    augment: bool = False,
):
    preprocessing_mode = resolve_preprocessing_mode(requested=preprocessing_mode)
    augmentation = build_augmentation()

    def normalize_labels(images, labels):
        labels = tf.cast(tf.reshape(labels, [-1]), tf.float32)
        return images, labels

    def apply_preprocessing(images, labels):
        return apply_model_preprocessing(images, preprocessing_mode), labels

    def augment_fn(images, labels):
        return augmentation(images, training=True), labels

    dataset = dataset.map(normalize_labels, num_parallel_calls=tf.data.AUTOTUNE)
    if augment and preprocessing_mode == PREPROCESSING_VGG16_IMAGENET:
        dataset = dataset.map(augment_fn, num_parallel_calls=tf.data.AUTOTUNE)
        dataset = dataset.map(apply_preprocessing, num_parallel_calls=tf.data.AUTOTUNE)
    else:
        dataset = dataset.map(apply_preprocessing, num_parallel_calls=tf.data.AUTOTUNE)
        if augment:
            dataset = dataset.map(augment_fn, num_parallel_calls=tf.data.AUTOTUNE)
    return dataset.prefetch(tf.data.AUTOTUNE)


def load_physical_split(
    img_size: int,
    batch_size: int,
    dataset_dir: Path | str | None = None,
    augment: bool = True,
    preprocessing_mode: str = PREPROCESSING_RESCALE_0_1,
    seed: int = 42,
):
    dataset_dir = resolve_physical_dataset_dir(dataset_dir)
    metadata = validate_physical_split(dataset_dir)
    print_physical_split_summary(dataset_dir, metadata)

    ds_train = make_image_dataset_from_directory(
        dataset_dir / "train",
        img_size=img_size,
        batch_size=batch_size,
        shuffle=True,
        seed=seed,
    )
    ds_val = make_image_dataset_from_directory(
        dataset_dir / "val",
        img_size=img_size,
        batch_size=batch_size,
        shuffle=False,
        seed=seed,
    )
    ds_test = make_image_dataset_from_directory(
        dataset_dir / "test",
        img_size=img_size,
        batch_size=batch_size,
        shuffle=False,
        seed=seed,
    )

    return (
        preprocess_physical_dataset(
            ds_train,
            preprocessing_mode=preprocessing_mode,
            augment=augment,
        ),
        preprocess_physical_dataset(
            ds_val,
            preprocessing_mode=preprocessing_mode,
            augment=False,
        ),
        preprocess_physical_dataset(
            ds_test,
            preprocessing_mode=preprocessing_mode,
            augment=False,
        ),
        build_dataset_info(DATA_SOURCE_PHYSICAL, dataset_dir, metadata),
    )


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


def load_raw_test_split(
    data_source: str = DATA_SOURCE_PHYSICAL,
    dataset_dir: Path | str | None = None,
    img_size: int = 200,
):
    """
    Carga solo el split de test sin preprocesamiento de modelo.

    Retorna imágenes resizeadas en escala [0, 255] y etiquetas ya mapeadas a:
      0 = uninfected
      1 = parasitized

    Útil para Test Time Augmentation.
    """
    if data_source == DATA_SOURCE_PHYSICAL:
        dataset_dir = resolve_physical_dataset_dir(dataset_dir)
        validate_physical_split(dataset_dir)
        dataset = make_image_dataset_from_directory(
            dataset_dir / "test",
            img_size=img_size,
            batch_size=None,
            shuffle=False,
        )

        def normalize(image, label):
            return tf.cast(image, tf.float32), tf.cast(tf.reshape(label, []), tf.float32)

        return dataset.map(normalize, num_parallel_calls=tf.data.AUTOTUNE)

    if data_source == DATA_SOURCE_TFDS:
        dataset = tfds.load(
            "malaria",
            split="train[90%:]",
            as_supervised=True,
            shuffle_files=False,
            data_dir=str(get_tfds_data_dir()),
        )

        def resize_and_remap(image, label):
            image = resize_image_tensor(image, img_size)
            return image, remap_tfds_malaria_label(label)

        return dataset.map(resize_and_remap, num_parallel_calls=tf.data.AUTOTUNE)

    raise ValueError(f"data_source no soportado: {data_source}")


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
