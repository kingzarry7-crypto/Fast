
"""
=========================================================
KING ZARRY AI 👑
GLOBAL NEWS + ECONOMIC CALENDAR ENGINE - FINAL PRODUCTION
=========================================================
Separated:
  NEWS_PROVIDER = headline providers
  CALENDAR_PROVIDER = economic calendar providers

Headline order AUTO: Currents -> NewsData -> NewsAPI -> EODHD (fallback)
Calendar order AUTO: EODHD -> TradingEconomics -> Finnhub -> TwelveData -> ForexFactory

Env:
  NEWS_PROVIDER=AUTO
  CALENDAR_PROVIDER=AUTO
  CURRENTS_API_KEY=
  NEWSDATA_API_KEY= / NEWSDATA_IO_API_KEY=
  NEWS_API_KEY=
  EODHD_API_KEY= / EODHD_KEY=
  TRADING_ECONOMICS_API_KEY= / TRADING_ECONOMICS_KEY=
  FINNHUB_API_KEY= / FINNHUB_KEY=
  TWELVE_DATA_API_KEY=
  MQL5_API_KEY= / MQL5_KEY= (reserved only)

Never fabricates news/events/prices/timestamps
"""
import os
import re
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
import requests

logger = logging.getLogger("king_zarry_news")

def clean_env(value: Optional[str], default: str = "") -> str:
    if not value:
        return default
    value = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(value)).strip()
    return value if value else default

NEWS_PROVIDER = clean_env(os.getenv("NEWS_PROVIDER"), "AUTO").upper()
CALENDAR_PROVIDER = clean_env(os.getenv("CALENDAR_PROVIDER"), "AUTO").upper()

EODHD_API_KEY = clean_env(os.getenv("EODHD_API_KEY") or os.getenv("EODHD_KEY"))
TRADING_ECONOMICS_API_KEY = clean_env(os.getenv("TRADING_ECONOMICS_API_KEY") or os.getenv("TRADING_ECONOMICS_KEY"))
FINNHUB_API_KEY = clean_env(os.getenv("FINNHUB_API_KEY") or os.getenv("FINNHUB_KEY"))
MQL5_API_KEY = clean_env(os.getenv("MQL5_API_KEY") or os.getenv("MQL5_KEY"))
CURRENTS_API_KEY = clean_env(os.getenv("CURRENTS_API_KEY"))
NEWSDATA_API_KEY = clean_env(os.getenv("NEWSDATA_API_KEY") or os.getenv("NEWSDATA_IO_API_KEY"))
NEWS_API_KEY = clean_env(os.getenv("NEWS_API_KEY"))
TWELVE_DATA_API_KEY = clean_env(os.getenv("TWELVE_DATA_API_KEY"))
TWELVE_DATA_URL = "https://api.twelvedata.com"

def provider_status() -> Dict[str, Any]:
    """
    Fixed consistency:
    - calendar_configured = at least one keyed provider configured OR public ForexFactory fallback exists
    - calendar_available = actual usable calendar data/provider availability, NOT simply because public URL exists
    ForexFactory True alone does NOT make calendar_available=True when no provider has produced usable data
    """
    headline_configured = {
        "currents": bool(CURRENTS_API_KEY),
        "newsdata": bool(NEWSDATA_API_KEY),
        "newsapi": bool(NEWS_API_KEY),
        "eodhd": bool(EODHD_API_KEY),
    }
    # Keyed calendar providers only
    calendar_keyed_configured = {
        "eodhd": bool(EODHD_API_KEY),
        "tradingeconomics": bool(TRADING_ECONOMICS_API_KEY),
        "finnhub": bool(FINNHUB_API_KEY),
        "twelvedata": bool(TWELVE_DATA_API_KEY),
    }
    # Full config including public fallback
    calendar_configured = {
        "eodhd": bool(EODHD_API_KEY),
        "tradingeconomics": bool(TRADING_ECONOMICS_API_KEY),
        "finnhub": bool(FINNHUB_API_KEY),
        "twelvedata": bool(TWELVE_DATA_API_KEY),
        "forexfactory": True,  # public no-key fallback - exists, but not proof of working
    }

    headlines_available = any(headline_configured.values())

    # calendar_configured = keyed OR fallback exists
    has_keyed_calendar = any(calendar_keyed_configured.values())
    has_fallback = True  # ForexFactory public endpoint exists
    calendar_configured_flag = has_keyed_calendar or has_fallback

    # calendar_available = actual usable availability, NOT just because URL exists
    # True only if:
    #   - at least one keyed provider configured, OR
    #   - engine cache has recent successful calendar data (proving fallback actually produced usable data)
    calendar_available = has_keyed_calendar  # base: keyed provider configured
    # If no keyed provider, check cache for evidence that fallback produced usable data
    if not calendar_available:
        try:
            engine = NewsEngineSingleton._instance
            if engine:
                for key in engine.cache:
                    if key.startswith("events_") and engine._is_cache_valid(key):
                        cached_events = engine.cache.get(key, [])
                        if cached_events:
                            calendar_available = True
                            break
        except Exception:
            pass
        # If still no cache and no keyed provider, calendar_available stays False
        # even though forexfactory True exists - this fixes false positive

    return {
        "selected_news_provider": NEWS_PROVIDER,
        "selected_calendar_provider": CALENDAR_PROVIDER,
        "eodhd": bool(EODHD_API_KEY),
        "tradingeconomics": bool(TRADING_ECONOMICS_API_KEY),
        "finnhub": bool(FINNHUB_API_KEY),
        "mql5": bool(MQL5_API_KEY),
        "currents": bool(CURRENTS_API_KEY),
        "newsdata": bool(NEWSDATA_API_KEY),
        "newsapi": bool(NEWS_API_KEY),
        "twelvedata": bool(TWELVE_DATA_API_KEY),
        "forexfactory": True,
        "headlines_configured": headline_configured,
        "calendar_configured": calendar_configured,
        "calendar_keyed_configured": calendar_keyed_configured,
        "calendar_configured_flag": calendar_configured_flag,
        "headlines_available": headlines_available,
        "calendar_available": calendar_available,
        "news_available": headlines_available,
    }

def utc_today():
    return datetime.now(timezone.utc).date()

def date_string(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)

def _has_explicit_timezone(time_str: str) -> bool:
    """Check if string contains explicit timezone info (Z, +hh:mm, GMT, UTC, offset)"""
    s = str(time_str).upper()
    if "Z" in s and "T" in s:
        return True
    if re.search(r"[+-]\d{2}:?\d{2}$", s.strip()):
        return True
    if re.search(r"\b(UTC|GMT|EST|PST|EDT|PDT)\b", s):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]", s):
        return True
    return False

