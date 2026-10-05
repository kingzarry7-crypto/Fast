"""Additive unified-memory patch for the web API."""
from __future__ import annotations
import asyncio
from fastapi import HTTPException, Request

def install_web_memory_bridge(app, web_memory_adapter, require_current_user):
    from memory_link_bridge import create_web_link_code

    original_get_history = web_memory_adapter.get_history

    def get_history(self, user_id, limit=20):
        result = original_get_history(self, user_id, limit)
        if not getattr(self, "shared", None):
            return result
        try:
            canonical = self.shared.resolve_identity("web", self.web_user_id)
            if not canonical:
                return result
            shared_rows = self.shared.get_history(canonical, limit=limit)
            seen = {(str(x.get("role","")), str(x.get("content",""))) for x in result}
            merged = list(result)
            for item in shared_rows:
                key = (str(item.get("role","")), str(item.get("content","")))
                if key not in seen:
                    merged.append({
                        "role": key[0],
                        "content": key[1],
                        "created_at": str(item.get("created_at","")),
                    })
                    seen.add(key)
            return merged[-max(1, min(int(limit), 50)):]
        except Exception:
            return result

    web_memory_adapter.get_history = get_history

    @app.post("/api/memory/link-code")
    async def create_memory_link_code(request: Request):
        user_row = await asyncio.to_thread(require_current_user, request)
        user_id = str(user_row["id"] if isinstance(user_row, dict) else user_row[0])
        try:
            code = await asyncio.to_thread(create_web_link_code, user_id)
            return {
                "status": "success",
                "code": code,
                "expires_in_minutes": 10,
                "instructions": "Send this code to /link in Telegram or Discord.",
            }
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Shared memory linking is unavailable")

    print("UNIFIED_MEMORY_BRIDGE_PATCH_INSTALLED", flush=True)
