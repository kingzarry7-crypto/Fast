import os
import unittest
from unittest.mock import patch

import torch
import kitty_v3_retrained as kitty


class _FakeScaler:
    n_features_in_ = 18
    def transform(self, values):
        return values


class _FakeModel:
    def __call__(self, tensor):
        return torch.tensor([[0.0, 0.1, 1.2]])


class KittyV3RetrainedTests(unittest.TestCase):
    def test_actual_uploaded_checkpoint_loads_and_matches_contract(self):
        model, scaler, checkpoint = kitty._load()
        self.assertFalse(model.training)
        self.assertEqual(len(checkpoint["features"]), 18)
        self.assertEqual(scaler.n_features_in_, 18)
        self.assertEqual(checkpoint["architecture"], [18, 64, 32, 3])

    def test_status_keeps_orders_disabled_by_default(self):
        with patch.dict(os.environ, {kitty.MONITORING_ENV: "false"}):
            result = kitty.status()
        self.assertTrue(result["available"], result)
        self.assertFalse(result["prediction_enabled"])
        self.assertFalse(result["automatic_order_execution_enabled"])
        self.assertTrue(result["signal_monitoring_only"])

    def test_prediction_fails_closed_by_default(self):
        with patch.dict(os.environ, {kitty.MONITORING_ENV: "false"}):
            with self.assertRaisesRegex(RuntimeError, "monitoring is disabled"):
                kitty.predict_features({name: 0.0 for name in kitty.EXPECTED_FEATURES})

    def test_opt_in_prediction_is_monitor_only(self):
        features = {name: 0.0 for name in kitty.EXPECTED_FEATURES}
        with patch.dict(os.environ, {kitty.MONITORING_ENV: "true"}), patch.object(
            kitty, "_load", return_value=(_FakeModel(), _FakeScaler(), {})
        ):
            result = kitty.predict_features(features)
        self.assertEqual(result["signal"], "LONG")
        self.assertTrue(result["monitor_only"])
        self.assertFalse(result["trading_authorized"])
        self.assertEqual(result["gold_forex_validation"], "unverified")

    def test_rejects_missing_or_non_finite_features(self):
        with patch.dict(os.environ, {kitty.MONITORING_ENV: "true"}):
            with self.assertRaisesRegex(ValueError, "exactly"):
                kitty.predict_features({"ret_1h": 0.0})
            features = {name: 0.0 for name in kitty.EXPECTED_FEATURES}
            features["ret_1h"] = float("nan")
            with self.assertRaisesRegex(ValueError, "finite"):
                kitty.predict_features(features)


if __name__ == "__main__":
    unittest.main()
