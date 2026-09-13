
"""
=========================================================
KING ZARRY AI 👑
LIVE NEWS MONITOR - FINAL PRODUCTION
=========================================================
Uses news.py unified engine
- Monitors BTC/USD, ETH/USD, SOL/USD, XAU/USD
- Intelligent deduplication: same FOMC event across assets = one alert with affected list
- No duplicate Telegram bot polling
- Safe startup: if __name__ == "__main__" only
- Expiry documented: same event suppressed for 6 hours (configurable)
"""
import os
import re
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set, Tuple

from news import (
    get_news_for_asset,
    get_economic_events,
    provider_status,
    get_available_calendar_provider,
    get_available_provider,
    filter_events,
    parse_event_time,
    parse_event_time_with_certainty,
    is_event_relevant_for_asset,
    classify_headline_impact,
    news_engine_instance,
)

logger = logging.getLogger("king_zarry_monitor")

def clean_env(value: Optional[str], default: str = "") -> str:
    if not value:
        return default
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(value)).strip() or default

CHECK_INTERVAL = int(clean_env(os.getenv("NEWS_MONITOR_INTERVAL"), "60"))
ALERT_EXPIRY_HOURS = int(clean_env(os.getenv("NEWS_ALERT_EXPIRY_HOURS"), "6"))

MONITORED_ASSETS = ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD"]

HIGH_IMPACT_KEYWORDS = [
    "CPI", "NFP", "Nonfarm Payrolls", "FOMC", "Federal Reserve", "Interest Rate",
    "PPI", "GDP", "Unemployment", "Powell", "Retail Sales", "PCE", "ECB", "BOE",
]

class AlertCache:
    """
    Intelligent deduplication:
    - Underlying economic event identified by provider+event name+time (not asset)
    - Same FOMC across BTC/ETH/SOL/XAU = one logical alert with affected assets list
    - Asset-specific headlines include asset in dedup key
    - Expired after ALERT_EXPIRY_HOURS (default 6 hours) - same event suppressed for 6 hours
    - Bounded cache with automatic expiry cleanup
    """
    def __init__(self, expiry_hours: int = 6):
        self.alerted: Dict[str, datetime] = {}
        self.expiry_hours = expiry_hours

    def _make_event_id(self, event: Dict[str, Any]) -> str:
        """Underlying event identity - asset-agnostic for calendar events"""
        parts = [
            str(event.get("provider", "")),
            str(event.get("event") or event.get("title", "")),
            str(event.get("time") or event.get("date") or ""),
        ]
        raw = "|".join(parts).lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _make_headline_id(self, headline: Dict[str, Any], asset: str = "") -> str:
        """Asset-specific headline identity - asset context included"""
        parts = [
            str(headline.get("provider", "")),
            str(headline.get("title") or headline.get("event", "")),
            str(headline.get("url") or headline.get("link") or ""),
            asset.upper(),
        ]
        raw = "|".join(parts).lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _cleanup(self):
        now = datetime.now(timezone.utc)
        expired = [k for k, v in self.alerted.items() if now - v > timedelta(hours=self.expiry_hours)]
        for k in expired:
            del self.alerted[k]

    def is_duplicate_event(self, event: Dict[str, Any]) -> bool:
        self._cleanup()
        eid = self._make_event_id(event)
        return eid in self.alerted

    def is_duplicate_headline(self, headline: Dict[str, Any], asset: str = "") -> bool:
        self._cleanup()
        eid = self._make_headline_id(headline, asset)
        return eid in self.alerted

    def mark_event_alerted(self, event: Dict[str, Any]):
        eid = self._make_event_id(event)
        self.alerted[eid] = datetime.now(timezone.utc)

    def mark_headline_alerted(self, headline: Dict[str, Any], asset: str = ""):
        eid = self._make_headline_id(headline, asset)
        self.alerted[eid] = datetime.now(timezone.utc)

    def count(self) -> int:
        self._cleanup()
        return len(self.alerted)

