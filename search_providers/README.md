# King Zarry AI search providers

All adapters normalize results to `{title, url, content, score, published_date}` and are isolated so a provider failure does not stop the next one.

## Actual runtime fallback order

1. **Tavily** — primary provider; `TAVILY_API_KEY`.
2. **Brave Search** — optional; `BRAVE_SEARCH_API_KEY`.
3. **Serper / Google results** — optional; `SERPER_API_KEY`.
4. **SearXNG** — optional self-hosted/public instance list; `SEARXNG_URLS` (comma-separated HTTPS base URLs).
5. **DuckDuckGo HTML** — keyless best-effort final fallback; it is unofficial and may be throttled or blocked.

The router skips providers that are not configured, return no usable results, or fail due to quota/rate limits, timeouts, or provider errors. Tavily quota/rate failures trigger the same fallback chain. Results are best-effort; the caller should cite only URLs actually returned by a provider.

## Railway environment

Already used by the application: `TAVILY_API_KEY`, `TAVILY_MAX_RESULTS`, `TAVILY_TIMEOUT`, `SEARXNG_URLS`, `WEB_RESEARCH_TIMEOUT`.

Optional additions (only if you have these provider accounts/keys):
- `BRAVE_SEARCH_API_KEY`: a Brave Search API key. If absent, Brave is skipped automatically.
- `SERPER_API_KEY`: a Serper API key. If absent, Serper is skipped automatically.

No key is required for DuckDuckGo. It is a best-effort fallback, not a guaranteed service. Do not paste secrets into source files or commit them. Empty/missing optional keys safely disable their provider.
