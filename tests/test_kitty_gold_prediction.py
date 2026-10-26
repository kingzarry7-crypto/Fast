"""Regression tests for gold/crypto candle timestamps used by Kitty signals."""
import unittest
from datetime import datetime, timezone

from kitty_features import normalize_candle_timestamp


class KittyGoldPredictionTests(unittest.TestCase):
    def test_unix_seconds_string_normalizes_to_utc_iso8601(self):
        value = str(datetime.now(timezone.utc).timestamp())
        result = normalize_candle_timestamp(value)
        self.assertTrue(result.endswith("+00:00"))
        self.assertIn("T", result)

    def test_unix_milliseconds_string_normalizes_to_utc_iso8601(self):
        value = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        result = normalize_candle_timestamp(value)
        self.assertTrue(result.endswith("+00:00"))
        self.assertIn("T", result)

    def test_iso_timestamp_normalizes_to_utc(self):
        result = normalize_candle_timestamp("2026-10-22T12:00:00Z")
        self.assertEqual(result, "2026-10-22T12:00:00+00:00")

    def test_invalid_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ISO-8601 or Unix"):
            normalize_candle_timestamp("not-a-time")


class BtcModelIdentityTests(unittest.TestCase):
    def test_btc_checkpoint_requires_explicit_btc_hourly_identity(self):
        import kitty_v3_retrained as model

        valid = {
            "training_symbol": "BTC",
            "training_timeframe": "1h",
            "automatic_order_execution_enabled": False,
        }
        model.validate_checkpoint_metadata(valid)

        invalid_checkpoints = [
            {"training_timeframe": "1h", "automatic_order_execution_enabled": False},
            {"training_symbol": "ETH", "training_timeframe": "1h", "automatic_order_execution_enabled": False},
            {"training_symbol": "BTC", "training_timeframe": "15m", "automatic_order_execution_enabled": False},
            {"training_symbol": "BTC", "training_timeframe": "1h", "automatic_order_execution_enabled": True},
        ]
        for invalid in invalid_checkpoints:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    model.validate_checkpoint_metadata(invalid)


class GoldModelIsolationTests(unittest.TestCase):
    def test_gold_checkpoint_requires_xauusd_symbol_and_twelve_data_spot_source(self):
        import kitty_gold_model

        valid = {
            "training_symbol": "XAUUSD",
            "training_data_sources": ["Twelve Data XAU/USD"],
            "features": kitty_gold_model.EXPECTED_FEATURES,
            "architecture": kitty_gold_model.EXPECTED_ARCHITECTURE,
            "automatic_order_execution_enabled": False,
        }
        kitty_gold_model.validate_checkpoint_metadata(valid)

        proxy = dict(valid, training_data_sources=["Yahoo Finance GC=F gold futures proxy (not XAU/USD spot)"])
        with self.assertRaisesRegex(ValueError, "Twelve Data XAU/USD"):
            kitty_gold_model.validate_checkpoint_metadata(proxy)

    def test_gold_checkpoint_rejects_btc_symbol(self):
        import kitty_gold_model

        invalid = {
            "training_symbol": "BTC",
            "training_data_sources": ["Twelve Data XAU/USD"],
            "features": kitty_gold_model.EXPECTED_FEATURES,
            "architecture": kitty_gold_model.EXPECTED_ARCHITECTURE,
            "automatic_order_execution_enabled": False,
        }
        with self.assertRaisesRegex(ValueError, "training_symbol"):
            kitty_gold_model.validate_checkpoint_metadata(invalid)

    def test_gold_directional_signal_requires_explicit_positive_holdout_edge(self):
        import kitty_gold_model

        self.assertFalse(kitty_gold_model.has_validated_edge({}))
        self.assertFalse(kitty_gold_model.has_validated_edge({
            "test_metrics": {"signals_disabled_for_no_validated_edge": True}
        }))
        self.assertFalse(kitty_gold_model.has_validated_edge({
            "test_metrics": {"signals_disabled_for_no_validated_edge": None}
        }))
        # A false flag alone is not evidence: explicit approval, a calibrated
        # threshold, and positive after-cost holdout results are all required.
        self.assertFalse(kitty_gold_model.has_validated_edge({
            "test_metrics": {"signals_disabled_for_no_validated_edge": False}
        }))
        approved = {
            "production_ready": True,
            "broker_spread_verified": True,
            "recommended_min_confidence": 0.55,
            "test_metrics": {
                "signals_disabled_for_no_validated_edge": False,
                "paper_backtest_after_assumed_costs": {
                    "trade_count": 35,
                    "average_net_return": 0.002,
                    "compounded_net_return": 0.04,
                    "max_drawdown": -0.02,
                    "profit_factor": 1.2,
                },
            },
        }
        self.assertTrue(kitty_gold_model.has_validated_edge(approved))
        approved["broker_spread_verified"] = False
        self.assertFalse(kitty_gold_model.has_validated_edge(approved))
        approved["broker_spread_verified"] = True
        approved["test_metrics"]["paper_backtest_after_assumed_costs"]["trade_count"] = 3
        self.assertFalse(kitty_gold_model.has_validated_edge(approved))
        approved["test_metrics"]["paper_backtest_after_assumed_costs"]["trade_count"] = 35
        approved["test_metrics"]["paper_backtest_after_assumed_costs"]["max_drawdown"] = -0.061
        self.assertFalse(kitty_gold_model.has_validated_edge(approved))

    def test_gold_checkpoint_must_keep_orders_disabled(self):
        import kitty_gold_model

        invalid = {
            "training_symbol": "XAUUSD",
            "training_data_sources": ["Twelve Data XAU/USD"],
            "features": kitty_gold_model.EXPECTED_FEATURES,
            "architecture": kitty_gold_model.EXPECTED_ARCHITECTURE,
            "automatic_order_execution_enabled": True,
        }
        with self.assertRaisesRegex(ValueError, "disable automatic order execution"):
            kitty_gold_model.validate_checkpoint_metadata(invalid)


if __name__ == "__main__":
    unittest.main()
