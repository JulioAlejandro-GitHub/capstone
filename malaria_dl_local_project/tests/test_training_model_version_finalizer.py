"""Contract-level tests for TRAIN model-version finalization."""
import unittest
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.data.input_contract import InputContractError

from src.malaria_dl.governance.services.training_model_version_finalizer import (
    _contract,
)


class TrainingModelVersionFinalizerTests(unittest.TestCase):
    def test_contract_is_derived_from_persisted_training_metadata(self):
        c = resolve_config("densenet121", {"model": {"input_shape": [224,224,3]}})["resolved"]["input_contract"]
        contract = _contract({
            "metadata": {"model_metadata": {"preprocessing": "rescale_0_1", "input_contract": c}},
            "execution_parameters": {"img_size": 224},
            "parameters": {},
        })

        self.assertEqual(contract["preprocessing"], {"mode": "rescale_0_1", "input_contract": c})
        self.assertEqual(contract["input"]["shape"], [None, 224, 224, 3])
        self.assertEqual(contract["output"]["shape"], [None, 1])
        self.assertEqual(contract["mapping"]["positive_class"], 1)
        self.assertEqual(contract["mapping"]["positive_label"], "parasitized")

    def test_missing_contract_blocks_finalization(self):
        with self.assertRaises(InputContractError):
            _contract({"execution_parameters": {"img_size": 224}})


if __name__ == "__main__":
    unittest.main()
