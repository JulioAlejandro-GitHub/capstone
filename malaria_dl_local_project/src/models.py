import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import DenseNet121, VGG16
from tensorflow.keras import regularizers

from src.config import NEGATIVE_CLASS_INDEX, POSITIVE_CLASS_INDEX


@tf.keras.utils.register_keras_serializable(package="malaria")
class ParasitizedRecall(tf.keras.metrics.Metric):
    """
    Sensibilidad clínica para la clase parasitized.

    Convención oficial:
      0 = uninfected
      1 = parasitized

    La salida sigmoid representa probability_parasitized.
    """

    def __init__(self, threshold: float = 0.5, name: str = "recall_parasitized", **kwargs):
        super().__init__(name=name, **kwargs)
        self.threshold = float(threshold)
        self.true_positives = self.add_weight(name="true_positives", initializer="zeros")
        self.false_negatives = self.add_weight(name="false_negatives", initializer="zeros")

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_true = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
        y_pred = tf.cast(tf.reshape(y_pred, [-1]), tf.float32)

        true_parasitized = tf.equal(y_true, float(POSITIVE_CLASS_INDEX))
        pred_parasitized = tf.greater_equal(y_pred, self.threshold)

        true_positive_mask = tf.cast(
            tf.logical_and(true_parasitized, pred_parasitized),
            tf.float32,
        )
        false_negative_mask = tf.cast(
            tf.logical_and(true_parasitized, tf.logical_not(pred_parasitized)),
            tf.float32,
        )

        if sample_weight is not None:
            sample_weight = tf.cast(tf.reshape(sample_weight, [-1]), tf.float32)
            true_positive_mask *= sample_weight
            false_negative_mask *= sample_weight

        self.true_positives.assign_add(tf.reduce_sum(true_positive_mask))
        self.false_negatives.assign_add(tf.reduce_sum(false_negative_mask))

    def result(self):
        return tf.math.divide_no_nan(
            self.true_positives,
            self.true_positives + self.false_negatives,
        )

    def reset_state(self):
        self.true_positives.assign(0.0)
        self.false_negatives.assign(0.0)

    def get_config(self):
        config = super().get_config()
        config.update({"threshold": self.threshold})
        return config


@tf.keras.utils.register_keras_serializable(package="malaria")
class Specificity(tf.keras.metrics.Metric):
    """
    Especificidad clínica: TN / (TN + FP) para la clase uninfected.
    """

    def __init__(self, threshold: float = 0.5, name: str = "specificity", **kwargs):
        super().__init__(name=name, **kwargs)
        self.threshold = float(threshold)
        self.true_negatives = self.add_weight(name="true_negatives", initializer="zeros")
        self.false_positives = self.add_weight(name="false_positives", initializer="zeros")

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_true = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
        y_pred = tf.cast(tf.reshape(y_pred, [-1]), tf.float32)

        true_uninfected = tf.equal(y_true, float(NEGATIVE_CLASS_INDEX))
        pred_parasitized = tf.greater_equal(y_pred, self.threshold)
        pred_uninfected = tf.logical_not(pred_parasitized)

        true_negative_mask = tf.cast(
            tf.logical_and(true_uninfected, pred_uninfected),
            tf.float32,
        )
        false_positive_mask = tf.cast(
            tf.logical_and(true_uninfected, pred_parasitized),
            tf.float32,
        )

        if sample_weight is not None:
            sample_weight = tf.cast(tf.reshape(sample_weight, [-1]), tf.float32)
            true_negative_mask *= sample_weight
            false_positive_mask *= sample_weight

        self.true_negatives.assign_add(tf.reduce_sum(true_negative_mask))
        self.false_positives.assign_add(tf.reduce_sum(false_positive_mask))

    def result(self):
        return tf.math.divide_no_nan(
            self.true_negatives,
            self.true_negatives + self.false_positives,
        )

    def reset_state(self):
        self.true_negatives.assign(0.0)
        self.false_positives.assign(0.0)

    def get_config(self):
        config = super().get_config()
        config.update({"threshold": self.threshold})
        return config


@tf.keras.utils.register_keras_serializable(package="malaria")
class BalancedAccuracy(tf.keras.metrics.Metric):
    """
    Balanced accuracy clínica:
      (recall_parasitized + specificity) / 2
    """

    def __init__(self, threshold: float = 0.5, name: str = "balanced_accuracy", **kwargs):
        super().__init__(name=name, **kwargs)
        self.threshold = float(threshold)
        self.recall_parasitized = ParasitizedRecall(threshold=threshold)
        self.specificity = Specificity(threshold=threshold)

    def update_state(self, y_true, y_pred, sample_weight=None):
        self.recall_parasitized.update_state(y_true, y_pred, sample_weight=sample_weight)
        self.specificity.update_state(y_true, y_pred, sample_weight=sample_weight)

    def result(self):
        return (self.recall_parasitized.result() + self.specificity.result()) / 2.0

    def reset_state(self):
        self.recall_parasitized.reset_state()
        self.specificity.reset_state()

    def get_config(self):
        config = super().get_config()
        config.update({"threshold": self.threshold})
        return config


def build_optimizer(optimizer_name: str = "adam", learning_rate: float = 1e-4):
    optimizer_name = str(optimizer_name).lower()
    if optimizer_name == "adam":
        return tf.keras.optimizers.Adam(learning_rate=learning_rate)
    if optimizer_name == "adamw":
        adamw = getattr(tf.keras.optimizers, "AdamW", None)
        if adamw is None:
            raise ValueError("AdamW no está disponible en esta versión de TensorFlow/Keras.")
        return adamw(learning_rate=learning_rate)
    if optimizer_name == "sgd":
        return tf.keras.optimizers.SGD(learning_rate=learning_rate, momentum=0.9)
    if optimizer_name == "adadelta":
        return tf.keras.optimizers.Adadelta(learning_rate=learning_rate)
    raise ValueError(f"Optimizador no soportado: {optimizer_name}")


