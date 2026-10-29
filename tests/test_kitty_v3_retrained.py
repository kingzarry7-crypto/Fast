import unittest
from unittest.mock import patch

import kitty_v3_retrained as kitty


class KittyV3RetrainedTests(unittest.TestCase):
    def test_actual_uploaded_checkpoint_loads_and_matches_contract(self):
        model, scaler, checkpoint = kitty._load()
        self.assertFalse(model.training)
        self.assertEqual(len(checkpoint["features"]), 18)
        self.assertEqual(scaler.n_features_in_, 18)
        self.assertEqual(checkpoint["architecture"], [18, 64, 32, 3])

    def test_status_keeps_inference_and_orders_disabled(self):
        result = kitty.status()
        self.assertTrue(result["available"], result)
        self.assertTrue(result["prediction_enabled"])
        self.assertFalse(result["automatic_order_execution_enabled"])

    def test_directional_signal_gate_requires_50_positive_after_cost_holdout_trades(self):
        checkpoint = {
            "production_ready": True,
            "broker_spread_verified": True,
            "recommended_min_confidence": 0.55,
            "test_metrics": {
                "signals_disabled_for_no_validated_edge": False,
                "paper_backtest_after_assumed_costs": {
                    "trade_count": 50,
                    "average_net_return": 0.002,
                    "compounded_net_return": 0.02,
                    "max_drawdown": -0.04,
                    "profit_factor": 1.15,
                },
            },
        }
        self.assertEqual(kitty.apply_research_signal_gate("LONG", 0.8, checkpoint)[0], "LONG")
        checkpoint["test_metrics"]["paper_backtest_after_assumed_costs"]["trade_count"] = 49
        self.assertEqual(kitty.apply_research_signal_gate("LONG", 0.8, checkpoint)[0], "NO TRADE")


    def test_prediction_returns_three_finite_class_probabilities(self):
        result = kitty.predict_features({name: 0.0 for name in kitty.EXPECTED_FEATURES})
        self.assertIn(result["signal"], {"LONG", "SHORT", "NO TRADE"})
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0, places=4)
        self.assertFalse(result["trading_enabled"])
        self.assertTrue(result["research_only"])


if __name__ == "__main__":
    unittest.main()
