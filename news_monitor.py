import asyncio
import os
import requests


# =========================================================
# KING ZARRY AI 👑
# LIVE NEWS MONITOR
# =========================================================

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

CHECK_INTERVAL = 60  # seconds


# =========================================================
# FETCH NEWS
# =========================================================

def fetch_news():

    if not NEWS_API_KEY:
        raise RuntimeError(
            "NEWS_API_KEY is missing from Railway Variables."
        )

    # Your live-news provider endpoint goes here.
    # We will connect the actual provider after
    # choosing the API.

    raise NotImplementedError(
        "Connect a live news/economic-calendar provider."
    )


# =========================================================
# FILTER IMPORTANT EVENTS
# =========================================================

def is_high_impact(event):

    keywords = [
        "CPI",
        "NFP",
        "Nonfarm Payrolls",
        "FOMC",
        "Federal Reserve",
        "Interest Rate",
        "PPI",
        "GDP",
        "Unemployment",
        "Powell",
        "Retail Sales"
    ]

    title = str(
        event.get("title", "")
    ).lower()

    return any(
        keyword.lower() in title
        for keyword in keywords
    )


# =========================================================
# FORMAT ALERT
# =========================================================

def format_news_alert(event):

    title = event.get(
        "title",
        "Unknown event"
    )

    country = event.get(
        "country",
        "US"
    )

    return (
        "🚨 **KING ZARRY AI NEWS ALERT**\n\n"

        f"🌍 Country: **{country}**\n"
        f"📌 Event: **{title}**\n\n"

        "📊 This is a high-impact event.\n"
        "🟡 XAU/USD may experience increased volatility.\n\n"

        "⚠️ Wait for confirmation before trading.\n\n"

        "👑 **KING ZARRY AI**"
    )


# =========================================================
# MONITOR LOOP
# =========================================================

async def monitor_news():

    print(
        "📰 KING ZARRY AI NEWS MONITOR STARTING..."
    )

    while True:

        try:

            events = fetch_news()

            for event in events:

                if is_high_impact(event):

                    alert = format_news_alert(
                        event
                    )

                    print(alert)

                    # Discord/Telegram sending
                    # will be connected here.

        except Exception as e:

            print(
                "❌ NEWS MONITOR ERROR:",
                repr(e)
            )

        await asyncio.sleep(
            CHECK_INTERVAL
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        monitor_news()
    )
