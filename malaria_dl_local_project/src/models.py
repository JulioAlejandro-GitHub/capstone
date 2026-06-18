import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import VGG16


@tf.keras.utils.register_keras_serializable(package="malaria")
class ParasitizedRecall(tf.keras.metrics.Metric):
    """
    Sensibilidad clínica para la clase parasitized.

    TFDS codifica:
      0 = parasitized
      1 = uninfected

    La salida sigmoid del proyecto representa P(label=1) = P(uninfected).
    Por eso una predicción parasitized corresponde a y_pred < threshold.
    """

    def __init__(self, threshold: float = 0.5, name: str = "recall_parasitized", **kwargs):
        super().__init__(name=name, **kwargs)
        self.threshold = float(threshold)
        self.true_positives = self.add_weight(name="true_positives", initializer="zeros")
        self.false_negatives = self.add_weight(name="false_negatives", initializer="zeros")

    def update_state(self, y_true, y_pred, sample_weight=None):
        y_true = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
        y_pred = tf.cast(tf.reshape(y_pred, [-1]), tf.float32)

        true_parasitized = tf.equal(y_true, 0.0)
        pred_parasitized = tf.less(y_pred, self.threshold)

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


def compile_binary_model(model, learning_rate: float = 1.0, optimizer_name: str = "adadelta"):
    """
    Compila un modelo binario con métricas útiles para salud/diagnóstico.
    """
    if optimizer_name.lower() == "adadelta":
        optimizer = tf.keras.optimizers.Adadelta(learning_rate=learning_rate)
    elif optimizer_name.lower() == "adam":
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    else:
        raise ValueError(f"Optimizador no soportado: {optimizer_name}")

    model.compile(
        optimizer=optimizer,
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            ParasitizedRecall(name="recall_parasitized"),
            tf.keras.metrics.AUC(name="auc"),
        ],
    )
    return model


def build_custom_cnn(input_shape=(200, 200, 3), learning_rate: float = 1.0):
    """
    CNN propia inspirada en el paper:
    bloques convolucionales + max pooling + densas + dropout.
    Salida binaria sigmoid:
        0 = parasitized
        1 = uninfected
    """
    model = models.Sequential(
        [
            layers.Input(shape=input_shape),

            layers.Conv2D(32, (3, 3), padding="same", activation="relu"),
            layers.Conv2D(32, (3, 3), padding="same", activation="relu"),
            layers.MaxPooling2D((2, 2)),

            layers.Conv2D(64, (3, 3), padding="same", activation="relu"),
            layers.Conv2D(64, (3, 3), padding="same", activation="relu"),
            layers.MaxPooling2D((2, 2)),

            layers.Conv2D(128, (3, 3), padding="same", activation="relu"),
            layers.Conv2D(128, (3, 3), padding="same", activation="relu"),
            layers.MaxPooling2D((2, 2)),

            layers.Conv2D(256, (3, 3), padding="same", activation="relu"),
            layers.Conv2D(256, (3, 3), padding="same", activation="relu"),
            layers.MaxPooling2D((2, 2)),

            layers.Flatten(),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.5),
            layers.Dense(1, activation="sigmoid"),
        ],
        name="custom_cnn",
    )

    return compile_binary_model(
        model,
        learning_rate=learning_rate,
        optimizer_name="adadelta",
    )


def build_vgg16_transfer(
    input_shape=(200, 200, 3),
    learning_rate: float = 0.01,
    trainable_backbone: bool = False,
):
    """
    Transfer Learning con VGG16 preentrenada en ImageNet.
    Se reemplaza la cabeza de clasificación por:
        GlobalAveragePooling2D -> Dense(1024) -> Dropout(0.5) -> Dense(1)
    """
    base_model = VGG16(
        include_top=False,
        weights="imagenet",
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
        optimizer_name="adadelta",
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
