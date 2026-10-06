"""KING ZARRY AI browser/computer operator."""
from __future__ import annotations
import json, os, re, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
try:
    from playwright.sync_api import sync_playwright, Page
except Exception:
    sync_playwright = None
    Page = Any
_LOCK = threading.RLock()
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_PLAYWRIGHT = None
# All Playwright Sync API objects for the persistent browser session stay on
# one dedicated thread. This prevents asyncio/FastAPI and worker threads from
# accidentally using the same Playwright objects concurrently.
_BROWSER_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kz-playwright")

def run_in_browser_thread(fn, *args, **kwargs):
    future = _BROWSER_EXECUTOR.submit(lambda: fn(*args, **kwargs))
    return future.result()

def status() -> Dict[str, Any]:
    profile = _profile_root()
    return {"available": sync_playwright is not None, "sessions": len(_SESSIONS), "profile_dir": str(profile), "persistent_storage_configured": str(profile).startswith("/data/") or bool(os.getenv("BROWSER_PROFILE_DIR")), "policy": "explicit browser actions; consequential external actions require approval"}

def _profile_root() -> Path:
    return Path(os.getenv("BROWSER_PROFILE_DIR", "./data/browser_profiles")).resolve()

def _session(user_id: str) -> Dict[str, Any]:
    global _PLAYWRIGHT
    with _LOCK:
        if str(user_id) in _SESSIONS: return _SESSIONS[str(user_id)]
        if sync_playwright is None: raise RuntimeError("Playwright is not installed")
        root = _profile_root() / re.sub(r"[^A-Za-z0-9_.-]", "_", str(user_id))
        root.mkdir(parents=True, exist_ok=True)
        if _PLAYWRIGHT is None: _PLAYWRIGHT = sync_playwright().start()
        # Prefer an explicitly configured/system browser, then the Chromium
        # installed by Playwright during the image build.
        configured = os.getenv("BROWSER_EXECUTABLE_PATH")
        candidates = [configured, "/usr/bin/chromium", "/usr/bin/chromium-browser"]
        executable = next((str(x) for x in candidates if x and Path(str(x)).exists()), None)
        if executable is None:
            try:
                managed = _PLAYWRIGHT.chromium.executable_path
                if managed and Path(managed).exists():
                    executable = str(managed)
            except Exception:
                executable = None
        kwargs = {"headless": True, "viewport": {"width": 1440, "height": 900}, "accept_downloads": True}
        if executable: kwargs["executable_path"] = executable
        context = _PLAYWRIGHT.chromium.launch_persistent_context(str(root), **kwargs)
        item = {"context": context, "page": context.pages[0] if context.pages else context.new_page()}
        _SESSIONS[str(user_id)] = item
        return item

def _page(user_id: str) -> Page: return _session(user_id)["page"]
def close(user_id: str) -> None:
    with _LOCK:
        item = _SESSIONS.pop(str(user_id), None)
        if item:
            try: item["context"].close()
            except Exception: pass

def _target(page: Page, selector: Optional[str] = None, text: Optional[str] = None):
    if selector: return page.locator(selector).first
    if text: return page.get_by_text(text, exact=True).first
    raise ValueError("selector or text is required")

def inspect(user_id: str) -> Dict[str, Any]:
    page = _page(user_id)
    return {"url": page.url, "title": page.title(), "text": page.locator("body").inner_text(timeout=10000)[:12000], "links": [{"text": (x.inner_text() or "")[:160], "href": x.get_attribute("href")} for x in page.locator("a").all()[:40]], "inputs": [{"selector": "#"+x.get_attribute("id") if x.get_attribute("id") else "input[name=\""+str(x.get_attribute("name") or "")+"\"]", "type": x.get_attribute("type") or "text", "name": x.get_attribute("name"), "placeholder": x.get_attribute("placeholder")} for x in page.locator("input,textarea,select").all()[:40]]}

def navigate(user_id: str, url: str) -> Dict[str, Any]:
    url = str(url or "").strip()
    if not re.match(r"^https?://", url, re.I): raise ValueError("Only http(s) URLs are allowed")
    page = _page(user_id); page.goto(url, wait_until="domcontentloaded", timeout=45000)
    return {"success": True, "url": page.url, "title": page.title()}

def click(user_id: str, selector: Optional[str] = None, text: Optional[str] = None) -> Dict[str, Any]:
    page = _page(user_id); _target(page, selector, text).click(timeout=15000); page.wait_for_timeout(300)
    return {"success": True, "url": page.url, "title": page.title()}

def fill(user_id: str, selector: str, value: str) -> Dict[str, Any]:
    if not selector: raise ValueError("selector is required")
    _page(user_id).locator(selector).first.fill(str(value)); return {"success": True, "selector": selector}

def select(user_id: str, selector: str, value: str) -> Dict[str, Any]:
    _page(user_id).locator(selector).first.select_option(str(value)); return {"success": True, "selector": selector}

def upload(user_id: str, selector: str, path: str) -> Dict[str, Any]:
    file_path = Path(str(path)).expanduser().resolve()
    if not file_path.is_file(): raise ValueError("upload file does not exist")
    _page(user_id).locator(selector).first.set_input_files(str(file_path)); return {"success": True, "filename": file_path.name}

def screenshot(user_id: str) -> bytes: return _page(user_id).screenshot(full_page=True)

