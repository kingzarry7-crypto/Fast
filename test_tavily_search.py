"""Regression tests for Tavily API limit error classification."""
import unittest
from unittest.mock import patch

import tavily_search


class _FailingClient:
    def __init__(self, message):
        self.message = message

    def search(self, **kwargs):
        raise RuntimeError(self.message)


class TavilyLimitClassificationTests(unittest.TestCase):
    def setUp(self):
        tavily_search._tavily_payment_blocked = False
        tavily_search._search_cache.clear()

    def tearDown(self):
        tavily_search._tavily_payment_blocked = False
        tavily_search._search_cache.clear()

    def _search_with_error(self, message):
        with patch.object(tavily_search, "is_tavily_configured", return_value=True), patch.object(
            tavily_search, "get_client", return_value=_FailingClient(message)
        ), patch.object(tavily_search, "_get_cached", return_value=None), patch.object(
            tavily_search, "_fallback_search",
            return_value={"success": False, "error": "fallback_unavailable", "results": [], "sources": []}
        ):
            return tavily_search.search_web("test query")

    def test_432_is_plan_limit_not_generic_failure(self):
        result = self._search_with_error("432 plan limit exceeded")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "plan_limit_exceeded")

    def test_433_is_payg_limit_not_generic_failure(self):
        result = self._search_with_error("433 pay-as-you-go limit exceeded")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "payg_limit_exceeded")

    def test_429_remains_rate_limit(self):
        result = self._search_with_error("429 Too Many Requests")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "rate_limit")

    def test_402_payment_error_opens_tavily_circuit(self):
        with patch.object(tavily_search, "is_tavily_configured", return_value=True), patch.object(
            tavily_search, "get_client", return_value=_FailingClient("HTTP 402 Payment Required")
        ) as get_client, patch.object(tavily_search, "_get_cached", return_value=None), patch(
            "search_providers.searxng.search",
            return_value={"success": False, "error": "not_configured", "results": [], "sources": []},
        ), patch.object(
            tavily_search, "_fallback_search",
            return_value={"success": False, "error": "fallback_unavailable", "results": [], "sources": []},
        ):
            first = tavily_search.search_web("latest market news")
            self.assertFalse(first["success"])
            self.assertEqual(first["error"], "payment_required")
            self.assertTrue(tavily_search.provider_status()["payment_blocked"])

            second = tavily_search.search_web("another current question")
            self.assertFalse(second["success"])
            self.assertEqual(second["error"], "payment_required")
            self.assertEqual(get_client.call_count, 1, "Tavily must not be called again after HTTP 402")

    def test_fallback_success_is_reused_from_fallback_cache(self):
        fallback = {"success": True, "provider": "duckduckgo_fallback", "results": [{"title": "Example", "url": "https://example.com", "content": ""}], "sources": []}
        with patch.object(tavily_search, "_get_cached", return_value=None), patch(
            "search_providers.searxng.search",
            return_value={"success": False, "error": "not_configured", "results": [], "sources": []},
        ), patch.object(tavily_search, "_fallback_search", return_value=fallback) as fallback_search:
            first = tavily_search._try_fallback("same query", 5, "payment_required")
            self.assertTrue(first["success"])
            self.assertEqual(tavily_search._search_cache[tavily_search._get_cache_key("same query", "fallback", 5)][1], fallback)
        with patch.object(tavily_search, "_get_cached", return_value=fallback), patch.object(
            tavily_search, "_fallback_search", side_effect=AssertionError("cached fallback should be reused")
        ):
            cached = tavily_search._try_fallback("same query", 5, "payment_required")
            self.assertTrue(cached["cached"])


if __name__ == "__main__":
    unittest.main()
