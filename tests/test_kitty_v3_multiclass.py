"""Contract tests for Kitty V3 multiclass inference; run with python -m unittest."""
import json
import unittest
from unittest.mock import patch

import kitty_v3_multiclass as kitty


class KittyV3ContractTests(unittest.TestCase):
    def test_model_parameter_shapes_match_expected_metadata(self):
        model = kitty.KittyV3MulticlassNet()
        actual = {key: list(value.shape) for key, value in model.state_dict().items()}
        expected = {
            "network.0.weight": [64, 18],
            "network.0.bias": [64],
            "network.3.weight": [32, 64],
            "network.3.bias": [32],
            "network.6.weight": [3, 32],
            "network.6.bias": [3],
        }
        self.assertEqual(actual, expected)

    def test_predictions_stay_blocked_until_both_audits_pass(self):
        metadata = {
            "feature_order": [f"f{i}" for i in range(18)],
            "architecture_expected": [18, 64, 32, 3],
            "class_mapping": {"0": "SHORT", "1": "NO_TRADE", "2": "LONG"},
            "target_execution_alignment_verified": False,
            "split_boundary_audit_passed": False,
        }
        with patch.object(kitty, "_load", return_value=(kitty.KittyV3MulticlassNet(), object(), metadata)):
            with self.assertRaisesRegex(RuntimeError, "audits are verified"):
                kitty.predict_features({name: 0.0 for name in metadata["feature_order"]})


if __name__ == "__main__":
    unittest.main()