def plan_goal(user_id: str, goal: str) -> Dict[str, Any]:
    page = inspect(user_id)
    from llm_client import ask
    prompt = "You are the KZ browser planner. User goal: " + goal + "\nCurrent URL: " + str(page.get("url")) + "\nTitle: " + str(page.get("title")) + "\nVisible text:\n" + str(page.get("text",""))[:9000] + "\nReturn JSON only with actions: navigate, inspect, click, fill, select, upload, submit, post, publish, send. Never invent passwords, OTPs, payment data, identity or secrets. Do not act outside the goal. Public submit/post/publish/send is consequential and requires approval. For edits, do not publish unless explicitly requested. If required information is missing, return an empty actions list and summary."
    raw = str(ask([{"role":"system","content":"Return valid JSON and nothing else."},{"role":"user","content":prompt}], max_tokens=900) or "").strip()
    raw = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", raw, flags=re.I)
    data = json.loads(raw)
    actions = data.get("actions") if isinstance(data, dict) else []
    if not isinstance(actions, list): raise ValueError("browser planner returned invalid actions")
    allowed = {"navigate","inspect","click","fill","select","upload","submit","post","publish","send"}
    clean = []
    for action in actions[:30]:
        if not isinstance(action, dict): continue
        kind = str(action.get("type") or "").lower()
        if kind in allowed: clean.append({k: action[k] for k in ("type","selector","text","value","url") if k in action})
    data["actions"] = clean
    return {"success": True, "plan": data, "page": page}

def _verification_evidence(before: Dict[str, Any], after: Dict[str, Any], actions: list[dict[str, Any]]) -> Dict[str, Any]:
    """Require destination-page evidence before calling an external action verified."""
    before_text = str(before.get("text") or "")
    after_text = str(after.get("text") or "")
    low = after_text.lower()

    # Generic provider success language. This is evidence from the destination
    # page, not proof that a recipient actually read the message.
    success_phrases = (
        "message sent", "sent successfully", "successfully sent",
        "application submitted", "application was submitted",
        "proposal submitted", "proposal was submitted",
        "submission successful", "successfully submitted",
        "your message has been sent", "your application has been submitted",
    )
    matched_phrase = next((p for p in success_phrases if p in low), None)

    submitted_values = [
        str(a.get("value") or "").strip()
        for a in actions
        if str(a.get("type") or "").lower() == "fill" and str(a.get("value") or "").strip()
    ]
    visible_message = None
    for value in submitted_values:
        normalized = " ".join(value.split()).lower()
        if len(normalized) >= 4 and normalized in " ".join(after_text.split()).lower():
            visible_message = value
            break

    url_changed = str(before.get("url") or "") != str(after.get("url") or "")
    evidence = []
    if matched_phrase:
        evidence.append({"type": "provider_confirmation", "text": matched_phrase})
    if visible_message:
        evidence.append({"type": "submitted_text_visible", "text": visible_message[:500]})
    if url_changed:
        evidence.append({"type": "destination_changed", "from": before.get("url"), "to": after.get("url")})

    verified = bool(matched_phrase or visible_message)
    return {
        "verification_status": "verified_sent" if verified else "not_verified",
        "verified": verified,
        "method": "provider_confirmation" if matched_phrase else ("submitted_text_visible" if visible_message else "none"),
        "evidence": evidence,
        "url": after.get("url"),
        "title": after.get("title"),
        "verified_at": datetime.now(timezone.utc).isoformat() if verified else None,
        "recipient_read": False,
        "note": "Verified means destination-page/provider evidence was observed; it does not confirm that the recipient read the message.",
    }


def _is_external_action(action: Dict[str, Any]) -> bool:
    kind = str(action.get("type") or "").lower()
    if kind in {"submit", "post", "publish", "send"}:
        return True
    # Some planners represent the final Fiverr/marketplace action as a click.
    if kind == "click":
        text = str(action.get("text") or "").strip().lower()
        selector = str(action.get("selector") or "").strip().lower()
        external_words = ("send", "submit", "apply", "place bid", "send proposal", "publish")
        return any(word in text or word in selector for word in external_words)
    return False


def execute_plan(user_id: str, actions: list[dict[str, Any]], *, allow_external: bool = False) -> Dict[str, Any]:
    results = []
    external = any(_is_external_action(a) for a in actions)
    before = inspect(user_id) if external else None

    for action in actions:
        kind = str(action.get("type") or "").lower()
        if _is_external_action(action) and not allow_external:
            raise PermissionError("external browser action requires approval")
        if kind == "navigate": result = navigate(user_id, action.get("url", ""))
        elif kind == "inspect": result = inspect(user_id)
        elif kind == "click": result = click(user_id, action.get("selector"), action.get("text"))
        elif kind == "fill": result = fill(user_id, action.get("selector", ""), action.get("value", ""))
        elif kind == "select": result = select(user_id, action.get("selector", ""), action.get("value", ""))
        elif kind == "upload": result = upload(user_id, action.get("selector", ""), action.get("path", ""))
        elif kind in {"submit","post","publish","send"}: result = click(user_id, action.get("selector"), action.get("text"))
        else: raise ValueError(f"unsupported browser action: {kind}")
        results.append({"type": kind, "result": result})

    final = inspect(user_id)
    verification = _verification_evidence(before or final, final, actions) if external else {
        "verification_status": "not_applicable",
        "verified": False,
        "method": "none",
        "evidence": [],
        "verified_at": None,
        "recipient_read": False,
        "note": "No external send/submit action was executed.",
    }
    return {
        "success": True,
        "external_executed": external,
        "results": results,
        "final": final,
        "verification": verification,
    }