def parse_event_time(time_str: str) -> Optional[datetime]:
    """
    Safe timezone handling:
    - Timezone-aware -> convert to UTC (certain)
    - Z suffix -> UTC (certain)
    - Explicit offset (+00:00, -05:00) -> convert to UTC (certain)
    - Provider-known timezone: Most calendar APIs (EODHD, Finnhub, TwelveData, ForexFactory) provide UTC, documented assumption
    - Genuinely naive unknown -> ASSUME UTC but log as uncertain (documented). Caller must decide if safe for imminent alerts.

    For imminent checks, use parse_event_time_with_certainty() to avoid false alerts from uncertain timestamps.
    """
    if not time_str:
        return None
    s = str(time_str).strip()
    if not s or s.upper() in ["TBD", "N/A", "UNKNOWN", ""]:
        return None
    iso_try = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_try)
        if dt.tzinfo is None:
            # Naive - documented assumption: assume UTC but uncertain
            logger.debug(f"parse_event_time: naive timestamp assumed UTC (uncertain): {s}")
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    formats = [
        ("%Y-%m-%dT%H:%M:%S%z", True),
        ("%Y-%m-%dT%H:%M:%S.%f%z", True),
        ("%Y-%m-%dT%H:%M:%SZ", True),
        ("%Y-%m-%d %H:%M:%S%z", True),
        ("%Y-%m-%d %H:%M:%S", False),
        ("%Y-%m-%d %H:%M", False),
        ("%Y-%m-%d", False),
        ("%m/%d/%Y %H:%M:%S", False),
        ("%m/%d/%Y %H:%M", False),
        ("%d/%m/%Y %H:%M", False),
    ]
    for fmt, has_tz in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                if not has_tz:
                    logger.debug(f"parse_event_time: naive format {fmt} assumed UTC (uncertain): {s}")
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    try:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
        if m:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)
            tm = re.search(r"(\d{1,2}:\d{2})", s)
            if tm:
                try:
                    h, mi = map(int, tm.group(1).split(":"))
                    dt = dt.replace(hour=h, minute=mi)
                except Exception:
                    pass
            logger.debug(f"parse_event_time: regex fallback assumed UTC (uncertain): {s} -> {dt}")
            return dt
    except Exception:
        pass
    logger.debug(f"parse_event_time: unable to parse, skipping: {s}")
    return None

def parse_event_time_with_certainty(time_str: str) -> Tuple[Optional[datetime], bool]:
    """
    Returns (datetime_utc, is_certain)
    is_certain = True if original string had explicit timezone
    is_certain = False if naive (assumed UTC, uncertain)
    Used to avoid false imminent alerts from unknown timezone.
    """
    if not time_str:
        return None, False
    s = str(time_str).strip()
    if not s or s.upper() in ["TBD", "N/A", "UNKNOWN", ""]:
        return None, False
    certain = _has_explicit_timezone(s)
    dt = parse_event_time(s)
    if dt is None:
        return None, False
    # If dt came from iso with offset, mark certain even if helper missed
    if dt.tzinfo is not None and certain is False:
        # Check if original had Z or offset
        if "Z" in str(time_str).upper() or re.search(r"[+-]\d{2}:?\d{2}", str(time_str)):
            certain = True
    # For naive, certain remains False
    if not certain:
        # Still, if string matches ISO with T and we converted, keep as uncertain for safety
        pass
    return dt, certain

GOLD_KEYWORDS = [
    "gold", "interest rate", "interest rates", "federal reserve", "fed", "fomc",
    "central bank", "inflation", "consumer price index", "cpi", "core cpi",
    "producer price index", "ppi", "core ppi", "nonfarm payroll", "non-farm payroll",
    "payroll", "unemployment", "employment", "jobs", "retail sales", "gdp",
    "gross domestic product", "pce", "personal consumption", "manufacturing pmi",
    "services pmi", "pmi", "powell", "treasury", "bond yields", "government bond",
    "geopolitical", "war", "sanctions", "trade war", "tariff", "tariffs",
]

def calculate_gold_relevance(event_name: str, country: str = "", currency: str = "") -> str:
    text = f"{event_name} {country} {currency}".lower()
    score = 0
    for keyword in GOLD_KEYWORDS:
        if keyword in text:
            score += 1
    if currency.upper() == "USD":
        score += 3
    if country.upper() in ("US", "USA", "UNITED STATES"):
        score += 2
    if score >= 6:
        return "VERY HIGH"
    if score >= 4:
        return "HIGH"
    if score >= 2:
        return "MEDIUM"
    return "LOW"

def estimate_gold_impact(event_name: str, currency: str = "", impact: str = "", actual: Any = None, forecast: Any = None, previous: Any = None) -> str:
    text = str(event_name).lower()
    currency = str(currency).upper()
    high_rate_events = ["interest rate", "federal reserve", "fomc", "inflation", "cpi", "core cpi", "ppi", "core ppi", "payroll", "nonfarm", "non-farm", "employment", "retail sales", "gdp", "pce"]
    relevant = any(keyword in text for keyword in high_rate_events)
    if not relevant and currency != "USD":
        return "LOW / INDIRECT"
    if actual is None or forecast is None:
        if currency == "USD":
            return "HIGH IMPACT - WATCH USD/YIELDS"
        return "POTENTIAL IMPACT - WATCH MARKET REACTION"
    try:
        actual_number = float(actual)
        forecast_number = float(forecast)
    except (TypeError, ValueError):
        return "WATCH MARKET REACTION"
    difference = actual_number - forecast_number
    if currency == "USD":
        if difference > 0:
            return "POTENTIALLY BEARISH GOLD"
        if difference < 0:
            return "POTENTIALLY BULLISH GOLD"
    return "WATCH MARKET REACTION"

def normalize_event(event: Dict[str, Any], provider: str) -> Dict[str, Any]:
    name = event.get("event") or event.get("name") or event.get("title") or "Economic Event"
    country = event.get("country") or event.get("country_code") or ""
    currency = event.get("currency") or event.get("unit") or ""
    event_time = event.get("date")
    if event_time is None:
        event_time = event.get("time")
    if event_time is None:
        event_time = event.get("datetime")
    if event_time is None:
        event_time = ""
    impact = event.get("impact")
    if impact is None:
        impact = event.get("importance")
    if impact is None:
        impact = event.get("importance_level")
    if impact is None:
        impact = "unknown"
    actual = event.get("actual")
    if actual is None:
        actual = event.get("value")
    forecast = event.get("forecast")
    if forecast is None:
        forecast = event.get("estimate")
    if forecast is None:
        forecast = event.get("consensus")
    previous = event.get("previous")
    if previous is None:
        previous = event.get("prev")
    gold_relevance = calculate_gold_relevance(name, country, currency)
    gold_impact = estimate_gold_impact(name, currency, impact, actual, forecast, previous)
    return {
        "provider": provider,
        "event": name,
        "country": country,
        "currency": currency,
        "time": event_time,
        "impact": str(impact).upper(),
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "gold_relevance": gold_relevance,
        "gold_impact": gold_impact,
    }

