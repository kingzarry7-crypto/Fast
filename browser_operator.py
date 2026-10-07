"""KING ZARRY AI browser/computer operator."""
from __future__ import annotations
import json, os, re, threading, time
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
    configured = os.getenv("BROWSER_EXECUTABLE_PATH")
    candidates = [configured, "/usr/bin/chromium", "/usr/bin/chromium-browser"]
    executable = next((str(x) for x in candidates if x and Path(str(x)).is_file()), None)
    if executable is None and sync_playwright is not None:
        try:
            with sync_playwright() as p:
                managed = str(p.chromium.executable_path or "")
                if managed and Path(managed).is_file():
                    executable = managed
        except Exception:
            executable = None

    return {
        "available": bool(sync_playwright is not None and executable),
        "playwright_installed": sync_playwright is not None,
        "executable": executable,
        "sessions": len(_SESSIONS),
        "profile_dir": str(profile),
        "persistent_storage_configured": str(profile).startswith("/data/") or bool(os.getenv("BROWSER_PROFILE_DIR")),
        "policy": "explicit browser actions; consequential external actions require approval",
    }

def _profile_root() -> Path:
    return Path(os.getenv("BROWSER_PROFILE_DIR", "./data/browser_profiles")).resolve()

def _account_key(user_id: str, account_id: str | None = None) -> str:
    """Return an isolated session key for one user/account pair."""
    account = re.sub(r"[^A-Za-z0-9_.-]", "_", str(account_id or "default").strip()) or "default"
    return f"{str(user_id)}::{account}"

def _session(user_id: str, account_id: str | None = None) -> Dict[str, Any]:
    global _PLAYWRIGHT
    with _LOCK:
        key = _account_key(user_id, account_id)
        if key in _SESSIONS: return _SESSIONS[key]
        if sync_playwright is None: raise RuntimeError("Playwright is not installed")
        root = _profile_root() / re.sub(r"[^A-Za-z0-9_.-]", "_", str(user_id)) / re.sub(r"[^A-Za-z0-9_.-]", "_", str(account_id or "default"))
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
        kwargs = {
            "headless": os.getenv("BROWSER_HEADLESS", "true").strip().lower() not in {"0", "false", "no"},
            "viewport": {"width": 1440, "height": 900},
            "accept_downloads": True,
            "args": [
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-features=Translate,BackForwardCache",
            ],
        }
        if executable: kwargs["executable_path"] = executable
        context = _PLAYWRIGHT.chromium.launch_persistent_context(str(root), **kwargs)
        item = {"context": context, "page": context.pages[0] if context.pages else context.new_page()}
        _SESSIONS[key] = item
        return item


def _detect_human_verification(page: Page) -> Dict[str, Any]:
    # Avoid repeatedly walking large pages during rapid UI polling. The state is
    # refreshed at most every 750ms; explicit navigation/action calls still
    # invalidate it by using the page URL as part of the cache key.
    """Detect provider anti-bot/human-verification pages without bypassing them."""
    now = time.monotonic()
    cached = getattr(page, "_kz_hv_cache", None)
    if isinstance(cached, dict) and now - float(cached.get("at", 0)) < 0.75 and cached.get("url") == page.url:
        return dict(cached["state"])
    try:
        text = page.locator("body").inner_text(timeout=1200)[:10000]
    except Exception:
        text = ""
    try:
        title = page.title()
    except Exception:
        title = ""
    combined = " ".join((title, str(page.url or ""), text)).lower()
    indicators = (
        "loading challenge", "it needs a human touch", "complete the challenge",
        "complete this challenge", "verify you are human", "verify that you are human",
        "human verification", "captcha", "recaptcha", "hcaptcha", "security check",
        "checking your browser", "are you a robot", "unusual traffic", "anti-bot",
    )
    matched = [x for x in indicators if x in combined]
    # CAPTCHA/Turnstile/reCAPTCHA challenges are commonly rendered inside
    # cross-origin iframes, so their text is not present in the top-level body.
    try:
        for frame in page.frames:
            frame_url = str(frame.url or "").lower()
            if any(token in frame_url for token in (
                "captcha", "recaptcha", "hcaptcha", "turnstile", "challenge",
                "arkoselabs", "funcaptcha", "cloudflare",
            )):
                matched.append("human_verification_frame")
                break
    except Exception:
        pass
    try:
        for selector in (
            'iframe[src*="captcha" i]', 'iframe[src*="recaptcha" i]',
            'iframe[src*="hcaptcha" i]', 'iframe[src*="turnstile" i]',
            '[class*="captcha" i]', '[id*="captcha" i]',
            '[class*="challenge" i]', '[id*="challenge" i]',
        ):
            if page.locator(selector).count() > 0:
                matched.append("human_verification_element")
                break
    except Exception:
        pass
    matched = list(dict.fromkeys(matched))
    if not matched:
        state = {"required": False, "reason": None, "indicators": []}
        try: page._kz_hv_cache = {"at": now, "url": page.url, "state": state}
        except Exception: pass
        return state
    state = {
        "required": True,
        "reason": "human_verification_required",
        "indicators": matched[:6],
        "message": "The website requires human verification. KZ paused automation and will not bypass the challenge.",
    }
    try:
        page._kz_hv_cache = {"at": now, "url": page.url, "state": state}
    except Exception:
        pass
    return state


