"""Regression tests for web research provider fallback."""
import sys
import types
import unittest
from unittest.mock import patch

import web_research_engine


class WebResearchFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tavily = types.ModuleType("tavily_search")
        self.tavily.search_web = lambda *args, **kwargs: {
            "success": True,
            "answer": "A concise answer",
            "results": [
                {
                    "title": "Trusted source",
                    "url": "https://example.com/article",
                    "content": "Relevant source text",
                },
                {
                    "title": "Unsafe URL",
                    "url": "javascript:alert(1)",
                    "content": "Must be rejected",
                },
            ],
        }
        self.modules = patch.dict(sys.modules, {"tavily_search": self.tavily})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_uses_tavily_when_searxng_is_not_configured(self):
        with patch.object(web_research_engine, "_env_urls", return_value=[]):
            result = web_research_engine.research("web developer opportunities")

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "tavily")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["url"], "https://example.com/article")
        self.assertEqual(result["sources"][0]["url"], "https://example.com/article")
        self.assertEqual(result["fallback_reason"], "SearXNG is not configured")

    def test_uses_tavily_when_configured_searxng_returns_no_results(self):
        with patch.object(web_research_engine, "_env_urls", return_value=["https://search.example"]), patch.object(
            web_research_engine, "_query_variants", return_value=["web developer opportunities"]
        ), patch.object(web_research_engine, "_search_instance", return_value=[]):
            result = web_research_engine.research("web developer opportunities")

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "tavily")
        self.assertTrue(result["results"])

    def test_returns_actionable_error_when_both_providers_fail(self):
        self.tavily.search_web = lambda *args, **kwargs: {
            "success": False, "error": "rate_limit", "results": [], "answer": ""
        }
        with patch.object(web_research_engine, "_env_urls", return_value=[]):
            result = web_research_engine.research("web developer opportunities")

        self.assertFalse(result["success"])
        self.assertIn("SearXNG is not configured", result["error"])
        self.assertIn("rate_limit", result["error"])
        self.assertTrue(result["needs_configuration"])


if __name__ == "__main__":
    unittest.main()
