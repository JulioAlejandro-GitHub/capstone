"""Contract-level tests for TRAIN model-version finalization."""
import unittest

from src.malaria_dl.governance.services.training_model_version_finalizer import (
    _contract,
)


class TrainingModelVersionFinalizerTests(unittest.TestCase):
    def test_contract_is_derived_from_persisted_training_metadata(self):
        contract = _contract({
            "metadata": {"model_metadata": {"preprocessing": "densenet"}},
            "execution_parameters": {"img_size": 224},
            "parameters": {},
        })

        self.assertEqual(contract["preprocessing"], {"mode": "densenet"})
        self.assertEqual(contract["input"]["shape"], [None, 224, 224, 3])
        self.assertEqual(contract["output"]["shape"], [None, 1])
        self.assertEqual(contract["mapping"]["positive_class"], 1)
        self.assertEqual(contract["mapping"]["positive_label"], "parasitized")


if __name__ == "__main__":
    unittest.main()
