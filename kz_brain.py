"""KZ AGENT BRAIN — safe planner and tool registry.

The brain decides what kind of work is needed and which existing KZ capability
should be used. It does not execute consequential actions or grant permissions.
Execution remains owned by the workflow engine and existing approval gateways.
"""
from __future__ import annotations

import re
from typing import Any, Callable

SAFE_TOOLS = {
    "shopify_read": {"description": "Read Shopify store, products, orders, and inventory through the official connector.", "risk": "green"},
    "shopify_inventory_watch": {"description": "Read tracked Shopify variant quantities and flag low/out-of-stock items; no purchase or quantity changes.", "risk": "green"},
    "autods_research": {"description": "Research AutoDS products, suppliers, margins, and store signals through the approved connection.", "risk": "green"},
    "fiverr_watch": {"description": "Monitor Fiverr opportunities and inspect permitted pages through the isolated browser.", "risk": "green"},
    "web_research": {
        "description": "Research current public information and opportunities.",
        "risk": "green",
    },
    "browser_read": {
        "description": "Open and inspect a website without making external changes.",
        "risk": "green",
    },
    "gmail_read": {
        "description": "Read connected Gmail information.",
        "risk": "green",
    },
    "calendar_read": {
        "description": "Read connected calendar information.",
        "risk": "green",
    },
    "drive_read": {
        "description": "Read connected Drive information.",
        "risk": "green",
    },
    "market_analysis": {
        "description": "Analyze market data without placing an order.",
        "risk": "green",
    },
    "memory": {
        "description": "Use existing shared memory and learning context.",
        "risk": "green",
    },
}

APPROVAL_TOOLS = {
    "shopify_write": {"description": "Create or modify Shopify products, prices, inventory, or other store data.", "risk": "yellow"},
    "autods_write": {"description": "Import, publish, or change AutoDS store/fulfillment data.", "risk": "yellow"},
    "fiverr_action": {"description": "Send Fiverr messages, submit offers, or perform delivery actions.", "risk": "yellow"},
    "gmail_send": {
        "description": "Send an email through an approved connected account.",
        "risk": "yellow",
    },
    "browser_action": {
        "description": "Perform an external browser action such as submit, post, or publish.",
        "risk": "yellow",
    },
    "github_change": {
        "description": "Modify repository code or deployment configuration.",
        "risk": "yellow",
    },
    "calendar_write": {
        "description": "Create or modify calendar data.",
        "risk": "yellow",
    },
    "drive_write": {
        "description": "Create or modify Drive data.",
        "risk": "yellow",
    },
    "social_send": {
        "description": "Publish or send external social/messaging content.",
        "risk": "yellow",
    },
    "trade": {
        "description": "Place a financial trade.",
        "risk": "red",
    },
}

ALL_TOOLS = {**SAFE_TOOLS, **APPROVAL_TOOLS}


