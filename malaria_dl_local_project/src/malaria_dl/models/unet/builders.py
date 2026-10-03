"""U-Net builders. Every variant composes blocks.unet_encoder; only heads differ."""

from tensorflow.keras import layers, models

from .blocks import DEFAULT_BOTTLENECK_FILTERS, DEFAULT_FILTERS, unet_decoder, unet_encoder


def build_unet_segmenter(
    input_shape=(200, 200, 3),
    filters=DEFAULT_FILTERS,
    bottleneck_filters=DEFAULT_BOTTLENECK_FILTERS,
):
    """RGB in [0,1] -> per-pixel sigmoid probability of the stain-derived pseudo-mask.

    Uncompiled. Input side must be divisible by 2 ** len(filters).
    """
    depth = 2 ** len(filters)
    if input_shape[0] % depth or input_shape[1] % depth:
        raise ValueError(f"UNET_INPUT_NOT_DIVISIBLE_BY_{depth}")
    inputs = layers.Input(shape=input_shape, name="image")
    bottleneck, skips = unet_encoder(inputs, filters, bottleneck_filters)
    features = unet_decoder(bottleneck, skips)
    outputs = layers.Conv2D(1, 1, activation="sigmoid", name="pseudo_mask")(features)
    return models.Model(inputs, outputs, name="unet_segmenter")