def get_eodhd_events(start_date=None, end_date=None) -> List[Dict[str, Any]]:
    if not EODHD_API_KEY:
        raise RuntimeError("EODHD_API_KEY is missing.")
    if start_date is None:
        start_date = utc_today()
    if end_date is None:
        end_date = start_date + timedelta(days=7)
    response = requests.get("https://eodhd.com/api/economic-events", params={"api_token": EODHD_API_KEY, "from": date_string(start_date), "to": date_string(end_date), "fmt": "json"}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"EODHD HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    if isinstance(data, dict):
        if data.get("error"):
            raise RuntimeError(str(data["error"]))
        events = data.get("data") or data.get("events") or []
    else:
        events = data
    return [normalize_event(event, "EODHD") for event in events if isinstance(event, dict)]

def get_finnhub_events(start_date=None, end_date=None) -> List[Dict[str, Any]]:
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY is missing.")
    if start_date is None:
        start_date = utc_today()
    if end_date is None:
        end_date = start_date + timedelta(days=7)
    response = requests.get("https://finnhub.io/api/v1/calendar/economic", params={"from": date_string(start_date), "to": date_string(end_date), "token": FINNHUB_API_KEY}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Finnhub HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    events = data.get("economicCalendar", [])
    return [normalize_event(event, "FINNHUB") for event in events if isinstance(event, dict)]

def get_tradingeconomics_events(start_date=None, end_date=None) -> List[Dict[str, Any]]:
    if not TRADING_ECONOMICS_API_KEY:
        raise RuntimeError("TRADING_ECONOMICS_API_KEY is missing.")
    if start_date is None:
        start_date = utc_today()
    if end_date is None:
        end_date = start_date + timedelta(days=7)
    url = "https://api.tradingeconomics.com/calendar/country/All"
    response = requests.get(url, params={"c": TRADING_ECONOMICS_API_KEY, "d1": date_string(start_date), "d2": date_string(end_date), "f": "json"}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Trading Economics HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    if isinstance(data, dict):
        events = data.get("data") or data.get("events") or []
    else:
        events = data
    return [normalize_event(event, "TRADINGECONOMICS") for event in events if isinstance(event, dict)]

def get_twelvedata_events(start_date=None, end_date=None) -> List[Dict[str, Any]]:
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing.")
    response = requests.get(f"{TWELVE_DATA_URL}/calendar", params={"apikey": TWELVE_DATA_API_KEY, "interval": "1day"}, timeout=20)
    if response.status_code != 200:
        raise RuntimeError(f"TwelveData HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    cal_events = data.get("calendar") or data.get("events") or []
    normalized = []
    for ev in cal_events[:30]:
        if not isinstance(ev, dict):
            continue
        event_time = ev.get("datetime")
        if event_time is None:
            event_time = ev.get("date")
        if event_time is None:
            event_time = ""
        normalized.append(normalize_event({"event": ev.get("event") or ev.get("name") or "Economic Event", "country": ev.get("country") or "", "currency": ev.get("currency") or "USD", "date": event_time, "impact": ev.get("importance") or ev.get("impact") or "Medium", "actual": ev.get("actual") if ev.get("actual") is not None else None, "forecast": ev.get("forecast") if ev.get("forecast") is not None else None, "previous": ev.get("previous") if ev.get("previous") is not None else None}, "TWELVEDATA"))
    return normalized

def get_forexfactory_events() -> List[Dict[str, Any]]:
    try:
        resp = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=12)
        if resp.status_code != 200:
            raise RuntimeError(f"ForexFactory HTTP {resp.status_code}")
        ff_data = resp.json()
        events = []
        for item in ff_data:
            try:
                if not isinstance(item, dict):
                    continue
                if item.get("currency") not in ["USD", "EUR", "GBP", "JPY", "XAU"]:
                    continue
                ev = {"title": item.get("title"), "country": item.get("country") or item.get("currency"), "currency": item.get("currency"), "date": item.get("date"), "impact": item.get("impact"), "forecast": item.get("forecast") if item.get("forecast") is not None else None, "previous": item.get("previous") if item.get("previous") is not None else None, "actual": item.get("actual") if item.get("actual") is not None else None}
                events.append(normalize_event(ev, "FOREXFACTORY"))
                if len(events) >= 30:
                    break
            except Exception:
                continue
        return events
    except Exception as e:
        logger.warning(f"ForexFactory failed: {e}")
        return []

def get_available_calendar_provider() -> str:
    effective_provider = CALENDAR_PROVIDER
    if effective_provider == "AUTO" and NEWS_PROVIDER in ["EODHD", "TRADINGECONOMICS", "FINNHUB", "TWELVEDATA", "FOREXFACTORY"]:
        effective_provider = NEWS_PROVIDER
    if effective_provider != "AUTO":
        if effective_provider == "EODHD" and EODHD_API_KEY:
            return "EODHD"
        if effective_provider == "TRADINGECONOMICS" and TRADING_ECONOMICS_API_KEY:
            return "TRADINGECONOMICS"
        if effective_provider == "FINNHUB" and FINNHUB_API_KEY:
            return "FINNHUB"
        if effective_provider == "TWELVEDATA" and TWELVE_DATA_API_KEY:
            return "TWELVEDATA"
        if effective_provider == "FOREXFACTORY":
            return "FOREXFACTORY"
        if effective_provider not in ["FOREXFACTORY"]:
            raise RuntimeError(f"CALENDAR_PROVIDER={effective_provider}, but its API key is missing.")
    if EODHD_API_KEY:
        return "EODHD"
    if TRADING_ECONOMICS_API_KEY:
        return "TRADINGECONOMICS"
    if FINNHUB_API_KEY:
        return "FINNHUB"
    if TWELVE_DATA_API_KEY:
        return "TWELVEDATA"
    return "FOREXFACTORY"

def get_available_provider() -> str:
    """
    Backward compatibility wrapper.
    Legacy code used NEWS_PROVIDER for both news and calendar.
    New architecture separates:
      get_available_calendar_provider() -> for economic calendar
      NEWS_PROVIDER ordering in NewsEngineSingleton -> for headlines

    This function returns calendar provider for backward compat.
    It explicitly documents that it resolves CALENDAR provider, not headline provider.
    New code should use get_available_calendar_provider() directly.

    Returns: calendar provider name (EODHD, TRADINGECONOMICS, FINNHUB, TWELVEDATA, FOREXFACTORY)
    """
    try:
        return get_available_calendar_provider()
    except Exception:
        # Fallback legacy logic for callers expecting old behavior
        if NEWS_PROVIDER != "AUTO":
            if NEWS_PROVIDER == "EODHD" and EODHD_API_KEY:
                return "EODHD"
            if NEWS_PROVIDER == "TRADINGECONOMICS" and TRADING_ECONOMICS_API_KEY:
                return "TRADINGECONOMICS"
            if NEWS_PROVIDER == "FINNHUB" and FINNHUB_API_KEY:
                return "FINNHUB"
        if EODHD_API_KEY:
            return "EODHD"
        if TRADING_ECONOMICS_API_KEY:
            return "TRADINGECONOMICS"
        if FINNHUB_API_KEY:
            return "FINNHUB"
        if TWELVE_DATA_API_KEY:
            return "TWELVEDATA"
        return "FOREXFACTORY"

def get_economic_events(days: int = 7, provider: Optional[str] = None) -> List[Dict[str, Any]]:
    provider = provider or get_available_calendar_provider()
    start_date = utc_today()
    end_date = start_date + timedelta(days=max(1, days))
    errors: List[str] = []
    providers = [provider]
    if CALENDAR_PROVIDER == "AUTO" or provider == get_available_calendar_provider():
        providers = []
        if EODHD_API_KEY:
            providers.append("EODHD")
        if TRADING_ECONOMICS_API_KEY:
            providers.append("TRADINGECONOMICS")
        if FINNHUB_API_KEY:
            providers.append("FINNHUB")
        if TWELVE_DATA_API_KEY:
            providers.append("TWELVEDATA")
        providers.append("FOREXFACTORY")
        if provider and provider in providers:
            providers = [provider] + [p for p in providers if p != provider]
        seen: Set[str] = set()
        uniq: List[str] = []
        for p in providers:
            if p not in seen:
                uniq.append(p)
                seen.add(p)
        providers = uniq
    for current_provider in providers:
        try:
            if current_provider == "EODHD":
                return get_eodhd_events(start_date, end_date)
            if current_provider == "FINNHUB":
                return get_finnhub_events(start_date, end_date)
            if current_provider == "TRADINGECONOMICS":
                return get_tradingeconomics_events(start_date, end_date)
            if current_provider == "TWELVEDATA":
                return get_twelvedata_events(start_date, end_date)
            if current_provider == "FOREXFACTORY":
                evs = get_forexfactory_events()
                if evs:
                    return evs
                else:
                    raise RuntimeError("ForexFactory returned empty")
        except Exception as error:
            errors.append(f"{current_provider}: {error}")
            logger.warning(f"Calendar provider {current_provider} failed: {error}")
            continue
    raise RuntimeError("All calendar providers failed.\n" + "\n".join(errors))

class BaseNewsProvider:
    name: str = "base"
    def is_configured(self) -> bool:
        return False
    def fetch_headlines(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return []

class CurrentsProvider(BaseNewsProvider):
    name = "currents"
    def is_configured(self) -> bool:
        return bool(CURRENTS_API_KEY)
    def fetch_headlines(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            url = "https://api.currentsapi.services/v1/latest-news"
            params = {"keywords": query, "language": "en", "apiKey": CURRENTS_API_KEY}
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Currents HTTP {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()
            articles = data.get("news", [])[:limit]
            return [{"title": a.get("title"), "source": a.get("author") or "Currents", "published": a.get("published"), "url": a.get("url"), "provider": "currents", "sentiment": None} for a in articles if isinstance(a, dict)]
        except Exception as e:
            logger.warning(f"Currents failed: {e}")
            return []

class NewsDataProvider(BaseNewsProvider):
    name = "newsdata"
    def is_configured(self) -> bool:
        return bool(NEWSDATA_API_KEY)
    def fetch_headlines(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            url = "https://newsdata.io/api/1/latest"
            params = {"apikey": NEWSDATA_API_KEY, "q": query, "language": "en", "size": limit}
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"NewsData HTTP {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()
            articles = data.get("results", [])[:limit]
            return [{"title": a.get("title"), "source": a.get("source_id") or "NewsData", "published": a.get("pubDate"), "url": a.get("link"), "provider": "newsdata"} for a in articles if isinstance(a, dict)]
        except Exception as e:
            logger.warning(f"NewsData failed: {e}")
            return []

class NewsAPIProvider(BaseNewsProvider):
    name = "newsapi"
    def is_configured(self) -> bool:
        return bool(NEWS_API_KEY)
    def fetch_headlines(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {"q": query, "sortBy": "publishedAt", "pageSize": limit, "language": "en", "apiKey": NEWS_API_KEY}
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"NewsAPI HTTP {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()
            articles = data.get("articles", [])[:limit]
            return [{"title": a.get("title"), "source": (a.get("source") or {}).get("name") or "NewsAPI", "published": a.get("publishedAt"), "url": a.get("url"), "provider": "newsapi"} for a in articles if isinstance(a, dict)]
        except Exception as e:
            logger.warning(f"NewsAPI failed: {e}")
            return []

class EODHDNewsProvider(BaseNewsProvider):
    name = "eodhd"
    def is_configured(self) -> bool:
        return bool(EODHD_API_KEY)
    def fetch_headlines(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            resp = requests.get("https://eodhd.com/api/news", params={"api_token": EODHD_API_KEY, "s": query.split()[0][:10], "limit": min(limit, 20), "fmt": "json"}, timeout=20)
            if resp.status_code != 200:
                logger.warning(f"EODHD news HTTP {resp.status_code}")
                return []
            data = resp.json()
            if isinstance(data, dict):
                if data.get("error"):
                    logger.warning(f"EODHD news error: {data.get('error')}")
                    return []
                data = data.get("data") or data.get("news") or []
            return [{"title": a.get("title"), "source": "EODHD", "published": a.get("date"), "url": a.get("link"), "provider": "eodhd", "content": (a.get("content") or "")[:500]} for a in data[:limit] if isinstance(a, dict)]
        except Exception as e:
            logger.warning(f"EODHD news failed: {e}")
            return []

def filter_events(events: List[Dict[str, Any]], country: Optional[str] = None, currency: Optional[str] = None, impact: Optional[str] = None, gold_only: bool = False) -> List[Dict[str, Any]]:
    results = events
    if country:
        country = country.upper()
        results = [event for event in results if str(event.get("country", "")).upper() == country]
    if currency:
        currency = currency.upper()
        results = [event for event in results if str(event.get("currency", "")).upper() == currency]
    if impact:
        impact = impact.lower()
        results = [event for event in results if impact in str(event.get("impact", "")).lower()]
    if gold_only:
        results = [event for event in results if event.get("gold_relevance") in ("VERY HIGH", "HIGH", "MEDIUM")]
    return results

def get_eodhd_news(limit: int = 20) -> List[Dict[str, Any]]:
    if not EODHD_API_KEY:
        raise RuntimeError("EODHD_API_KEY is missing.")
    response = requests.get("https://eodhd.com/api/news", params={"api_token": EODHD_API_KEY, "limit": max(1, min(limit, 100)), "fmt": "json"}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"EODHD news HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    if isinstance(data, dict):
        if data.get("error"):
            raise RuntimeError(str(data["error"]))
        data = data.get("data") or data.get("news") or []
    results = []
    for article in data:
        if not isinstance(article, dict):
            continue
        results.append({"provider": "EODHD", "date": article.get("date"), "title": article.get("title"), "content": article.get("content"), "link": article.get("link"), "symbols": article.get("symbols", []), "tags": article.get("tags", []), "sentiment": article.get("sentiment")})
    return results

def get_global_news(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Respects NEWS_PROVIDER ordering:
    AUTO -> Currents -> NewsData -> NewsAPI -> EODHD
    CURRENTS/NEWSDATA/NEWSAPI/EODHD -> respective first, then fallback
    """
    # Build ordered list based on NEWS_PROVIDER
    def _order():
        if NEWS_PROVIDER == "AUTO":
            order = ["CURRENTS", "NEWSDATA", "NEWSAPI", "EODHD"]
        elif NEWS_PROVIDER == "CURRENTS":
            order = ["CURRENTS", "NEWSDATA", "NEWSAPI", "EODHD"]
        elif NEWS_PROVIDER == "NEWSDATA":
            order = ["NEWSDATA", "CURRENTS", "NEWSAPI", "EODHD"]
        elif NEWS_PROVIDER == "NEWSAPI":
            order = ["NEWSAPI", "CURRENTS", "NEWSDATA", "EODHD"]
        elif NEWS_PROVIDER == "EODHD":
            order = ["EODHD", "CURRENTS", "NEWSDATA", "NEWSAPI"]
        else:
            order = ["CURRENTS", "NEWSDATA", "NEWSAPI", "EODHD"]
        return order

    order = _order()
    errors: List[str] = []
    for prov in order:
        try:
            if prov == "EODHD" and EODHD_API_KEY:
                return get_eodhd_news(limit)
            elif prov == "CURRENTS" and CURRENTS_API_KEY:
                engine = NewsEngineSingleton._instance
                if engine:
                    # Use dedicated provider instance
                    cp = engine.news_providers.get("currents")
                    if cp and cp.is_configured():
                        headlines = cp.fetch_headlines("finance", limit)
                        if headlines:
                            return headlines
            elif prov == "NEWSDATA" and NEWSDATA_API_KEY:
                engine = NewsEngineSingleton._instance
                if engine:
                    nd = engine.news_providers.get("newsdata")
                    if nd and nd.is_configured():
                        headlines = nd.fetch_headlines("finance", limit)
                        if headlines:
                            return headlines
            elif prov == "NEWSAPI" and NEWS_API_KEY:
                engine = NewsEngineSingleton._instance
                if engine:
                    na = engine.news_providers.get("newsapi")
                    if na and na.is_configured():
                        headlines = na.fetch_headlines("finance", limit)
                        if headlines:
                            return headlines
        except Exception as e:
            errors.append(f"{prov}: {e}")
            continue

    # Final fallback using general engine fallback (respects AUTO ordering internally)
    try:
        engine = NewsEngineSingleton._instance
        if engine:
            headlines = engine.fetch_headlines_with_fallback("finance", limit)
            if headlines["available"]:
                return headlines["headlines"]
    except Exception as e:
        errors.append(f"fallback: {e}")

    raise RuntimeError(
        "No news provider available for general news. Add EODHD_API_KEY, CURRENTS_API_KEY, NEWSDATA_API_KEY or NEWS_API_KEY. Errors: "
        + "; ".join(errors)
    )

def get_gold_news(days: int = 7, minimum_relevance: str = "MEDIUM") -> List[Dict[str, Any]]:
    events = get_economic_events(days=days)
    allowed = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY HIGH": 4}
    minimum_score = allowed.get(minimum_relevance.upper(), 2)
    results = [event for event in events if allowed.get(event.get("gold_relevance", "LOW"), 1) >= minimum_score]
    return results

def is_event_relevant_for_asset(event: Dict[str, Any], asset: str) -> Tuple[bool, str]:
    asset = asset.upper()
    currency = str(event.get("currency", "")).upper()
    ev_text = f"{event.get('event','')} {currency} {event.get('country','')}".upper()
    usd_macro_high = ["FOMC", "CPI", "PPI", "NFP", "NONFARM", "UNEMPLOYMENT", "INTEREST RATE", "FEDERAL RESERVE", "POWELL", "GDP", "PCE", "RETAIL SALES", "INFLATION"]
    usd_macro = any(kw in ev_text for kw in usd_macro_high)
    if asset in ["BTC/USD", "BTC"]:
        btc_keywords = ["FEDERAL RESERVE", "FED", "FOMC", "INTEREST RATE", "CPI", "PPI", "NFP", "UNEMPLOYMENT", "GDP", "PCE", "POWELL", "SEC", "BITCOIN ETF", "BTC ETF", "CRYPTO REGULATION", "BITCOIN", "BINANCE", "COINBASE", "BLACKROCK", "STABLECOIN", "EXCHANGE HACK", "BANKRUPTCY", "LIQUIDITY"]
        if any(kw in ev_text for kw in btc_keywords):
            return True, f"BTC relevant: {next((kw for kw in btc_keywords if kw in ev_text), 'macro')}"
        if currency == "USD" and usd_macro:
            return True, "BTC: USD macro high-impact"
        return False, "Not BTC relevant"
    elif asset in ["ETH/USD", "ETH"]:
        eth_keywords = ["FEDERAL RESERVE", "FED", "FOMC", "INTEREST RATE", "CPI", "PPI", "NFP", "POWELL", "SEC", "ETHEREUM ETF", "ETH ETF", "ETHEREUM", "CRYPTO REGULATION", "BLACKROCK", "BINANCE", "COINBASE", "EXCHANGE HACK", "STABLECOIN"]
        if any(kw in ev_text for kw in eth_keywords):
            return True, f"ETH relevant: {next((kw for kw in eth_keywords if kw in ev_text), 'macro')}"
        if currency == "USD" and usd_macro:
            return True, "ETH: USD macro high-impact"
        return False, "Not ETH relevant"
    elif asset in ["SOL/USD", "SOL"]:
        sol_keywords = ["FEDERAL RESERVE", "FED", "FOMC", "INTEREST RATE", "CPI", "PPI", "NFP", "POWELL", "CRYPTO REGULATION", "SOLANA", "SOL", "BINANCE", "COINBASE", "EXCHANGE HACK", "BLACKROCK", "SEC"]
        if any(kw in ev_text for kw in sol_keywords):
            return True, f"SOL relevant: {next((kw for kw in sol_keywords if kw in ev_text), 'macro')}"
        if currency == "USD" and usd_macro:
            return True, "SOL: USD macro high-impact"
        return False, "Not SOL relevant"
    elif asset in ["XAU/USD", "XAU", "GOLD"]:
        xau_keywords = ["GOLD", "XAU", "FEDERAL RESERVE", "FED", "FOMC", "INTEREST RATE", "CPI", "PPI", "NFP", "UNEMPLOYMENT", "GDP", "PCE", "POWELL", "TREASURY", "BOND YIELD", "DOLLAR", "DXY", "GEOPOLITICAL", "WAR", "SANCTIONS", "TRADE WAR", "TARIFF", "INFLATION", "RETAIL SALES"]
        if any(kw in ev_text for kw in xau_keywords):
            return True, f"XAU relevant: {next((kw for kw in xau_keywords if kw in ev_text), 'macro')}"
        return False, "Not XAU relevant"
    else:
        if currency == "USD" and usd_macro:
            return True, "Generic USD macro"
        return False, "Not relevant"

def calculate_risk_for_events(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "LOW"
    high_count = sum(1 for e in events if str(e.get("impact", "")).upper() in ["HIGH", "VERY HIGH", "EXTREME", "3", "RED"])
    very_high_gold = sum(1 for e in events if str(e.get("gold_relevance", "")).upper() in ["VERY HIGH", "HIGH"])
    critical_keywords = ["FOMC", "INTEREST RATE DECISION", "FEDERAL RESERVE"]
    has_critical = any(any(kw in str(e.get("event", "")).upper() for kw in critical_keywords) for e in events)
    major_inflation = any(any(kw in str(e.get("event", "")).upper() for kw in ["CPI", "PCE"]) and str(e.get("impact", "")).upper() in ["HIGH", "VERY HIGH"] for e in events)
    if has_critical:
        return "EXTREME"
    if high_count >= 3 or very_high_gold >= 3:
        return "HIGH"
    if high_count >= 1 or major_inflation:
        if any(str(e.get("impact", "")).upper() in ["HIGH", "VERY HIGH"] for e in events):
            return "HIGH"
        return "MEDIUM"
    if len(events) >= 2:
        return "MEDIUM"
    if len(events) == 1:
        ev = events[0]
        if str(ev.get("impact", "")).upper() in ["LOW"]:
            return "LOW"
        return "MEDIUM"
    return "LOW"

CRYPTO_HEADLINE_KEYWORDS_HIGH = ["bitcoin etf approval", "ethereum etf approval", "sec approves", "sec rejects etf", "exchange hack", "exchange bankruptcy", "binance hack", "coinbase hack", "stablecoin depeg", "usdt depeg", "usdc depeg", "blackrock bitcoin", "federal reserve emergency", "emergency rate cut", "emergency rate hike"]
CRYPTO_HEADLINE_KEYWORDS_MEDIUM = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "etf", "sec", "crypto regulation", "binance", "coinbase", "blackrock", "federal reserve", "powell", "interest rate", "cpi", "ppi", "nfp", "nonfarm payrolls", "fomc", "stablecoin", "crypto", "blockchain"]

def classify_headline_impact(title: str, asset: str = "") -> str:
    if not title:
        return "LOW"
    t = title.lower()
    if any(kw in t for kw in ["emergency rate", "flash crash", "exchange hack", "bankruptcy", "depeg"]):
        return "EXTREME"
    if any(kw in t for kw in CRYPTO_HEADLINE_KEYWORDS_HIGH):
        return "HIGH"
    if "BTC" in asset.upper() and ("bitcoin" in t or "btc" in t):
        if any(kw in t for kw in ["etf", "sec", "regulation", "hack", "blackrock"]):
            return "HIGH"
        return "MEDIUM"
    if "ETH" in asset.upper() and ("ethereum" in t or "eth" in t):
        if any(kw in t for kw in ["etf", "sec", "regulation", "blackrock"]):
            return "HIGH"
        return "MEDIUM"
    if "SOL" in asset.upper() and ("solana" in t or " sol " in f" {t} "):
        if any(kw in t for kw in ["etf", "sec", "hack", "outage"]):
            return "HIGH"
        return "MEDIUM"
    if "XAU" in asset.upper() and ("gold" in t or "xau" in t or "federal reserve" in t or "powell" in t or "cpi" in t):
        if any(kw in t for kw in ["fomc", "rate decision", "cpi", "powell"]):
            return "HIGH"
        return "MEDIUM"
    if any(kw in t for kw in CRYPTO_HEADLINE_KEYWORDS_MEDIUM):
        return "MEDIUM"
    return "LOW"

class NewsEngineSingleton:
    _instance: Optional["NewsEngineSingleton"] = None
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.news_providers: Dict[str, BaseNewsProvider] = {"currents": CurrentsProvider(), "newsdata": NewsDataProvider(), "newsapi": NewsAPIProvider(), "eodhd": EODHDNewsProvider()}
        NewsEngineSingleton._instance = self
        logger.info(f"NewsEngine init: NEWS={NEWS_PROVIDER} CAL={CALENDAR_PROVIDER}")

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self.cache:
            return False
        expiry = self.cache_expiry.get(key)
        return bool(expiry and datetime.now(timezone.utc) < expiry)

    def _get_news_provider_order(self) -> List[BaseNewsProvider]:
        configured = [p for p in self.news_providers.values() if p.is_configured()]
        if not configured:
            return []
        if NEWS_PROVIDER == "AUTO":
            priority = ["currents", "newsdata", "newsapi", "eodhd"]
            ordered: List[BaseNewsProvider] = []
            for name in priority:
                if name in self.news_providers and self.news_providers[name].is_configured():
                    ordered.append(self.news_providers[name])
            for p in configured:
                if p not in ordered:
                    ordered.append(p)
            return ordered
        else:
            key = NEWS_PROVIDER.lower()
            if key in self.news_providers:
                provider = self.news_providers[key]
                if provider.is_configured():
                    return [provider]
                else:
                    logger.warning(f"NEWS_PROVIDER={NEWS_PROVIDER} not configured, fallback AUTO")
                    return configured
            else:
                if NEWS_PROVIDER in ["EODHD", "TRADINGECONOMICS", "FINNHUB", "TWELVEDATA", "FOREXFACTORY"]:
                    logger.info(f"NEWS_PROVIDER={NEWS_PROVIDER} is calendar provider, using AUTO for headlines")
                    return configured
                logger.warning(f"Unknown NEWS_PROVIDER={NEWS_PROVIDER}, using AUTO")
                return configured

    def fetch_headlines_with_fallback(self, query: str, limit: int = 5) -> Dict[str, Any]:
        provider_context = "_".join(sorted([f"{k}:{v.is_configured()}" for k, v in self.news_providers.items()]))
        cache_key = f"headlines_{query}_{limit}_{hashlib.sha256(provider_context.encode()).hexdigest()[:8]}_{NEWS_PROVIDER}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        providers = self._get_news_provider_order()
        if not providers:
            result = {"headlines": [], "provider": "none", "available": False, "error": "No headline news provider configured. Add CURRENTS_API_KEY, NEWSDATA_API_KEY, NEWS_API_KEY or EODHD_API_KEY"}
            self.cache[cache_key] = result
            self.cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(minutes=3)
            return result
        for provider in providers:
            headlines = provider.fetch_headlines(query, limit)
            if headlines:
                result = {"headlines": headlines, "provider": provider.name, "available": True, "error": None}
                self.cache[cache_key] = result
                self.cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(minutes=10)
                logger.info(f"Headlines from {provider.name}: {len(headlines)} for '{query}'")
                return result
            else:
                logger.info(f"Provider {provider.name} 0 headlines for '{query}', trying next")
        result = {"headlines": [], "provider": "all_failed", "available": False, "error": "All headline providers failed or returned empty."}
        self.cache[cache_key] = result
        self.cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(minutes=3)
        return result

    def get_upcoming_events_cached(self, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        cal_context = f"{CALENDAR_PROVIDER}_{get_available_calendar_provider()}"
        cache_key = f"events_{hours_ahead}_{cal_context}"
        if self._is_cache_valid(cache_key):
            cached = self.cache[cache_key]
            return self._filter_events_by_window(cached, hours_ahead)
        try:
            days_needed = max(1, (hours_ahead // 24) + 1)
            events = get_economic_events(days=days_needed)
        except Exception as e:
            logger.warning(f"Calendar fetch failed: {e}")
            events = []
            try:
                events = get_forexfactory_events()
            except Exception:
                events = []
        filtered = self._filter_events_by_window(events, hours_ahead)
        self.cache[cache_key] = filtered
        self.cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(minutes=15)
        return filtered

    def _filter_events_by_window(self, events: List[Dict[str, Any]], hours_ahead: int) -> List[Dict[str, Any]]:
        if not events:
            return []
        now = datetime.now(timezone.utc)
        limit_time = now + timedelta(hours=hours_ahead)
        filtered: List[Dict[str, Any]] = []
        for ev in events:
            time_str = ev.get("time", "")
            dt = parse_event_time(time_str)
            if not dt:
                if hours_ahead >= 24:
                    filtered.append(ev)
                continue
            if now - timedelta(minutes=30) <= dt <= limit_time:
                filtered.append(ev)
            elif dt > now and dt <= limit_time:
                filtered.append(ev)
        return filtered

    def get_news_for_asset(self, asset: str) -> Dict[str, Any]:
        cache_key = f"asset_news_{asset}_{NEWS_PROVIDER}_{CALENDAR_PROVIDER}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
        asset = asset.upper()
        query_map = {"BTC/USD": "Bitcoin BTC ETF SEC", "ETH/USD": "Ethereum ETH ETF SEC", "SOL/USD": "Solana SOL ETF", "XAU/USD": "Gold XAU Federal Reserve CPI", "BTC": "Bitcoin BTC", "ETH": "Ethereum ETH", "SOL": "Solana SOL", "XAU": "Gold XAU", "GOLD": "Gold XAU"}
        query = query_map.get(asset, asset.replace("/USD", ""))
        upcoming = self.get_upcoming_events_cached(hours_ahead=24)
        relevant_events: List[Dict[str, Any]] = []
        for ev in upcoming:
            is_rel, _ = is_event_relevant_for_asset(ev, asset)
            if is_rel:
                relevant_events.append(ev)
        risk = calculate_risk_for_events(relevant_events)
        headline_result = self.fetch_headlines_with_fallback(query, limit=5)
        headlines = headline_result.get("headlines", [])
        headline_provider = headline_result.get("provider", "none")
        news_available = headline_result.get("available", False)
        if headlines:
            high_headline = any(classify_headline_impact(h.get("title", ""), asset) in ["HIGH", "EXTREME"] for h in headlines)
            if high_headline and risk == "LOW":
                risk = "MEDIUM"
            elif high_headline and risk == "MEDIUM":
                risk = "HIGH"
        try:
            cal_provider = get_available_calendar_provider()
        except Exception:
            cal_provider = "none"
        headlines_available = news_available
        calendar_available = len(upcoming) > 0

        if not relevant_events and not headlines_available:
            summary = "No high-impact events or headlines detected in next 24H - Calendar: UNAVAILABLE, Headlines: UNAVAILABLE"
            risk = "LOW"
        elif relevant_events and not headlines_available:
            summary = f"{len(relevant_events)} calendar events detected via {cal_provider} - Calendar: AVAILABLE, Headlines: UNAVAILABLE (no headline provider configured)"
        elif headlines_available and not relevant_events:
            summary = f"{len(headlines)} headlines from {headline_provider} - Calendar: No events, Headlines: AVAILABLE"
        elif headlines_available:
            summary = f"{len(relevant_events)} calendar events (via {cal_provider}) + {len(headlines)} headlines (via {headline_provider}) - Calendar: AVAILABLE, Headlines: AVAILABLE"
        else:
            summary = f"{len(relevant_events)} calendar events - Calendar: {'AVAILABLE' if calendar_available else 'UNAVAILABLE'}, Headlines: UNAVAILABLE"
        result = {"asset": asset, "risk": risk, "events": relevant_events[:8], "headlines": headlines[:5], "headline_provider": headline_provider, "calendar_provider": cal_provider, "news_available": news_available, "headlines_available": news_available, "calendar_available": calendar_available, "summary": summary, "checked_at": datetime.now(timezone.utc).isoformat(), "error": headline_result.get("error") if not news_available and not relevant_events else None}
        self.cache[cache_key] = result
        self.cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(minutes=10)
        return result

    def check_imminent_event(self, asset: str, minutes_threshold: int = 120) -> Optional[Dict[str, Any]]:
        """
        Timezone-safe imminent detection:
        Ignores events whose timestamp cannot be safely normalized (uncertain timezone)
        to avoid false imminent alerts.
        """
        events = self.get_upcoming_events_cached(hours_ahead=6)
        now = datetime.now(timezone.utc)
        imminent: List[Tuple[float, Dict[str, Any]]] = []
        for ev in events:
            time_str = ev.get("time", "")
            dt, certain = parse_event_time_with_certainty(time_str)
            if not dt:
                continue
            # For safety, if timestamp is uncertain (naive) and we are within small threshold, skip to avoid false alert
            # However, if provider is known to provide UTC (EODHD, ForexFactory, etc) we have already assumed UTC,
            # but we mark uncertain. For imminent, require certain OR provider in trusted list with explicit assumption.
            # For now: if not certain, skip imminent check to avoid false positive from unknown timezone.
            if not certain:
                # Allow uncertain only if event is from trusted provider that we know provides UTC and time string is today
                # For strict safety per requirements: ignore uncertain for imminent
                logger.debug(f"check_imminent_event: skipping uncertain timestamp for safety: {time_str} event={ev.get('event')}")
                continue
            delta_min = (dt - now).total_seconds() / 60.0
            if 0 <= delta_min <= minutes_threshold:
                imminent.append((delta_min, ev))
            elif -30 <= delta_min < 0:
                imminent.append((delta_min, ev))
        if not imminent:
            return None
        imminent.sort(key=lambda x: x[0])
        return imminent[0][1]

    def format_news_for_signal(self, asset: str) -> str:
        """
        Fixed: news_available = headline availability only
        Must show calendar events even when headlines unavailable
        Cases:
          A: Calendar + events + headlines unavailable -> show calendar + risk + Headlines UNAVAILABLE
          B: Calendar unavailable + headlines available -> show headlines + Calendar UNAVAILABLE
          C: Both available -> show both
          D: Both unavailable -> NEWS DATA UNAVAILABLE
        """
        data = self.get_news_for_asset(asset)
        headlines_available = data.get("headlines_available", False)
        calendar_available = data.get("calendar_available", False)
        events = data.get("events", [])
        headlines = data.get("headlines", [])
        risk = data.get("risk", "LOW")

        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "EXTREME": "🔴"}.get(risk, "⚪")

        # Case D: Both unavailable
        if not calendar_available and not headlines_available and not events and not headlines:
            return "📰 NEWS RISK: LOW\n📅 Calendar: UNAVAILABLE\n📰 Headlines: UNAVAILABLE\n⚠️ Status: NEWS DATA UNAVAILABLE - No calendar or headline provider available\n"

        lines: list[str] = [f"{risk_emoji} NEWS RISK: {risk}"]

        # Calendar section
        if events:
            lines.append(f"📅 UPCOMING ({len(events)} events) via {data.get('calendar_provider','unknown')}:")
            for ev in events[:4]:
                imp = ev.get("impact", "")
                imp_icon = "🔴" if str(imp).upper() in ["HIGH", "VERY HIGH", "EXTREME", "3", "RED"] else "🟡"
                lines.append(f"{imp_icon} {ev.get('event','')} - {ev.get('time','TBD')} ({ev.get('currency','')}) [Gold: {ev.get('gold_relevance','')}]")
        else:
            if calendar_available:
                lines.append("📅 No high-impact calendar events in window")
            else:
                lines.append("📅 Calendar: UNAVAILABLE - No economic calendar provider available or no data")

        # Headlines section
        if headlines:
            lines.append(f"📰 Headlines via {data.get('headline_provider','unknown')}:")
            for h in headlines[:2]:
                lines.append(f"• {h.get('title','')[:80]} ({h.get('source','')})")
        else:
            if headlines_available:
                lines.append("📰 Headlines: No high-impact headlines in window")
            else:
                lines.append("📰 Headlines: UNAVAILABLE - No headline provider configured")

        if risk in ["HIGH", "EXTREME"]:
            lines.append("⚠️ Volatility warning: Major event approaching - reduce size or avoid")

        return "\n".join(lines)



news_engine_instance = NewsEngineSingleton()
news_engine = news_engine_instance

def format_event(event: Dict[str, Any]) -> str:
    return (f"📰 **{event.get('event', 'Economic Event')}**\n" f"🌍 Country: **{event.get('country') or 'N/A'}**\n" f"💱 Currency: **{event.get('currency') or 'N/A'}**\n" f"⏰ Time: **{event.get('time') or 'N/A'}**\n" f"🚨 Impact: **{event.get('impact') or 'N/A'}**\n" f"📊 Actual: **{event.get('actual') if event.get('actual') is not None else 'N/A'}**\n" f"📈 Forecast: **{event.get('forecast') if event.get('forecast') is not None else 'N/A'}**\n" f"📉 Previous: **{event.get('previous') if event.get('previous') is not None else 'N/A'}**\n" f"🟡 Gold relevance: **{event.get('gold_relevance')}**\n" f"🟡 Gold view: **{event.get('gold_impact')}**")

def format_news_article(article: Dict[str, Any]) -> str:
    return (f"📰 **{article.get('title', 'Financial News')}**\n\n" f"{article.get('content', '')[:800]}\n\n" f"🔗 {article.get('link', '')}")

def news_health() -> Dict[str, Any]:
    """
    Health check without excessive API calls.
    Distinguishes:
    - configured: API key exists (or public endpoint known)
    - reachable/working: cache has recent successful data or provider order non-empty and last fetch succeeded
    Does NOT call external APIs every time; uses cache and configured flags.
    ForexFactory is NOT reported as READY simply because URL is known - must have recent successful data in cache.
    """
    status = provider_status()
    try:
        # Calendar health
        cal_configured = any([
            bool(EODHD_API_KEY),
            bool(TRADING_ECONOMICS_API_KEY),
            bool(FINNHUB_API_KEY),
            bool(TWELVE_DATA_API_KEY),
        ])
        # ForexFactory considered configured (no key) but not necessarily working
        forex_configured = True  # public endpoint exists

        calendar_configured_flag = cal_configured or forex_configured

        # Check cache for working evidence (no API call)
        calendar_working = False
        calendar_provider_name = "none"
        try:
            calendar_provider_name = get_available_calendar_provider()
            # If we have cached events, consider working
            engine = NewsEngineSingleton._instance
            if engine:
                # Look for any cached events
                for key in engine.cache:
                    if key.startswith("events_") and engine._is_cache_valid(key):
                        cached_events = engine.cache.get(key, [])
                        if cached_events:
                            calendar_working = True
                            break
            # If no cache but we have a configured provider with key, we are CONFIGURED but not proven READY
            # Do not call ForexFactory just for health - require cache evidence for READY
            if not calendar_working:
                if cal_configured:
                    # At least one keyed provider configured -> CONFIGURED, not necessarily READY until fetch succeeds
                    calendar_working = False
                else:
                    # Only ForexFactory public - need cache evidence to be READY
                    calendar_working = False
        except Exception:
            calendar_working = False

        # Headline health
        headline_configured = status["headlines_available"]
        headline_working = False
        headline_provider_name = "none"
        try:
            engine = NewsEngineSingleton._instance
            if engine:
                providers = engine._get_news_provider_order()
                if providers:
                    headline_provider_name = providers[0].name
                    # Check cache for headlines
                    for key in engine.cache:
                        if key.startswith("headlines_") and engine._is_cache_valid(key):
                            cached = engine.cache.get(key, {})
                            if cached.get("available") and cached.get("headlines"):
                                headline_working = True
                                break
                    if not headline_working and headline_configured:
                        # Configured but no cache yet -> not READY, but CONFIGURED
                        headline_working = False
        except Exception:
            headline_working = False

        # Determine statuses
        if calendar_working:
            calendar_status = "READY"
        elif calendar_configured_flag:
            # Distinguish: if only ForexFactory and no cache, it's CONFIGURED but not READY
            # If keyed provider configured but no cache, CONFIGURED
            calendar_status = "CONFIGURED" if cal_configured or forex_configured else "UNAVAILABLE"
            # If every provider failed previously and no cache, override to UNAVAILABLE
            # We check if we have ever failed: if no configured keyed providers and no cache -> UNAVAILABLE is too harsh, keep CONFIGURED for public
            # But if caller wants strict: if all fail, we report UNAVAILABLE
            # For now, if no cache and no keyed provider, but ForexFactory is public, we say CONFIGURED, not READY
            # The monitor will attempt fetch and if fails, it will remain CONFIGURED
            # To meet requirement: If every calendar provider fails, return UNAVAILABLE
            # We detect this via no cache and previous errors? Simplified: if not cal_configured and not calendar_working, check if we have attempted and failed
            # For health without API calls, we cannot know failure unless cache empty and we have no configured keys -> UNAVAILABLE would be wrong for ForexFactory
            # So we keep CONFIGURED for public endpoint, but if explicit check shows all failed, caller can interpret
            # Final logic: if not calendar_working and not calendar_configured_flag -> UNAVAILABLE
            if not calendar_configured_flag:
                calendar_status = "UNAVAILABLE"
        else:
            calendar_status = "UNAVAILABLE"

        if headline_working:
            headline_status = "READY"
        elif headline_configured:
            headline_status = "CONFIGURED"
        else:
            headline_status = "UNAVAILABLE"

        overall = "READY" if (calendar_status == "READY" or headline_status == "READY") else ("CONFIGURED" if (calendar_status == "CONFIGURED" or headline_status == "CONFIGURED") else "ERROR")

        # If both UNAVAILABLE -> ERROR
        if calendar_status == "UNAVAILABLE" and headline_status == "UNAVAILABLE":
            overall = "ERROR"

        return {
            "status": overall,
            "calendar_provider": calendar_provider_name,
            "headline_provider": headline_provider_name,
            "headline_status": headline_status,
            "calendar_status": calendar_status,
            "headlines_available": status["headlines_available"],
            "calendar_available": status["calendar_available"],
            "headlines_configured": status["headlines_configured"],
            "calendar_configured": status["calendar_configured"],
            "providers": status,
        }
    except Exception as error:
        return {"status": "ERROR", "error": str(error), "providers": status}

def upcoming_news(days: int = 1, high_impact_only: bool = False) -> List[Dict[str, Any]]:
    events = get_economic_events(days=days)
    if high_impact_only:
        events = filter_events(events, impact="high")
    return events

def upcoming_gold_news(days: int = 1) -> List[Dict[str, Any]]:
    return get_gold_news(days=days, minimum_relevance="MEDIUM")

def get_upcoming_events(hours_ahead: int = 24) -> List[Dict[str, Any]]:
    return news_engine_instance.get_upcoming_events_cached(hours_ahead=hours_ahead)

def get_news_for_asset(asset: str) -> Dict[str, Any]:
    return news_engine_instance.get_news_for_asset(asset)

def check_imminent_event(asset: str, minutes_threshold: int = 120) -> Optional[Dict[str, Any]]:
    return news_engine_instance.check_imminent_event(asset, minutes_threshold)

if __name__ == "__main__":
    print("👑 KING ZARRY AI GLOBAL NEWS ENGINE - FINAL")
    print("Provider status:", provider_status())
