"""KING ZARRY AI — controlled client acquisition agent.

Turns a researched opportunity into a qualified prospect brief and personalized
outreach draft. It does not send messages. Sending remains an approval-gated
external action handled by the Action Gateway / Work Engine.
"""
from __future__ import annotations
import hashlib, re
from typing import Any, Dict

def _clean(value: Any, limit: int = 1200) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

def qualify(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    title = _clean(opportunity.get("title"), 300)
    summary = _clean(opportunity.get("summary"), 900)
    url = _clean(opportunity.get("url"), 1200)
    text = (title + " " + summary).lower()
    fit = 0
    reasons = []
    if any(x in text for x in ("website", "web developer", "landing page", "redesign")):
        fit += 40; reasons.append("strong website-development fit")
    if any(x in text for x in ("hire", "looking for", "need a", "seeking")):
        fit += 30; reasons.append("active demand signal")
    if any(x in text for x in ("paid", "budget", "contract", "freelance", "project")):
        fit += 20; reasons.append("commercial engagement signal")
    if url.startswith(("https://", "http://")):
        fit += 10; reasons.append("verifiable public source")
    fit = min(fit, 100)
    return {
        "fit_score": fit,
        "qualification": "high" if fit >= 75 else "medium" if fit >= 50 else "low",
        "reasons": reasons,
        "needs_manual_verification": True,
        "checks": ["verify opportunity is still open", "verify identity/contact channel", "verify budget and terms"],
    }

def draft_outreach(opportunity: Dict[str, Any], qualification: Dict[str, Any], profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    profile = dict(profile or {})
    title = _clean(opportunity.get("title"), 180) or "your project"
    summary = _clean(opportunity.get("summary"), 420)
    name = _clean(profile.get("display_name"), 160)
    role = _clean(profile.get("professional_title"), 160)
    business = _clean(profile.get("business_name"), 160)
    services = _clean(profile.get("services"), 420)
    intro = f"Hi — I’m {name}" if name else "Hi —"
    if role: intro += f", a {role}"
    if business: intro += f" at {business}"
    intro += "."
    hook = summary if summary else "I came across your project requirements"
    service_line = f" I focus on {services}." if services else " I’d be happy to review the requirements and confirm whether I’m a good fit."
    body = f"{intro} I came across your post about {title}. {hook}.{service_line} If the project is still open, I can review the requirements and send a concise proposal with scope, timing, and pricing. No pressure either way.\n\nBest,\n{name or 'The developer'}"
    return {
        "subject": f"Website help — {title}",
        "message": body,
        "personalization_basis": qualification.get("reasons", []),
        "approval_required": True,
        "send_status": "draft_only",
        "profile_used": bool(name),
        "contact": {
            "email": _clean(opportunity.get("contact_email"), 320).lower(),
            "phone": _clean(opportunity.get("contact_phone"), 80),
        },
    }

def prepare(user_id: str, opportunity: Dict[str, Any], profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if profile is None:
        try:
            from owner_profile import get_profile
            profile = get_profile(user_id)
        except Exception:
            profile = {}
    q = qualify(opportunity)
    draft = draft_outreach(opportunity, q, profile)
    oid = _clean(opportunity.get("id"), 100)
    key = hashlib.sha1((str(user_id) + oid + _clean(opportunity.get("url"))).encode()).hexdigest()[:16]
    return {
        "acquisition_id": key,
        "status": "draft_ready",
        "opportunity": opportunity,
        "qualification": q,
        "outreach": draft,
        "next_step": "Review the source and draft. Only an explicit approval may authorize external outreach.",
    }
