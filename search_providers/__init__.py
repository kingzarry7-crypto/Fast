"""Isolated web-search provider adapters.

The public entry point is ``tavily_search.search_web``. Its ordered runtime
fallback chain is Tavily -> Brave Search (when BRAVE_SEARCH_API_KEY is set)
-> Serper/Google (when SERPER_API_KEY is set) -> configured SearXNG instances
-> keyless DuckDuckGo HTML. A provider that is unconfigured, rate-limited,
blocked, times out, or returns no usable results is skipped in favor of the
next provider. External providers remain best-effort and may be throttled.
"""