def _set_human_verification_state(user_id: str, page: Page, account_id: str | None = None) -> Dict[str, Any]:
    state = _detect_human_verification(page)
    with _LOCK:
        item = _SESSIONS.get(_account_key(user_id, account_id))
        if item is not None:
            item["human_verification"] = state
    return state

def _page(user_id: str, account_id: str | None = None) -> Page: return _session(user_id, account_id)["page"]
def close(user_id: str, account_id: str | None = None) -> None:
    with _LOCK:
        item = _SESSIONS.pop(_account_key(user_id, account_id), None)
        if item:
            try: item["context"].close()
            except Exception: pass

def _target(page: Page, selector: Optional[str] = None, text: Optional[str] = None):
    if selector: return page.locator(selector).first
    if text: return page.get_by_text(text, exact=True).first
    raise ValueError("selector or text is required")

def connection_status(user_id: str, account_id: str | None = None) -> Dict[str, Any]:
    """Return a conservative, freshly-verified login/session state."""
    page = _page(user_id, account_id)
    verification = _set_human_verification_state(user_id, page, account_id)
    try:
        text = page.locator("body").inner_text(timeout=5000)[:16000].lower()
    except Exception:
        text = ""

    password_fields = page.locator('input[type="password"]').count()
    login_words = (
        "sign in", "sign in to", "log in", "log in to", "forgot password",
        "enter your password", "create your account", "join now", "join here",
    )
    logout_words = ("log out", "logout", "sign out", "signout")
    account_words = (
        "account settings", "my profile", "dashboard", "my orders", "my gigs",
        "inbox", "messages", "seller dashboard", "profile picture",
        "my account", "account menu",
    )
    login_signal = password_fields > 0 or any(word in text for word in login_words)
    logout_signal = any(word in text for word in logout_words)
    account_matches = {word for word in account_words if word in text}

    # Provider-specific authenticated UI markers. These are deliberately
    # positive/account-only signals; a public homepage or login form cannot
    # satisfy them.
    provider = (page.url or "").lower()
    provider_markers: list[str] = []
    if "fiverr.com" in provider:
        fiverr_markers = (
            "switch to selling", "switch to buying", "seller dashboard",
            "my gigs", "my orders", "my profile", "manage orders",
            "earnings", "inbox", "profile settings",
        )
        provider_markers = [x for x in fiverr_markers if x in text]
        # Fiverr's authenticated shell can expose account/profile links without
        # printing the word "logout".
        try:
            account_links = page.locator(
                'a[href*="/users/"], a[href*="/profile"], '
                'a[href*="/dashboard"], a[href*="/gigs"], '
                'button[aria-label*="profile" i], button[aria-label*="account" i]'
            ).count()
        except Exception:
            account_links = 0
    else:
        account_links = 0

    positive_auth = (
        logout_signal
        or len(account_matches) >= 2
        or len(provider_markers) >= 2
        or (bool(provider_markers) and account_links >= 1)
    )

    # Cookie values are never returned, logged, or stored. Cookie names are
    # only a secondary signal because anonymous sessions also have cookies.
    auth_cookie_names = {
        "session_id", "session", "sid", "auth", "authenticated",
        "access_token", "refresh_token", "user_session", "login_session",
    }
    try:
        context = getattr(page, "context", None)
        cookies = context.cookies() if context is not None else []
        cookie_names = {
            str(c.get("name") or "").lower()
            for c in cookies
            if c.get("name")
        }
    except Exception:
        cookie_names = set()
    auth_cookie_matches = sorted(cookie_names.intersection(auth_cookie_names))
    auth_cookie_signal = bool(auth_cookie_matches)

    authenticated = bool(
        positive_auth
        or (auth_cookie_signal and (len(account_matches) >= 1 or len(provider_markers) >= 1))
    )

    with _LOCK:
        session = _SESSIONS.get(_account_key(user_id, account_id)) or {}
        previously_confirmed = bool(session.get("account_connected"))
        # Never let a previous confirmation override current live evidence.
        if previously_confirmed and not authenticated:
            session["account_connected"] = False
            session["disconnected_at"] = datetime.now(timezone.utc).isoformat()

    if verification.get("required"):
        status = "human_verification"
    elif authenticated:
        status = "connected" if previously_confirmed else "ready_to_confirm"
    else:
        status = "login_required"

    return {
        "status": status,
        "connected": status == "connected",
        "login_required": status == "login_required",
        "authenticated": authenticated,
        "login_evidence": {
            "password_field": bool(password_fields),
            "login_signal": bool(login_signal),
            "logout_signal": bool(logout_signal),
            "account_markers": sorted(account_matches),
            "provider_markers": provider_markers,
            "account_link_count": account_links,
            "positive_auth_signal": bool(positive_auth),
            "auth_cookie_names": auth_cookie_matches,
            "auth_cookie_signal": auth_cookie_signal,
            "method": (
                "authenticated_dom"
                if positive_auth
                else "authenticated_dom_plus_session_cookie"
                if authenticated
                else "none"
            ),
        },
        "human_verification_required": verification.get("required", False),
        "url": page.url,
        "title": page.title(),
    }

