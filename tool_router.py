from __future__ import annotations

import asyncio
import copy
import hashlib
import inspect
import json
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from permissions import (
    PermissionLevel,
    Operation,
    Service,
    ApprovalStatus,
    PermissionChecker,
    PermissionRecord,
    ExactAction,
    Approval,
    _now_utc,
)


# ============================================================
# ENUMS
# ============================================================

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolStatus(str, Enum):
    SUCCESS = "success"
    BLOCKED = "blocked"
    REQUIRES_APPROVAL = "requires_approval"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    APPROVAL_INVALID = "approval_invalid"
    APPROVAL_EXPIRED = "approval_expired"
    EXECUTION_FAILED = "execution_failed"


# ============================================================
# TOOL FINGERPRINT
# ============================================================

def _tool_fingerprint(
    name: str,
    service: Service,
    operation: Operation,
    required_scope: str,
    risk_level: RiskLevel,
    requires_confirmation: bool,
    handler: Callable[..., Any],
) -> str:
    """
    Fingerprint the complete security-relevant tool definition.

    Handler object identity is included so replacing a handler invalidates
    previously issued approvals, even when the visible tool metadata remains
    unchanged.
    """
    handler_id = (
        f"{getattr(handler, '__module__', 'unknown')}."
        f"{getattr(handler, '__qualname__', str(id(handler)))}"
    )

    payload = {
        "name": name,
        "service": service.value,
        "operation": operation.value,
        "required_scope": required_scope,
        "risk_level": risk_level.value,
        "requires_confirmation": requires_confirmation,
        "handler_id": handler_id,
        "handler_obj_id": id(handler),
    }

    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


# ============================================================
# TOOL DEFINITION
# ============================================================

@dataclass
class ToolDefinition:
    name: str
    service: Service
    operation: Operation
    required_scope: str
    risk_level: RiskLevel
    requires_confirmation: bool
    handler: Callable[..., Any]
    description: str = ""
    fingerprint: str = field(init=False)
    version: int = 1

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name")

        if not isinstance(self.service, Service):
            raise ValueError("service")

        if not isinstance(self.operation, Operation):
            raise ValueError("operation")

        if not isinstance(self.required_scope, str) or not self.required_scope.strip():
            raise ValueError("required_scope")

        if not isinstance(self.risk_level, RiskLevel):
            raise ValueError("risk_level")

        if not isinstance(self.requires_confirmation, bool):
            raise ValueError("requires_confirmation")

        if not callable(self.handler):
            raise ValueError("handler")

        self.fingerprint = _tool_fingerprint(
            self.name,
            self.service,
            self.operation,
            self.required_scope,
            self.risk_level,
            self.requires_confirmation,
            self.handler,
        )


# ============================================================
# TOOL RESULT
# ============================================================

@dataclass
class ToolResult:
    success: bool
    status: ToolStatus
    tool_name: Optional[str]
    service: Optional[Service]
    operation: Optional[Operation]
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None
    simulated: bool = True
    error_code: Optional[str] = None
    target: Optional[str] = None
    exact_content: Optional[str] = None
    amount: Optional[str] = None
    fingerprint: Optional[str] = None

    def to_dict(self):
        return {
            "success": self.success,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "service": self.service.value if self.service else None,
            "operation": self.operation.value if self.operation else None,
            "message": self.message,
            "data": self.data,
            "requires_approval": self.requires_approval,
            "approval_id": self.approval_id,
            "simulated": self.simulated,
            "error_code": self.error_code,
        }


# ============================================================
# MOCK HANDLERS
# ============================================================

def _mock_base(tool_name, service, operation, **kwargs):
    safe = {}

    for key, value in kwargs.items():
        if key == "user_id":
            continue

        try:
            if isinstance(value, str):
                safe[key] = value[:200]
            else:
                rendered = str(value)
                safe[key] = value if len(rendered) <= 200 else rendered[:200]
        except Exception:
            safe[key] = "<unavailable>"

    return {
        "simulated": True,
        "tool": tool_name,
        "service": service.value,
        "operation": operation.value,
        "params": safe,
        "note": "This is a simulated result. No external action was performed.",
    }


def mock_gmail_read(user_id, **kw):
    return _mock_base("mock_gmail_read", Service.gmail, Operation.read, **kw)


def mock_gmail_draft(user_id, **kw):
    return _mock_base("mock_gmail_draft", Service.gmail, Operation.draft, **kw)


def mock_gmail_send(user_id, **kw):
    return _mock_base("mock_gmail_send", Service.gmail, Operation.send, **kw)


def mock_whatsapp_read(user_id, **kw):
    return _mock_base(
        "mock_whatsapp_read",
        Service.whatsapp_business,
        Operation.read,
        **kw,
    )


def mock_whatsapp_draft(user_id, **kw):
    return _mock_base(
        "mock_whatsapp_draft",
        Service.whatsapp_business,
        Operation.draft,
        **kw,
    )


def mock_whatsapp_send(user_id, **kw):
    return _mock_base(
        "mock_whatsapp_send",
        Service.whatsapp_business,
        Operation.send,
        **kw,
    )


def mock_social_read(user_id, **kw):
    return _mock_base(
        "mock_social_read",
        Service.social_media,
        Operation.read,
        **kw,
    )


def mock_social_draft(user_id, **kw):
    return _mock_base(
        "mock_social_draft",
        Service.social_media,
        Operation.draft,
        **kw,
    )


def mock_social_publish(user_id, **kw):
    return _mock_base(
        "mock_social_publish",
        Service.social_media,
        Operation.publish,
        **kw,
    )


def mock_store_read(user_id, **kw):
    return _mock_base(
        "mock_store_read",
        Service.store,
        Operation.read,
        **kw,
    )


def mock_store_create_order(user_id, **kw):
    return _mock_base(
        "mock_store_create_order",
        Service.store,
        Operation.purchase,
        **kw,
    )


def mock_calendar_read(user_id, **kw):
    return _mock_base(
        "mock_calendar_read",
        Service.calendar,
        Operation.read,
        **kw,
    )


def mock_calendar_create_event(user_id, **kw):
    return _mock_base(
        "mock_calendar_create_event",
        Service.calendar,
        Operation.write,
        **kw,
    )


def mock_files_read(user_id, **kw):
    return _mock_base(
        "mock_files_read",
        Service.files,
        Operation.read,
        **kw,
    )


def mock_files_modify(user_id, **kw):
    return _mock_base(
        "mock_files_modify",
        Service.files,
        Operation.modify,
        **kw,
    )


def mock_contacts_read(user_id, **kw):
    return _mock_base(
        "mock_contacts_read",
        Service.contacts,
        Operation.read,
        **kw,
    )


def mock_failing_tool(user_id, **kw):
    raise RuntimeError("simulated failure")


# ============================================================
# SECURITY PARAMETER BLOCKLIST
# ============================================================

FORBIDDEN = {
    "user_id",
    "service",
    "operation",
    "required_scope",
    "permission_level",
    "allowed_operations",
    "approval_id",
    "approval_state",
    "fingerprint",
    "tool_identity",
    "tool_name",
    "requires_confirmation",
    "risk_level",
    "handler",
    "tool_fingerprint",
    "tool_version",
}


# ============================================================
# TOOL ROUTER
# ============================================================