alert_cache = AlertCache(expiry_hours=ALERT_EXPIRY_HOURS)

def is_high_impact(event: Dict[str, Any]) -> bool:
    title = str(event.get("event") or event.get("title", "")).lower()
    impact = str(event.get("impact", "")).lower()
    gold_rel = str(event.get("gold_relevance", "")).upper()
    if impact in ["high", "very high", "red", "3", "extreme"]:
        return True
    if gold_rel in ["VERY HIGH", "HIGH"]:
        return True
    return any(keyword.lower() in title for keyword in HIGH_IMPACT_KEYWORDS)

def is_imminent(event: Dict[str, Any], minutes_threshold: int = 120) -> Tuple[bool, Optional[int]]:
    """
    Safe imminent check: ignores uncertain timezone to avoid false alerts
    """
    time_str = event.get("time") or event.get("published") or event.get("date") or ""
    dt, certain = parse_event_time_with_certainty(time_str)
    if not dt:
        return False, None
    if not certain:
        logger.debug(f"is_imminent: skipping uncertain timestamp for safety: {time_str}")
        return False, None
    now = datetime.now(timezone.utc)
    delta_min = (dt - now).total_seconds() / 60.0
    if 0 <= delta_min <= minutes_threshold:
        return True, int(delta_min)
    if -30 <= delta_min < 0:
        return True, int(delta_min)
    return False, None

def format_news_alert(event: Dict[str, Any], affected_assets: List[str] = None, risk: str = "HIGH") -> str:
    if affected_assets is None:
        affected_assets = []
    title = event.get("event") or event.get("title") or "Unknown event"
    country = event.get("country") or "US"
    currency = event.get("currency") or "USD"
    time_str = event.get("time") or event.get("published") or "TBD"
    impact = event.get("impact") or event.get("gold_relevance") or "HIGH"
    provider = event.get("provider") or "Unknown"
    risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "EXTREME": "🔴"}.get(risk, "🟡")
    impact_emoji = "🔴" if str(impact).lower() in ["high", "very high", "extreme"] else "🟡"

    asset_icons = {"BTC/USD": "₿ BTC/USD", "ETH/USD": "Ξ ETH/USD", "SOL/USD": "◎ SOL/USD", "XAU/USD": "🥇 XAU/USD"}
    affected_lines = []
    if affected_assets:
        for a in affected_assets:
            affected_lines.append(asset_icons.get(a, f"• {a}"))
    else:
        affected_lines = ["₿ BTC/USD", "Ξ ETH/USD", "◎ SOL/USD", "🥇 XAU/USD"]

    return (
        f"🚨 **KING ZARRY AI HIGH-IMPACT EVENT**\n\n"
        f"📌 Event: **{title}**\n"
        f"🌍 Country: **{country}**\n"
        f"⏱ Time: **{time_str}**\n"
        f"💱 Currency: **{currency}**\n"
        f"{impact_emoji} Impact: **{impact}**\n"
        f"{risk_emoji} Risk: **{risk}**\n"
        f"📰 Provider: **{provider}**\n\n"
        f"Potentially affected:\n"
        + "\n".join(affected_lines)
        + "\n\n"
        f"⚠️ Avoid blind entries before confirmation.\n\n"
        f"👑 **KING ZARRY AI**"
    )

def format_imminent_alert(event: Dict[str, Any], minutes_until: int, affected_assets: List[str] = None) -> str:
    if affected_assets is None:
        affected_assets = ["XAU/USD"]
    title = event.get("event") or event.get("title") or "High-Impact Event"
    country = event.get("country") or "US"
    currency = event.get("currency") or "USD"
    asset_icons = {"BTC/USD": "₿ BTC/USD", "ETH/USD": "Ξ ETH/USD", "SOL/USD": "◎ SOL/USD", "XAU/USD": "🥇 XAU/USD"}
    affected_lines = [asset_icons.get(a, a) for a in affected_assets]
    return (
        f"⚠️ **HIGH-IMPACT EVENT IMMINENT**\n\n"
        f"📌 Event: **{title}**\n"
        f"🌍 Country: **{country}**\n"
        f"⏱ In: **{minutes_until} minutes**\n"
        f"💱 Currency: **{currency}**\n\n"
        f"Potentially affected:\n"
        + "\n".join(affected_lines)
        + "\n\n"
        f"🔴 **NEWS RISK: HIGH - Volatility expected**\n"
        f"⚠️ Consider reducing size or waiting for release.\n\n"
        f"👑 KING ZARRY AI"
    )

