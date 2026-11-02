"""Regression tests for ZARRY's Gold chat fallback to the live Kitty snapshot."""
import sys
import types
import unittest
from unittest.mock import patch


def _fake_modules(*, gold_candles_available=True, model_available=True):
    agent_core = types.ModuleType("agent_core")
    agent_core.tool_analyze_symbol = lambda symbol, timeframe: {
        "symbol": symbol,
        "timeframe": timeframe,
        "signal": "WAIT",
        "data_ok": False,
        "error": "DATA UNAVAILABLE: MTF provider did not return all required candles",
    }
    agent_core.tool_news_risk = lambda symbol: {"risk": "LOW"}
    agent_core.tool_learn = lambda **kwargs: "learning-id"

    market = types.ModuleType("market")

    def get_candles(symbol, timeframe, outputsize):
        if not gold_candles_available:
            raise RuntimeError("No fresh candle provider returned data")
        return [
            {
                "datetime": "2026-11-02T05:00:00+00:00",
                "open": 3900.0,
                "high": 3915.0,
                "low": 3895.0,
                "close": 3910.0,
            }
            for _ in range(56)
        ]

    market.get_candles = get_candles

    kitty_api = types.ModuleType("kitty_api")
    kitty_api._validate_candles = lambda candles, timeframe, symbol: "2026-11-02T05:00:00+00:00"
    kitty_api._kitty_features = lambda candles: {"feature": 1.0}

    gold_model = types.ModuleType("kitty_gold_model")
    gold_model.status = lambda: {
        "available": model_available,
        "signal_edge_validated": False,
        "error": "Gold checkpoint is not installed" if not model_available else None,
    }
    gold_model.predict_features = lambda features: {
        "signal": "NO TRADE",
        "class_prediction": "LONG",
        "confidence": 0.6227,
        "signal_edge_validated": False,
        "signal_block_reason": "Holdout diagnostics did not validate positive net edge",
    }

    return {
        "agent_core": agent_core,
        "market": market,
        "kitty_api": kitty_api,
        "kitty_gold_model": gold_model,
    }


class AgentRouterGoldFallbackTests(unittest.TestCase):
    def test_reports_available_kitty_gold_candidate_when_mtf_agent_cannot_finish(self):
        import agent_router

        modules = _fake_modules()
        with patch.dict(sys.modules, modules):
            result = agent_router.route_agent_request("gold signal now", "user-1")

        self.assertEqual(result["status"], "partial")
        self.assertIn("XAU/USD", result["reply"])
        self.assertIn("NO TRADE", result["reply"])
        self.assertIn("LONG", result["reply"])
        self.assertIn("62.27%", result["reply"])
        self.assertIn("not been validated", result["reply"].lower())
        self.assertNotIn("market data feed is unavailable", result["reply"].lower())

    def test_does_not_claim_gold_snapshot_when_candle_provider_fails(self):
        import agent_router

        modules = _fake_modules(gold_candles_available=False)
        with patch.dict(sys.modules, modules):
            result = agent_router.route_agent_request("gold signal now", "user-1")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("No fresh candle provider returned data", result["reply"])
        self.assertNotIn("candidate LONG", result["reply"])


if __name__ == "__main__":
    unittest.main()
