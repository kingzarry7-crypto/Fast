"""KING ZARRY AI browser/computer operator.

Uses Playwright for real browser interaction. The operator is deliberately
small and deterministic: it can navigate, inspect, click, fill, select and
upload. External/public actions are approval-gated by the caller.
"""
from __future__ import annotations

import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page
except Exception:
    sync_playwright = None
    BrowserContext = Page = Any

_LOCK = threading.RLock()
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_PLAYWRIGHT = None


def status() -> Dict[str, Any]:
    return {
        "available": sync_playwright is not None,
        "sessions": len(_SESSIONS),
        "policy": "browser actions are scoped to an explicit task; consequential external actions require approval",
    }


def _profile_root() -> Path:
    return Path(os.getenv("BROWSER_PROFILE_DIR", "./data/browser_profiles")).resolve()


def _session(user_id: str) -> Dict[str, Any]:
    with _LOCK:
        item = _SESSIONS.get(str(user_id))
        if item:
            return item
        if sync_playwright is None:
            raise RuntimeError("Playwright is not installed")
        root = _profile_root() / re.sub(r"[^A-Za-z0-9_.-]", "_", str(user_id))
        root.mkdir(parents=True, exist_ok=True)
        global _PLAYWRIGHT
        if _PLAYWRIGHT is None:
            _PLAYWRIGHT = sync_playwright().start()
        context = _PLAYWRIGHT.chromium.launch_persistent_context(
            str(root),
            headless=True,
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        item = {"context": context, "page": context.pages[0] if context.pages else context.new_page()}
        _SESSIONS[str(user_id)] = item
        return item


def close(user_id: str) -> None:
    with _LOCK:
        item = _SESSIONS.pop(str(user_id), None)
        if item:
            try:
                item["context"].close()
            except Exception:
                pass


def _page(user_id: str) -> Page:
    return _session(user_id)["page"]


def _target(page: Page, selector: Optional[str] = None, text: Optional[str] = None):
    if selector:
        return page.locator(selector).first
    if text:
        return page.get_by_text(text, exact=True).first
    raise ValueError("selector or text is required")


def inspect(user_id: str) -> Dict[str, Any]:
    page = _page(user_id)
    return {
        "url": page.url,
        "title": page.title(),
        "text": page.locator("body").inner_text(timeout=10000)[:12000],
        "links": [
            {"text": (x.inner_text() or "")[:160], "href": x.get_attribute("href")}
            for x in page.locator("a").all()[:40]
        ],
    }


def navigate(user_id: str, url: str) -> Dict[str, Any]:
    url = str(url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("Only http(s) URLs are allowed")
    page = _page(user_id)
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    return {"success": True, "url": page.url, "title": page.title()}


def click(user_id: str, selector: Optional[str] = None, text: Optional[str] = None) -> Dict[str, Any]:
    page = _page(user_id)
    _target(page, selector, text).click(timeout=15000)
    page.wait_for_timeout(300)
    return {"success": True, "url": page.url, "title": page.title()}


def fill(user_id: str, selector: str, value: str) -> Dict[str, Any]:
    if not selector:
        raise ValueError("selector is required")
    page = _page(user_id)
    page.locator(selector).first.fill(str(value))
    return {"success": True, "selector": selector}


def select(user_id: str, selector: str, value: str) -> Dict[str, Any]:
    page = _page(user_id)
    page.locator(selector).first.select_option(str(value))
    return {"success": True, "selector": selector}


def upload(user_id: str, selector: str, path: str) -> Dict[str, Any]:
    file_path = Path(str(path)).expanduser().resolve()
    if not file_path.is_file():
        raise ValueError("upload file does not exist")
    page = _page(user_id)
    page.locator(selector).first.set_input_files(str(file_path))
    return {"success": True, "selector": selector, "filename": file_path.name}


def screenshot(user_id: str) -> bytes:
    return _page(user_id).screenshot(full_page=True)


def execute_plan(user_id: str, actions: list[dict[str, Any]], *, allow_external: bool = False) -> Dict[str, Any]:
    """Execute a previously approved browser plan.

    Each action is explicit. The browser never invents a click target or
    submits a form unless that action is present in the approved plan.
    """
    results = []
    for action in actions:
        kind = str(action.get("type") or "").lower()
        if kind in {"submit", "post", "publish", "send"} and not allow_external:
            raise PermissionError("external browser action requires approval")
        if kind == "navigate":
            result = navigate(user_id, action.get("url", ""))
        elif kind == "inspect":
            result = inspect(user_id)
        elif kind == "click":
            result = click(user_id, action.get("selector"), action.get("text"))
        elif kind == "fill":
            result = fill(user_id, action.get("selector", ""), action.get("value", ""))
        elif kind == "select":
            result = select(user_id, action.get("selector", ""), action.get("value", ""))
        elif kind == "upload":
            result = upload(user_id, action.get("selector", ""), action.get("path", ""))
        elif kind in {"submit", "post", "publish", "send"}:
            result = click(user_id, action.get("selector"), action.get("text"))
        else:
            raise ValueError(f"unsupported browser action: {kind}")
        results.append({"type": kind, "result": result})
    return {"success": True, "results": results, "final": inspect(user_id)}
