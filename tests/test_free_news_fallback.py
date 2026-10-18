"""Regression tests for the free, no-key news fallback."""
import unittest
from unittest.mock import Mock, patch

import news


class FreeNewsFallbackTests(unittest.TestCase):
    def setUp(self):
        self.cooldown_patch = patch.object(news, "_NEWS_PROVIDER_COOLDOWNS", {})
        self.cooldown_patch.start()
        self.addCleanup(self.cooldown_patch.stop)

    def test_gdelt_provider_needs_no_api_key(self):
        self.assertTrue(news.GDELTNewsProvider().is_configured())

    @patch("news.requests.get")
    def test_gdelt_provider_normalizes_real_article_results(self, request):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "articles": [
                {
                    "title": "Bitcoin market update",
                    "url": "https://example.com/bitcoin",
                    "domain": "example.com",
                    "seendate": "20261018T210000Z",
                },
                {"title": "missing url"},
            ]
        }
        request.return_value = response
        items = news.GDELTNewsProvider().fetch_headlines("Bitcoin BTC", 5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Bitcoin market update")
        self.assertEqual(items[0]["provider"], "gdelt")
        self.assertEqual(items[0]["url"], "https://example.com/bitcoin")
        self.assertEqual(request.call_args.args[0], "https://api.gdeltproject.org/api/v2/doc/doc")
        self.assertEqual(request.call_args.kwargs["params"]["format"], "json")

    @patch("news.requests.get")
    def test_gdelt_429_sets_cooldown_and_skips_repeat_request(self, request):
        response = Mock()
        response.status_code = 429
        request.return_value = response
        provider = news.GDELTNewsProvider()
        self.assertEqual(provider.fetch_headlines("world news", 5), [])
        self.assertIn("gdelt", news._NEWS_PROVIDER_COOLDOWNS)
        self.assertEqual(provider.fetch_headlines("world news", 5), [])
        self.assertEqual(request.call_count, 1)

    @patch("news.requests.get")
    def test_gdelt_429_cooldown_applies_across_different_asset_queries(self, request):
        response = Mock()
        response.status_code = 429
        request.return_value = response
        provider = news.GDELTNewsProvider()

        self.assertEqual(provider.fetch_headlines("Bitcoin BTC", 5), [])
        self.assertEqual(provider.fetch_headlines("Gold XAU/USD", 5), [])
        self.assertEqual(provider.fetch_headlines("EUR/USD forex", 5), [])

        # Cooldown is provider-wide, not scoped to the query string.
        self.assertEqual(request.call_count, 1)

    def test_auto_news_order_starts_with_no_key_provider(self):
        with patch.object(news, "NEWS_PROVIDER", "AUTO"):
            engine = news.NewsEngineSingleton()
            ordered = engine._get_news_provider_order()
        self.assertTrue(ordered)
        self.assertEqual(ordered[0].name, "gdelt")

    def test_selected_provider_still_has_free_fallback(self):
        with (
            patch.object(news, "NEWS_PROVIDER", "CURRENTS"),
            patch.object(news, "CURRENTS_API_KEY", "test-key"),
        ):
            engine = news.NewsEngineSingleton()
            ordered = engine._get_news_provider_order()
        self.assertEqual(ordered[0].name, "currents")
        self.assertIn("gdelt", [provider.name for provider in ordered])


if __name__ == "__main__":
    unittest.main()
