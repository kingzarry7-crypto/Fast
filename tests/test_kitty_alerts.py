import unittest

from kitty_alerts import normalize_kitty_alert


class KittyAlertNormalizationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
