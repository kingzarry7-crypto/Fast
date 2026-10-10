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
    def _search_with_error(self, message):
        with patch.object(tavily_search, "is_tavily_configured", return_value=True), patch.object(
            tavily_search, "get_client", return_value=_FailingClient(message)
        ), patch.object(tavily_search, "_get_cached", return_value=None):
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


if __name__ == "__main__":
    unittest.main()
