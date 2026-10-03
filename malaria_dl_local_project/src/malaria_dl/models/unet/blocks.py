"""Shared U-Net blocks. One encoder/decoder used by every U-Net variant."""

from tensorflow.keras import layers

DEFAULT_FILTERS = (32, 64, 128)
DEFAULT_BOTTLENECK_FILTERS = 256


def conv_block(x, filters, name):
    """(Conv2D 3x3 no bias -> BatchNorm -> ReLU) x 2.

    Same layer recipe as architectures.conv_bn_relu, built here with stable
    names so encoder weights can later be transferred by name between the
    Segmenter, Encoder-classifier and Multi-Task variants.
    """
    for i in (1, 2):
        x = layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_conv{i}")(x)
        x = layers.BatchNormalization(name=f"{name}_bn{i}")(x)
        x = layers.Activation("relu", name=f"{name}_relu{i}")(x)
    return x


def unet_encoder(x, filters=DEFAULT_FILTERS, bottleneck_filters=DEFAULT_BOTTLENECK_FILTERS):
    """Contracting path. Returns (bottleneck, skips) with skips ordered shallow -> deep.

    200x200 input: 200 -> 100 -> 50 -> 25 at the bottleneck.
    """
    skips = []
    for level, f in enumerate(filters, start=1):
        x = conv_block(x, f, name=f"enc{level}")
        skips.append(x)
        x = layers.MaxPooling2D(2, name=f"enc{level}_pool")(x)
    bottleneck = conv_block(x, bottleneck_filters, name="bottleneck")
    return bottleneck, skips


def unet_decoder(bottleneck, skips):
    """Expanding path symmetric to unet_encoder; returns the last feature map (no head)."""
    x = bottleneck
    for level, skip in reversed(list(enumerate(skips, start=1))):
        f = skip.shape[-1]
        x = layers.Conv2DTranspose(f, 2, strides=2, padding="same", name=f"dec{level}_up")(x)
        x = layers.Concatenate(name=f"dec{level}_concat")([x, skip])
        x = conv_block(x, f, name=f"dec{level}")
    return x