def confirm_connection(user_id: str, account_id: str | None = None) -> Dict[str, Any]:
    """Mark the current authenticated browser session as connected after user confirmation."""
    page = _page(user_id, account_id)
    verification = _set_human_verification_state(user_id, page, account_id)
    if verification.get("required"):
        raise PermissionError("Human verification is still required. Complete it yourself first.")
    state = connection_status(user_id, account_id)
    if state.get("status") != "ready_to_confirm":
        raise PermissionError(
            "KZ cannot connect this account yet. The live browser session does not contain enough evidence of a completed login."
        )
    with _LOCK:
        item = _SESSIONS.get(_account_key(user_id, account_id))
        if item is not None:
            item["account_connected"] = True
            item["connected_at"] = datetime.now(timezone.utc).isoformat()
    return connection_status(user_id, account_id)


def inspect(user_id: str, account_id: str | None = None) -> Dict[str, Any]:
    page = _page(user_id, account_id)
    text = page.locator("body").inner_text(timeout=2500)[:12000]
    verification = _set_human_verification_state(user_id, page, account_id)
    state = connection_status(user_id, account_id)
    return {"url": page.url, "title": page.title(), "text": text, "human_verification": verification, "connection": state, "buttons": [{"text": (x.inner_text() or "")[:160], "selector": "#" + x.get_attribute("id") if x.get_attribute("id") else None} for x in page.locator("button, [role=\"button\"]").all()[:40]], "links": [{"text": (x.inner_text() or "")[:160], "href": x.get_attribute("href")} for x in page.locator("a").all()[:40]], "inputs": [{"selector": "#"+x.get_attribute("id") if x.get_attribute("id") else "input[name=\""+str(x.get_attribute("name") or "")+"\"]", "type": x.get_attribute("type") or "text", "name": x.get_attribute("name"), "placeholder": x.get_attribute("placeholder")} for x in page.locator("input,textarea,select").all()[:40]]}

