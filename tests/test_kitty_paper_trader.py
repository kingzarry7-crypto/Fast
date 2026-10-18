import os
import tempfile
import unittest
from unittest.mock import patch

import kitty_paper_trader as paper


def candles(count=60):
    result = []
    for i in range(count):
        close = 50_000 + i * 100
        result.append({
            "datetime": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
            "open": close - 25, "high": close + 100,
            "low": close - 100, "close": close, "volume": 10,
        })
    return result


class KittyPaperTraderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "KITTY_PAPER_DB_PATH": os.path.join(self.tmp.name, "paper.db"),
            "KITTY_PAPER_TRADING_ENABLED": "true",
            "KITTY_PAPER_ORDER_BTC": "0.001",
            "KITTY_PAPER_MAX_NOTIONAL_USD": "100",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_feature_contract_and_finite_values(self):
        values = paper._features(candles())
        self.assertEqual(set(values), {"Close", "SMA_20", "RSI_14", "BB_Upper", "BB_Lower", "MACD"})
        self.assertTrue(all(map(lambda x: isinstance(x, float), values.values())))

    def test_paper_cycle_isolated_from_live_connector_and_deduplicates_candle(self):
        rows = candles()
        rows[-2]["datetime"] = "2026-10-14T00:00:00Z"
        with patch("market.get_candles", return_value=rows), \
             patch("kitty_v3.predict_features", return_value={
                 "probability_next_close_up": 0.9,
                 "signal": "BUY_BIAS",
                 "thresholds": {"sell_below": 0.47, "buy_above": 0.53},
                 "warning": "experimental",
             }), \
             patch("trading_connector.place_market_order", side_effect=AssertionError("live connector must never be called")):
            first = paper.run_cycle()
            second = paper.run_cycle()
        self.assertEqual(first["mode"], "paper_only")
        self.assertEqual(first["simulated_side"], "BUY")
        self.assertFalse(first["live_trading_enabled"])
        self.assertEqual(second["status"], "already_processed")
        state = paper.status()["state"]
        self.assertAlmostEqual(state["quantity"], 0.001)
        self.assertAlmostEqual(state["cash"], 10_000 - 0.001 * (50_000 + 43 * 100))

    def test_runtime_controls_override_enabled_and_tuning(self):
        with paper._runtime_lock:
            paper._runtime_settings.update({"enabled": False, "order_btc": 0.002, "max_notional_usd": 250.0})
        try:
            self.assertFalse(paper._enabled())
            self.assertAlmostEqual(paper._quantity(), 0.002)
            self.assertAlmostEqual(paper._max_notional(), 250.0)
            with paper._runtime_lock:
                paper._runtime_settings["enabled"] = True
            self.assertTrue(paper._enabled())
        finally:
            with paper._runtime_lock:
                paper._runtime_settings.update({"enabled": None, "order_btc": None, "max_notional_usd": None})

    def test_disabled_flag_prevents_cycles(self):
        with patch.dict(os.environ, {"KITTY_PAPER_TRADING_ENABLED": "false"}):
            result = paper.run_cycle()
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["live_trading_enabled"])


if __name__ == "__main__":
    unittest.main()