class ToolRouter:

    def __init__(self, permission_checker=None):
        self.checker = permission_checker or PermissionChecker()

        self._tools: Dict[str, ToolDefinition] = {}

        # Security-sensitive approval state is owned by permissions.py.
        # This context contains only immutable routing metadata.
        self._approval_context: Dict[str, MappingProxyType] = {}

        self._lock = threading.RLock()
        self._audit: List[Dict[str, Any]] = []
        self._audit_lock = threading.RLock()

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    def _audit_log(
        self,
        event,
        user_id,
        tool_name=None,
        approval_id=None,
        details=None,
    ):
        safe = {}

        if details:
            for key, value in details.items():
                if key.lower() in {
                    "password",
                    "api_key",
                    "secret",
                    "token",
                    "access_token",
                }:
                    continue

                if isinstance(value, str) and len(value) > 200:
                    safe[key] = value[:200] + "...[truncated]"
                else:
                    safe[key] = value

        with self._audit_lock:
            self._audit.append(
                {
                    "ts": _now_utc().isoformat(),
                    "event": event,
                    "user_id": user_id,
                    "tool_name": tool_name,
                    "approval_id": approval_id,
                    "details": safe,
                }
            )

    # --------------------------------------------------------
    # TOOL VALIDATION
    # --------------------------------------------------------

    def _validate_tool_definition(self, tool):
        if not isinstance(tool, ToolDefinition):
            return "invalid_tool_type"

        if not isinstance(tool.name, str) or not tool.name.strip():
            return "name"

        if not isinstance(tool.service, Service):
            return "service"

        if not isinstance(tool.operation, Operation):
            return "operation"

        if (
            not isinstance(tool.required_scope, str)
            or not tool.required_scope.strip()
        ):
            return "required_scope"

        if not isinstance(tool.risk_level, RiskLevel):
            return "risk_level"

        if not isinstance(tool.requires_confirmation, bool):
            return "requires_confirmation"

        if not callable(tool.handler):
            return "handler"

        if not isinstance(tool.fingerprint, str) or not tool.fingerprint:
            return "fingerprint"

        if not isinstance(tool.version, int) or tool.version < 1:
            return "version"

        return None

    # --------------------------------------------------------
    # JSON VALIDATION
    # --------------------------------------------------------

    def _is_json_compatible(self, value, depth=0):
        if depth > 10:
            return False

        if value is None:
            return True

        if isinstance(value, (str, int, float, bool)):
            return True

        if isinstance(value, list):
            return all(
                self._is_json_compatible(item, depth + 1)
                for item in value
            )

        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    return False

                if not self._is_json_compatible(item, depth + 1):
                    return False

            return True

        return False

    def _validate_params(self, params):
        if params is None:
            return True, ""

        if not isinstance(params, dict):
            return False, "params must be a dictionary"

        if len(params) > 50:
            return False, "too many parameters"

        for key, value in params.items():

            if not isinstance(key, str):
                return False, "parameter keys must be strings"

            if key in FORBIDDEN:
                return False, f"param '{key}' not allowed"

            if not self._is_json_compatible(value):
                return False, f"param '{key}' has unsupported type"

        return True, ""

    # --------------------------------------------------------
    # IMMUTABLE SNAPSHOT
    # --------------------------------------------------------

    def _snapshot(self, params):
        """
        Return an immutable deep snapshot.

        JSON serialization is deliberately used because tool parameters are
        restricted to JSON-compatible values.
        """
        canonical = json.dumps(
            params,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        frozen = json.loads(canonical)

        return self._freeze(frozen)

    def _freeze(self, value):
        if isinstance(value, dict):
            return MappingProxyType(
                {
                    key: self._freeze(item)
                    for key, item in value.items()
                }
            )

        if isinstance(value, list):
            return tuple(self._freeze(item) for item in value)

        return value

    def _thaw(self, value):
        if isinstance(value, MappingProxyType):
            return {
                key: self._thaw(item)
                for key, item in value.items()
            }

        if isinstance(value, tuple):
            return [self._thaw(item) for item in value]

        return value

    def _snapshot_to_json(self, snapshot):
        return json.dumps(
            self._thaw(snapshot),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def _snapshot_from_json(self, value):
        return self._freeze(json.loads(value))

    # --------------------------------------------------------
    # TOOL REGISTRATION
    # --------------------------------------------------------

    def register_tool(self, tool, replace=False):

        validation_error = self._validate_tool_definition(tool)

        if validation_error:
            return False

        if not isinstance(replace, bool):
            return False

        with self._lock:
            existing = self._tools.get(tool.name)

            if existing and not replace:
                return False

            tool.version = existing.version + 1 if existing else 1

            # Recompute after version assignment.
            tool.fingerprint = _tool_fingerprint(
                tool.name,
                tool.service,
                tool.operation,
                tool.required_scope,
                tool.risk_level,
                tool.requires_confirmation,
                tool.handler,
            )

            self._tools[tool.name] = tool

        self._audit_log(
            "tool_registered",
            "system",
            tool_name=tool.name,
            details={"replace": replace},
        )

        return True

    def get_tool(self, name):
        if not name or not isinstance(name, str):
            return None

        with self._lock:
            return self._tools.get(name)

    def list_tools(self):
        with self._lock:
            return list(self._tools.values())

    # --------------------------------------------------------
    # TOOL RESOLUTION
    # --------------------------------------------------------

    def _resolve_tool(self, name):

        with self._lock:
            tool = self._tools.get(name)

        if not tool:
            return (
                None,
                ToolResult(
                    False,
                    ToolStatus.NOT_FOUND,
                    name,
                    None,
                    None,
                    "Unknown tool",
                    error_code="tool_not_found",
                    simulated=True,
                ),
            )

        validation_error = self._validate_tool_definition(tool)

        if validation_error:
            return (
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    name,
                    tool.service,
                    tool.operation,
                    "Invalid tool",
                    error_code="invalid_tool",
                    simulated=True,
                ),
            )

        return tool, None

    # --------------------------------------------------------
    # PERMISSION CHECK
    # --------------------------------------------------------

    def _check_perm(self, user_id, tool):

        try:
            result = self.checker.check(
                user_id,
                tool.service,
                tool.operation,
                required_scope=tool.required_scope,
            )

            return result, None

        except Exception:
            self._audit_log(
                "permission_check_failure",
                user_id,
                tool_name=tool.name,
            )

            return (
                None,
                ToolResult(
                    False,
                    ToolStatus.BLOCKED,
                    tool.name,
                    tool.service,
                    tool.operation,
                    "Permission check failed",
                    error_code="permission_error",
                    simulated=True,
                ),
            )

    # --------------------------------------------------------
    # APPROVAL DECISION
    # --------------------------------------------------------

    def _requires_approval(self, tool, permission_result):

        # PermissionChecker explicitly says an action requires approval.
        if (
            not permission_result.allowed
            and permission_result.requires_approval
        ):
            return True

        # Permission is completely denied.
        if not permission_result.allowed:
            return False

        # Reads and drafts do not require confirmation merely because the
        # tool has confirmation enabled.
        if tool.operation in (Operation.read, Operation.draft):
            return False

        # A tool requiring confirmation cannot bypass it unless the
        # permission level explicitly grants automatic action.
        if tool.requires_confirmation:
            if (
                permission_result.permission_level
                != PermissionLevel.automatic_action
            ):
                return True

        return False

    # --------------------------------------------------------
    # EXACT ACTION
    # --------------------------------------------------------

    def _build_action(self, user_id, tool, snapshot):

        params = self._thaw(snapshot)

        target = str(
            params.get("to")
            or params.get("target")
            or params.get("product_id")
            or params.get("file_id")
            or params.get("title")
            or params.get("recipient")
            or "generic_target"
        )

        # Canonical exact content.
        exact_content = self._snapshot_to_json(snapshot)

        amount = (
            str(params.get("amount"))
            if params.get("amount") is not None
            else None
        )

        action = self.checker.create_exact_action(
            user_id=user_id,
            service=tool.service,
            operation=tool.operation,
            target=target,
            exact_content=exact_content,
            amount=amount,
        )

        return action, target, exact_content, amount

    # --------------------------------------------------------
    # PREPARE
    # --------------------------------------------------------

    def _prepare(self, user_id, tool_name, params):

        if (
            not user_id
            or not isinstance(user_id, str)
            or not user_id.strip()
        ):
            return (
                None,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    tool_name,
                    None,
                    None,
                    "Invalid user_id",
                    error_code="invalid_user",
                    simulated=True,
                ),
                None,
            )

        if params is None:
            params = {}

        valid, reason = self._validate_params(params)

        if not valid:
            return (
                None,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    tool_name,
                    None,
                    None,
                    reason,
                    error_code="invalid_params",
                    simulated=True,
                ),
                None,
            )

        try:
            snapshot = self._snapshot(params)
        except Exception:
            return (
                None,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    tool_name,
                    None,
                    None,
                    "Invalid parameters",
                    error_code="invalid_params",
                    simulated=True,
                ),
                None,
            )

        tool, error = self._resolve_tool(tool_name)

        if error:
            self._audit_log(
                "tool_not_found",
                user_id,
                tool_name=tool_name,
            )
            return None, None, error, None

        permission_result, permission_error = self._check_perm(
            user_id,
            tool,
        )

        if permission_error:
            return None, None, permission_error, None

        return tool, snapshot, None, permission_result

    # --------------------------------------------------------
    # READ-ONCE
    # --------------------------------------------------------

    def _consume_read_once(self, user_id, tool):

        try:
            result = self.checker.try_consume_read_once_atomic(
                user_id,
                tool.service,
                tool.operation,
                required_scope=tool.required_scope,
            )

            if not result.allowed:
                return (
                    False,
                    ToolResult(
                        False,
                        ToolStatus.PERMISSION_DENIED,
                        tool.name,
                        tool.service,
                        tool.operation,
                        "Read permission is no longer available",
                        error_code="read_once_consumed",
                        simulated=True,
                    ),
                )

            return True, None

        except Exception:
            self._audit_log(
                "read_once_failure",
                user_id,
                tool_name=tool.name,
            )

            return (
                False,
                ToolResult(
                    False,
                    ToolStatus.BLOCKED,
                    tool.name,
                    tool.service,
                    tool.operation,
                    "Read-once permission check failed",
                    error_code="read_once_error",
                    simulated=True,
                ),
            )

    # --------------------------------------------------------
    # APPROVAL CONTEXT
    # --------------------------------------------------------

    def _store_context(
        self,
        approval_id,
        user_id,
        tool,
        snapshot,
        target,
        exact_content,
        amount,
        action,
    ):

        context = {
            "tool_name": tool.name,
            "tool_service": tool.service.value,
            "tool_operation": tool.operation.value,
            "tool_required_scope": tool.required_scope,
            "tool_fingerprint": tool.fingerprint,
            "tool_version": tool.version,
            "tool_risk_level": tool.risk_level.value,
            "tool_requires_confirmation": tool.requires_confirmation,
            "tool_handler_id": id(tool.handler),
            "user_id": user_id,
            "params_json": self._snapshot_to_json(snapshot),
            "target": target,
            "exact_content": exact_content,
            "amount": amount,
            "fingerprint": action.fingerprint(),
        }

        # The context itself is immutable.
        with self._lock:
            self._approval_context[approval_id] = MappingProxyType(context)

    def _get_context(self, approval_id):
        with self._lock:
            return self._approval_context.get(approval_id)

    def _context_snapshot(self, context):
        try:
            return self._snapshot_from_json(context["params_json"])
        except Exception:
            return None

    # --------------------------------------------------------
    # APPROVED TOOL VALIDATION
    # --------------------------------------------------------

    def _validate_approved_tool(self, tool, context):

        if not tool or not context:
            return False

        checks = (
            tool.name == context.get("tool_name"),
            tool.service.value == context.get("tool_service"),
            tool.operation.value == context.get("tool_operation"),
            tool.required_scope == context.get("tool_required_scope"),
            tool.fingerprint == context.get("tool_fingerprint"),
            tool.version == context.get("tool_version"),
            tool.risk_level.value == context.get("tool_risk_level"),
            tool.requires_confirmation
            == context.get("tool_requires_confirmation"),
            id(tool.handler) == context.get("tool_handler_id"),
        )

        return all(checks)

    # --------------------------------------------------------
    # ROUTE SECURITY PIPELINE
    # --------------------------------------------------------

    def _handle(self, user_id, tool_name, params):

        tool, snapshot, error, permission_result = self._prepare(
            user_id,
            tool_name,
            params,
        )

        if error:
            return error, None, None, None

        if (
            not permission_result.allowed
            and not permission_result.requires_approval
        ):
            self._audit_log(
                "permission_denied",
                user_id,
                tool_name=tool.name,
            )

            return (
                ToolResult(
                    False,
                    ToolStatus.PERMISSION_DENIED,
                    tool.name,
                    tool.service,
                    tool.operation,
                    "Permission denied",
                    error_code="permission_denied",
                    simulated=True,
                ),
                None,
                None,
                None,
            )

        if self._requires_approval(tool, permission_result):

            try:
                action, target, exact_content, amount = self._build_action(
                    user_id,
                    tool,
                    snapshot,
                )
            except Exception:
                return (
                    ToolResult(
                        False,
                        ToolStatus.INVALID_REQUEST,
                        tool.name,
                        tool.service,
                        tool.operation,
                        "Invalid action",
                        error_code="invalid_action",
                        simulated=True,
                    ),
                    None,
                    None,
                    None,
                )

            approval_id = str(uuid.uuid4())

            approval = Approval(
                approval_id=approval_id,
                action=action,
                status=ApprovalStatus.pending,
                created_at=_now_utc(),
            )

            try:
                self.checker.approval_store.set(approval)

                self._store_context(
                    approval_id,
                    user_id,
                    tool,
                    snapshot,
                    target,
                    exact_content,
                    amount,
                    action,
                )

            except Exception:
                return (
                    ToolResult(
                        False,
                        ToolStatus.EXECUTION_FAILED,
                        tool.name,
                        tool.service,
                        tool.operation,
                        "Failed to create approval",
                        error_code="approval_creation_failed",
                        simulated=True,
                    ),
                    None,
                    None,
                    None,
                )

            self._audit_log(
                "approval_required",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
                details={"target": target[:100]},
            )

            return (
                ToolResult(
                    False,
                    ToolStatus.REQUIRES_APPROVAL,
                    tool.name,
                    tool.service,
                    tool.operation,
                    (
                        f"Service: {tool.service.value} | "
                        f"Action: {tool.operation.value} | "
                        f"Target: {target} | "
                        f"Exact content: {exact_content[:300]} | "
                        "Effect: This will execute externally. "
                        "Should I proceed?"
                    ),
                    data={
                        "approval_proposal": action.fingerprint(),
                    },
                    requires_approval=True,
                    approval_id=approval_id,
                    simulated=True,
                    target=target,
                    exact_content=exact_content,
                    amount=amount,
                    fingerprint=action.fingerprint(),
                ),
                None,
                None,
                None,
            )

        if permission_result.permission_level == PermissionLevel.read_once:

            consumed, read_error = self._consume_read_once(
                user_id,
                tool,
            )

            if not consumed:
                return read_error, None, None, None

        return None, tool, snapshot, permission_result

    # --------------------------------------------------------
    # HANDLER EXECUTION
    # --------------------------------------------------------

    def _execute_sync_handler(self, tool, user_id, snapshot):

        params = self._thaw(snapshot)

        if inspect.iscoroutinefunction(tool.handler):
            try:
                asyncio.get_running_loop()
                return None, "async_in_running_loop"
            except RuntimeError:
                pass

            return asyncio.run(
                tool.handler(
                    user_id=user_id,
                    **params,
                )
            )

        result = tool.handler(
            user_id=user_id,
            **params,
        )

        if inspect.isawaitable(result):

            try:
                asyncio.get_running_loop()
                return None, "async_in_running_loop"
            except RuntimeError:
                pass

            return asyncio.run(result), None

        return result, None

    async def _execute_async_handler(
        self,
        tool,
        user_id,
        snapshot,
    ):

        params = self._thaw(snapshot)

        if inspect.iscoroutinefunction(tool.handler):
            return (
                await tool.handler(
                    user_id=user_id,
                    **params,
                ),
                None,
            )

        result = tool.handler(
            user_id=user_id,
            **params,
        )

        if inspect.isawaitable(result):
            return await result, None

        return result, None

    # --------------------------------------------------------
    # NORMAL ROUTE
    # --------------------------------------------------------

    def route(self, user_id, tool_name, params=None):

        early, tool, snapshot, permission_result = self._handle(
            user_id,
            tool_name,
            params,
        )

        if early:
            return early

        try:
            result, async_error = self._execute_sync_handler(
                tool,
                user_id,
                snapshot,
            )

            if async_error:
                self._audit_log(
                    "execution_failed",
                    user_id,
                    tool_name=tool.name,
                )

                return ToolResult(
                    False,
                    ToolStatus.EXECUTION_FAILED,
                    tool.name,
                    tool.service,
                    tool.operation,
                    "Async tool requires route_async",
                    error_code="async_error",
                    simulated=True,
                )

            self._audit_log(
                "execution_succeeded",
                user_id,
                tool_name=tool.name,
            )

            return ToolResult(
                True,
                ToolStatus.SUCCESS,
                tool.name,
                tool.service,
                tool.operation,
                f"Executed {tool.name} (simulated)",
                data=(
                    result
                    if isinstance(result, dict)
                    else {"result": result}
                ),
                simulated=True,
            )

        except Exception:
            self._audit_log(
                "execution_failed",
                user_id,
                tool_name=tool.name,
            )

            return ToolResult(
                False,
                ToolStatus.EXECUTION_FAILED,
                tool.name,
                tool.service,
                tool.operation,
                "Tool execution failed",
                error_code="execution_failed",
                simulated=True,
            )

    # --------------------------------------------------------
    # ASYNC ROUTE
    # --------------------------------------------------------

    async def route_async(
        self,
        user_id,
        tool_name,
        params=None,
    ):

        early, tool, snapshot, permission_result = self._handle(
            user_id,
            tool_name,
            params,
        )

        if early:
            return early

        try:
            result, async_error = await self._execute_async_handler(
                tool,
                user_id,
                snapshot,
            )

            if async_error:
                return ToolResult(
                    False,
                    ToolStatus.EXECUTION_FAILED,
                    tool.name,
                    tool.service,
                    tool.operation,
                    "Async execution failed",
                    error_code="async_error",
                    simulated=True,
                )

            self._audit_log(
                "execution_succeeded",
                user_id,
                tool_name=tool.name,
            )

            return ToolResult(
                True,
                ToolStatus.SUCCESS,
                tool.name,
                tool.service,
                tool.operation,
                f"Executed {tool.name} (simulated)",
                data=(
                    result
                    if isinstance(result, dict)
                    else {"result": result}
                ),
                simulated=True,
            )

        except Exception:
            self._audit_log(
                "execution_failed",
                user_id,
                tool_name=tool.name,
            )

            return ToolResult(
                False,
                ToolStatus.EXECUTION_FAILED,
                tool.name,
                tool.service,
                tool.operation,
                "Tool execution failed",
                error_code="execution_failed",
                simulated=True,
            )

    # --------------------------------------------------------
    # COMPATIBILITY API
    # --------------------------------------------------------

    def request_action(
        self,
        user_id,
        tool_name,
        params=None,
    ):
        return self.route(user_id, tool_name, params)

    # --------------------------------------------------------
    # APPROVE
    # --------------------------------------------------------

    def approve_action(
        self,
        user_id,
        approval_id,
    ):

        if not approval_id or not isinstance(approval_id, str):
            return ToolResult(
                False,
                ToolStatus.INVALID_REQUEST,
                None,
                None,
                None,
                "Missing approval_id",
                error_code="missing_approval_id",
                simulated=True,
            )

        store = self.checker.approval_store

        store_lock = getattr(store, "_lock", self._lock)

        with store_lock:

            approval = store.get(approval_id)

            if not approval:
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    None,
                    None,
                    None,
                    "Approval not found",
                    error_code="approval_not_found",
                    approval_id=approval_id,
                    simulated=True,
                )

            context = self._get_context(approval_id)

            if approval.action.user_id != user_id:
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    None,
                    approval.action.service,
                    approval.action.operation,
                    "User mismatch",
                    error_code="user_mismatch",
                    approval_id=approval_id,
                    simulated=True,
                )

            if (
                context
                and context.get("user_id") != user_id
            ):
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    context.get("tool_name"),
                    approval.action.service,
                    approval.action.operation,
                    "User mismatch",
                    error_code="user_mismatch",
                    approval_id=approval_id,
                    simulated=True,
                )

            if approval.is_expired():
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_EXPIRED,
                    context.get("tool_name") if context else None,
                    approval.action.service,
                    approval.action.operation,
                    "Approval expired",
                    error_code="expired",
                    approval_id=approval_id,
                    simulated=True,
                )

            if approval.status != ApprovalStatus.pending:
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    context.get("tool_name") if context else None,
                    approval.action.service,
                    approval.action.operation,
                    "Approval is not pending",
                    error_code="invalid_status",
                    approval_id=approval_id,
                    simulated=True,
                )

            approval.status = ApprovalStatus.approved
            approval.approved_at = _now_utc()

            store.set(approval)

        self._audit_log(
            "approval_approved",
            user_id,
            tool_name=context.get("tool_name") if context else None,
            approval_id=approval_id,
        )

        return ToolResult(
            True,
            ToolStatus.SUCCESS,
            context.get("tool_name") if context else None,
            approval.action.service,
            approval.action.operation,
            "Approval granted",
            approval_id=approval_id,
            simulated=True,
            target=context.get("target") if context else None,
            exact_content=(
                context.get("exact_content")
                if context
                else None
            ),
            fingerprint=approval.action.fingerprint(),
        )

    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    def reject_action(
        self,
        user_id,
        approval_id,
    ):

        if not approval_id or not isinstance(approval_id, str):
            return ToolResult(
                False,
                ToolStatus.INVALID_REQUEST,
                None,
                None,
                None,
                "Missing approval_id",
                error_code="missing_approval_id",
                simulated=True,
            )

        store = self.checker.approval_store
        store_lock = getattr(store, "_lock", self._lock)

        with store_lock:

            approval = store.get(approval_id)

            if not approval:
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    None,
                    None,
                    None,
                    "Approval not found",
                    error_code="not_found",
                    approval_id=approval_id,
                    simulated=True,
                )

            context = self._get_context(approval_id)

            if (
                approval.action.user_id != user_id
                or (
                    context
                    and context.get("user_id") != user_id
                )
            ):
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    context.get("tool_name") if context else None,
                    approval.action.service,
                    approval.action.operation,
                    "User mismatch",
                    error_code="user_mismatch",
                    approval_id=approval_id,
                    simulated=True,
                )

            if approval.is_expired():
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_EXPIRED,
                    context.get("tool_name") if context else None,
                    approval.action.service,
                    approval.action.operation,
                    "Approval expired",
                    error_code="expired",
                    approval_id=approval_id,
                    simulated=True,
                )

            if approval.status != ApprovalStatus.pending:
                return ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    context.get("tool_name") if context else None,
                    approval.action.service,
                    approval.action.operation,
                    "Approval is not pending",
                    error_code="invalid_status",
                    approval_id=approval_id,
                    simulated=True,
                )

            approval.status = ApprovalStatus.rejected
            store.set(approval)

        self._audit_log(
            "approval_rejected",
            user_id,
            tool_name=context.get("tool_name") if context else None,
            approval_id=approval_id,
        )

        return ToolResult(
            True,
            ToolStatus.BLOCKED,
            context.get("tool_name") if context else None,
            approval.action.service,
            approval.action.operation,
            "Approval rejected",
            approval_id=approval_id,
            simulated=True,
        )

    # --------------------------------------------------------
    # APPROVED ACTION VALIDATION
    # --------------------------------------------------------

    def _prepare_approved_action(
        self,
        user_id,
        approval_id,
    ):

        if not approval_id or not isinstance(approval_id, str):
            return (
                None,
                None,
                None,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    None,
                    None,
                    None,
                    "Missing approval_id",
                    error_code="missing_approval_id",
                    simulated=True,
                ),
            )

        store = self.checker.approval_store

        context = self._get_context(approval_id)
        approval = store.get(approval_id)

        if not approval:
            return (
                None,
                None,
                None,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    None,
                    None,
                    None,
                    "Approval not found",
                    error_code="not_found",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if not context:
            return (
                None,
                approval,
                None,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    None,
                    approval.action.service,
                    approval.action.operation,
                    "Approval context unavailable",
                    error_code="context_not_found",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if (
            context.get("user_id") != user_id
            or approval.action.user_id != user_id
        ):
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    context.get("tool_name"),
                    approval.action.service,
                    approval.action.operation,
                    "User mismatch",
                    error_code="user_mismatch",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        with self._lock:
            current_tool = self._tools.get(
                context.get("tool_name")
            )

        if not current_tool:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.NOT_FOUND,
                    context.get("tool_name"),
                    approval.action.service,
                    approval.action.operation,
                    "Tool not found",
                    error_code="tool_not_found",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if not self._validate_tool_definition(current_tool):
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Invalid tool",
                    error_code="invalid_tool",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if not self._validate_approved_tool(
            current_tool,
            context,
        ):
            self._audit_log(
                "tool_drift",
                user_id,
                tool_name=current_tool.name,
                approval_id=approval_id,
            )

            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    current_tool.name,
                    approval.action.service,
                    approval.action.operation,
                    "Tool changed after approval",
                    error_code="tool_drift",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        try:
            permission_result = self.checker.check(
                user_id,
                current_tool.service,
                current_tool.operation,
                required_scope=current_tool.required_scope,
            )
        except Exception:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.BLOCKED,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Permission re-check failed",
                    error_code="permission_error",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if not permission_result.allowed:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.PERMISSION_DENIED,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Permission is no longer available",
                    error_code="permission_revoked",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if approval.is_expired():
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_EXPIRED,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Approval expired",
                    error_code="expired",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if approval.status != ApprovalStatus.approved:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Approval is not approved",
                    error_code="invalid_status",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        snapshot = self._context_snapshot(context)

        if snapshot is None:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Stored parameters are invalid",
                    error_code="invalid_params",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        try:
            current_action, target, exact_content, amount = (
                self._build_action(
                    user_id,
                    current_tool,
                    snapshot,
                )
            )
        except Exception:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.INVALID_REQUEST,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Stored action is invalid",
                    error_code="invalid_action",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        if (
            current_action.fingerprint()
            != context.get("fingerprint")
            or target != context.get("target")
            or exact_content != context.get("exact_content")
            or (amount or "") != (context.get("amount") or "")
        ):
            self._audit_log(
                "approval_invalid",
                user_id,
                tool_name=current_tool.name,
                approval_id=approval_id,
            )

            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Approved action no longer matches",
                    error_code="fingerprint_mismatch",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        try:
            approval_check = self.checker.check_approval(
                current_action,
                approval,
            )

            if not approval_check.allowed:
                return (
                    None,
                    approval,
                    context,
                    None,
                    ToolResult(
                        False,
                        ToolStatus.APPROVAL_INVALID,
                        current_tool.name,
                        current_tool.service,
                        current_tool.operation,
                        "Approval validation failed",
                        error_code="approval_check_failed",
                        approval_id=approval_id,
                        simulated=True,
                    ),
                )

        except Exception:
            return (
                None,
                approval,
                context,
                None,
                ToolResult(
                    False,
                    ToolStatus.APPROVAL_INVALID,
                    current_tool.name,
                    current_tool.service,
                    current_tool.operation,
                    "Approval validation failed",
                    error_code="approval_check_failed",
                    approval_id=approval_id,
                    simulated=True,
                ),
            )

        return (
            current_tool,
            approval,
            context,
            snapshot,
            None,
        )

    # --------------------------------------------------------
    # EXECUTE APPROVED ACTION
    # --------------------------------------------------------

    def execute_approved_action(
        self,
        user_id,
        approval_id,
    ):

        (
            tool,
            approval,
            context,
            snapshot,
            error,
        ) = self._prepare_approved_action(
            user_id,
            approval_id,
        )

        if error:
            return error

        store = self.checker.approval_store

        try:
            consumed, _, reason = store.consume_approval(
                approval_id,
                self.checker.create_exact_action(
                    user_id=user_id,
                    service=tool.service,
                    operation=tool.operation,
                    target=context["target"],
                    exact_content=context["exact_content"],
                    amount=context["amount"],
                ),
            )
        except Exception:
            return ToolResult(
                False,
                ToolStatus.EXECUTION_FAILED,
                tool.name,
                tool.service,
                tool.operation,
                "Approval consumption failed",
                error_code="consume_error",
                approval_id=approval_id,
                simulated=True,
            )

        if not consumed:
            self._audit_log(
                "approval_invalid",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
                details={"reason": reason},
            )

            return ToolResult(
                False,
                ToolStatus.APPROVAL_INVALID,
                tool.name,
                tool.service,
                tool.operation,
                "Approval cannot be consumed",
                error_code="already_consumed",
                approval_id=approval_id,
                simulated=True,
            )

        self._audit_log(
            "approval_consumed",
            user_id,
            tool_name=tool.name,
            approval_id=approval_id,
        )

        try:
            result, async_error = self._execute_sync_handler(
                tool,
                user_id,
                snapshot,
            )

            if async_error:
                self._audit_log(
                    "execution_failed",
                    user_id,
                    tool_name=tool.name,
                    approval_id=approval_id,
                )

                return ToolResult(
                    False,
                    ToolStatus.EXECUTION_FAILED,
                    tool.name,
                    tool.service,
                    tool.operation,
                    "Async approved tool requires execute_approved_action_async",
                    error_code="async_error",
                    approval_id=approval_id,
                    simulated=True,
                )

            self._audit_log(
                "execution_succeeded",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
            )

            return ToolResult(
                True,
                ToolStatus.SUCCESS,
                tool.name,
                tool.service,
                tool.operation,
                f"Executed approved {tool.name} (simulated)",
                data=(
                    result
                    if isinstance(result, dict)
                    else {"result": result}
                ),
                approval_id=approval_id,
                simulated=True,
                target=context["target"],
                exact_content=context["exact_content"],
                amount=context["amount"],
                fingerprint=context["fingerprint"],
            )

        except Exception:
            self._audit_log(
                "execution_failed",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
            )

            return ToolResult(
                False,
                ToolStatus.EXECUTION_FAILED,
                tool.name,
                tool.service,
                tool.operation,
                "Tool execution failed after approval consumption",
                error_code="execution_failed",
                approval_id=approval_id,
                simulated=True,
            )

    # --------------------------------------------------------
    # ASYNC APPROVED EXECUTION
    # --------------------------------------------------------

    async def execute_approved_action_async(
        self,
        user_id,
        approval_id,
    ):

        (
            tool,
            approval,
            context,
            snapshot,
            error,
        ) = self._prepare_approved_action(
            user_id,
            approval_id,
        )

        if error:
            return error

        store = self.checker.approval_store

        try:
            action = self.checker.create_exact_action(
                user_id=user_id,
                service=tool.service,
                operation=tool.operation,
                target=context["target"],
                exact_content=context["exact_content"],
                amount=context["amount"],
            )

            consumed, _, reason = store.consume_approval(
                approval_id,
                action,
            )

        except Exception:
            return ToolResult(
                False,
                ToolStatus.EXECUTION_FAILED,
                tool.name,
                tool.service,
                tool.operation,
                "Approval consumption failed",
                error_code="consume_error",
                approval_id=approval_id,
                simulated=True,
            )

        if not consumed:
            self._audit_log(
                "approval_invalid",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
                details={"reason": reason},
            )

            return ToolResult(
                False,
                ToolStatus.APPROVAL_INVALID,
                tool.name,
                tool.service,
                tool.operation,
                "Approval cannot be consumed",
                error_code="already_consumed",
                approval_id=approval_id,
                simulated=True,
            )

        self._audit_log(
            "approval_consumed",
            user_id,
            tool_name=tool.name,
            approval_id=approval_id,
        )

        try:
            result, _ = await self._execute_async_handler(
                tool,
                user_id,
                snapshot,
            )

            self._audit_log(
                "execution_succeeded",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
            )

            return ToolResult(
                True,
                ToolStatus.SUCCESS,
                tool.name,
                tool.service,
                tool.operation,
                f"Executed approved {tool.name} (simulated)",
                data=(
                    result
                    if isinstance(result, dict)
                    else {"result": result}
                ),
                approval_id=approval_id,
                simulated=True,
                target=context["target"],
                exact_content=context["exact_content"],
                amount=context["amount"],
                fingerprint=context["fingerprint"],
            )

        except Exception:
            self._audit_log(
                "execution_failed",
                user_id,
                tool_name=tool.name,
                approval_id=approval_id,
            )

            return ToolResult(
                False,
                ToolStatus.EXECUTION_FAILED,
                tool.name,
                tool.service,
                tool.operation,
                "Tool execution failed after approval consumption",
                error_code="execution_failed",
                approval_id=approval_id,
                simulated=True,
            )


# ============================================================
# DEFAULT ROUTER
# ============================================================

def create_default_router(checker=None):

    router = ToolRouter(permission_checker=checker)

    tools = [
        ToolDefinition(
            name="mock_gmail_read",
            service=Service.gmail,
            operation=Operation.read,
            required_scope="read_email",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_gmail_read,
        ),
        ToolDefinition(
            name="mock_gmail_draft",
            service=Service.gmail,
            operation=Operation.draft,
            required_scope="draft_email",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,
            handler=mock_gmail_draft,
        ),
        ToolDefinition(
            name="mock_gmail_send",
            service=Service.gmail,
            operation=Operation.send,
            required_scope="send_email",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            handler=mock_gmail_send,
        ),
        ToolDefinition(
            name="mock_whatsapp_read",
            service=Service.whatsapp_business,
            operation=Operation.read,
            required_scope="read_messages",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_whatsapp_read,
        ),
        ToolDefinition(
            name="mock_whatsapp_draft",
            service=Service.whatsapp_business,
            operation=Operation.draft,
            required_scope="draft_message",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,
            handler=mock_whatsapp_draft,
        ),
        ToolDefinition(
            name="mock_whatsapp_send",
            service=Service.whatsapp_business,
            operation=Operation.send,
            required_scope="send_message",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            handler=mock_whatsapp_send,
        ),
        ToolDefinition(
            name="mock_social_read",
            service=Service.social_media,
            operation=Operation.read,
            required_scope="read_posts",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_social_read,
        ),
        ToolDefinition(
            name="mock_social_draft",
            service=Service.social_media,
            operation=Operation.draft,
            required_scope="draft_post",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,
            handler=mock_social_draft,
        ),
        ToolDefinition(
            name="mock_social_publish",
            service=Service.social_media,
            operation=Operation.publish,
            required_scope="publish_post",
            risk_level=RiskLevel.CRITICAL,
            requires_confirmation=True,
            handler=mock_social_publish,
        ),
        ToolDefinition(
            name="mock_store_read",
            service=Service.store,
            operation=Operation.read,
            required_scope="read_products",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_store_read,
        ),
        ToolDefinition(
            name="mock_store_create_order",
            service=Service.store,
            operation=Operation.purchase,
            required_scope="create_order",
            risk_level=RiskLevel.CRITICAL,
            requires_confirmation=True,
            handler=mock_store_create_order,
        ),
        ToolDefinition(
            name="mock_calendar_read",
            service=Service.calendar,
            operation=Operation.read,
            required_scope="read_events",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_calendar_read,
        ),
        ToolDefinition(
            name="mock_calendar_create_event",
            service=Service.calendar,
            operation=Operation.write,
            required_scope="create_event",
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            handler=mock_calendar_create_event,
        ),
        ToolDefinition(
            name="mock_files_read",
            service=Service.files,
            operation=Operation.read,
            required_scope="read_files",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_files_read,
        ),
        ToolDefinition(
            name="mock_files_modify",
            service=Service.files,
            operation=Operation.modify,
            required_scope="modify_files",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            handler=mock_files_modify,
        ),
        ToolDefinition(
            name="mock_contacts_read",
            service=Service.contacts,
            operation=Operation.read,
            required_scope="read_contacts",
            risk_level=RiskLevel.LOW,
            requires_confirmation=False,
            handler=mock_contacts_read,
        ),
        ToolDefinition(
            name="mock_failing_tool",
            service=Service.other,
            operation=Operation.write,
            required_scope="write",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            handler=mock_failing_tool,
        ),
    ]

    for tool in tools:
        router.register_tool(tool)

    return router


# ============================================================
# DEFAULT API
# ============================================================

default_router = create_default_router()


def register_tool(tool, replace=False):
    return default_router.register_tool(
        tool,
        replace=replace,
    )


def get_tool(name):
    return default_router.get_tool(name)


def list_tools():
    return default_router.list_tools()


def route(user_id, tool_name, params=None):
    return default_router.route(
        user_id,
        tool_name,
        params,
    )


# ============================================================
# TEST SUITE
# ============================================================

def _run_tests():

    import threading
    from datetime import timedelta

    print(
        "Running hardened ToolRouter tests against "
        "NEW permissions.py architecture..."
    )

    checker = PermissionChecker()
    router = create_default_router(checker=checker)

    passed = 0

    def ok(condition, name):
        nonlocal passed

        if not condition:
            print(f"FAIL: {name}")
            raise AssertionError(f"Failed: {name}")

        passed += 1
        print(f"PASS: {name}")

    # 1
    result = router.route("u1", "unknown_tool")
    ok(
        result.status == ToolStatus.NOT_FOUND,
        "1 Unknown tool blocked",
    )

    # 2
    result = router.route("u2", "mock_gmail_read")
    ok(
        result.status == ToolStatus.PERMISSION_DENIED,
        "2 Missing permission blocked",
    )

    # 3
    checker.grant(
        "u3",
        Service.gmail,
        PermissionLevel.read_only,
        scopes=["read_email"],
        allowed_operations={Operation.read},
    )

    result = router.route("u3", "mock_gmail_read")

    ok(
        result.success
        and result.data.get("simulated") is True,
        "3 Read permission succeeds",
    )

    # 4
    checker.grant(
        "u4",
        Service.gmail,
        PermissionLevel.read_only,
        scopes=["read_email", "send_email"],
        allowed_operations={Operation.read, Operation.send},
    )

    result = router.route(
        "u4",
        "mock_gmail_send",
        {"to": "a@b.com"},
    )

    ok(
        result.status == ToolStatus.PERMISSION_DENIED,
        "4 Read-only cannot send",
    )

    # 5
    checker.grant(
        "u5",
        Service.gmail,
        PermissionLevel.draft_only,
        scopes=["read", "draft_email"],
        allowed_operations={Operation.read, Operation.draft},
    )

    result = router.route(
        "u5",
        "mock_gmail_draft",
        {"to": "a@b.com"},
    )

    ok(
        result.success,
        "5 Draft-only draft succeeds",
    )

    # 6
    result = router.route(
        "u5",
        "mock_gmail_send",
        {"to": "a@b.com"},
    )

    ok(
        result.status == ToolStatus.PERMISSION_DENIED,
        "6 Draft-only send blocked",
    )

    # 7
    checker.grant(
        "u7",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u7",
        "mock_gmail_send",
        {
            "to": "approval@test.com",
            "body": "Need approval",
        },
    )

    ok(
        result.status == ToolStatus.REQUIRES_APPROVAL
        and bool(result.approval_id),
        "7 action_with_approval requires approval",
    )

    # 8
    checker.grant(
        "u8",
        Service.gmail,
        PermissionLevel.automatic_action,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u8",
        "mock_gmail_send",
        {"to": "auto@test.com"},
    )

    ok(
        result.success,
        "8 automatic_action explicitly allowed succeeds",
    )

    # 9
    checker.grant(
        "u9",
        Service.gmail,
        PermissionLevel.automatic_action,
        scopes=["send_email"],
        allowed_operations=set(),
    )

    result = router.route(
        "u9",
        "mock_gmail_send",
        {"to": "auto@test.com"},
    )

    ok(
        result.status == ToolStatus.PERMISSION_DENIED,
        "9 automatic_action empty fails closed",
    )

    # 10
    checker.grant(
        "u10",
        Service.gmail,
        PermissionLevel.read_once,
        scopes=["read_email"],
        allowed_operations={Operation.read},
    )

    first = router.route(
        "u10",
        "mock_gmail_read",
    )

    ok(
        first.success,
        "10 read_once first succeeds",
    )

    # 11
    second = router.route(
        "u10",
        "mock_gmail_read",
    )

    ok(
        not second.success
        and second.status == ToolStatus.PERMISSION_DENIED,
        "11 second read_once fails",
    )

    # 12
    checker.grant(
        "u12",
        Service.gmail,
        PermissionLevel.read_once,
        scopes=["read_email"],
        allowed_operations={Operation.read},
    )

    wrong = checker.try_consume_read_once_atomic(
        "u12",
        Service.gmail,
        Operation.send,
        required_scope="read_email",
    )

    ok(
        not wrong.allowed,
        "12 failed authorization does not consume read_once",
    )

    still_works = router.route(
        "u12",
        "mock_gmail_read",
    )

    ok(
        still_works.success,
        "12b valid read_once remains available",
    )

    # 13
    checker.grant(
        "u13",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u13",
        "mock_gmail_send",
        {"to": "store@test.com"},
    )

    stored = checker.approval_store.get(
        result.approval_id
    )

    ok(
        stored is not None,
        "13 approval stored in authoritative approval store",
    )

    # 14
    approved = router.approve_action(
        "u13",
        result.approval_id,
    )

    ok(
        approved.success,
        "14 correct user can approve",
    )

    # 15
    checker.grant(
        "u15",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u15",
        "mock_gmail_send",
        {"to": "wronguser@test.com"},
    )

    wrong_user = router.approve_action(
        "other_user",
        result.approval_id,
    )

    ok(
        wrong_user.status == ToolStatus.APPROVAL_INVALID,
        "15 wrong user cannot approve",
    )

    # 16
    checker.grant(
        "u16",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u16",
        "mock_gmail_send",
        {"to": "execwrong@test.com"},
    )

    router.approve_action(
        "u16",
        result.approval_id,
    )

    wrong_exec = router.execute_approved_action(
        "other_user",
        result.approval_id,
    )

    ok(
        wrong_exec.status == ToolStatus.APPROVAL_INVALID,
        "16 wrong user cannot execute",
    )

    # 17
    checker.grant(
        "u17",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u17",
        "mock_gmail_send",
        {"to": "reject@test.com"},
    )

    router.reject_action(
        "u17",
        result.approval_id,
    )

    rejected_exec = router.execute_approved_action(
        "u17",
        result.approval_id,
    )

    ok(
        rejected_exec.status == ToolStatus.APPROVAL_INVALID,
        "17 rejected approval cannot execute",
    )

    # 18
    checker.grant(
        "u18",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u18",
        "mock_gmail_send",
        {"to": "expire@test.com"},
    )

    with checker.approval_store._lock:
        approval = checker.approval_store.get(
            result.approval_id
        )
        approval.expires_at = (
            _now_utc() - timedelta(seconds=10)
        )
        checker.approval_store.set(approval)

    expired = router.execute_approved_action(
        "u18",
        result.approval_id,
    )

    ok(
        expired.status == ToolStatus.APPROVAL_EXPIRED,
        "18 expired approval cannot execute",
    )

    # 19
    checker.grant(
        "u19",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u19",
        "mock_gmail_send",
        {
            "to": "original@test.com",
            "body": "hi",
        },
    )

    router.approve_action(
        "u19",
        result.approval_id,
    )

    context = router._get_context(
        result.approval_id
    )

    mutation_blocked = False

    try:
        context["target"] = "changed"
    except TypeError:
        mutation_blocked = True

    ok(
        mutation_blocked,
        "19 approval context is immutable",
    )

    # 20
    checker.grant(
        "u20",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    original_params = {
        "to": "immutable@test.com",
        "body": "original",
    }

    result = router.route(
        "u20",
        "mock_gmail_send",
        original_params,
    )

    original_params["to"] = "mutated@test.com"

    router.approve_action(
        "u20",
        result.approval_id,
    )

    immutable_result = router.execute_approved_action(
        "u20",
        result.approval_id,
    )

    ok(
        immutable_result.success
        and immutable_result.target == "immutable@test.com",
        "20 caller parameter mutation cannot alter approval",
    )

    # 21
    checker.grant(
        "u21",
        Service.store,
        PermissionLevel.action_with_approval,
        scopes=["create_order"],
        allowed_operations={Operation.purchase},
    )

    result = router.route(
        "u21",
        "mock_store_create_order",
        {
            "product_id": "p1",
            "amount": "10.00",
        },
    )

    router.approve_action(
        "u21",
        result.approval_id,
    )

    context = router._get_context(
        result.approval_id
    )

    try:
        context["params_json"] = "{}"
        tamper_blocked = False
    except TypeError:
        tamper_blocked = True

    ok(
        tamper_blocked,
        "21 stored action context cannot be modified",
    )

    # 22
    checker.grant(
        "u22",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u22",
        "mock_gmail_send",
        {"to": "drift@test.com"},
    )

    router.approve_action(
        "u22",
        result.approval_id,
    )

    def new_handler(user_id, **kw):
        return {
            "simulated": True,
            "tool": "replacement",
            "params": kw,
            "note": "This is a simulated result. No external action was performed.",
        }

    replacement = ToolDefinition(
        name="mock_gmail_send",
        service=Service.gmail,
        operation=Operation.send,
        required_scope="send_email",
        risk_level=RiskLevel.HIGH,
        requires_confirmation=True,
        handler=new_handler,
    )

    router.register_tool(
        replacement,
        replace=True,
    )

    drift = router.execute_approved_action(
        "u22",
        result.approval_id,
    )

    ok(
        drift.status == ToolStatus.APPROVAL_INVALID,
        "22 handler replacement invalidates old approval",
    )

    # Restore original handler
    router.register_tool(
        ToolDefinition(
            name="mock_gmail_send",
            service=Service.gmail,
            operation=Operation.send,
            required_scope="send_email",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            handler=mock_gmail_send,
        ),
        replace=True,
    )

    # 23
    checker.grant(
        "u23",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u23",
        "mock_gmail_send",
        {"to": "revoke@test.com"},
    )

    router.approve_action(
        "u23",
        result.approval_id,
    )

    checker.revoke(
        "u23",
        Service.gmail,
    )

    revoked = router.execute_approved_action(
        "u23",
        result.approval_id,
    )

    ok(
        revoked.status == ToolStatus.PERMISSION_DENIED,
        "23 revoked permission blocks approved action",
    )

    # 24
    checker.grant(
        "u24",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
        expires_in=timedelta(seconds=1),
    )

    result = router.route(
        "u24",
        "mock_gmail_send",
        {"to": "expireperm@test.com"},
    )

    router.approve_action(
        "u24",
        result.approval_id,
    )

    record = checker.store.get(
        "u24",
        Service.gmail,
    )

    record.expires_at = (
        _now_utc() - timedelta(seconds=5)
    )

    checker.store.set(record)

    expired_permission = router.execute_approved_action(
        "u24",
        result.approval_id,
    )

    ok(
        expired_permission.status
        == ToolStatus.PERMISSION_DENIED,
        "24 expired permission blocks approved action",
    )

    # 25
    checker.grant(
        "u25",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u25",
        "mock_gmail_send",
        {"to": "twice@test.com"},
    )

    router.approve_action(
        "u25",
        result.approval_id,
    )

    first_execution = router.execute_approved_action(
        "u25",
        result.approval_id,
    )

    second_execution = router.execute_approved_action(
        "u25",
        result.approval_id,
    )

    ok(
        first_execution.success
        and not second_execution.success,
        "25 same approval cannot execute twice",
    )

    # 26
    checker.grant(
        "u26",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u26",
        "mock_gmail_send",
        {"to": "concurrent@test.com"},
    )

    router.approve_action(
        "u26",
        result.approval_id,
    )

    results = []
    results_lock = threading.Lock()

    def concurrent_execute():
        execution = router.execute_approved_action(
            "u26",
            result.approval_id,
        )

        with results_lock:
            results.append(execution.success)

    threads = [
        threading.Thread(
            target=concurrent_execute
        )
        for _ in range(5)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    ok(
        sum(results) == 1,
        "26 concurrent approval consumption allows exactly one execution",
    )

    # 27
    checker.grant(
        "u27",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u27",
        "mock_gmail_send",
        {"to": "race@test.com"},
    )

    approve_results = []
    reject_results = []

    def approve_race():
        approve_results.append(
            router.approve_action(
                "u27",
                result.approval_id,
            )
        )

    def reject_race():
        reject_results.append(
            router.reject_action(
                "u27",
                result.approval_id,
            )
        )

    t1 = threading.Thread(target=approve_race)
    t2 = threading.Thread(target=reject_race)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    final = checker.approval_store.get(
        result.approval_id
    )

    successful_transitions = (
        sum(x.success for x in approve_results)
        + sum(x.success for x in reject_results)
    )

    ok(
        successful_transitions == 1
        and final.status
        in (
            ApprovalStatus.approved,
            ApprovalStatus.rejected,
        ),
        "27 concurrent approve/reject allows exactly one transition",
    )

    # 28
    checker.grant(
        "u28",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u28",
        "mock_gmail_send",
        {"to": "confirm@test.com"},
    )

    ok(
        result.status == ToolStatus.REQUIRES_APPROVAL,
        "28 requires_confirmation cannot be bypassed",
    )

    # 29
    checker.grant(
        "u29",
        Service.gmail,
        PermissionLevel.read_only,
        scopes=["read_email"],
        allowed_operations={Operation.read},
    )

    result = router.route(
        "u29",
        "mock_gmail_read",
    )

    ok(
        result.success,
        "29 read without confirmation succeeds",
    )

    # 30
    result = router.route(
        "u29",
        "mock_gmail_read",
        {
            "requires_confirmation": False,
            "operation": "read",
        },
    )

    ok(
        result.status == ToolStatus.INVALID_REQUEST,
        "30 security fields cannot be overridden",
    )

    # 31
    checker.grant(
        "u31",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u31",
        "mock_gmail_send",
        {
            "to": "nested@test.com",
            "body": "hello",
            "meta": {
                "cc": ["a@b.com"],
            },
        },
    )

    router.approve_action(
        "u31",
        result.approval_id,
    )

    result_data = router.execute_approved_action(
        "u31",
        result.approval_id,
    )

    ok(
        result_data.success
        and result_data.target == "nested@test.com",
        "31 nested parameters remain immutable",
    )

    # 32
    checker.grant(
        "u32",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u32",
        "mock_gmail_send",
        {"to": "async@test.com"},
    )

    router.approve_action(
        "u32",
        result.approval_id,
    )

    async_result = asyncio.run(
        router.execute_approved_action_async(
            "u32",
            result.approval_id,
        )
    )

    ok(
        async_result.success,
        "32 approved async execution works",
    )

    # 33
    checker.grant(
        "u33",
        Service.gmail,
        PermissionLevel.action_with_approval,
        scopes=["send_email"],
        allowed_operations={Operation.send},
    )

    result = router.route(
        "u33",
        "mock_gmail_send",
        {"to": "drift2@test.com"},
    )

    router.approve_action(
        "u33",
        result.approval_id,
    )

    original_tool = router.get_tool(
        "mock_gmail_send"
    )

    changed_handler = lambda user_id, **kw: {
        "simulated": True,
        "changed": True,
    }

    changed_tool = ToolDefinition(
        name="mock_gmail_send",
        service=original_tool.service,
        operation=original_tool.operation,
        required_scope=original_tool.required_scope,
        risk_level=original_tool.risk_level,
        requires_confirmation=original_tool.requires_confirmation,
        handler=changed_handler,
    )

    router.register_tool(
        changed_tool,
        replace=True,
    )

    drift2 = router.execute_approved_action(
        "u33",
        result.approval_id,
    )

    ok(
        drift2.status == ToolStatus.APPROVAL_INVALID,
        "33 handler drift with identical metadata invalidates approval",
    )

    # Restore
    router.register_tool(
        ToolDefinition(
            name="mock_gmail_send",
            service=Service.gmail,
            operation=Operation.send,
            required_scope="send_email",
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            handler=mock_gmail_send,
        ),
        replace=True,
    )

    # 34
    checker.grant(
        "u34",
        Service.other,
        PermissionLevel.automatic_action,
        scopes=["write"],
        allowed_operations={Operation.write},
    )

    result = router.route(
        "u34",
        "mock_failing_tool",
    )

    ok(
        result.status == ToolStatus.EXECUTION_FAILED,
        "34 handler failure returns EXECUTION_FAILED",
    )

    # 35
    checker.grant(
        "u35",
        Service.other,
        PermissionLevel.action_with_approval,
        scopes=["write"],
        allowed_operations={Operation.write},
    )

    result = router.route(
        "u35",
        "mock_failing_tool",
    )

    router.approve_action(
        "u35",
        result.approval_id,
    )

    failed_execution = router.execute_approved_action(
        "u35",
        result.approval_id,
    )

    approval_after_failure = checker.approval_store.get(
        result.approval_id
    )

    ok(
        failed_execution.status == ToolStatus.EXECUTION_FAILED,
        "35a execution failure returns EXECUTION_FAILED",
    )

    ok(
        approval_after_failure.status == ApprovalStatus.executed,
        "35b approval remains consumed after execution failure",
    )

    # 36
    ok(
        "Traceback" not in failed_execution.message
        and "RuntimeError" not in failed_execution.message,
        "36 execution exceptions are not leaked",
    )

    # 37
    async def async_mock(user_id, **kw):
        return {
            "simulated": True,
            "async": True,
            "note": "This is a simulated result. No external action was performed.",
        }

    async_tool = ToolDefinition(
        name="mock_async_tool",
        service=Service.other,
        operation=Operation.read,
        required_scope="read",
        risk_level=RiskLevel.LOW,
        requires_confirmation=False,
        handler=async_mock,
    )

    router.register_tool(async_tool)

    checker.grant(
        "u37",
        Service.other,
        PermissionLevel.read_only,
        scopes=["read"],
        allowed_operations={Operation.read},
    )

    async_result = asyncio.run(
        router.route_async(
            "u37",
            "mock_async_tool",
        )
    )

    ok(
        async_result.success
        and async_result.data.get("simulated") is True,
        "37 async handler works safely",
    )

    # 38
    class FakeTool:
        name = ""
        service = Service.gmail
        operation = Operation.read
        required_scope = "read_email"
        risk_level = RiskLevel.LOW
        requires_confirmation = False
        handler = mock_gmail_read

    ok(
        not router.register_tool(FakeTool()),
        "38 malformed registration rejected",
    )

    # 39
    checker.grant(
        "u39",
        Service.gmail,
        PermissionLevel.read_only,
        scopes=["read_email"],
        allowed_operations={Operation.read},
    )

    result = router.route(
        "u39",
        "mock_gmail_read",
    )

    ok(
        result.data.get("simulated") is True,
        "39 mock result explicitly reports simulated execution",
    )

    # 40
    ok(
        result.simulated is True
        and result.data.get("note")
        == "This is a simulated result. No external action was performed.",
        "40 no real external action is performed",
    )

    print(
        f"\nAll {passed}/40 hardened ToolRouter tests PASSED"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    _run_tests()