def compile_binary_model(model, learning_rate: float = 1e-4, optimizer_name: str = "adam"):
    """
    Compila un modelo binario con métricas útiles para salud/diagnóstico.
    """
    optimizer = build_optimizer(optimizer_name=optimizer_name, learning_rate=learning_rate)

    model.compile(
        optimizer=optimizer,
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            ParasitizedRecall(name="recall_parasitized"),
            Specificity(name="specificity"),
            BalancedAccuracy(name="balanced_accuracy"),
            tf.keras.metrics.AUC(curve="ROC", name="auc"),
            tf.keras.metrics.AUC(curve="PR", name="pr_auc"),
        ],
    )
    return model


def conv_bn_relu(filters, l2_weight):
    return [
        layers.Conv2D(
            filters,
            (3, 3),
            padding="same",
            use_bias=False,
            kernel_regularizer=regularizers.l2(l2_weight) if l2_weight else None,
        ),
        layers.BatchNormalization(),
        layers.Activation("relu"),
    ]


def build_custom_cnn(
    input_shape=(200, 200, 3),
    learning_rate: float = 1e-4,
    optimizer_name: str = "adam",
    l2_weight: float = 1e-4,
):
    """
    CNN propia inspirada en el paper:
    bloques convolucionales + batch normalization + global average pooling.
    Salida binaria sigmoid:
        0 = uninfected
        1 = parasitized
    La salida cerca de 1 representa probability_parasitized.
    """
    model = models.Sequential(
        [
            layers.Input(shape=input_shape),
            *conv_bn_relu(32, l2_weight),
            layers.MaxPooling2D((2, 2)),
            *conv_bn_relu(64, l2_weight),
            layers.MaxPooling2D((2, 2)),
            *conv_bn_relu(128, l2_weight),
            layers.MaxPooling2D((2, 2)),
            *conv_bn_relu(256, l2_weight),
            layers.GlobalAveragePooling2D(),
            layers.Dense(
                128,
                activation="relu",
                kernel_regularizer=regularizers.l2(l2_weight) if l2_weight else None,
            ),
            layers.Dropout(0.4),
            layers.Dense(1, activation="sigmoid"),
        ],
        name="custom_cnn",
    )

    return compile_binary_model(
        model,
        learning_rate=learning_rate,
        optimizer_name=optimizer_name,
    )


def build_vgg16_transfer(
    input_shape=(200, 200, 3),
    learning_rate: float = 1e-4,
    optimizer_name: str = "adam",
    trainable_backbone: bool = False,
    weights: str | None = "imagenet",
):
    """
    Transfer Learning con VGG16 preentrenada en ImageNet.
    Se reemplaza la cabeza de clasificación por:
        GlobalAveragePooling2D -> Dense(1024) -> Dropout(0.5) -> Dense(1)
    """
    base_model = VGG16(
        include_top=False,
        weights=weights,
        input_shape=input_shape,
    )

    for layer in base_model.layers:
        layer.trainable = trainable_backbone

    x = base_model.output
    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    x = layers.Dense(1024, activation="relu", name="feature_dense_1024")(x)
    x = layers.Dropout(0.5, name="dropout_50")(x)
    output = layers.Dense(1, activation="sigmoid", name="binary_output")(x)

    model = models.Model(
        inputs=base_model.input,
        outputs=output,
        name="tl_vgg16_malaria",
    )

    model = compile_binary_model(
        model,
        learning_rate=learning_rate,
        optimizer_name=optimizer_name,
    )

    return model, base_model


def build_densenet121_transfer(
    input_shape=(200, 200, 3),
    learning_rate: float = 1e-4,
    optimizer_name: str = "adam",
    trainable_backbone: bool = False,
    weights: str | None = "imagenet",
    dropout_rate: float = 0.5,
):
    """Build a binary DenseNet121 transfer-learning model.

    The project data pipeline supplies RGB tensors in ``[0, 1]`` for the
    default/``auto`` preprocessing mode.  The persisted normalization layer
    applies the same channel-wise mean/std contract as
    ``tf.keras.applications.densenet.preprocess_input`` (torch mode).

    Clinical convention remains unchanged: sigmoid output is
    ``probability_parasitized`` (0 = uninfected, 1 = parasitized).
    """
    base_model = DenseNet121(
        include_top=False,
        weights=weights,
        input_shape=input_shape,
    )
    for layer in base_model.layers:
        layer.trainable = bool(trainable_backbone)

    inputs = layers.Input(shape=input_shape, name="image")
    normalized = layers.Normalization(
        axis=-1,
        mean=[0.485, 0.456, 0.406],
        variance=[0.229**2, 0.224**2, 0.225**2],
        name="densenet_imagenet_normalization",
    )(inputs)
    features = base_model(normalized, training=False)
    pooled = layers.GlobalAveragePooling2D(name="global_avg_pool")(features)
    dropped = layers.Dropout(dropout_rate, name="dropout_50")(pooled)
    outputs = layers.Dense(1, activation="sigmoid", name="binary_output")(dropped)

    model = models.Model(
        inputs=inputs,
        outputs=outputs,
        name="tl_densenet121_malaria",
    )
    model = compile_binary_model(
        model,
        learning_rate=learning_rate,
        optimizer_name=optimizer_name,
    )
    return model, base_model


def unfreeze_last_layers(base_model, n_layers: int = 4):
    """
    Descongela las últimas capas del backbone para fine-tuning.
    """
    for layer in base_model.layers:
        layer.trainable = False

    for layer in base_model.layers[-n_layers:]:
        layer.trainable = True

    return base_model
