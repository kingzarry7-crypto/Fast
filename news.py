import os
import requests
from datetime import datetime, timedelta, timezone


# =========================================================
# KING ZARRY AI 👑
# GLOBAL NEWS + ECONOMIC CALENDAR ENGINE
# =========================================================
#
# Supported providers:
#
#   1. EODHD
#   2. TradingEconomics
#   3. Finnhub
#
# Provider selection:
#
#   NEWS_PROVIDER=AUTO
#
# The engine automatically looks for an available API key.
#
# Railway variables supported:
#
#   EODHD_API_KEY
#   TRADING_ECONOMICS_API_KEY
#   FINNHUB_API_KEY
#   MQL5_API_KEY
#
# IMPORTANT:
# MQL5_API_KEY is accepted as a configuration variable,
# but it is NOT automatically treated as an economic-calendar
# API key because an MQL5 profile/API key may not provide
# economic-calendar REST access.
# =========================================================


# =========================================================
# CONFIG
# =========================================================

NEWS_PROVIDER = (
    os.getenv(
        "NEWS_PROVIDER",
        "AUTO"
    )
    .upper()
    .strip()
)

EODHD_API_KEY = (
    os.getenv("EODHD_API_KEY")
    or os.getenv("EODHD_KEY")
)

TRADING_ECONOMICS_API_KEY = (
    os.getenv("TRADING_ECONOMICS_API_KEY")
    or os.getenv("TRADING_ECONOMICS_KEY")
)

FINNHUB_API_KEY = (
    os.getenv("FINNHUB_API_KEY")
    or os.getenv("FINNHUB_KEY")
)

# Reserved only. Do not assume it provides calendar access.
MQL5_API_KEY = (
    os.getenv("MQL5_API_KEY")
    or os.getenv("MQL5_KEY")
)


# =========================================================
# PROVIDER STATUS
# =========================================================

def provider_status():

    return {

        "selected_provider":
            NEWS_PROVIDER,

        "eodhd":
            bool(EODHD_API_KEY),

        "tradingeconomics":
            bool(TRADING_ECONOMICS_API_KEY),

        "finnhub":
            bool(FINNHUB_API_KEY),

        "mql5":
            bool(MQL5_API_KEY),
    }


# =========================================================
# PROVIDER SELECTION
# =========================================================

def get_available_provider():

    if NEWS_PROVIDER != "AUTO":

        if NEWS_PROVIDER == "EODHD" and EODHD_API_KEY:
            return "EODHD"

        if (
            NEWS_PROVIDER == "TRADINGECONOMICS"
            and TRADING_ECONOMICS_API_KEY
        ):
            return "TRADINGECONOMICS"

        if NEWS_PROVIDER == "FINNHUB" and FINNHUB_API_KEY:
            return "FINNHUB"

        raise RuntimeError(
            f"NEWS_PROVIDER={NEWS_PROVIDER}, "
            "but its API key is missing."
        )

    # Automatic priority

    if EODHD_API_KEY:
        return "EODHD"

    if TRADING_ECONOMICS_API_KEY:
        return "TRADINGECONOMICS"

    if FINNHUB_API_KEY:
        return "FINNHUB"

    raise RuntimeError(
        "No supported news API key was found. "
        "Add EODHD_API_KEY, "
        "TRADING_ECONOMICS_API_KEY, "
        "or FINNHUB_API_KEY to Railway."
    )


# =========================================================
# DATE HELPERS
# =========================================================

def utc_today():

    return datetime.now(
        timezone.utc
    ).date()


def date_string(value):

    if hasattr(value, "strftime"):

        return value.strftime(
            "%Y-%m-%d"
        )

    return str(value)


# =========================================================
# GOLD IMPACT ENGINE
# =========================================================

GOLD_KEYWORDS = [

    "gold",

    "interest rate",
    "interest rates",

    "federal reserve",
    "fed",

    "fomc",

    "central bank",

    "inflation",
    "consumer price index",
    "cpi",

    "core cpi",

    "producer price index",
    "ppi",

    "core ppi",

    "nonfarm payroll",
    "non-farm payroll",
    "payroll",

    "unemployment",

    "employment",

    "jobs",

    "retail sales",

    "gdp",

    "gross domestic product",

    "pce",
    "personal consumption",

    "manufacturing pmi",
    "services pmi",
    "pmi",

    "powell",

    "treasury",

    "bond yields",

    "government bond",

    "geopolitical",

    "war",

    "sanctions",

    "trade war",

    "tariff",

    "tariffs",
]


