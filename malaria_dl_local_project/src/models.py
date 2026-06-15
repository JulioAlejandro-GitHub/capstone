import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import VGG16


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
