"""Isolated web-search provider adapters.

The public search entry point is tavily_search.search_web. Its ordered fallback
chain is Tavily -> configured SearXNG instances -> DuckDuckGo HTML.
"""
