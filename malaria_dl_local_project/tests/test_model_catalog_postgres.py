"""public.models decides which models exist; registry.py only how Python implements them.

Compose PostgreSQL only. Synthetic rows/updates live in an outer transaction that is always
rolled back, so the development catalog is never modified.
"""

from contextlib import contextmanager
from dataclasses import replace

import pytest
from sqlalchemy import text

from src.malaria_dl.campaigns import configuration as cc
from src.malaria_dl.campaigns import repository as campaign_repository
from src.malaria_dl.models import registry
from src.malaria_dl.persistence.database import get_engine

pytestmark = pytest.mark.requires_docker_postgres

EXPECTED = {
    "custom_cnn": ("Custom CNN", "classification", "tensorflow/keras"),
    "densenet121": ("DenseNet121", "classification", "tensorflow/keras"),
    "vgg16": ("VGG16", "classification", "tensorflow/keras"),
}


@pytest.fixture
def catalog_transaction(monkeypatch):
    """Registry reads go through this uncommitted transaction; rollback on exit."""
    engine = get_engine()
    connection = engine.connect()
    outer = connection.begin()

    @contextmanager
    def scope(readonly=False):
        yield connection

    monkeypatch.setattr(campaign_repository, "connection_scope", scope)
    try:
        yield connection
    finally:
        outer.rollback()
        connection.close()
        engine.dispose()


def sql(c, statement):
    return c.execute(text(statement))


def labels():
    return {m["id"]: m["label"] for m in cc.catalog()["models"]}


def test_catalog_comes_from_public_models(catalog_transaction):
    rows = sql(
        catalog_transaction,
        "SELECT name, architecture, model_type, framework FROM public.models ORDER BY name",
    ).mappings().all()
    assert registry.model_catalog() == tuple(dict(r) for r in rows)
    assert set(EXPECTED) <= set(registry.registered_models())
    # Adding a row makes the model exist; deleting it makes it disappear.
    sql(catalog_transaction, "INSERT INTO public.models(name, model_type) VALUES ('catalog_probe', 'cnn')")
    assert "catalog_probe" in registry.registered_models()
    sql(catalog_transaction, "DELETE FROM public.models WHERE name='catalog_probe'")
    assert "catalog_probe" not in registry.registered_models()


def test_catalog_metadata():
    rows = {m["name"]: m for m in registry.model_catalog()}
    for name, (architecture, model_type, framework) in EXPECTED.items():
        assert rows[name] == dict(
            name=name, architecture=architecture, model_type=model_type, framework=framework
        )


def test_labels_are_public_models_architecture(catalog_transaction):
    assert not hasattr(cc, "MODEL_LABELS")
    assert labels() == {name: v[0] for name, v in EXPECTED.items()}
    sql(catalog_transaction, "UPDATE public.models SET architecture='Custom CNN probe' WHERE name='custom_cnn'")
    assert labels()["custom_cnn"] == "Custom CNN probe"


def test_unregistered_model_is_rejected_before_implementation_lookup():
    with pytest.raises(ValueError, match="^MODEL_NOT_REGISTERED:unet$"):
        registry.resolve_descriptor("unet")


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_registered_model_with_implementation_resolves(name):
    descriptor = registry.resolve_descriptor(name)
    assert descriptor.id == name and descriptor.create_adapter() is not None


def test_registered_model_without_implementation_is_explicit(catalog_transaction):
    sql(
        catalog_transaction,
        "INSERT INTO public.models(name, architecture, model_type) "
        "VALUES ('model_without_implementation', 'No implementation', 'classification')",
    )
    assert "model_without_implementation" in registry.enabled_models()
    with pytest.raises(
        ValueError, match="^IMPLEMENTATION_NOT_AVAILABLE:model_without_implementation$"
    ):
        registry.resolve_descriptor("model_without_implementation")
    # The campaign catalog does not hide it either.
    with pytest.raises(ValueError, match="^IMPLEMENTATION_NOT_AVAILABLE:"):
        cc.catalog()


def test_consumers_use_catalog_for_existence_and_python_for_implementation(monkeypatch):
    names = tuple(m["name"] for m in registry.model_catalog())
    assert registry.registered_models() == registry.enabled_models() == names
    assert tuple(labels()) == names
    # An implementation known only to Python does not make a model exist.
    monkeypatch.setattr(registry, "MODEL_REGISTRY", dict(registry.MODEL_REGISTRY))
    registry.register(replace(registry.MODEL_REGISTRY["custom_cnn"], id="python_only", aliases=()))
    assert "python_only" not in registry.enabled_models()
    assert "python_only" not in labels()
    with pytest.raises(ValueError, match="^MODEL_NOT_REGISTERED:python_only$"):
        registry.resolve_descriptor("python_only")
