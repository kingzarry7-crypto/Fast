import os
import requests
from datetime import datetime, timezone


# =========================================================
# KING ZARRY AI 👑
# LIVE ECONOMIC CALENDAR
# Trading Economics API
# =========================================================

TRADING_ECONOMICS_API_KEY = os.getenv(
    "TRADING_ECONOMICS_API_KEY"
)

TRADING_ECONOMICS_URL = (
    "https://api.tradingeconomics.com"
)


# =========================================================
# SETTINGS
# =========================================================

HIGH_IMPACT = 3

WATCH_COUNTRIES = [
    "united states",
    "united kingdom",
    "euro area",
    "china",
    "japan"
]


# =========================================================
# API REQUEST
# =========================================================

def _request(endpoint, params=None):

    if not TRADING_ECONOMICS_API_KEY:

        raise RuntimeError(
            "TRADING_ECONOMICS_API_KEY is missing. "
            "Add it to Railway Variables."
        )

    request_params = {
        "c": TRADING_ECONOMICS_API_KEY,
        "f": "json"
    }

    if params:
        request_params.update(params)

    response = requests.get(

        f"{TRADING_ECONOMICS_URL}{endpoint}",

        params=request_params,

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Trading Economics HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "Trading Economics returned "
            "invalid JSON."
        )

    if isinstance(data, dict):

        if data.get("error"):

            raise RuntimeError(
                str(data["error"])
            )

    return data


# =========================================================
# GET HIGH-IMPACT EVENTS
# =========================================================

def get_high_impact_news():

    data = _request(
        "/calendar",
        {
            "importance": HIGH_IMPACT
        }
    )

    if not isinstance(data, list):

        return []

    events = []

    for event in data:

        country = str(
            event.get(
                "Country",
                event.get("country", "")
            )
        ).strip()

        if country.lower() not in [
            item.lower()
            for item in WATCH_COUNTRIES
        ]:

            continue

        events.append(
            normalize_event(event)
        )

    return events


# =========================================================
# GET US EVENTS
# =========================================================

def get_us_news():

    data = _request(
        "/calendar/country/united%20states",
        {
            "importance": HIGH_IMPACT
        }
    )

    if not isinstance(data, list):

        return []

    return [
        normalize_event(event)
        for event in data
    ]


# =========================================================
# NORMALIZE EVENT
# =========================================================

def normalize_event(event):

    return {

        "id":
            event.get(
                "CalendarId",
                event.get(
                    "CalendarID",
                    event.get(
                        "ID",
                        ""
                    )
                )
            ),

        "country":
            event.get(
                "Country",
                event.get(
                    "country",
                    ""
                )
            ),

        "event":
            event.get(
                "Event",
                event.get(
                    "event",
                    event.get(
                        "Category",
                        ""
                    )
                )
            ),

        "category":
            event.get(
                "Category",
                event.get(
                    "category",
                    ""
                )
            ),

        "date":
            event.get(
                "Date",
                event.get(
                    "date",
                    ""
                )
            ),

        "importance":
            event.get(
                "Importance",
                event.get(
                    "importance",
                    0
                )
            ),

        "actual":
            event.get(
                "Actual",
                event.get(
                    "actual",
                    ""
                )
            ),

        "forecast":
            event.get(
                "Forecast",
                event.get(
                    "forecast",
                    ""
                )
            ),

        "previous":
            event.get(
                "Previous",
                event.get(
                    "previous",
                    ""
                )
            ),

        "unit":
            event.get(
                "Unit",
                event.get(
                    "unit",
                    ""
                )
            )
    }


# =========================================================
# GOLD / USD RELEVANCE
# =========================================================

def is_gold_relevant(event):

    text = (

        str(event.get("event", ""))

        + " "

        + str(event.get("category", ""))

        + " "

        + str(event.get("country", ""))

    ).lower()

    keywords = [

        "cpi",
        "inflation",
        "non farm",
        "nonfarm",
        "payroll",
        "employment",
        "unemployment",
        "interest rate",
        "federal reserve",
        "fed",
        "fomc",
        "powell",
        "ppi",
        "gdp",
        "retail sales",
        "jobless claims",
        "consumer confidence",
        "producer price",
        "manufacturing",
        "services pmi",
        "pmi",
        "trade balance",
        "dollar"
    ]

    return any(
        keyword in text
        for keyword in keywords
    )


# =========================================================
# GET GOLD-RELEVANT NEWS
# =========================================================

def get_gold_news():

    events = get_high_impact_news()

    return [
        event
        for event in events
        if is_gold_relevant(event)
    ]


# =========================================================
# FORMAT NEWS ALERT
# =========================================================

def format_news_alert(event):

    country = event.get(
        "country",
        "Unknown"
    )

    name = event.get(
        "event",
        "Unknown event"
    )

    date = event.get(
        "date",
        "Unknown"
    )

    actual = event.get(
        "actual",
        "-"
    )

    forecast = event.get(
        "forecast",
        "-"
    )

    previous = event.get(
        "previous",
        "-"
    )

    unit = event.get(
        "unit",
        ""
    )

    return (

        "🚨 **KING ZARRY AI NEWS ALERT**\n\n"

        f"🌍 Country: **{country}**\n"

        f"📌 Event: **{name}**\n"

        f"🕐 Time: **{date}**\n\n"

        f"📊 Actual: **{actual}** "
        f"{unit}\n"

        f"🔮 Forecast: **{forecast}** "
        f"{unit}\n"

        f"📚 Previous: **{previous}** "
        f"{unit}\n\n"

        "🔥 **HIGH IMPACT EVENT**\n"

        "🟡 XAU/USD may experience "
        "increased volatility.\n\n"

        "⚠️ Algorithmic market alert. "
        "Not financial advice."
    )


# =========================================================
# TEST
# =========================================================

def test_news():

    print(
        "📰 KING ZARRY AI "
        "LIVE ECONOMIC CALENDAR"
    )

    events = get_gold_news()

    if not events:

        print(
            "ℹ️ No high-impact "
            "gold-relevant events found."
        )

        return

    for event in events:

        print()
        print(
            format_news_alert(event)
        )


# =========================================================
# RUN DIRECTLY
# =========================================================

if __name__ == "__main__":

    try:

        test_news()

    except Exception as e:

        print(
            "❌ NEWS ERROR:",
            repr(e)
        )
