
"""
=========================================================
KING ZARRY AI 👑
news_engine.py - COMPATIBILITY SHIM
=========================================================
Lightweight compatibility layer - exposes public API from news.py
Do NOT duplicate implementation here
"""
from news import (
    # Singleton
    news_engine_instance,
    news_engine,
    # Status
    provider_status,
    news_health,
    # Time handling
    parse_event_time,
    parse_event_time_with_certainty,
    _has_explicit_timezone,
    # Calendar providers
    get_eodhd_events,
    get_finnhub_events,
    get_tradingeconomics_events,
    get_twelvedata_events,
    get_forexfactory_events,
    get_available_provider,
    get_available_calendar_provider,
    get_economic_events,
    # Filtering
    filter_events,
    # News
    get_eodhd_news,
    get_global_news,
    get_gold_news,
    # Gold intelligence
    calculate_gold_relevance,
    estimate_gold_impact,
    normalize_event,
    # Asset news
    get_news_for_asset,
    get_upcoming_events,
    check_imminent_event,
    is_event_relevant_for_asset,
    calculate_risk_for_events,
    classify_headline_impact,
    # Formatters
    format_event,
    format_news_article,
    # Helpers
    upcoming_news,
    upcoming_gold_news,
    # Date helpers
    utc_today,
    date_string,
)

# Backward compatibility for old imports
__all__ = [
    "news_engine_instance",
    "news_engine",
    "provider_status",
    "news_health",
    "parse_event_time",
    "get_eodhd_events",
    "get_finnhub_events",
    "get_tradingeconomics_events",
    "get_twelvedata_events",
    "get_forexfactory_events",
    "get_available_provider",
    "get_available_calendar_provider",
    "get_economic_events",
    "filter_events",
    "get_eodhd_news",
    "get_global_news",
    "get_gold_news",
    "calculate_gold_relevance",
    "estimate_gold_impact",
    "normalize_event",
    "get_news_for_asset",
    "get_upcoming_events",
    "check_imminent_event",
    "is_event_relevant_for_asset",
    "calculate_risk_for_events",
    "classify_headline_impact",
    "format_event",
    "format_news_article",
    "upcoming_news",
    "upcoming_gold_news",
    "utc_today",
    "date_string",
]
