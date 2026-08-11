from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from malaria_split.persistence.database import create_postgresql_engine
from malaria_split.persistence.models import DatasetVersionDefinition, DatasetVersionStatus


class PersistenceModelTests(TestCase):
    def test_draft_dataset_version_is_not_trainable(self):
        version = DatasetVersionDefinition(
            id=uuid4(),
            name="transactional fixture",
            semantic_version="0.0.0",
            status=DatasetVersionStatus.DRAFT,
            target_train_ratio=Decimal("0.8"),
            target_val_ratio=Decimal("0.1"),
            target_test_ratio=Decimal("0.1"),
        )
        self.assertFalse(version.is_trainable_without_physical_state)

    def test_non_postgresql_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires PostgreSQL"):
            create_postgresql_engine("sqlite://")