def fetch_all_monitoring_data() -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for asset in MONITORED_ASSETS:
        try:
            data = get_news_for_asset(asset)
            results[asset] = data
        except Exception as e:
            logger.warning(f"Failed to fetch news for {asset}: {e}")
            results[asset] = {"asset": asset, "risk": "LOW", "events": [], "headlines": [], "news_available": False, "error": str(e)}
    return results

def detect_alerts() -> List[Dict[str, Any]]:
    """
    Intelligent deduplication:
    Group same underlying event across assets into one alert with affected list
    """
    all_data = fetch_all_monitoring_data()
    # Map event_id -> {event, affected_assets, max_risk}
    event_groups: Dict[str, Dict[str, Any]] = {}
    headline_alerts: List[Dict[str, Any]] = []

    for asset, data in all_data.items():
        risk = data.get("risk", "LOW")
        for event in data.get("events", []):
            if not is_high_impact(event):
                continue
            # Group by underlying event id (asset-agnostic)
            eid = alert_cache._make_event_id(event)
            if eid not in event_groups:
                event_groups[eid] = {"event": event, "affected": [], "risk": risk, "max_risk_level": 0}
            # Track affected asset
            if asset not in event_groups[eid]["affected"]:
                event_groups[eid]["affected"].append(asset)
            # Track max risk
            risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "EXTREME": 4}
            current_level = risk_levels.get(risk, 1)
            if current_level > event_groups[eid]["max_risk_level"]:
                event_groups[eid]["max_risk_level"] = current_level
                event_groups[eid]["risk"] = risk

        # Headlines - asset specific - uses single classifier from news.py
        for headline in data.get("headlines", []):
            title = headline.get("title", "")
            if not title:
                continue
            # Use unified classifier from news.py
            impact = classify_headline_impact(title, asset)
            if impact in ["HIGH", "EXTREME"]:
                # Asset-specific dedup
                if alert_cache.is_duplicate_headline(headline, asset):
                    continue
                headline_alerts.append({"type": "breaking_news", "asset": asset, "event": headline, "risk": impact, "affected": [asset]})

    alerts: List[Dict[str, Any]] = []

    # Process grouped events - DO NOT mark as alerted here, marking happens after successful delivery
    for eid, group in event_groups.items():
        event = group["event"]
        affected = group["affected"]
        risk = group["risk"]
        if alert_cache.is_duplicate_event(event):
            continue

        # Check imminent - use safe parsing to avoid false alerts from unknown timezone
        imminent, minutes_until = is_imminent(event, minutes_threshold=120)
        if imminent and minutes_until is not None:
            alerts.append({
                "type": "imminent",
                "event": event,
                "risk": risk,
                "minutes_until": minutes_until,
                "affected": affected,
                "formatted": format_imminent_alert(event, minutes_until, affected),
            })
        elif risk in ["HIGH", "EXTREME"]:
            alerts.append({
                "type": "high_impact",
                "event": event,
                "risk": risk,
                "affected": affected,
                "formatted": format_news_alert(event, affected, risk),
            })

    # Process headline alerts - DO NOT mark here, marking after delivery
    for ha in headline_alerts:
        headline = ha["event"]
        asset = ha["asset"]
        # Already checked duplicate above
        alerts.append({
            "type": "breaking_news",
            "event": headline,
            "risk": ha["risk"],
            "affected": ha["affected"],
            "formatted": format_news_alert(
                {"event": headline.get("title"), "country": "Global", "currency": asset.split("/")[0], "time": headline.get("published") or "Now", "impact": ha["risk"], "provider": headline.get("provider", "news"), "title": headline.get("title")},
                ha["affected"],
                ha["risk"],
            ),
        })

    return alerts

