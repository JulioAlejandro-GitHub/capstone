"""REPRESENT: governed embeddings of an EVALUATE population and their descriptive projections.

The representation is the output of the model's single top-level GlobalAveragePooling2D layer
(VGG16, DenseNet121 and custom_cnn all expose one), so architectures are compared at the same point.
PCA and UMAP are fitted once by the executor and persisted; CKA is computed on read because it
depends on which attempts are compared.
"""

from .contracts import require

ROLES = ("embeddings", "pca", "pca_variance", "umap")


def representation_spec():
    return {
        "method": "global_average_pooling",
        "version": "represent_v1",
        "layer": "GlobalAveragePooling2D",
        "pca": {"n_components": 50, "svd_solver": "full", "centering": "population_mean"},
        "umap": {"n_components": 2, "n_neighbors": 15, "min_dist": 0.1, "metric": "euclidean"},
    }


def pooling_layer(model):
    import tensorflow as tf

    layers = [layer for layer in model.layers if isinstance(layer, tf.keras.layers.GlobalAveragePooling2D)]
    require(len(layers) == 1, "REPRESENTATION_LAYER_AMBIGUOUS")
    return layers[0]


def project(features, spec, seed):
    """PCA (variance curve + first two components) and UMAP 2D, deterministic for a seed."""
    import numpy as np
    import umap
    from sklearn.decomposition import PCA

    features = np.asarray(features, dtype="float64")
    require(features.ndim == 2 and np.isfinite(features).all(), "REPRESENTATION_NONFINITE")
    components = min(spec["pca"]["n_components"], *features.shape)
    pca = PCA(n_components=components, svd_solver=spec["pca"]["svd_solver"], random_state=seed)
    coordinates = pca.fit_transform(features)
    options = spec["umap"]
    reducer = umap.UMAP(n_components=options["n_components"], n_neighbors=options["n_neighbors"],
                        min_dist=options["min_dist"], metric=options["metric"], random_state=seed)
    embedded = reducer.fit_transform(features)
    result = {
        "pca": coordinates[:, :2].astype("float32"),
        "pca_variance": pca.explained_variance_ratio_.astype("float64"),
        "umap": np.asarray(embedded, dtype="float32"),
    }
    require(all(np.isfinite(value).all() for value in result.values()), "REPRESENTATION_NONFINITE")
    return result


def linear_cka(x, y):
    """Linear CKA (Kornblith et al., 2019) between two representations of the same ordered samples."""
    import numpy as np

    x = np.asarray(x, dtype="float64")
    y = np.asarray(y, dtype="float64")
    require(x.ndim == y.ndim == 2 and x.shape[0] == y.shape[0] and x.shape[0] > 1, "CKA_POPULATION_CONFLICT")
    x = x - x.mean(axis=0)
    y = y - y.mean(axis=0)
    cross = np.linalg.norm(y.T @ x, "fro") ** 2
    norms = np.linalg.norm(x.T @ x, "fro") * np.linalg.norm(y.T @ y, "fro")
    return float(cross / norms) if norms else None
