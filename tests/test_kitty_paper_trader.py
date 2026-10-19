import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import kitty_paper_trader as paper


def candles(count=60):
    result = []
    for i in range(count):
        close = 50_000 + i * 100
        result.append({
            "datetime": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i)).isoformat(),
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
        self.assertEqual(set(values), set(__import__("kitty_v3_retrained").EXPECTED_FEATURES))
        self.assertTrue(all(map(lambda x: isinstance(x, float), values.values())))

    def test_paper_cycle_isolated_from_live_connector_and_deduplicates_candle(self):
        rows = candles()
        with patch("market.get_candles", return_value=rows), \
             patch("kitty_v3_retrained.predict_features", return_value={
                 "confidence": 0.9,
                 "signal": "LONG",
                 "probabilities": {"SHORT": 0.02, "NO TRADE": 0.08, "LONG": 0.9},
                 "research_only": True,
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
        self.assertAlmostEqual(state["cash"], 10_000 - 0.001 * (50_000 + 58 * 100))

    def test_prediction_feedback_settles_only_when_entry_and_exit_candles_exist(self):
        rows = candles(10)
        signal_time = datetime.fromisoformat(rows[0]["datetime"])
        entry_time = (signal_time + timedelta(hours=1)).isoformat()
        exit_time = (signal_time + timedelta(hours=7)).isoformat()
        paper._init_db()
        conn = paper._connect()
        try:
            conn.execute(
                """INSERT INTO kitty_signal_feedback(
                   id,candle_time,symbol,signal,confidence,entry_time,exit_time,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                ("feedback-test", rows[0]["datetime"], paper.SYMBOL, "LONG", 0.9,
                 entry_time, exit_time, paper._now()),
            )
            conn.commit()
            self.assertEqual(paper._settle_signal_feedback(conn, rows[:5]), 0)
            self.assertEqual(paper._settle_signal_feedback(conn, rows), 1)
            row = conn.execute(
                "SELECT * FROM kitty_signal_feedback WHERE id='feedback-test'"
            ).fetchone()
            self.assertIsNotNone(row["settled_at"])
            self.assertEqual(row["actual_label"], "LONG")
            self.assertEqual(row["correct"], 1)
            self.assertGreater(row["forward_return"], 0)
        finally:
            conn.close()

    def test_feedback_summary_starts_empty_and_never_updates_model_automatically(self):
        summary = paper.feedback_summary()
        self.assertEqual(summary["recorded_predictions"], 0)
        self.assertEqual(summary["settled_predictions"], 0)
        self.assertFalse(summary["automatic_model_updates"])

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