def calculate_gold_relevance(
    event_name,
    country="",
    currency=""
):

    text = (
        f"{event_name} "
        f"{country} "
        f"{currency}"
    ).lower()

    score = 0

    for keyword in GOLD_KEYWORDS:

        if keyword in text:

            score += 1

    # USD events are especially important
    if currency.upper() == "USD":
        score += 3

    if country.upper() in (
        "US",
        "USA",
        "UNITED STATES"
    ):
        score += 2

    if score >= 6:

        return "VERY HIGH"

    if score >= 4:

        return "HIGH"

    if score >= 2:

        return "MEDIUM"

    return "LOW"


# =========================================================
# GOLD DIRECTION ESTIMATE
# =========================================================
#
# This is NOT a guaranteed trading signal.
#
# It describes the usual macro relationship only.
# Actual market reaction depends on expectations,
# the surprise, yields, USD and risk sentiment.
# =========================================================

def estimate_gold_impact(
    event_name,
    currency="",
    impact="",
    actual=None,
    forecast=None,
    previous=None
):

    text = str(
        event_name
    ).lower()

    currency = str(
        currency
    ).upper()

    impact = str(
        impact
    ).lower()

    high_rate_events = [

        "interest rate",
        "federal reserve",
        "fomc",
        "inflation",
        "cpi",
        "core cpi",
        "ppi",
        "core ppi",
        "payroll",
        "nonfarm",
        "non-farm",
        "employment",
        "retail sales",
        "gdp",
        "pce",
    ]

    relevant = any(
        keyword in text
        for keyword in high_rate_events
    )

    if not relevant and currency != "USD":

        return "LOW / INDIRECT"

    # We deliberately do not claim a direction
    # when actual/forecast data cannot be compared.

    if actual is None or forecast is None:

        if currency == "USD":

            return (
                "HIGH IMPACT - WATCH USD/YIELDS"
            )

        return (
            "POTENTIAL IMPACT - WATCH MARKET REACTION"
        )

    try:

        actual_number = float(actual)
        forecast_number = float(forecast)

    except (
        TypeError,
        ValueError
    ):

        return (
            "WATCH MARKET REACTION"
        )

    difference = (
        actual_number
        - forecast_number
    )

    # Macro interpretation:
    #
    # Stronger-than-expected US data
    # can support USD/yields and pressure gold.
    #
    # We label this as a potential tendency,
    # not a guaranteed direction.

    if currency == "USD":

        if difference > 0:

            return (
                "POTENTIALLY BEARISH GOLD"
            )

        if difference < 0:

            return (
                "POTENTIALLY BULLISH GOLD"
            )

    return (
        "WATCH MARKET REACTION"
    )


# =========================================================
# NORMALIZE EVENT
# =========================================================

def normalize_event(
    event,
    provider
):

    name = (
        event.get("event")
        or event.get("name")
        or event.get("title")
        or "Economic Event"
    )

    country = (
        event.get("country")
        or event.get("country_code")
        or ""
    )

    currency = (
        event.get("currency")
        or event.get("unit")
        or ""
    )

    event_time = (
        event.get("date")
        or event.get("time")
        or event.get("datetime")
        or ""
    )

    impact = (
        event.get("impact")
        or event.get("importance")
        or event.get("importance_level")
        or "unknown"
    )

    actual = (
        event.get("actual")
        or event.get("value")
    )

    forecast = (
        event.get("forecast")
        or event.get("estimate")
        or event.get("consensus")
    )

    previous = (
        event.get("previous")
        or event.get("prev")
    )

    gold_relevance = calculate_gold_relevance(
        name,
        country,
        currency
    )

    gold_impact = estimate_gold_impact(
        name,
        currency,
        impact,
        actual,
        forecast,
        previous
    )

    return {

        "provider":
            provider,

        "event":
            name,

        "country":
            country,

        "currency":
            currency,

        "time":
            event_time,

        "impact":
            str(impact).upper(),

        "actual":
            actual,

        "forecast":
            forecast,

        "previous":
            previous,

        "gold_relevance":
            gold_relevance,

        "gold_impact":
            gold_impact,
    }


# =========================================================
# EODHD ECONOMIC CALENDAR
# =========================================================

