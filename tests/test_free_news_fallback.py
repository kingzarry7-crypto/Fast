"""Regression tests for the free, no-key news fallback."""
from unittest.mock import Mock

import news


def test_gdelt_provider_needs_no_api_key():
    provider = news.GDELTNewsProvider()
    assert provider.is_configured() is True


def test_gdelt_provider_normalizes_real_article_results(monkeypatch):
    provider = news.GDELTNewsProvider()
    monkeypatch.setattr(news, "_NEWS_PROVIDER_COOLDOWNS", {})

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
    request = Mock(return_value=response)
    monkeypatch.setattr(news.requests, "get", request)

    items = provider.fetch_headlines("Bitcoin BTC", 5)

    assert len(items) == 1
    assert items[0]["title"] == "Bitcoin market update"
    assert items[0]["provider"] == "gdelt"
    assert items[0]["url"] == "https://example.com/bitcoin"
    assert request.call_args.args[0] == "https://api.gdeltproject.org/api/v2/doc/doc"
    assert request.call_args.kwargs["params"]["format"] == "json"


def test_gdelt_429_sets_cooldown_and_skips_repeat_request(monkeypatch):
    provider = news.GDELTNewsProvider()
    cooldowns = {}
    monkeypatch.setattr(news, "_NEWS_PROVIDER_COOLDOWNS", cooldowns)

    response = Mock()
    response.status_code = 429
    request = Mock(return_value=response)
    monkeypatch.setattr(news.requests, "get", request)

    assert provider.fetch_headlines("world news", 5) == []
    assert "gdelt" in cooldowns
    assert provider.fetch_headlines("world news", 5) == []
    assert request.call_count == 1


def test_auto_news_order_starts_with_no_key_provider(monkeypatch):
    monkeypatch.setattr(news, "NEWS_PROVIDER", "AUTO")
    engine = news.NewsEngineSingleton()
    ordered = engine._get_news_provider_order()

    assert ordered
    assert ordered[0].name == "gdelt"