def navigate(user_id: str, url: str, account_id: str | None = None) -> Dict[str, Any]:
    url = str(url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("Only http(s) URLs are allowed")

    page = _page(user_id, account_id)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as exc:
        message = str(exc)
        # Chromium can crash a renderer on heavier sites such as WhatsApp Web.
        # Recover the page inside the existing persistent browser context and
        # retry once instead of exposing a raw Playwright Page.goto crash.
        if "Page crashed" not in message and "page crashed" not in message.lower():
            raise
        with _LOCK:
            session = _SESSIONS.get(_account_key(user_id, account_id))
        if not session:
            raise RuntimeError("The KZ browser session is no longer available. Please open login again.")
        context = session["context"]
        try:
            try:
                page.close()
            except Exception:
                pass
            page = context.new_page()
            with _LOCK:
                session["page"] = page
            page.goto(url, wait_until="commit", timeout=45000)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=20000)
            except Exception:
                # Some SPA-heavy sites remain active while the document is
                # already usable. A committed page is enough to continue.
                pass
        except Exception as retry_exc:
            raise RuntimeError(
                "The website browser page crashed while opening this site. KZ recovered the browser session, "
                "but the site could not be loaded. Please try OPEN LOGIN again."
            ) from retry_exc

    verification = _set_human_verification_state(user_id, page, account_id)
    return {"success": True, "url": page.url, "title": page.title(), "human_verification": verification}

def click(user_id: str, selector: Optional[str] = None, text: Optional[str] = None, account_id: str | None = None) -> Dict[str, Any]:
    page = _page(user_id, account_id); _target(page, selector, text).click(timeout=15000); page.wait_for_timeout(80)
    return {"success": True, "url": page.url, "title": page.title()}

def fill(user_id: str, selector: str, value: str, account_id: str | None = None) -> Dict[str, Any]:
    if not selector: raise ValueError("selector is required")
    _page(user_id, account_id).locator(selector).first.fill(str(value)); return {"success": True, "selector": selector}

def select(user_id: str, selector: str, value: str, account_id: str | None = None) -> Dict[str, Any]:
    _page(user_id, account_id).locator(selector).first.select_option(str(value)); return {"success": True, "selector": selector}

def upload(user_id: str, selector: str, path: str, account_id: str | None = None) -> Dict[str, Any]:
    file_path = Path(str(path)).expanduser().resolve()
    if not file_path.is_file(): raise ValueError("upload file does not exist")
    _page(user_id, account_id).locator(selector).first.set_input_files(str(file_path)); return {"success": True, "filename": file_path.name}

def screenshot(user_id: str, account_id: str | None = None) -> bytes:
    """Capture the current browser viewport for user-controlled remote interaction."""
    return _page(user_id, account_id).screenshot(full_page=False)


def viewport(user_id: str, account_id: str | None = None) -> Dict[str, Any]:
    page = _page(user_id, account_id)
    size = page.viewport_size or {}
    return {
        "width": int(size.get("width") or 0),
        "height": int(size.get("height") or 0),
    }


def manual_click(user_id: str, x: float, y: float, account_id: str | None = None) -> Dict[str, Any]:
    """Forward one click explicitly chosen by the logged-in KZ user.

    This is not autonomous browser control: the coordinate comes directly
    from the user's live-browser click. It is primarily for login UI controls
    that are not represented reliably as accessible buttons.
    """
    page = _page(user_id, account_id)
    challenge = _set_human_verification_state(user_id, page, account_id)
    if challenge.get("required"):
        raise PermissionError("Use the manual human-verification control while a challenge is active.")
    size = viewport(user_id, account_id)
    px, py = float(x), float(y)
    if px < 0 or py < 0 or px > size["width"] or py > size["height"]:
        raise ValueError("Click coordinates are outside the browser viewport.")
    page.mouse.click(px, py)
    page.wait_for_timeout(100)
    return {"success": True, "x": px, "y": py, "url": page.url, "title": page.title()}


