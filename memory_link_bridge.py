"""Secure one-time identity linking for KING ZARRY AI shared memory."""
from __future__ import annotations
import hashlib, secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from neon_memory import NeonMemory

_CODE_TTL_MINUTES = 10

def _hash(code: str) -> str:
    return hashlib.sha256(str(code).strip().upper().encode("utf-8")).hexdigest()

def _now():
    return datetime.now(timezone.utc)

def _db():
    return NeonMemory()

def ensure_tables():
    mem = _db()
    with mem.lock:
        conn = mem._connect()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS kz_memory_link_codes (
                code_hash TEXT PRIMARY KEY,
                canonical_user_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                used_platform TEXT,
                used_external_id TEXT
            )""")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_kz_link_codes_expiry ON kz_memory_link_codes(expires_at)")
            conn.commit()
        finally:
            conn.close()

def create_web_link_code(web_user_id: str) -> str:
    ensure_tables()
    code = secrets.token_urlsafe(8).replace("-", "").replace("_", "").upper()[:8]
    expires = _now() + timedelta(minutes=_CODE_TTL_MINUTES)
    mem = _db()
    with mem.lock:
        conn = mem._connect()
        try:
            conn.cursor().execute(
                "INSERT INTO kz_memory_link_codes(code_hash,canonical_user_id,expires_at) VALUES(%s,%s,%s)",
                (_hash(code), f"web:{str(web_user_id)}", expires),
            )
            conn.commit()
        finally:
            conn.close()
    return code

def redeem_link_code(platform: str, external_id: str, code: str, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ensure_tables()
    platform, external_id, code = str(platform or "").strip().lower(), str(external_id or "").strip(), str(code or "").strip()
    if platform not in {"telegram", "discord"} or not external_id or not code:
        return None
    mem = _db()
    with mem.lock:
        conn = mem._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT canonical_user_id,expires_at FROM kz_memory_link_codes WHERE code_hash=%s AND used_at IS NULL FOR UPDATE", (_hash(code),))
            row = cur.fetchone()
            if not row or row[1] <= _now():
                conn.rollback()
                return None
            canonical = str(row[0])
            cur.execute("UPDATE kz_memory_link_codes SET used_at=NOW(),used_platform=%s,used_external_id=%s WHERE code_hash=%s", (platform, external_id, _hash(code)))
            conn.commit()
        finally:
            conn.close()
    # Preserve any memory already created on this platform before linking.
    try:
        legacy_id = f"{platform}:{external_id}"
        if legacy_id != canonical:
            legacy_history = mem.get_history(legacy_id, limit=200)
            existing = {(x.get("role"), x.get("content")) for x in mem.get_history(canonical, limit=200)}
            for item in legacy_history:
                key = (item.get("role"), item.get("content"))
                if key not in existing:
                    mem.add_message(
                        canonical,
                        item.get("role", "user"),
                        item.get("content", ""),
                        source_platform=platform,
                    )
                    existing.add(key)
            for fact in mem.get_facts(legacy_id, limit=100):
                mem.add_fact(
                    canonical,
                    fact.get("fact", ""),
                    category=fact.get("category", "general"),
                    source=fact.get("source", platform),
                )
    except Exception:
        # Linking must never fail because an old memory record is malformed.
        pass

    mem.add_identity(canonical, platform, external_id, username=username)
    return {"canonical_user_id": canonical, "platform": platform}

def resolve_user_channels(canonical_user_id: str) -> Dict[str, list[str]]:
    """Return linked Telegram/Discord external IDs for one shared user."""
    mem = _db()
    result: Dict[str, list[str]] = {"telegram": [], "discord": []}
    try:
        with mem.lock:
            conn = mem._connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT platform, external_id FROM kz_memory_identities WHERE user_id=%s AND platform IN ('telegram','discord')",
                    (str(canonical_user_id),),
                )
                for platform, external_id in cur.fetchall() or []:
                    result.setdefault(str(platform), []).append(str(external_id))
            finally:
                conn.close()
    except Exception:
        pass
    return result


def resolve_platform_identity(platform: str, external_id: str) -> Optional[str]:
    try:
        return _db().resolve_identity(platform, external_id)
    except Exception:
        return None
