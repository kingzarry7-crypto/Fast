import unittest

from kitty_alerts import normalize_kitty_alert


class KittyAlertNormalizationTests(unittest.TestCase):
    def test_mtf_watch_returns_buy_when_timeframes_confirm(self):
        from kitty_alerts import normalize_mtf_watch_signal
        result = normalize_mtf_watch_signal({
            "mtf_signal": "BUY", "4h": {"signal": "BUY"}, "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"}, "5m": {"signal": "BUY"},
        }, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0})
        self.assertEqual(result["signal"], "BUY")

    def test_mtf_watch_returns_wait_when_higher_timeframe_conflicts(self):
        from kitty_alerts import normalize_mtf_watch_signal
        result = normalize_mtf_watch_signal({
            "mtf_signal": "BUY", "4h": {"signal": "SELL"}, "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"}, "5m": {"signal": "BUY"},
        }, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0})
        self.assertEqual(result["signal"], "WAIT")
        self.assertIn("conflict", result["reason"])

    def test_mtf_watch_returns_wait_when_any_timeframe_is_missing_or_neutral(self):
        from kitty_alerts import normalize_mtf_watch_signal
        mtf = {
            "mtf_signal": "BUY",
            "4h": {"signal": "BUY"},
            "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"},
            "5m": {"signal": "WAIT"},
        }
        result = normalize_mtf_watch_signal(
            mtf, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0}
        )
        self.assertEqual(result["signal"], "WAIT")
        self.assertIn("5m", result["reason"])

    def test_mtf_watch_requires_all_four_timeframes_to_agree_for_sell(self):
        from kitty_alerts import normalize_mtf_watch_signal
        mtf = {
            "mtf_signal": "SELL",
            "4h": {"signal": "SELL"},
            "1h": {"signal": "SELL"},
            "15m": {"signal": "SELL"},
            "5m": {"signal": "SELL"},
        }
        result = normalize_mtf_watch_signal(
            mtf, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0}
        )
        self.assertEqual(result["signal"], "SELL")

    def test_mtf_watch_returns_wait_when_late_or_safety_check_missing(self):
        from kitty_alerts import normalize_mtf_watch_signal
        mtf = {"mtf_signal": "SELL", "4h": {"signal": "SELL"}, "1h": {"signal": "SELL"},
               "15m": {"signal": "SELL"}, "5m": {"signal": "SELL"}}
        late = normalize_mtf_watch_signal(mtf, {"action": "WAIT FOR RETEST", "status": "LATE", "score": 45})
        missing = normalize_mtf_watch_signal(mtf, None)
        self.assertEqual(late["signal"], "WAIT")
        self.assertEqual(missing["signal"], "WAIT")

    def test_mtf_watch_fails_closed_on_non_finite_late_entry_score(self):
        from kitty_alerts import normalize_mtf_watch_signal
        mtf = {
            "mtf_signal": "BUY", "4h": {"signal": "BUY"}, "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"}, "5m": {"signal": "BUY"},
        }
        for score in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(score=score):
                result = normalize_mtf_watch_signal(
                    mtf, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": score}
                )
                self.assertEqual(result["signal"], "WAIT")
                self.assertIn("not finite", result["reason"])

    def test_research_gold_candidate_is_not_promoted_to_actionable_signal(self):
        result = normalize_kitty_alert({
            "signal": "NO TRADE",
            "class_prediction": "LONG",
            "confidence": 0.81,
            "research_only": True,
            "production_ready": False,
            "signal_edge_validated": False,
        })
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertEqual(result["candidate_signal"], "LONG")
        self.assertFalse(result["actionable"])
        self.assertTrue(result["research_only"])

    def test_directional_alert_requires_explicit_production_and_edge_approval(self):
        result = normalize_kitty_alert({
            "signal": "SHORT",
            "confidence": 0.75,
            "production_ready": True,
            "signal_edge_validated": True,
        })
        self.assertEqual(result["signal"], "SHORT")
        self.assertTrue(result["actionable"])

    def test_invalid_confidence_is_clamped_to_safe_default(self):
        result = normalize_kitty_alert({
            "signal": "LONG",
            "confidence": float("nan"),
            "production_ready": True,
            "signal_edge_validated": True,
        })
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertFalse(result["actionable"])


    def test_mtf_watch_levels_accept_valid_buy_levels(self):
        from kitty_alerts import validate_mtf_watch_levels
        result = validate_mtf_watch_levels({"15m": {
            "price": 100, "entry_zone_low": 99, "entry_zone_high": 100,
            "stop_loss": 98, "tp1": 102, "tp2": 103, "tp3": 104,
        }}, "BUY")
        self.assertTrue(result["valid"])
        self.assertEqual(result["signal"], "BUY")
        self.assertGreater(result["risk_reward_tp1"], 0)

    def test_mtf_watch_levels_accept_valid_sell_levels(self):
        from kitty_alerts import validate_mtf_watch_levels
        result = validate_mtf_watch_levels({"15m": {
            "price": 100, "entry_zone_low": 99, "entry_zone_high": 100,
            "stop_loss": 102, "tp1": 98, "tp2": 97, "tp3": 96,
        }}, "SELL")
        self.assertTrue(result["valid"])
        self.assertEqual(result["signal"], "SELL")

    def test_mtf_watch_levels_fail_closed_if_missing_or_wrong_direction(self):
        from kitty_alerts import validate_mtf_watch_levels
        missing = validate_mtf_watch_levels({"15m": {"price": 100}}, "BUY")
        wrong = validate_mtf_watch_levels({"15m": {
            "price": 100, "entry_zone_low": 99, "entry_zone_high": 100,
            "stop_loss": 101, "tp1": 102, "tp2": 103, "tp3": 104,
        }}, "BUY")
        self.assertFalse(missing["valid"])
        self.assertEqual(missing["signal"], "WAIT")
        self.assertFalse(wrong["valid"])
        self.assertEqual(wrong["signal"], "WAIT")


    def test_research_only_kitty_model_forces_wait_even_when_mtf_agrees(self):
        from kitty_alerts import normalize_kitty_mtf_signal
        prediction = {
            "signal": "NO TRADE", "class_prediction": "LONG", "confidence": 0.82,
            "production_ready": False, "signal_edge_validated": False, "research_only": True,
        }
        mtf = {
            "mtf_signal": "BUY", "4h": {"signal": "BUY"}, "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"}, "5m": {"signal": "BUY"},
        }
        result = normalize_kitty_mtf_signal(
            prediction, mtf, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0}
        )
        self.assertEqual(result["signal"], "WAIT")
        self.assertFalse(result["model_actionable"])
        self.assertIn("Kitty model gate", result["reason"])

    def test_approved_kitty_model_and_all_matching_timeframes_can_signal_buy(self):
        from kitty_alerts import normalize_kitty_mtf_signal
        prediction = {
            "signal": "LONG", "class_prediction": "LONG", "confidence": 0.82,
            "production_ready": True, "signal_edge_validated": True,
        }
        mtf = {
            "mtf_signal": "BUY", "4h": {"signal": "BUY"}, "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"}, "5m": {"signal": "BUY"},
        }
        result = normalize_kitty_mtf_signal(
            prediction, mtf, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0}
        )
        self.assertEqual(result["signal"], "BUY")
        self.assertTrue(result["model_actionable"])

    def test_model_direction_conflict_forces_wait(self):
        from kitty_alerts import normalize_kitty_mtf_signal
        prediction = {
            "signal": "SHORT", "class_prediction": "SHORT", "confidence": 0.82,
            "production_ready": True, "signal_edge_validated": True,
        }
        mtf = {
            "mtf_signal": "BUY", "4h": {"signal": "BUY"}, "1h": {"signal": "BUY"},
            "15m": {"signal": "BUY"}, "5m": {"signal": "BUY"},
        }
        result = normalize_kitty_mtf_signal(
            prediction, mtf, {"action": "EARLY - GOOD ENTRY WINDOW", "status": "EARLY", "score": 0}
        )
        self.assertEqual(result["signal"], "WAIT")
        self.assertIn("model direction conflicts", result["reason"])


if __name__ == "__main__":
    unittest.main()