def human_click(user_id: str, x: float, y: float, account_id: str | None = None) -> Dict[str, Any]:
    """Allow the authenticated user to interact with an active human challenge.

    This is deliberately limited to the period where the detector says a human
    verification challenge is present. KZ never chooses the coordinates.
    """
    page = _page(user_id, account_id)
    challenge = _set_human_verification_state(user_id, page, account_id)
    if not challenge.get("required"):
        raise PermissionError("Manual challenge interaction is only available while human verification is active.")
    size = viewport(user_id, account_id)
    px, py = float(x), float(y)
    if px < 0 or py < 0 or px > size["width"] or py > size["height"]:
        raise ValueError("Click coordinates are outside the browser viewport.")
    page.mouse.click(px, py)
    page.wait_for_timeout(350)
    return {"success": True, "x": px, "y": py, "human_verification": _set_human_verification_state(user_id, page, account_id)}


def _human_pointer_position(user_id: str, x: float, y: float, account_id: str | None = None):
    page = _page(user_id, account_id)
    challenge = _set_human_verification_state(user_id, page, account_id)
    if not challenge.get("required"):
        raise PermissionError("Manual challenge interaction is only available while human verification is active.")
    size = viewport(user_id, account_id)
    px, py = float(x), float(y)
    if px < 0 or py < 0 or px > size["width"] or py > size["height"]:
        raise ValueError("Pointer coordinates are outside the browser viewport.")
    return page, px, py


def human_down(user_id: str, x: float, y: float, account_id: str | None = None) -> Dict[str, Any]:
    page, px, py = _human_pointer_position(user_id, x, y, account_id)
    page.mouse.move(px, py)
    page.mouse.down()
    return {"success": True, "x": px, "y": py}


def human_up(user_id: str, x: float, y: float, account_id: str | None = None) -> Dict[str, Any]:
    page, px, py = _human_pointer_position(user_id, x, y, account_id)
    page.mouse.move(px, py)
    page.mouse.up()
    page.wait_for_timeout(200)
    return {"success": True, "x": px, "y": py, "human_verification": _set_human_verification_state(user_id, page, account_id)}


def human_press(user_id: str, x: float, y: float, duration_ms: int, account_id: str | None = None) -> Dict[str, Any]:
    """Replay one user-initiated press-and-hold without choosing or solving the challenge."""
    page, px, py = _human_pointer_position(user_id, x, y, account_id)
    duration = max(100, min(int(duration_ms), 15000))
    page.mouse.move(px, py)
    page.mouse.down()
    try:
        page.wait_for_timeout(duration)
    finally:
        page.mouse.up()
    # Fiverr can take several seconds to remove the challenge iframe and
    # rebuild the authenticated page. Do not stop immediately after releasing
    # the pointer; poll the live browser and then refresh the real connection
    # state before returning.
    deadline = time.monotonic() + 10.0
    verification = _set_human_verification_state(user_id, page, account_id)
    while verification.get("required") and time.monotonic() < deadline:
        page.wait_for_timeout(500)
        verification = _set_human_verification_state(user_id, page, account_id)

    state = connection_status(user_id, account_id)
    return {
        "success": True,
        "verified": not verification.get("required", False),
        "status": "verified" if not verification.get("required", False) else "still_required",
        "x": px,
        "y": py,
        "duration_ms": duration,
        "human_verification": verification,
        "connection": state,
    }


def human_move(user_id: str, x: float, y: float, account_id: str | None = None) -> Dict[str, Any]:
    """Move the user's pointer inside an active human challenge."""
    page = _page(user_id, account_id)
    challenge = _set_human_verification_state(user_id, page, account_id)
    if not challenge.get("required"):
        raise PermissionError("Manual challenge interaction is only available while human verification is active.")
    size = viewport(user_id, account_id)
    px, py = float(x), float(y)
    if px < 0 or py < 0 or px > size["width"] or py > size["height"]:
        raise ValueError("Pointer coordinates are outside the browser viewport.")
    page.mouse.move(px, py)
    return {"success": True, "x": px, "y": py}

