import unittest

from zarry_baseline import (
    classification_metrics,
    predict_baseline,
    simulate_predictions,
    BTC_ROUND_TRIP_COST,
    XAU_ROUND_TRIP_COST,
)


def sample(label="NO TRADE", ret_6h=0.0, close_vs_sma6=0.0,
           close_vs_sma20=0.0, sma6_vs_sma20=0.0, forward_return=0.0):
    return {
        "label": label,
        "features": {
            "ret_6h": ret_6h,
            "close_vs_sma6": close_vs_sma6,
            "close_vs_sma20": close_vs_sma20,
            "sma6_vs_sma20": sma6_vs_sma20,
        },
        "forward_return": forward_return,
    }


class ZarryBaselineTests(unittest.TestCase):
    def test_majority_class_is_fitted_from_train_only(self):
        train = [sample("SHORT"), sample("SHORT"), sample("LONG")]
        evaluation = [sample("LONG"), sample("LONG"), sample("LONG")]
        self.assertEqual(predict_baseline("majority", evaluation, train_rows=train), [0, 0, 0])

    def test_always_wait_never_emits_a_trade(self):
        rows = [sample("LONG", ret_6h=0.01), sample("SHORT", ret_6h=-0.02)]
        self.assertEqual(predict_baseline("always_wait", rows), [1, 1])

    def test_momentum_uses_asset_specific_inclusive_threshold(self):
        btc = [sample(ret_6h=0.003), sample(ret_6h=-0.0029), sample(ret_6h=0.0)]
        gold = [sample(ret_6h=0.0015), sample(ret_6h=-0.0014)]
        self.assertEqual(predict_baseline("momentum", btc, asset="BTCUSD"), [2, 1, 1])
        self.assertEqual(predict_baseline("momentum", gold, asset="XAUUSD"), [2, 1])

    def test_trend_confirmation_requires_all_three_features_to_agree(self):
        rows = [
            sample(ret_6h=0.004, close_vs_sma6=0.01, close_vs_sma20=0.02, sma6_vs_sma20=0.01),
            sample(ret_6h=0.004, close_vs_sma6=0.01, close_vs_sma20=-0.02, sma6_vs_sma20=0.01),
            sample(ret_6h=-0.004, close_vs_sma6=-0.01, close_vs_sma20=-0.02, sma6_vs_sma20=-0.01),
        ]
        self.assertEqual(predict_baseline("trend_confirmation", rows, asset="BTCUSD"), [2, 1, 0])

    def test_trade_simulation_applies_costs_and_skips_overlapping_signals(self):
        rows = [sample(forward_return=0.01) for _ in range(20)]
        predictions = [1] * 20
        predictions[0] = predictions[2] = predictions[8] = predictions[16] = 2
        result = simulate_predictions(rows, predictions, asset="BTCUSD")
        self.assertEqual(result["completed_trades"], 2)
        self.assertEqual(result["overlap_skips"], 1)
        self.assertAlmostEqual(result["net_trade_returns"][0], 0.009)
        self.assertAlmostEqual(result["compounded_net_return"], (1.009 ** 2) - 1)

    def test_classification_metrics_include_three_class_confusion_and_macro_scores(self):
        result = classification_metrics(
            ["SHORT", "NO TRADE", "LONG", "LONG"],
            [0, 1, 1, 2],
        )
        self.assertEqual(result["sample_count"], 4)
        self.assertEqual(result["confusion_matrix"], [[1, 0, 0], [0, 1, 0], [0, 1, 1]])
        self.assertAlmostEqual(result["accuracy"], 0.75)
        self.assertAlmostEqual(result["balanced_accuracy"], 2 / 3)
        self.assertIn("macro_f1", result)
        self.assertEqual(result["class_distribution"]["LONG"], 2)

    def test_asset_cost_defaults_are_frozen(self):
        self.assertEqual(BTC_ROUND_TRIP_COST, 0.001)
        self.assertEqual(XAU_ROUND_TRIP_COST, 0.0005)

    def test_missing_or_nonfinite_trade_return_is_rejected(self):
        rows = [sample(forward_return=float("nan")) for _ in range(9)]
        predictions = [2] + [1] * 8
        with self.assertRaises(ValueError):
            simulate_predictions(rows, predictions, asset="BTCUSD")


if __name__ == "__main__":
    unittest.main()
