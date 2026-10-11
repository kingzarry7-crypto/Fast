"""Unit tests for isolated web-search provider adapters and failover."""
import os
import unittest
from unittest.mock import patch

from search_providers import brave, serper, searxng


class OptionalProviderTests(unittest.TestCase):
    def test_brave_is_disabled_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(brave.search("test")["error"], "not_configured")

    def test_serper_is_disabled_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(serper.search("test")["error"], "not_configured")

    def test_searxng_skips_unconfigured_and_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(brave, "search", return_value={"success": False, "results": []}), patch.object(
                serper, "search", return_value={"success": False, "results": []}
            ):
                result = searxng.search("test")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "not_configured")

    def test_brave_success_short_circuits_later_providers(self):
        expected = {"success": True, "results": [{"title": "ok", "url": "https://example.com"}], "provider": "brave"}
        with patch.object(brave, "search", return_value=expected), patch.object(
            serper, "search", side_effect=AssertionError("Serper should not run after success")
        ):
            result = searxng.search("test")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
