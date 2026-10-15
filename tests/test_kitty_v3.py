"""Contract tests for the packaged six-feature Kitty V3 model."""
import math
import unittest
from unittest.mock import patch

import kitty_v3


class KittyV3ContractTests(unittest.TestCase):
    def setUp(self):
        kitty_v3._load.cache_clear()

    def test_packaged_weights_and_scaler_load_with_six_feature_contract(self):
        model, scaler, metadata = kitty_v3._load()
        self.assertFalse(model.training)
        self.assertEqual(len(metadata["features"]), 6)
        self.assertNotIsInstance(scaler, kitty_v3._ScalerFallback)
        self.assertEqual(scaler.n_features_in_, 6)
        self.assertEqual(tuple(model.layer_1.weight.shape), (32, 6))
        self.assertEqual(tuple(model.layer_2.weight.shape), (16, 32))
        self.assertEqual(tuple(model.layer_out.weight.shape), (1, 16))

    def test_status_reports_actual_load_result(self):
        result = kitty_v3.status()
        self.assertTrue(result.get("available"), result)
        self.assertEqual(result["features"], [
            "Close", "SMA_20", "RSI_14", "BB_Upper", "BB_Lower", "MACD"
        ])
        self.assertTrue(result["inference_only"])

    def test_prediction_returns_finite_probability_and_expected_contract(self):
        features = {
            "Close": 60000.0,
            "SMA_20": 59000.0,
            "RSI_14": 55.0,
            "BB_Upper": 62000.0,
            "BB_Lower": 56000.0,
            "MACD": 500.0,
        }
        result = kitty_v3.predict_features(features)
        probability = result["probability_next_close_up"]
        self.assertTrue(math.isfinite(probability))
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)
        self.assertIn(result["signal"], {"BUY_BIAS", "SELL_BIAS", "HOLD"})
        self.assertIn("No trades are placed", result["warning"])


    def test_scaler_output_with_wrong_width_is_rejected(self):
        model, _, metadata = kitty_v3._load()

        class BadScaler:
            def transform(self, rows):
                return [[0.0] * 5]

        features = {
            "Close": 60000.0,
            "SMA_20": 59000.0,
            "RSI_14": 55.0,
            "BB_Upper": 62000.0,
            "BB_Lower": 56000.0,
            "MACD": 500.0,
        }
        with patch.object(kitty_v3, "_load", return_value=(model, BadScaler(), metadata)):
            with self.assertRaisesRegex(ValueError, "exactly six scaled features"):
                kitty_v3.predict_features(features)

    def test_missing_feature_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing required Kitty features"):
            kitty_v3.predict_features({"Close": 60000.0})

    def test_nonfinite_feature_is_rejected(self):
        features = {
            "Close": float("nan"),
            "SMA_20": 59000.0,
            "RSI_14": 55.0,
            "BB_Upper": 62000.0,
            "BB_Lower": 56000.0,
            "MACD": 500.0,
        }
        with self.assertRaisesRegex(ValueError, "must be finite"):
            kitty_v3.predict_features(features)


if __name__ == "__main__":
    unittest.main()
