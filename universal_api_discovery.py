"""
KING ZARRY AI — Universal API Discovery Layer.

Additive layer: does not replace existing provider adapters.
It discovers generic APIs from Railway ENV configuration and OpenAPI JSON,
builds a tool/capability catalog, and keeps secrets server-side.

Supported ENV pattern:
  KZ_API_<NAME>_KEY
  KZ_API_<NAME>_BASE_URL
  KZ_API_<NAME>_OPENAPI_URL   (optional; auto-probes common OpenAPI locations)
  KZ_API_<NAME>_DOCS_URL      (optional human docs URL)
  KZ_API_<NAME>_NAME          (optional display name)

Also recognizes an existing *_API_KEY when matching *_BASE_URL / *_OPENAPI_URL
metadata exists.

The generic executor is deliberately conservative: it can automatically
execute documented GET/HEAD operations, while write operations are exposed
as discovered capabilities but remain adapter/approval work until a dedicated
safe mapping exists.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger("universal_api_discovery")

_TIMEOUT = max(3, int(os.getenv("KZ_API_DISCOVERY_TIMEOUT", "8")))
_MAX_OPS = max(1, int(os.getenv("KZ_API_DISCOVERY_MAX_OPERATIONS", "80")))
_cache: Dict[str, Dict[str, Any]] = {}


def _env(name: str) -> str:
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(os.getenv(name) or "")).strip()


def _safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme == "https" and bool(p.netloc)
    except Exception:
        return False


def _candidate_configs() -> List[Dict[str, str]]:
    found: Dict[str, Dict[str, str]] = {}
    for key, value in os.environ.items():
        if not value:
            continue
        m = re.match(r"^KZ_API_([A-Z0-9]+)_(KEY|BASE_URL|OPENAPI_URL|DOCS_URL|NAME)$", key)
        if m:
            ident, field = m.groups()
            found.setdefault(ident, {})[field] = str(value).strip()

    # Existing API-key ENV names become discoverable when the user also gives
    # a matching base/docs/openapi URL using the same prefix.
    for key, value in os.environ.items():
        if not value or not (key.endswith("_API_KEY") or key.endswith("_KEY")):
            continue
        prefix = key.rsplit("_", 1)[0]
        if prefix in {"GROQ", "GEMINI", "OPENROUTER", "ELEVENLABS", "TAVILY", "NEWSAPI",
                      "NEWS", "NEWSDATA", "CURRENTS", "EODHD", "FINNHUB", "TWELVEDATA",
                      "TRADING_ECONOMICS", "MASSIVE", "POLYGON", "FAL", "AGNES", "ACEDATA", "RESEND"}:
            continue
        base = _env(prefix + "_BASE_URL")
        docs = _env(prefix + "_DOCS_URL")
        spec = _env(prefix + "_OPENAPI_URL")
        if base or docs or spec:
            found.setdefault(prefix, {})["KEY"] = str(value).strip()
            if base:
                found[prefix]["BASE_URL"] = base
            if docs:
                found[prefix]["DOCS_URL"] = docs
            if spec:
                found[prefix]["OPENAPI_URL"] = spec

    out = []
    for ident, cfg in sorted(found.items()):
        if cfg.get("KEY") and (cfg.get("BASE_URL") or cfg.get("OPENAPI_URL") or cfg.get("DOCS_URL")):
            cfg = dict(cfg)
            cfg["ID"] = ident.lower()
            cfg["KEY_ENV"] = f"KZ_API_{ident}_KEY" if _env(f"KZ_API_{ident}_KEY") else next(
                (k for k in os.environ if k == f"{ident}_API_KEY" or k == f"{ident}_KEY"), ""
            )
            out.append(cfg)
    return out


def _fetch_json(url: str) -> Optional[Dict[str, Any]]:
    if not _safe_url(url):
        return None
    try:
        r = requests.get(url, timeout=_TIMEOUT, headers={"Accept": "application/json"})
        if r.status_code >= 400:
            return None
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.debug("OpenAPI fetch failed: %s", type(exc).__name__)
        return None


def _find_openapi(cfg: Dict[str, str]) -> Optional[Dict[str, Any]]:
    explicit = cfg.get("OPENAPI_URL")
    if explicit:
        data = _fetch_json(explicit)
        if data:
            return data

    base = (cfg.get("BASE_URL") or "").rstrip("/") + "/"
    if base:
        for path in ("openapi.json", "swagger.json", "v1/openapi.json", "api/openapi.json"):
            data = _fetch_json(urljoin(base, path))
            if data:
                return data
    return None


def _resolve_ref(root: Dict[str, Any], obj: Any) -> Any:
    if not isinstance(obj, dict) or "$ref" not in obj:
        return obj
    ref = obj.get("$ref", "")
    if not ref.startswith("#/"):
        return obj
    cur: Any = root
    for part in ref[2:].split("/"):
        cur = cur.get(part.replace("~1", "/").replace("~0", "~")) if isinstance(cur, dict) else None
    return cur if cur is not None else obj


def _operation_skill(path: str, method: str, op: Dict[str, Any]) -> str:
    text = " ".join([
        path, method,
        str(op.get("operationId") or ""),
        str(op.get("summary") or ""),
        str(op.get("description") or ""),
        " ".join(str(x) for x in op.get("tags") or []),
    ]).lower()
    rules = [
        (("image", "picture", "photo", "art", "img2img"), "image_generation"),
        (("video", "clip", "animation"), "video_generation"),
        (("audio", "speech", "voice", "transcrib"), "audio_voice"),
        (("search", "query", "lookup"), "search"),
        (("news", "headline", "article"), "news"),
        (("market", "stock", "forex", "crypto", "price", "quote"), "market_data"),
        (("calendar", "event", "economic"), "calendar"),
        (("email", "mail", "message"), "email"),
        (("payment", "invoice", "charge"), "payments"),
        (("user", "profile", "account"), "account_data"),
    ]
    for words, skill in rules:
        if any(w in text for w in words):
            return skill
    return "api_data" if method.lower() in ("get", "head") else "api_action"


def _operations(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    paths = spec.get("paths") or {}
    out = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "head"} or not isinstance(op, dict):
                continue
            out.append({
                "operation_id": op.get("operationId") or f"{method.lower()}_{str(path).strip('/').replace('/', '_') or 'root'}",
                "method": method.upper(),
                "path": path,
                "summary": str(op.get("summary") or op.get("description") or "").strip()[:240],
                "skill": _operation_skill(path, method, op),
                "auto_safe": method.lower() in {"get", "head"},
                "parameters": _parameter_names(spec, op),
            })
            if len(out) >= _MAX_OPS:
                return out
    return out


def _parameter_names(root: Dict[str, Any], op: Dict[str, Any]) -> List[str]:
    names = []
    for p in op.get("parameters") or []:
        p = _resolve_ref(root, p)
        if isinstance(p, dict) and p.get("name"):
            names.append(str(p["name"]))
    return names[:30]


def discover_one(cfg: Dict[str, str], force: bool = False) -> Dict[str, Any]:
    cache_key = cfg.get("ID", "")
    if cache_key and not force and cache_key in _cache:
        return _cache[cache_key]

    spec = _find_openapi(cfg)
    if not spec:
        result = {
            "id": cfg.get("ID"),
            "name": cfg.get("NAME") or cfg.get("ID", "unknown").replace("_", " ").title(),
            "env": cfg.get("KEY_ENV"),
            "base_url": cfg.get("BASE_URL"),
            "docs_url": cfg.get("DOCS_URL"),
            "adapter": "discovery_pending",
            "needs_code": True,
            "configured": True,
            "skills": [],
            "operations": [],
            "what_it_can_do": "API detected, but no readable OpenAPI specification was found.",
            "integration_hint": "Add KZ_API_<NAME>_OPENAPI_URL pointing to the provider's OpenAPI JSON, or build a dedicated adapter.",
            "openapi_found": False,
        }
        _cache[cache_key] = result
        return result

    ops = _operations(spec)
    skills = sorted(set(o["skill"] for o in ops))
    read_ops = sum(1 for o in ops if o["auto_safe"])
    write_ops = len(ops) - read_ops
    result = {
        "id": cfg.get("ID"),
        "name": cfg.get("NAME") or ((spec.get("info") or {}).get("title")) or cfg.get("ID", "unknown").replace("_", " ").title(),
        "env": cfg.get("KEY_ENV"),
        "base_url": cfg.get("BASE_URL") or ((spec.get("servers") or [{}])[0].get("url") if spec.get("servers") else None),
        "docs_url": cfg.get("DOCS_URL"),
        "adapter": "openapi_generic",
        "needs_code": write_ops > 0,
        "configured": True,
        "skills": skills,
        "operations": ops,
        "what_it_can_do": ", ".join(skills) if skills else "OpenAPI service",
        "integration_hint": (
            f"Generic OpenAPI tool registry ready: {read_ops} read operation(s) can be auto-used; "
            f"{write_ops} write operation(s) require a safe adapter/approval."
        ),
        "openapi_found": True,
        "openapi_version": spec.get("openapi") or spec.get("swagger"),
    }
    _cache[cache_key] = result
    return result


def snapshot() -> Dict[str, Any]:
    providers = [discover_one(cfg) for cfg in _candidate_configs()]
    return {
        "providers": providers,
        "configured_count": len(providers),
    }


def signature(s: Dict[str, Any]) -> str:
    return "\n".join(sorted(
        f'{p["id"]}|{p.get("adapter")}|{",".join(p.get("skills", []))}|{len(p.get("operations", []))}|{p.get("env")}'
        for p in s.get("providers", [])
    ))


def report_lines(s: Dict[str, Any]) -> List[str]:
    lines = []
    for p in s.get("providers", []):
        if p.get("openapi_found"):
            lines.append(
                f'🧠 <b>{p["name"]}</b> — API learned from OpenAPI '
                f'({len(p.get("operations", []))} operations)'
            )
            lines.append(f'   Skills: <b>{p.get("what_it_can_do")}</b>')
            lines.append(f'   Auto-use: <b>{sum(1 for x in p.get("operations", []) if x.get("auto_safe"))}</b> read operation(s)')
            if p.get("needs_code"):
                lines.append("   Write/actions: custom safe adapter or approval still required")
        else:
            lines.append(f'🟠 <b>{p["name"]}</b> — API detected, but not learned yet')
            lines.append(f'   {p.get("integration_hint")}')
    return lines


def tool_catalog() -> List[Dict[str, Any]]:
    tools = []
    for p in snapshot().get("providers", []):
        for op in p.get("operations", []):
            tools.append({
                "name": f'{p["id"]}__{op["operation_id"]}',
                "provider": p["name"],
                "description": op.get("summary") or f'{op["method"]} {op["path"]}',
                "method": op["method"],
                "path": op["path"],
                "skill": op["skill"],
                "parameters": op.get("parameters", []),
                "auto_safe": bool(op.get("auto_safe")),
            })
    return tools


def context_for_ai() -> str:
    lines = []
    for p in snapshot().get("providers", []):
        lines.append(
            f'UNIVERSAL API: {p["name"]} | skills={",".join(p.get("skills", [])) or "unknown"} '
            f'| learned={p.get("openapi_found")} | operations={len(p.get("operations", []))}'
        )
        for op in p.get("operations", [])[:30]:
            lines.append(
                f'  TOOL {p["id"]}__{op["operation_id"]}: {op["method"]} {op["path"]} '
                f'| skill={op["skill"]} | params={",".join(op.get("parameters", [])) or "none"} '
                f'| auto_safe={op.get("auto_safe")}'
            )
    return "\n".join(lines)


def execute_read_tool(tool_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute only a discovered GET/HEAD operation. Never exposes the API key."""
    parameters = parameters or {}
    for p in snapshot().get("providers", []):
        for op in p.get("operations", []):
            expected = f'{p["id"]}__{op["operation_id"]}'
            if expected != tool_name:
                continue
            if not op.get("auto_safe"):
                return {"success": False, "error": "write_operation_requires_adapter_or_approval"}
            base = (p.get("base_url") or "").rstrip("/")
            if not _safe_url(base):
                return {"success": False, "error": "secure_base_url_required"}
            path = op["path"]
            for key, value in parameters.items():
                path = path.replace("{" + key + "}", requests.utils.quote(str(value), safe=""))
            if "{" in path or "}" in path:
                return {"success": False, "error": "missing_path_parameter"}
            url = urljoin(base + "/", path.lstrip("/"))
            key_env = p.get("env")
            secret = _env(key_env) if key_env else ""
            headers = {"Accept": "application/json"}
            # Generic APIs commonly use Bearer authentication. OpenAPI-specific
            # security placement is intentionally not guessed for execution.
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            try:
                resp = requests.get(url, headers=headers, params=parameters, timeout=_TIMEOUT)
                body = resp.json() if "json" in (resp.headers.get("content-type") or "").lower() else resp.text[:12000]
                return {"success": resp.status_code < 400, "status_code": resp.status_code, "data": body, "tool": tool_name}
            except Exception as exc:
                logger.warning("Universal API execution failed: %s", type(exc).__name__)
                return {"success": False, "error": "request_failed"}
    return {"success": False, "error": "tool_not_found"}
