"""King Zarry AI extensible plugin/tool registry.

Tools are explicitly registered with JSON-schema-like parameter metadata, a provider,
risk classification, and a callable. Only read-only tools are executable through this
generic endpoint; consequential writes remain behind each connector's approval flow.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from database import get_db_cursor

logger = logging.getLogger("king_zarry_plugin_registry")
router = APIRouter(prefix="/api/plugins", tags=["plugin-registry"])

class ToolDefinition:
    def __init__(self, name: str, provider: str, description: str,
                 parameters: Dict[str, Any], handler: Callable[..., Dict[str, Any]],
                 risk: str = "read_only"):
        self.name = name
        self.provider = provider
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.risk = risk

_TOOLS: Dict[str, ToolDefinition] = {}

def register_tool(tool: ToolDefinition) -> None:
    """Register a uniquely named tool; duplicate names fail fast at startup."""
    if tool.name in _TOOLS:
        raise RuntimeError(f"Duplicate plugin tool registered: {tool.name}")
    _TOOLS[tool.name] = tool

def _row_value(row: Any, key: str, index: int = 0) -> Any:
    if row is None:
        return None
    try:
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
    except Exception:
        pass
    try:
        return row[index]
    except Exception:
        return None

def _user_id(request: Request) -> str:
    raw = request.cookies.get("king_zarry_web_session")
    if not raw or len(raw) > 500:
        raise HTTPException(status_code=401, detail="Authentication required")
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT s.user_id FROM web_sessions s
               JOIN web_users u ON u.id=s.user_id
               WHERE s.token_hash=%s AND s.revoked_at IS NULL
                 AND s.expires_at>NOW() AND u.account_status='active'
               LIMIT 1""",
            (token_hash,),
        )
        row = cur.fetchone()
    value = str(_row_value(row, "user_id", 0) or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Authentication required")
    return value

def _connected_providers(user_id: str) -> set[str]:
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT DISTINCT provider FROM web_connected_accounts
               WHERE user_id=%s AND revoked_at IS NULL""",
            (user_id,),
        )
        rows = cur.fetchall() or []
    return {str(_row_value(row, "provider", 0) or "").lower() for row in rows}

def _github_repositories(user_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    import connector_api
    result = connector_api._github_execute(user_id, "list_repositories", {})
    return {"status": "success", **result}

def _github_repository(user_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    owner = str(arguments.get("owner") or "").strip()
    repo = str(arguments.get("repo") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", repo):
        raise HTTPException(status_code=400, detail="Valid owner and repo are required")
    import connector_api
    return {"status": "success", **connector_api._github_execute(user_id, "get_repository", {"owner": owner, "repo": repo})}

def _google_tool(operation: str) -> Callable[..., Dict[str, Any]]:
    def run(user_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import google_connector
        if operation == "list_gmail":
            query = str(arguments.get("query") or "in:anywhere")[:500]
            limit = max(1, min(int(arguments.get("limit") or 10), 25))
            payload = {"query": query, "limit": limit}
        elif operation == "list_drive":
            query = str(arguments.get("query") or "trashed = false")[:1000]
            limit = max(1, min(int(arguments.get("limit") or 20), 50))
            payload = {"query": query, "limit": limit}
        else:
            limit = max(1, min(int(arguments.get("limit") or 10), 25))
            payload = {"limit": limit}
        result = google_connector._execute(user_id, operation, payload)
        return {"status": "success", **result}
    return run

def _shopify_tool(operation: str) -> Callable[..., Dict[str, Any]]:
    def run(user_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import connector_api
        store, token = connector_api._shopify_token(user_id)
        limit = max(1, min(int(arguments.get("limit") or 10), 25))
        if operation == "list_products":
            query = """query KZPluginProducts($first: Int!) {
              products(first: $first, sortKey: UPDATED_AT, reverse: true) {
                edges { node { id title handle status updatedAt onlineStoreUrl } }
              }
            }"""
            body = connector_api._shopify_request(store, token, query, {"first": limit})
            edges = (((body.get("data") or {}).get("products") or {}).get("edges") or [])
            return {"status": "success", "verified": True, "operation": operation, "store": store,
                    "products": [edge.get("node") or {} for edge in edges]}
        query = """query KZPluginOrders($first: Int!) {
          orders(first: $first, sortKey: CREATED_AT, reverse: true) {
            edges { node { id name createdAt displayFinancialStatus displayFulfillmentStatus
              totalPriceSet { shopMoney { amount currencyCode } } } }
          }
        }"""
        body = connector_api._shopify_request(store, token, query, {"first": limit})
        edges = (((body.get("data") or {}).get("orders") or {}).get("edges") or [])
        return {"status": "success", "verified": True, "operation": operation, "store": store,
                "orders": [edge.get("node") or {} for edge in edges]}
    return run

register_tool(ToolDefinition(
    "github.list_repositories", "github",
    "List repositories accessible to the authenticated GitHub account.",
    {"type": "object", "properties": {}, "additionalProperties": False},
    _github_repositories,
))
register_tool(ToolDefinition(
    "github.get_repository", "github",
    "Read metadata for one repository.",
    {"type": "object", "properties": {
        "owner": {"type": "string", "minLength": 1, "maxLength": 100},
        "repo": {"type": "string", "minLength": 1, "maxLength": 100}},
     "required": ["owner", "repo"], "additionalProperties": False},
    _github_repository,
))
register_tool(ToolDefinition(
    "google.list_gmail", "google",
    "List recent Gmail message metadata; does not send or modify email.",
    {"type": "object", "properties": {
        "query": {"type": "string", "maxLength": 500},
        "limit": {"type": "integer", "minimum": 1, "maximum": 25}},
     "additionalProperties": False},
    _google_tool("list_gmail"),
))
register_tool(ToolDefinition(
    "google.list_drive", "google",
    "List Google Drive file metadata; does not modify files.",
    {"type": "object", "properties": {
        "query": {"type": "string", "maxLength": 1000},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50}},
     "additionalProperties": False},
    _google_tool("list_drive"),
))
register_tool(ToolDefinition(
    "google.list_calendar", "google",
    "List upcoming Google Calendar events; does not modify events.",
    {"type": "object", "properties": {
        "limit": {"type": "integer", "minimum": 1, "maximum": 25}},
     "additionalProperties": False},
    _google_tool("list_calendar"),
))
register_tool(ToolDefinition(
    "shopify.list_products", "shopify",
    "Read recent Shopify products and their metadata; does not change products.",
    {"type": "object", "properties": {
        "limit": {"type": "integer", "minimum": 1, "maximum": 25}},
     "additionalProperties": False},
    _shopify_tool("list_products"),
))
register_tool(ToolDefinition(
    "shopify.list_orders", "shopify",
    "Read recent Shopify orders and financial/fulfillment status; does not modify orders.",
    {"type": "object", "properties": {
        "limit": {"type": "integer", "minimum": 1, "maximum": 25}},
     "additionalProperties": False},
    _shopify_tool("list_orders"),
))

class ToolCallRequest(BaseModel):
    tool: str = Field(min_length=3, max_length=100)
    arguments: Dict[str, Any] = Field(default_factory=dict)

def _validate_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> None:
    props = schema.get("properties") or {}
    unknown = set(arguments) - set(props)
    if unknown and schema.get("additionalProperties") is False:
        raise HTTPException(status_code=400, detail="Unknown tool argument(s): " + ", ".join(sorted(unknown)))
    for key, value in arguments.items():
        spec = props.get(key, {})
        kind = spec.get("type")
        if kind == "string":
            if not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"{key} must be a string")
            if len(value) > int(spec.get("maxLength", 100000)):
                raise HTTPException(status_code=400, detail=f"{key} is too long")
            if len(value) < int(spec.get("minLength", 0)):
                raise HTTPException(status_code=400, detail=f"{key} is too short")
        elif kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise HTTPException(status_code=400, detail=f"{key} must be an integer")
            if value < int(spec.get("minimum", -2147483648)) or value > int(spec.get("maximum", 2147483647)):
                raise HTTPException(status_code=400, detail=f"{key} is outside the allowed range")
    missing = set(schema.get("required") or []) - set(arguments)
    if missing:
        raise HTTPException(status_code=400, detail="Missing required argument(s): " + ", ".join(sorted(missing)))

@router.get("")
@router.get("/")
def list_plugins(request: Request) -> Dict[str, Any]:
    """Return authenticated user's plugin catalog with real connection state."""
    user_id = _user_id(request)
    connected = _connected_providers(user_id)
    tools = []
    for tool in sorted(_TOOLS.values(), key=lambda item: item.name):
        configured = True
        if tool.provider == "github":
            configured = bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")
                              and os.getenv("GITHUB_REDIRECT_URI")
                              and len((os.getenv("CONNECTOR_STATE_SECRET") or os.getenv("SESSION_SECRET") or "").strip()) >= 32
                              and len((os.getenv("KZ_CONNECTOR_ENCRYPTION_KEY") or "").strip()) >= 32)
        elif tool.provider == "google":
            configured = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")
                              and len((os.getenv("CONNECTOR_STATE_SECRET") or os.getenv("SESSION_SECRET") or "").strip()) >= 32
                              and len((os.getenv("KZ_CONNECTOR_ENCRYPTION_KEY") or "").strip()) >= 32)
        elif tool.provider == "shopify":
            configured = bool(os.getenv("SHOPIFY_CLIENT_ID") and os.getenv("SHOPIFY_CLIENT_SECRET")
                              and len((os.getenv("CONNECTOR_STATE_SECRET") or os.getenv("SESSION_SECRET") or "").strip()) >= 32
                              and len((os.getenv("KZ_CONNECTOR_ENCRYPTION_KEY") or "").strip()) >= 32)
        tools.append({
            "name": tool.name,
            "provider": tool.provider,
            "description": tool.description,
            "parameters": tool.parameters,
            "risk": tool.risk,
            "available": configured and tool.provider in connected,
            "connection_status": "linked_unverified" if tool.provider in connected else ("not_configured" if not configured else "disconnected"),
        })
    return {"status": "success", "plugin_system": "registry-v1", "connection_status_note": "linked_unverified means a token record exists; provider authentication is verified only when a real tool call succeeds.", "tools": tools,
            "providers": {name: {"connected": name in connected} for name in sorted({x.provider for x in _TOOLS.values()})}}

@router.post("/execute")
def execute_plugin_tool(request: Request, payload: ToolCallRequest) -> Dict[str, Any]:
    """Execute a registered read-only tool for the currently authenticated user."""
    user_id = _user_id(request)
    tool = _TOOLS.get(payload.tool)
    if not tool:
        raise HTTPException(status_code=404, detail="Unknown tool")
    if tool.risk != "read_only":
        raise HTTPException(status_code=403, detail="This tool must use its provider approval workflow")
    connected = _connected_providers(user_id)
    if tool.provider not in connected:
        raise HTTPException(status_code=409, detail=f"{tool.provider} is not connected to this King Zarry AI account")
    _validate_arguments(tool.parameters, payload.arguments)
    try:
        result = tool.handler(user_id, payload.arguments)
        verified = bool(result.get("verified"))
        logger.info("plugin_tool_executed tool=%s user=%s verified=%s", tool.name, user_id, verified)
        return {"status": "success", "tool": tool.name, "verified": verified, "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Plugin tool failed: %s", tool.name)
        raise HTTPException(status_code=502, detail=f"Tool execution failed ({type(exc).__name__})") from exc
