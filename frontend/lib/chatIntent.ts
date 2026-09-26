// Detect premium vs normal chat intents (frontend-only gating).

export type ChatIntent = "signal" | "plan" | "alert" | "normal";

const SIGNAL_PATTERNS: RegExp[] = [
  /\b(signal|signals)\b/i,
  /\b(buy|sell)\s+(btc|eth|sol|xau|gold|bitcoin|ethereum)\b/i,
  /\b(entry(\s+zone)?|stop\s*loss|\bsl\b|take\s*profit|\btp[123]?\b)\b/i,
  /\b(mtf|multi[- ]?timeframe)\b/i,
  /\b(analyze|analysis)\s+(btc|eth|sol|xau|gold|the\s+market|this\s+chart)\b/i,
  /^\/?(btc|eth|sol|xau|signal)\b/i,
  /\b(long|short)\s+(setup|bias|on)\b/i,
];

const PLAN_PATTERNS: RegExp[] = [
  /\b(one[- ]?day\s+plan|daily\s+plan|trade\s+plan)\b/i,
  /^\/?plan\b/i,
  /\bplan\s+(for\s+)?(btc|eth|sol|xau|gold)\b/i,
];

const ALERT_PATTERNS: RegExp[] = [
  /\b(alert|notify|notification)\b/i,
  /\b(when|if)\s+.+\s+(hits|reaches|above|below|crosses)\b/i,
  /^\/?alert\b/i,
];

export function detectChatIntent(text: string): ChatIntent {
  const t = text.trim();
  if (!t) return "normal";
  if (ALERT_PATTERNS.some((re) => re.test(t))) return "alert";
  if (PLAN_PATTERNS.some((re) => re.test(t))) return "plan";
  if (SIGNAL_PATTERNS.some((re) => re.test(t))) return "signal";
  return "normal";
}

export function upgradeMessageForIntent(intent: ChatIntent): string {
  if (intent === "signal") {
    return [
      "Signals are a VIP feature.",
      "",
      "Free chat is open for normal questions. Multi-timeframe signals (entry, SL, TP1–TP3) unlock with membership.",
      "",
      "→ Open Pricing to upgrade, or activate VIP on Telegram after payment.",
      "→ Then confirm membership under Settings if you already paid on Telegram.",
    ].join("\n");
  }
  if (intent === "plan") {
    return [
      "One-day trade plans are a VIP feature.",
      "",
      "You can still chat normally. Upgrade for full daily plans with levels and risk context.",
      "",
      "→ Open Pricing or confirm membership in Settings after Telegram payment.",
    ].join("\n");
  }
  if (intent === "alert") {
    return [
      "Personal price alerts are a VIP feature on the full product.",
      "",
      "Normal chat still works. Upgrade to set alerts, or use the Telegram bot VIP after subscribing.",
      "",
      "→ Pricing · Settings (mark VIP after you pay on Telegram).",
    ].join("\n");
  }
  return "This feature requires VIP. Normal chat remains available on the free tier.";
}
