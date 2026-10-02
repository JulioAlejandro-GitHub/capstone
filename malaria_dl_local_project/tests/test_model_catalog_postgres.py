"""public.models decides which models exist; registry.py only how Python implements them.

Compose PostgreSQL only. Synthetic rows live in an outer transaction that is always
rolled back, so the development catalog is never modified.
"""

from contextlib import contextmanager
from dataclasses import replace

import pytest
from sqlalchemy import text

from src.malaria_dl.campaigns import repository as campaign_repository
from src.malaria_dl.models import registry
from src.malaria_dl.persistence.database import get_engine

pytestmark = pytest.mark.requires_docker_postgres


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


@pytest.mark.parametrize("name", ("custom_cnn", "vgg16", "densenet121"))
def test_registered_model_with_implementation_resolves(name):
    assert name in registry.registered_models()
    descriptor = registry.resolve_descriptor(name)
    assert descriptor.id == name and descriptor.create_adapter() is not None


def test_unregistered_model_is_rejected_before_implementation_lookup():
    with pytest.raises(ValueError, match="^MODEL_NOT_REGISTERED:unet$"):
        registry.resolve_descriptor("unet")


def test_registered_model_without_implementation_is_explicit(catalog_transaction):
    catalog_transaction.execute(
        text("INSERT INTO public.models(name, model_type) VALUES ('model_without_implementation', 'cnn')")
    )
    assert "model_without_implementation" in registry.enabled_models()
    with pytest.raises(
        ValueError, match="^IMPLEMENTATION_NOT_AVAILABLE:model_without_implementation$"
    ):
        registry.resolve_descriptor("model_without_implementation")


def test_catalog_is_governed_by_public_models(catalog_transaction, monkeypatch):
    def names():
        return tuple(
            catalog_transaction.execute(
                text("SELECT DISTINCT name FROM public.models ORDER BY name")
            ).scalars()
        )

    assert registry.enabled_models() == names()
    # A row added only to the database appears; nothing was added to Python.
    catalog_transaction.execute(
        text("INSERT INTO public.models(name, model_type) VALUES ('catalog_probe', 'cnn')")
    )
    assert "catalog_probe" not in registry.MODEL_REGISTRY
    assert registry.enabled_models() == names()
    assert "catalog_probe" in registry.enabled_models()
    # An implementation known only to Python does not make a model exist.
    monkeypatch.setattr(registry, "MODEL_REGISTRY", dict(registry.MODEL_REGISTRY))
    registry.register(replace(registry.MODEL_REGISTRY["custom_cnn"], id="python_only", aliases=()))
    assert "python_only" not in registry.enabled_models()
    with pytest.raises(ValueError, match="^MODEL_NOT_REGISTERED:python_only$"):
        registry.resolve_descriptor("python_only")