def check_human_verification(user_id: str, account_id: str | None = None) -> Dict[str, Any]:
    """Wait briefly for the provider to finish updating the manual challenge."""
    page = _page(user_id, account_id)
    last = {"required": True, "reason": "human_verification_required", "indicators": []}
    deadline = time.monotonic() + 6.0

    while time.monotonic() < deadline:
        last = _set_human_verification_state(user_id, page, account_id)
        if not last.get("required"):
            break
        page.wait_for_timeout(500)

    verified = not last.get("required", False)
    state = connection_status(user_id, account_id)
    return {
        "verified": verified,
        "status": "verified" if verified else "still_required",
        "message": (
            "Human verification completed in the live browser session."
            if verified
            else "The live browser still reports a human-verification challenge."
        ),
        "human_verification": last,
        "connection": state,
        "url": page.url,
        "title": page.title(),
    }

def plan_goal(user_id: str, goal: str, account_id: str | None = None) -> Dict[str, Any]:
    page = inspect(user_id, account_id)
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
        if not isinstance(action, dict):
            continue
        kind = str(action.get("type") or "").lower()
        if kind in allowed:
            clean.append({
                k: action[k]
                for k in ("type", "selector", "text", "value", "url", "path")
                if k in action
            })
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

    # A filled value can remain visible after a failed submit, so it is not
    # sufficient evidence by itself. Require provider/destination confirmation.
    verified = bool(matched_phrase)
    return {
        "verification_status": "verified_sent" if verified else "not_verified",
        "verified": verified,
        "method": "provider_confirmation" if matched_phrase else "none",
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


def execute_plan(user_id: str, actions: list[dict[str, Any]], *, allow_external: bool = False, account_id: str | None = None) -> Dict[str, Any]:
    results = []
    external = any(_is_external_action(a) for a in actions)

    # Reject consequential actions before touching the browser runtime. This
    # keeps the approval boundary deterministic even when Playwright/Chromium
    # is unavailable and avoids opening a session for a request we will reject.
    if external and not allow_external:
        raise PermissionError("external browser action requires approval")

    before = inspect(user_id, account_id) if external else None
    if external and before and (before.get("human_verification") or {}).get("required"):
        return {
            "success": True,
            "paused": True,
            "requires_human_verification": True,
            "results": [],
            "final": before,
            "verification": {
                "verification_status": "human_verification_required",
                "verified": False,
                "method": "human_verification_gate",
                "evidence": [],
                "human_verification": before.get("human_verification"),
                "note": "Automation paused. Complete the website's human verification yourself, then resume the approved workflow. KZ does not bypass CAPTCHA or anti-bot controls.",
            },
        }

    for action in actions:
        kind = str(action.get("type") or "").lower()
        if _is_external_action(action) and not allow_external:
            raise PermissionError("external browser action requires approval")
        if kind == "navigate": result = navigate(user_id, action.get("url", ""), account_id)
        elif kind == "inspect": result = inspect(user_id, account_id)
        elif kind == "click": result = click(user_id, action.get("selector"), action.get("text"), account_id)
        elif kind == "fill": result = fill(user_id, action.get("selector", ""), action.get("value", ""), account_id)
        elif kind == "select": result = select(user_id, action.get("selector", ""), action.get("value", ""), account_id)
        elif kind == "upload": result = upload(user_id, action.get("selector", ""), action.get("path", ""), account_id)
        elif kind in {"submit","post","publish","send"}: result = click(user_id, action.get("selector"), action.get("text"), account_id)
        else: raise ValueError(f"unsupported browser action: {kind}")
        results.append({"type": kind, "result": result})
        if external:
            current = inspect(user_id, account_id)
            if (current.get("human_verification") or {}).get("required"):
                return {
                    "success": True,
                    "paused": True,
                    "requires_human_verification": True,
                    "results": results,
                    "final": current,
                    "verification": {
                        "verification_status": "human_verification_required",
                        "verified": False,
                        "method": "human_verification_gate",
                        "evidence": [],
                        "human_verification": current.get("human_verification"),
                        "note": "Automation paused when a human-verification challenge appeared. No bypass was attempted.",
                    },
                }

    final = inspect(user_id, account_id)
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