def fetch_news() -> List[Dict[str, Any]]:
    """Compatibility: returns useful monitoring data from unified engine"""
    try:
        events = get_economic_events(days=1)
        # Also include headlines availability info
        all_data = fetch_all_monitoring_data()
        combined = []
        for asset_data in all_data.values():
            combined.extend(asset_data.get("events", [])[:2])
        # Deduplicate combined
        seen = set()
        uniq = []
        for ev in combined + events:
            eid = f"{ev.get('event')}|{ev.get('time')}"
            if eid not in seen:
                uniq.append(ev)
                seen.add(eid)
        return uniq[:20]
    except Exception as e:
        logger.warning(f"fetch_news failed: {e}")
        return []

async def monitor_news(send_callback=None):
    print("📰 KING ZARRY AI NEWS MONITOR STARTING...")
    print(f"⏱ Interval: {CHECK_INTERVAL}s | Assets: {', '.join(MONITORED_ASSETS)} | Expiry: {ALERT_EXPIRY_HOURS}h (same event suppressed for {ALERT_EXPIRY_HOURS}h)")
    try:
        status = provider_status()
        print(f"🔌 Provider status: {status}")
        provider = get_available_calendar_provider()
        print(f"✅ Active calendar provider: {provider}")
    except Exception as e:
        print(f"⚠️ Provider check failed: {e}")
        print("📰 Status: NEWS DATA UNAVAILABLE - will retry")

    while True:
        try:
            alerts = await asyncio.to_thread(detect_alerts)
            if alerts:
                print(f"🚨 {len(alerts)} new alert(s) at {datetime.now(timezone.utc).isoformat()}")
                for alert in alerts:
                    formatted = alert.get("formatted", "")
                    print(formatted)
                    print("-" * 60)
                    delivery_success = False
                    if send_callback:
                        try:
                            await send_callback(alert)
                            delivery_success = True
                        except Exception as cb_err:
                            logger.error(f"Failed to send alert via callback: {cb_err} - will retry next cycle")
                            delivery_success = False
                    else:
                        # Standalone mode: printing counts as delivery
                        delivery_success = True

                    if delivery_success:
                        # Mark as alerted only after successful delivery - 6h suppression after success
                        try:
                            event_data = alert.get("event", {})
                            affected = alert.get("affected", [])
                            if alert.get("type") in ["breaking_news"]:
                                # Headline - asset-specific
                                asset_for_headline = affected[0] if affected else ""
                                alert_cache.mark_headline_alerted(event_data, asset_for_headline)
                            else:
                                alert_cache.mark_event_alerted(event_data)
                        except Exception as mark_err:
                            logger.warning(f"Failed to mark alert as delivered: {mark_err}")
                    else:
                        # Do NOT suppress - allow retry next cycle
                        logger.info(f"Alert not marked as delivered due to callback failure, will retry: {alert.get('event', {}).get('event') or alert.get('event', {}).get('title')}")
            else:
                logger.info(f"✅ No new alerts at {datetime.now(timezone.utc).isoformat()} | Cache size: {alert_cache.count()}")
        except Exception as e:
            logger.error(f"❌ NEWS MONITOR ERROR: {repr(e)}", exc_info=True)
            print(f"❌ NEWS MONITOR ERROR: {repr(e)} - retry in {CHECK_INTERVAL}s")
        await asyncio.sleep(CHECK_INTERVAL)

async def send_to_telegram_discord(alert: Dict[str, Any], bot=None, chat_ids: List[int] = None):
    formatted = alert.get("formatted", "")
    if bot and chat_ids:
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id=chat_id, text=formatted, parse_mode="Markdown")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")
    return formatted

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    try:
        asyncio.run(monitor_news())
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped by user")