def _has(text: str, *terms: str) -> bool:
    low = text.lower()
    return any(term in low for term in terms)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def plan(goal: str) -> dict[str, Any]:
    """Build a deterministic, inspectable plan before workflow execution."""
    raw = str(goal or "").strip()
    if not raw:
        return {"goal": "", "kind": "unknown", "tools": [], "risk": "green", "approval_required": False, "reasoning": []}

    tools: list[str] = ["memory"]
    reasoning: list[str] = []
    low = raw.lower()

    if _has(low, "shopify", "store product", "shopify store"):
        tools.append("shopify_read")
    if _has(low, "stock", "inventory", "restock", "replenish", "out of stock", "low stock"):
        tools.append("shopify_inventory_watch")
        reasoning.append("Check actual tracked stock and prioritize low/out-of-stock items before proposing replenishment.")
        reasoning.append("Shopify store data can be inspected through the official connector.")
        if _has(low, "create", "add", "publish", "update", "change", "delete", "price", "inventory"):
            tools.append("shopify_write")
            reasoning.append("Shopify changes require approval.")

    if _has(low, "autods", "dropshipping", "supplier", "product research"):
        tools.append("autods_research")
        reasoning.append("AutoDS can be researched through the authenticated connection.")
        if _has(low, "import", "publish", "fulfill", "order", "change", "update"):
            tools.append("autods_write")
            reasoning.append("AutoDS changes or fulfillment actions require approval.")

    if _has(low, "fiverr"):
        tools.append("fiverr_watch")
        if _has(low, "message", "reply", "offer", "submit", "apply", "deliver", "send"):
            tools.append("fiverr_action")
            reasoning.append("Fiverr external actions require approval.")

    if _has(low, "gmail", "email", "inbox", "mail"):
        tools.append("gmail_read")
        reasoning.append("Email-related work can use the connected Google account.")
        if _has(low, "send", "reply", "compose", "draft", "write", "forward"):
            tools.append("gmail_send")
            reasoning.append("Sending or replying is an external action and requires approval.")

    if _has(low, "calendar", "meeting", "schedule", "appointment"):
        tools.append("calendar_read")
        if _has(low, "create", "schedule", "book", "add", "move", "cancel"):
            tools.append("calendar_write")
            reasoning.append("Calendar changes require approval.")

    if _has(low, "drive", "file", "document", "spreadsheet"):
        tools.append("drive_read")
        if _has(low, "create", "upload", "edit", "update", "delete", "share"):
            tools.append("drive_write")
            reasoning.append("Drive changes require approval.")

    if _has(low, "github", "code", "fix my app", "deploy", "repository", "repo"):
        tools.append("github_change")
        reasoning.append("Repository or deployment changes require approval before the final external change.")

    if _has(low, "browser", "website", "open ", "click", "fill", "submit", "publish", "apply"):
        tools.append("browser_read")
        if _has(low, "click", "fill", "submit", "publish", "apply", "post", "send", "upload"):
            tools.append("browser_action")
            reasoning.append("Browser actions that change or submit data require approval.")

    if _has(low, "market", "btc", "bitcoin", "eth", "ethereum", "sol", "solana", "gold", "xau"):
        tools.append("market_analysis")
        if _has(low, "buy", "sell", "trade", "long", "short"):
            tools.append("trade")
            reasoning.append("Trading is high-risk and must never be auto-approved.")

    if _has(low, "find", "research", "opportun", "client", "job", "fiverr", "upwork", "news", "latest"):
        tools.append("web_research")
        reasoning.append("Current information is needed, so the plan includes live research.")

    tools = _dedupe(tools)
    approval_tools = [x for x in tools if x in APPROVAL_TOOLS]
    risk = "red" if "trade" in tools else ("yellow" if approval_tools else "green")

    if approval_tools:
        reasoning.append("KZ will research and prepare first, then stop at the approval boundary.")
    else:
        reasoning.append("No consequential external action is required by the detected intent.")

    if _has(low, "client", "freelance", "fiverr", "upwork", "job", "opportun", "shopify", "autods", "dropshipping"):
        kind = "opportunity"
    elif "github_change" in tools:
        kind = "engineering"
    elif "trade" in tools:
        kind = "market"
    elif approval_tools:
        kind = "action"
    elif "web_research" in tools:
        kind = "research"
    else:
        kind = "assistant"

    return {
        "goal": raw,
        "kind": kind,
        "tools": tools,
        "approval_tools": approval_tools,
        "risk": risk,
        "approval_required": bool(approval_tools),
        "reasoning": reasoning,
        "tool_details": {name: ALL_TOOLS[name] for name in tools},
        "operating_constraints": {
            "upfront_spend_limit_usd": 0,
            "revenue_target_window_days": 7,
            "income_is_guaranteed": False,
            "paid_job_application_fees_allowed": False,
            "subscriptions_or_bids_without_approval_allowed": False,
            "external_actions_require_approval": True,
            "verify_before_claiming_complete": True,
            "learn_only_from_verified_outcomes": True,
        },
        "priority_policy": [
            "Prefer legitimate work with no application fee, deposit, paid bid, or required subscription.",
            "Prioritize fast-to-deliver services matching the owner's web development and AI integration skills.",
            "Prepare tailored proposals and a realistic delivery checklist; never claim a job or payment is secured until verified.",
            "Keep API and tool usage economical, reuse cached research where possible, and never spend money on behalf of the user.",
        ],
    }


def describe_tool(tool_name: str) -> dict[str, Any]:
    return dict(ALL_TOOLS.get(str(tool_name), {"description": "Unknown tool", "risk": "red"}))


def watch_categories() -> list[dict[str, Any]]:
    """The safe categories KZ can monitor and turn into approval proposals."""
    return [
        {"id": "client_opportunities", "label": "Potential clients", "tool": "web_research"},
        {"id": "freelance_jobs", "label": "Freelance jobs", "tool": "web_research"},
        {"id": "important_email", "label": "Important email", "tool": "gmail_read"},
        {"id": "calendar_followups", "label": "Calendar follow-ups", "tool": "calendar_read"},
        {"id": "website_health", "label": "Website/deployment issues", "tool": "github_change"},
        {"id": "shopify_inventory", "label": "Shopify low/out-of-stock alerts", "tool": "shopify_inventory_watch"},
        {"id": "market_watch", "label": "Market developments", "tool": "market_analysis"},
    ]