def get_eodhd_events(
    start_date=None,
    end_date=None
):

    if not EODHD_API_KEY:

        raise RuntimeError(
            "EODHD_API_KEY is missing."
        )

    if start_date is None:

        start_date = utc_today()

    if end_date is None:

        end_date = (
            start_date
            + timedelta(days=7)
        )

    response = requests.get(

        "https://eodhd.com/api/economic-events",

        params={

            "api_token":
                EODHD_API_KEY,

            "from":
                date_string(start_date),

            "to":
                date_string(end_date),

            "fmt":
                "json",
        },

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"EODHD HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    if isinstance(data, dict):

        if data.get("error"):

            raise RuntimeError(
                str(data["error"])
            )

        events = (
            data.get("data")
            or data.get("events")
            or []
        )

    else:

        events = data

    return [

        normalize_event(
            event,
            "EODHD"
        )

        for event in events

        if isinstance(event, dict)
    ]


# =========================================================
# FINNHUB ECONOMIC CALENDAR
# =========================================================

def get_finnhub_events(
    start_date=None,
    end_date=None
):

    if not FINNHUB_API_KEY:

        raise RuntimeError(
            "FINNHUB_API_KEY is missing."
        )

    if start_date is None:

        start_date = utc_today()

    if end_date is None:

        end_date = (
            start_date
            + timedelta(days=7)
        )

    response = requests.get(

        "https://finnhub.io/api/v1/calendar/economic",

        params={

            "from":
                date_string(start_date),

            "to":
                date_string(end_date),

            "token":
                FINNHUB_API_KEY,
        },

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Finnhub HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    events = (
        data.get(
            "economicCalendar",
            []
        )
    )

    return [

        normalize_event(
            event,
            "FINNHUB"
        )

        for event in events

        if isinstance(event, dict)
    ]


# =========================================================
# TRADING ECONOMICS
# =========================================================

def get_tradingeconomics_events(
    start_date=None,
    end_date=None
):

    if not TRADING_ECONOMICS_API_KEY:

        raise RuntimeError(
            "TRADING_ECONOMICS_API_KEY is missing."
        )

    if start_date is None:

        start_date = utc_today()

    if end_date is None:

        end_date = (
            start_date
            + timedelta(days=7)
        )

    # Trading Economics credentials can have
    # different authentication formats.
    #
    # The key is therefore read from Railway
    # instead of being hard-coded.

    url = (
        "https://api.tradingeconomics.com/"
        "calendar/country/All"
    )

    response = requests.get(

        url,

        params={

            "c":
                TRADING_ECONOMICS_API_KEY,

            "d1":
                date_string(start_date),

            "d2":
                date_string(end_date),

            "f":
                "json",
        },

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Trading Economics HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    if isinstance(data, dict):

        events = (
            data.get("data")
            or data.get("events")
            or []
        )

    else:

        events = data

    return [

        normalize_event(
            event,
            "TRADINGECONOMICS"
        )

        for event in events

        if isinstance(event, dict)
    ]


# =========================================================
# GLOBAL ECONOMIC EVENTS
# =========================================================

def get_economic_events(
    days=7,
    provider=None
):

    provider = (
        provider
        or get_available_provider()
    )

    start_date = utc_today()

    end_date = (
        start_date
        + timedelta(days=max(1, days))
    )

    errors = []

    providers = [

        provider

    ]

    # AUTO fallback
    if NEWS_PROVIDER == "AUTO":

        providers = []

        if EODHD_API_KEY:
            providers.append("EODHD")

        if TRADING_ECONOMICS_API_KEY:
            providers.append(
                "TRADINGECONOMICS"
            )

        if FINNHUB_API_KEY:
            providers.append("FINNHUB")

    for current_provider in providers:

        try:

            if current_provider == "EODHD":

                return get_eodhd_events(
                    start_date,
                    end_date
                )

            if current_provider == "FINNHUB":

                return get_finnhub_events(
                    start_date,
                    end_date
                )

            if current_provider == "TRADINGECONOMICS":

                return get_tradingeconomics_events(
                    start_date,
                    end_date
                )

        except Exception as error:

            errors.append(
                f"{current_provider}: {error}"
            )

    raise RuntimeError(
        "All news providers failed.\n"
        + "\n".join(errors)
    )


# =========================================================
# FILTER EVENTS
# =========================================================

def filter_events(
    events,
    country=None,
    currency=None,
    impact=None,
    gold_only=False
):

    results = events

    if country:

        country = country.upper()

        results = [

            event

            for event in results

            if str(
                event.get("country", "")
            ).upper()
            == country
        ]

    if currency:

        currency = currency.upper()

        results = [

            event

            for event in results

            if str(
                event.get("currency", "")
            ).upper()
            == currency
        ]

    if impact:

        impact = impact.lower()

        results = [

            event

            for event in results

            if impact in str(
                event.get("impact", "")
            ).lower()
        ]

    if gold_only:

        results = [

            event

            for event in results

            if event.get(
                "gold_relevance"
            ) in (
                "VERY HIGH",
                "HIGH",
                "MEDIUM"
            )
        ]

    return results


# =========================================================
# GLOBAL FINANCIAL NEWS
# =========================================================

def get_eodhd_news(
    limit=20
):

    if not EODHD_API_KEY:

        raise RuntimeError(
            "EODHD_API_KEY is missing."
        )

    response = requests.get(

        "https://eodhd.com/api/news",

        params={

            "api_token":
                EODHD_API_KEY,

            "limit":
                max(
                    1,
                    min(limit, 100)
                ),

            "fmt":
                "json",
        },

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"EODHD news HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    data = response.json()

    if isinstance(data, dict):

        if data.get("error"):

            raise RuntimeError(
                str(data["error"])
            )

        data = (
            data.get("data")
            or data.get("news")
            or []
        )

    results = []

    for article in data:

        if not isinstance(
            article,
            dict
        ):
            continue

        results.append({

            "provider":
                "EODHD",

            "date":
                article.get("date"),

            "title":
                article.get("title"),

            "content":
                article.get("content"),

            "link":
                article.get("link"),

            "symbols":
                article.get("symbols", []),

            "tags":
                article.get("tags", []),

            "sentiment":
                article.get("sentiment"),
        })

    return results


def get_global_news(
    limit=20
):

    provider = get_available_provider()

    # EODHD currently provides a general financial
    # news endpoint, so use it when available.

    if provider == "EODHD":

        return get_eodhd_news(
            limit
        )

    raise RuntimeError(
        "The selected economic-calendar provider "
        "does not provide the general news feed "
        "through this engine. Add EODHD_API_KEY "
        "if you also want general financial news."
    )


# =========================================================
# GOLD NEWS SUMMARY
# =========================================================

def get_gold_news(
    days=7,
    minimum_relevance="MEDIUM"
):

    events = get_economic_events(
        days=days
    )

    allowed = {

        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "VERY HIGH": 4,
    }

    minimum_score = allowed.get(
        minimum_relevance.upper(),
        2
    )

    results = [

        event

        for event in events

        if allowed.get(
            event.get(
                "gold_relevance",
                "LOW"
            ),
            1
        ) >= minimum_score
    ]

    return results


# =========================================================
# DISCORD / TELEGRAM FORMATTER
# =========================================================

def format_event(
    event
):

    return (

        f"📰 **{event.get('event', 'Economic Event')}**\n"

        f"🌍 Country: "
        f"**{event.get('country') or 'N/A'}**\n"

        f"💱 Currency: "
        f"**{event.get('currency') or 'N/A'}**\n"

        f"⏰ Time: "
        f"**{event.get('time') or 'N/A'}**\n"

        f"🚨 Impact: "
        f"**{event.get('impact') or 'N/A'}**\n"

        f"📊 Actual: "
        f"**{event.get('actual') if event.get('actual') is not None else 'N/A'}**\n"

        f"📈 Forecast: "
        f"**{event.get('forecast') if event.get('forecast') is not None else 'N/A'}**\n"

        f"📉 Previous: "
        f"**{event.get('previous') if event.get('previous') is not None else 'N/A'}**\n"

        f"🟡 Gold relevance: "
        f"**{event.get('gold_relevance')}**\n"

        f"🟡 Gold view: "
        f"**{event.get('gold_impact')}**"
    )


def format_news_article(
    article
):

    return (

        f"📰 **{article.get('title', 'Financial News')}**\n\n"

        f"{article.get('content', '')[:800]}\n\n"

        f"🔗 {article.get('link', '')}"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

def news_health():

    status = provider_status()

    try:

        provider = get_available_provider()

        return {

            "status":
                "READY",

            "provider":
                provider,

            "providers":
                status,
        }

    except Exception as error:

        return {

            "status":
                "ERROR",

            "error":
                str(error),

            "providers":
                status,
        }


# =========================================================
# COMMAND-LIKE HELPERS
# =========================================================

def upcoming_news(
    days=1,
    high_impact_only=False
):

    events = get_economic_events(
        days=days
    )

    if high_impact_only:

        events = filter_events(
            events,
            impact="high"
        )

    return events


def upcoming_gold_news(
    days=1
):

    return get_gold_news(
        days=days,
        minimum_relevance="MEDIUM"
    )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "👑 KING ZARRY AI GLOBAL NEWS ENGINE"
    )

    print(
        "Provider status:"
    )

    print(
        provider_status()
    )

    try:

        provider = get_available_provider()

        print(
            f"📰 Provider: {provider}"
        )

        events = get_economic_events(
            days=1
        )

        print(
            f"📊 Events received: {len(events)}"
        )

        for event in events[:10]:

            print(
                "\n"
                + format_event(event)
            )

    except Exception as error:

        print(
            "❌ NEWS ERROR:",
            repr(error)
        )
