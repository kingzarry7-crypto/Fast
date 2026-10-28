import unittest

import numpy as np
import pandas as pd

from kitty_realistic_backtest import BacktestConfig
from kitty_trade_quality import (
    build_quality_features,
    filter_signals,
    label_trade_outcomes,
    train_quality_model,
    predict_quality,
)


class KittyTradeQualityTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2026-01-01", periods=1200, freq="5min", tz="UTC")
        steps = np.sin(np.arange(1200) / 7) * 0.002 + 0.00015
        close = 100 * np.exp(np.cumsum(steps))
        self.candles = pd.DataFrame({
            "open": close * (1 - 0.0002),
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
        }, index=self.index)
        self.signals = pd.Series(
            np.where(np.arange(1200) % 18 == 0, np.where(np.arange(1200) % 36 == 0, 1, -1), 0),
            index=self.index,
            dtype=int,
        )
        self.config = BacktestConfig(
            stop_pct=0.002, target_pct=0.003, max_hold_bars=8,
            spread_bps_per_side=1, commission_bps_per_side=0,
            slippage_bps_per_side=1,
        )

    def test_features_are_causal_and_include_direction(self):
        features = build_quality_features(self.candles, self.signals)
        changed = self.candles.copy()
        changed.iloc[900:, :] *= 1.2
        changed_features = build_quality_features(changed, self.signals)
        pd.testing.assert_frame_equal(features.iloc[:900], changed_features.iloc[:900])
        self.assertEqual(features.loc[self.index[36], "direction"], 1)
        self.assertEqual(features.loc[self.index[18], "direction"], -1)

    def test_labels_only_exist_for_completed_executed_trades_and_are_binary(self):
        labels = label_trade_outcomes(self.candles, self.signals, self.config)
        self.assertGreater(labels.notna().sum(), 10)
        self.assertTrue(set(labels.dropna().unique()).issubset({0.0, 1.0}))
        self.assertTrue(labels[self.signals.eq(0)].isna().all())

    def test_model_fails_closed_when_training_labels_are_insufficient(self):
        features = build_quality_features(self.candles, self.signals)
        labels = pd.Series(np.nan, index=self.index)
        labels.iloc[100:110] = [0, 1] * 5
        self.assertIsNone(train_quality_model(features, labels))

    def test_model_fits_only_when_both_outcome_classes_have_enough_examples(self):
        features = build_quality_features(self.candles, self.signals)
        labels = pd.Series(np.nan, index=self.index)
        labels.iloc[100:500] = np.arange(400) % 2
        model = train_quality_model(features, labels)
        self.assertIsNotNone(model)
        scores = predict_quality(model, features)
        self.assertTrue(scores.dropna().between(0, 1).all())
        self.assertGreater(scores.notna().sum(), 100)

    def test_filter_rejects_low_confidence_and_non_signal_rows(self):
        probabilities = pd.Series(0.9, index=self.index)
        probabilities.iloc[18] = 0.4
        filtered = filter_signals(self.signals, probabilities, threshold=0.6)
        self.assertEqual(filtered.iloc[18], 0)
        self.assertEqual(filtered.iloc[36], 1)
        self.assertTrue(filtered[self.signals.eq(0)].eq(0).all())
        self.assertTrue(filtered.isin([-1, 0, 1]).all())


if __name__ == "__main__":
    unittest.main()
