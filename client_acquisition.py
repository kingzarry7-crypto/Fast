"""KING ZARRY AI — controlled client acquisition agent.

Qualifies a researched opportunity and creates a truthful, source-aware draft.
External sending is never automatic.
"""
from __future__ import annotations
import hashlib, re
from typing import Any, Dict

def _clean(value: Any, limit: int = 1200) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

def _source_kind(opportunity: Dict[str, Any]) -> str:
    return _clean(opportunity.get("source_kind") or "direct_client", 80).lower()

def qualify(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    title = _clean(opportunity.get("title"), 300)
    summary = _clean(opportunity.get("summary"), 900)
    url = _clean(opportunity.get("url"), 1200)
    text = (title + " " + summary).lower()
    kind = _source_kind(opportunity)
    fit = 0
    reasons = []
    if any(x in text for x in ("website", "web developer", "landing page", "redesign")):
        fit += 40; reasons.append("strong website-development fit")
    if any(x in text for x in ("hire", "looking for", "need a", "seeking", "wanted")):
        fit += 30; reasons.append("active demand signal")
    if any(x in text for x in ("paid", "budget", "contract", "freelance", "project")):
        fit += 20; reasons.append("commercial engagement signal")
    if url.startswith(("https://", "http://")):
        fit += 10; reasons.append("verifiable public source")
    if kind != "direct_client":
        reasons.insert(0, f"source classified as {kind.replace('_', ' ')}")
    fit = min(fit, 100)
    return {
        "fit_score": fit,
        "qualification": "high" if fit >= 75 else "medium" if fit >= 50 else "low",
        "source_kind": kind,
        "direct_client": kind == "direct_client",
        "reasons": reasons[:6],
        "needs_manual_verification": True,
        "checks": [
            "verify the opportunity is still open",
            "verify the actual client/recruiter/platform identity",
            "verify the allowed application or contact channel",
            "verify budget and terms",
        ],
    }

def draft_outreach(opportunity: Dict[str, Any], qualification: Dict[str, Any], profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    profile = dict(profile or {})
    title = _clean(opportunity.get("title"), 180) or "your project"
    summary = _clean(opportunity.get("summary"), 320)
    name = _clean(profile.get("display_name"), 160)
    role = _clean(profile.get("professional_title"), 160)
    business = _clean(profile.get("business_name"), 160)
    services = _clean(profile.get("services"), 360)
    kind = _source_kind(opportunity)
    intro = f"Hi — I’m {name}" if name else "Hi —"
    if role: intro += f", a {role}"
    if business: intro += f" at {business}"
    if kind == "direct_client":
        subject = f"Website help — {title}"
        hook = "I came across your project requirements."
        body = f"{intro}. {hook} I focus on {services or 'responsive websites and AI integrations'}. If the project is still open, I can review the requirements and send a concise proposal with scope, timing, and pricing."
    elif kind == "marketplace":
        subject = f"Application — {title}"
        body = f"{intro}. I’m interested in the project listed on this marketplace. My relevant services include {services or 'responsive websites and AI integrations'}. I can review the brief, confirm scope and timing, and submit the appropriate application through the marketplace."
    elif kind in {"recruiter", "recruiter_platform"}:
        subject = f"Developer application — {title}"
        body = f"{intro}. I’m interested in suitable web-development opportunities represented by this recruiter/platform. My relevant services include {services or 'responsive websites and AI integrations'}. I’m happy to provide relevant work, availability, scope, and pricing for a matched project."
    else:
        subject = f"Application — {title}"
        body = f"{intro}. I’m interested in the web-development opportunity listed here. My relevant services include {services or 'responsive websites and AI integrations'}. I can tailor an application to the listed requirements and confirm availability, scope, and pricing."
    message = f"{body}\n\nBest,\n{name or 'The developer'}"
    return {
        "subject": subject, "message": message,
        "personalization_basis": qualification.get("reasons", []),
        "approval_required": True, "send_status": "draft_only",
        "profile_used": bool(name),
        "source_kind": kind, "direct_client": kind == "direct_client",
        "contact": {"email": _clean(opportunity.get("contact_email"), 320).lower(), "phone": _clean(opportunity.get("contact_phone"), 80)},
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
    try:
        from owner_profile import profile_ready
        readiness = profile_ready(profile)
    except Exception:
        readiness = {"ready": bool(profile.get("display_name")), "missing": []}
    oid = _clean(opportunity.get("id"), 100)
    key = hashlib.sha1((str(user_id) + oid + _clean(opportunity.get("url"))).encode()).hexdigest()[:16]
    return {
        "acquisition_id": key, "status": "draft_ready", "opportunity": opportunity,
        "qualification": q, "profile": profile, "profile_ready": readiness["ready"],
        "missing_profile": readiness["missing"], "outreach": draft,
        "next_step": ("Review the exact message and destination, then approve to send."
                      if readiness["ready"] else "Complete your professional profile before external outreach."),
    }

def save_draft(user_id: str, acquisition: Dict[str, Any]) -> Dict[str, Any]:
    return {"acquisition_id": str(acquisition.get("acquisition_id") or ""), "status": str(acquisition.get("status") or "draft_ready"), "user_id": str(user_id)}
