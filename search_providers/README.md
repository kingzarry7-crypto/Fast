# King Zarry AI search providers

All adapters normalize results to `{title, url, content, score, published_date}` and are isolated so a failing provider does not stop the next one.

## Runtime order

1. Tavily — primary provider, uses `TAVILY_API_KEY`.
2. Brave Search — optional paid/free-tier API, uses `BRAVE_SEARCH_API_KEY`.
3. Serper (Google results) — optional API, uses `SERPER_API_KEY`.
4. SearXNG — optional self-hosted/public instance list, uses `SEARXNG_URLS` (comma-separated HTTPS base URLs).
5. DuckDuckGo HTML — keyless best-effort final fallback; it is unofficial and can be throttled or blocked.

Tavily quota/rate failures trigger the same fallback chain. Search results are best-effort, not guaranteed to be complete or current; the caller should cite actual returned URLs only.

## Railway environment

Already-used variables: `TAVILY_API_KEY`, `TAVILY_MAX_RESULTS`, `TAVILY_TIMEOUT`, `SEARXNG_URLS`, `WEB_RESEARCH_TIMEOUT`.

Optional additions:
- `BRAVE_SEARCH_API_KEY`: add a key from Brave Search API if you choose to enable that provider.
- `SERPER_API_KEY`: add a key from Serper if you choose to enable that provider.

No API key is required for DuckDuckGo, but it is a best-effort HTML fallback and may fail under bot protection. Do not paste secrets into source files or commit them. A blank or missing optional key safely disables its provider.
