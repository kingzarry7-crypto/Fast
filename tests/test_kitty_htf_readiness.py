"""Regression tests for fail-closed higher-timeframe signal readiness."""
import unittest

import market


class HigherTimeframeReadinessTests(unittest.TestCase):
    def test_requires_both_four_hour_and_one_hour_analysis(self):
        analyses = {
            "4h": {"trend": "BULLISH"},
            "1h": {"trend": "BEARISH"},
        }
        self.assertTrue(market.required_higher_timeframes_ready(analyses))

    def test_missing_higher_timeframe_fails_closed(self):
        self.assertFalse(market.required_higher_timeframes_ready({"4h": {"trend": "BULLISH"}}))
        self.assertFalse(market.required_higher_timeframes_ready({"1h": {"trend": "BEARISH"}}))

    def test_failed_or_error_analysis_fails_closed(self):
        self.assertFalse(market.required_higher_timeframes_ready({
            "4h": {"trend": "BULLISH"},
            "1h": {"trend": "BEARISH", "success": False},
        }))
        self.assertFalse(market.required_higher_timeframes_ready({
            "4h": {"trend": "BULLISH"},
            "1h": {"trend": "BEARISH", "error": "provider failure"},
        }))

    def test_unknown_trend_fails_closed_but_neutral_is_valid(self):
        self.assertFalse(market.required_higher_timeframes_ready({
            "4h": {"trend": "UNAVAILABLE"},
            "1h": {"trend": "BEARISH"},
        }))
        self.assertTrue(market.required_higher_timeframes_ready({
            "4h": {"trend": "NEUTRAL"},
            "1h": {"trend": "BEARISH"},
        }))


if __name__ == "__main__":
    unittest.main()
