"""
permissions.py - Permission and safety gate for KING ZARRY AI WEB application.

WEB ONLY - Completely independent from Telegram.
- Fail closed
- No external API calls
- No secrets stored
- Approval separate from permission
- Timezone-aware UTC timestamps
- Thread-safe RLock stores
- Strict exact scope matching
- Atomic read_once with full authorization before consumption
- allowed_operations: empty = no operations authorized (deny)
- None vs explicit empty distinction for safe defaults
- Typed ApprovalStatus
- Atomic approval consumption
- Canonical JSON fingerprint
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

# ============================================================
# ENUMS
# ============================================================

class PermissionLevel(str, Enum):
    denied = "denied"
    read_once = "read_once"
    read_session = "read_session"
    read_only = "read_only"
    draft_only = "draft_only"
    action_with_approval = "action_with_approval"
    automatic_action = "automatic_action"

class Operation(str, Enum):
    read = "read"
    draft = "draft"
    write = "write"
    delete = "delete"
    publish = "publish"
    purchase = "purchase"
    refund = "refund"
    send = "send"
    modify = "modify"

class Service(str, Enum):
    gmail = "gmail"
    whatsapp_business = "whatsapp_business"
    social_media = "social_media"
    store = "store"
    calendar = "calendar"
    files = "files"
    contacts = "contacts"
    other = "other"

class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    invalidated = "invalidated"

# ============================================================
# SCOPES
# ============================================================

SERVICE_SCOPES: Dict[Service, Set[str]] = {
    Service.gmail: {"read_email", "draft_email", "send_email", "read_emails", "read", "draft", "send"},
    Service.whatsapp_business: {"read_messages", "draft_message", "send_message", "read", "draft", "send"},
    Service.social_media: {"read_posts", "draft_post", "publish_post", "read", "draft", "publish"},
    Service.store: {"read_products", "read_orders", "create_order", "purchase", "refund", "read", "write", "modify"},
    Service.calendar: {"read_events", "create_event", "modify_event", "read", "write", "modify"},
    Service.files: {"read_files", "create_files", "modify_files", "delete_files", "read", "write", "delete", "modify"},
    Service.contacts: {"read_contacts", "read", "write"},
    Service.other: {"read", "write", "draft", "send", "publish", "delete", "modify", "purchase", "refund"},
}

OPERATION_SCOPE_HINTS: Dict[Operation, Set[str]] = {
    Operation.read: {"read", "read_email", "read_emails", "read_messages", "read_posts", "read_products", "read_orders", "read_events", "read_files", "read_contacts"},
    Operation.draft: {"draft", "draft_email", "draft_message", "draft_post", "create_order"},
    Operation.write: {"write", "create_files", "create_event", "create_order"},
    Operation.send: {"send", "send_email", "send_message"},
    Operation.publish: {"publish", "publish_post"},
    Operation.delete: {"delete", "delete_files"},
    Operation.modify: {"modify", "modify_event", "modify_files"},
    Operation.purchase: {"purchase", "create_order"},
    Operation.refund: {"refund"},
}

# ============================================================
# HELPERS
# ============================================================

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    d = _ensure_utc(dt)
    return d.isoformat() if d else None

def _normalize_operation(op: Operation | str) -> Operation:
    if isinstance(op, Operation):
        return op
    if isinstance(op, str):
        try:
            return Operation(op)
        except ValueError:
            raise ValueError(f"Invalid operation: {op}")
    raise ValueError(f"Invalid operation type: {type(op)}")

def _normalize_service(svc: Service | str) -> Service:
    if isinstance(svc, Service):
        return svc
    if isinstance(svc, str):
        try:
            return Service(svc)
        except ValueError:
            raise ValueError(f"Invalid service: {svc}")
    raise ValueError(f"Invalid service type: {type(svc)}")

def _normalize_permission_level(lvl: PermissionLevel | str) -> PermissionLevel:
    if isinstance(lvl, PermissionLevel):
        return lvl
    if isinstance(lvl, str):
        try:
            return PermissionLevel(lvl)
        except ValueError:
            raise ValueError(f"Invalid permission level: {lvl}")
    raise ValueError(f"Invalid permission level type: {type(lvl)}")

def _normalize_approval_status(s: ApprovalStatus | str) -> ApprovalStatus:
    if isinstance(s, ApprovalStatus):
        return s
    if isinstance(s, str):
        try:
            return ApprovalStatus(s)
        except ValueError:
            raise ValueError(f"Invalid approval status: {s}")
    raise ValueError(f"Invalid approval status type: {type(s)}")

def _normalize_scopes(service: Service, scopes: Optional[List[str]]) -> List[str]:
    if scopes is None:
        return []
    if not isinstance(scopes, (list, tuple, set)):
        raise ValueError("scopes must be list of strings")
    out: List[str] = []
    for s in scopes:
        if not isinstance(s, str) or not s.strip():
            raise ValueError(f"Invalid scope: {s}")
        out.append(s.strip())
    allowed = SERVICE_SCOPES.get(service, set())
    for s in out:
        if s not in allowed:
            raise ValueError(f"Invalid scope '{s}' for service '{service.value}'. Allowed: {sorted(allowed)}")
    return sorted(set(out))

def _normalize_allowed_operations(ops) -> Set[Operation]:
    if ops is None:
        return set()
    if not isinstance(ops, (set, list, tuple)):
        raise ValueError("allowed_operations must be set/list of Operations")
    res: Set[Operation] = set()
    for o in ops:
        res.add(_normalize_operation(o))
    return res

# ============================================================
# PERMISSION RECORD
# ============================================================

@dataclass
class PermissionRecord:
    user_id: str
    service: Service
    permission_level: PermissionLevel
    scopes: List[str] = field(default_factory=list)
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)
    consumed_at: Optional[datetime] = None
    allowed_operations: Set[Operation] = field(default_factory=set)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        self.service = _normalize_service(self.service)
        self.permission_level = _normalize_permission_level(self.permission_level)
        self.granted_at = _ensure_utc(self.granted_at)
        self.expires_at = _ensure_utc(self.expires_at)
        self.revoked_at = _ensure_utc(self.revoked_at)
        self.created_at = _ensure_utc(self.created_at) or _now_utc()
        self.updated_at = _ensure_utc(self.updated_at) or _now_utc()
        self.consumed_at = _ensure_utc(self.consumed_at)
        self.scopes = _normalize_scopes(self.service, self.scopes)
        self.allowed_operations = _normalize_allowed_operations(self.allowed_operations)

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return _now_utc() > self.expires_at

    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def to_dict(self, include_private: bool = False) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "service": self.service.value,
            "permission_level": self.permission_level.value,
            "scopes": self.scopes,
            "allowed_operations": sorted([o.value for o in self.allowed_operations]),
            "granted_at": _utc_iso(self.granted_at),
            "expires_at": _utc_iso(self.expires_at),
            "revoked_at": _utc_iso(self.revoked_at),
            "created_at": _utc_iso(self.created_at),
            "updated_at": _utc_iso(self.updated_at),
            "consumed_at": _utc_iso(self.consumed_at),
        }

@dataclass
class PermissionCheckResult:
    allowed: bool
    reason: str
    permission_level: Optional[PermissionLevel]
    requires_approval: bool
    service: Service
    operation: Operation
    permission_record: Optional[PermissionRecord] = None
    required_scope: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "permission_level": self.permission_level.value if self.permission_level else None,
            "requires_approval": self.requires_approval,
            "service": self.service.value,
            "operation": self.operation.value,
            "required_scope": self.required_scope,
        }

# ============================================================
# EXACT ACTION / APPROVAL
# ============================================================

@dataclass(frozen=True)
class ExactAction:
    user_id: str
    service: Service
    operation: Operation
    target: str
    exact_content: str
    amount: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(self, 'service', _normalize_service(self.service))
        object.__setattr__(self, 'operation', _normalize_operation(self.operation))
        if not self.user_id or not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("user_id required in ExactAction")
        if not self.target or not isinstance(self.target, str):
            raise ValueError("target required in ExactAction")
        if not isinstance(self.exact_content, str) or not self.exact_content.strip():
            raise ValueError("exact_content required in ExactAction")

    def fingerprint(self) -> str:
        payload = {
            "user_id": self.user_id,
            "service": self.service.value,
            "operation": self.operation.value,
            "target": self.target,
            "exact_content": self.exact_content,
            "amount": self.amount if self.amount is not None else "",
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

@dataclass
class Approval:
    approval_id: str
    action: ExactAction
    status: ApprovalStatus
    created_at: datetime = field(default_factory=_now_utc)
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        self.status = _normalize_approval_status(self.status)
        self.created_at = _ensure_utc(self.created_at) or _now_utc()
        self.approved_at = _ensure_utc(self.approved_at)
        self.executed_at = _ensure_utc(self.executed_at)
        self.expires_at = _ensure_utc(self.expires_at)

    def is_valid_for(self, action: ExactAction) -> bool:
        return self.action.fingerprint() == action.fingerprint() and self.status == ApprovalStatus.approved

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return _now_utc() > self.expires_at

@dataclass
class ApprovalCheckResult:
    allowed: bool
    reason: str
    approval: Optional[Approval] = None
    requires_approval: bool = True

# ============================================================
# STORES
# ============================================================

class PermissionStore:
    def get(self, user_id: str, service: Service) -> Optional[PermissionRecord]:
        raise NotImplementedError
    def set(self, record: PermissionRecord) -> PermissionRecord:
        raise NotImplementedError
    def revoke(self, user_id: str, service: Service) -> bool:
        raise NotImplementedError
    def list_for_user(self, user_id: str) -> List[PermissionRecord]:
        raise NotImplementedError
    def try_consume_read_once(self, user_id: str, service: Service, operation: Operation, required_scope: Optional[str]) -> Tuple[bool, Optional[PermissionRecord], str]:
        raise NotImplementedError

class InMemoryPermissionStore(PermissionStore):
    def __init__(self):
        self._store: Dict[Tuple[str, str], PermissionRecord] = {}
        self._lock = threading.RLock()

    def _key(self, user_id: str, service: Service) -> Tuple[str, str]:
        return (user_id, service.value)

    def get(self, user_id: str, service: Service) -> Optional[PermissionRecord]:
        if not user_id or not service:
            return None
        with self._lock:
            return self._store.get(self._key(user_id, service))

    def set(self, record: PermissionRecord) -> PermissionRecord:
        if not record.user_id or not record.service:
            raise ValueError("user_id and service required")
        with self._lock:
            record.updated_at = _now_utc()
            self._store[self._key(record.user_id, record.service)] = record
            return record

    def revoke(self, user_id: str, service: Service) -> bool:
        with self._lock:
            rec = self._store.get(self._key(user_id, service))
            if not rec:
                return False
            rec.revoked_at = _now_utc()
            rec.permission_level = PermissionLevel.denied
            rec.updated_at = _now_utc()
            self._store[self._key(user_id, service)] = rec
            return True

    def list_for_user(self, user_id: str) -> List[PermissionRecord]:
        with self._lock:
            return [r for (uid, _), r in self._store.items() if uid == user_id]

    def clear(self):
        with self._lock:
            self._store.clear()

    def try_consume_read_once(self, user_id: str, service: Service, operation: Operation, required_scope: Optional[str]) -> Tuple[bool, Optional[PermissionRecord], str]:
        with self._lock:
            rec = self._store.get(self._key(user_id, service))
            if rec is None:
                return False, None, f"No permission for service {service.value}"
            if rec.is_revoked():
                return False, rec, f"Permission revoked for {service.value}"
            if rec.is_expired():
                return False, rec, f"Permission expired for {service.value}"
            if rec.permission_level!= PermissionLevel.read_once:
                return False, rec, f"Permission level is not read_once, is {rec.permission_level.value}"
            if rec.is_consumed():
                return False, rec, f"read_once already consumed for {service.value}"
            if operation!= Operation.read:
                return False, rec, f"read_once only allows read, not {operation.value}"
            if not rec.allowed_operations:
                return False, rec, f"read_once with empty allowed_operations - fails closed for {operation.value}"
            if Operation.read not in rec.allowed_operations:
                return False, rec, f"read_once operation {operation.value} not explicitly allowed - allowed_operations={sorted([o.value for o in rec.allowed_operations])}"
            if required_scope:
                if required_scope not in rec.scopes:
                    return False, rec, f"Missing required scope '{required_scope}' for {service.value}"
            rec.consumed_at = _now_utc()
            rec.updated_at = _now_utc()
            self._store[self._key(user_id, service)] = rec
            return True, rec, f"read_once atomically consumed for {operation.value} on {service.value}"

class ApprovalStore:
    def get(self, approval_id: str) -> Optional[Approval]:
        raise NotImplementedError
    def set(self, approval: Approval) -> Approval:
        raise NotImplementedError
    def consume_approval(self, approval_id: str, proposed_action: ExactAction) -> Tuple[bool, Optional[Approval], str]:
        raise NotImplementedError

class InMemoryApprovalStore(ApprovalStore):
    def __init__(self):
        self._store: Dict[str, Approval] = {}
        self._lock = threading.RLock()

    def get(self, approval_id: str) -> Optional[Approval]:
        with self._lock:
            return self._store.get(approval_id)

    def set(self, approval: Approval) -> Approval:
        with self._lock:
            if not approval.approval_id:
                raise ValueError("approval_id required")
            self._store[approval.approval_id] = approval
            return approval

    def consume_approval(self, approval_id: str, proposed_action: ExactAction) -> Tuple[bool, Optional[Approval], str]:
        with self._lock:
            approval = self._store.get(approval_id)
            if approval is None:
                return False, None, "Approval not found"
            if approval.status!= ApprovalStatus.approved:
                return False, approval, f"Approval not in approved state: {approval.status.value}"
            if approval.is_expired():
                return False, approval, "Approval expired"
            if approval.action.fingerprint()!= proposed_action.fingerprint():
                return False, approval, "Approval fingerprint mismatch - target/recipient/content/amount/operation/user/service changed"
            if approval.executed_at is not None or approval.status == ApprovalStatus.executed:
                return False, approval, "Approval already executed"
            approval.status = ApprovalStatus.executed
            approval.executed_at = _now_utc()
            self._store[approval_id] = approval
            return True, approval, "Approval consumed and executed"

    def clear(self):
        with self._lock:
            self._store.clear()

# ============================================================
# PERMISSION CHECKER
# ============================================================

class PermissionChecker:
    def __init__(self, store: Optional[PermissionStore] = None, approval_store: Optional[ApprovalStore] = None):
        self.store = store or InMemoryPermissionStore()
        self.approval_store = approval_store or InMemoryApprovalStore()

    def _validate_inputs(self, user_id: str, service: Service, operation: Operation) -> Optional[str]:
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            return "invalid or missing user_id"
        if not isinstance(service, Service):
            return "invalid service"
        if not isinstance(operation, Operation):
            return "invalid operation"
        return None

    def check(self, user_id: str, service: Service | str, operation: Operation | str, required_scope: Optional[str] = None) -> PermissionCheckResult:
        try:
            svc = _normalize_service(service)
            op = _normalize_operation(operation)
        except ValueError as e:
            return PermissionCheckResult(allowed=False, reason=f"invalid enum: {e}", permission_level=None, requires_approval=False, service=Service.other, operation=Operation.read, required_scope=required_scope)
        err = self._validate_inputs(user_id, svc, op)
        if err:
            return PermissionCheckResult(allowed=False, reason=err, permission_level=None, requires_approval=False, service=svc, operation=op, required_scope=required_scope)

        rec = self.store.get(user_id, svc)
        if rec is None:
            return PermissionCheckResult(allowed=False, reason=f"No permission for service {svc.value}", permission_level=None, requires_approval=False, service=svc, operation=op, required_scope=required_scope)
        if rec.is_revoked():
            return PermissionCheckResult(allowed=False, reason=f"Permission revoked for {svc.value}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
        if rec.is_expired():
            return PermissionCheckResult(allowed=False, reason=f"Permission expired for {svc.value}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
        if rec.permission_level == PermissionLevel.denied:
            return PermissionCheckResult(allowed=False, reason=f"Permission denied for {svc.value}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
        if rec.permission_level == PermissionLevel.read_once and rec.is_consumed():
            return PermissionCheckResult(allowed=False, reason=f"read_once permission already consumed for {svc.value}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if not rec.allowed_operations:
            return PermissionCheckResult(allowed=False, reason=f"Permission with empty allowed_operations - fails closed for {op.value}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if op not in rec.allowed_operations:
            return PermissionCheckResult(allowed=False, reason=f"Operation {op.value} not in allowed_operations {sorted([o.value for o in rec.allowed_operations])}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if required_scope and required_scope not in rec.scopes:
            return PermissionCheckResult(allowed=False, reason=f"Missing required scope '{required_scope}' for {svc.value}", permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        level = rec.permission_level

        if level == PermissionLevel.read_once:
            if op == Operation.read:
                return PermissionCheckResult(allowed=True, reason=f"read_once allowed for {op.value} on {svc.value}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
            return PermissionCheckResult(allowed=False, reason=f"read_once does not authorize {op.value}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if level in (PermissionLevel.read_session, PermissionLevel.read_only):
            if op == Operation.read:
                return PermissionCheckResult(allowed=True, reason=f"{level.value} allows {op.value}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
            return PermissionCheckResult(allowed=False, reason=f"{level.value} does not authorize {op.value}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if level == PermissionLevel.draft_only:
            if op in (Operation.read, Operation.draft):
                return PermissionCheckResult(allowed=True, reason=f"draft_only allows {op.value}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
            return PermissionCheckResult(allowed=False, reason=f"draft_only does not authorize {op.value} - draft only, not send/publish/delete/etc", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if level == PermissionLevel.action_with_approval:
            if op in (Operation.read, Operation.draft):
                return PermissionCheckResult(allowed=True, reason=f"action_with_approval allows {op.value} without approval", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
            return PermissionCheckResult(allowed=False, reason=f"action_with_approval requires explicit approval for {op.value} on {svc.value}", permission_level=level, requires_approval=True, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        if level == PermissionLevel.automatic_action:
            return PermissionCheckResult(allowed=True, reason=f"automatic_action explicitly granted for {op.value} on {svc.value}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

        return PermissionCheckResult(allowed=False, reason=f"Unknown level {level}", permission_level=level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

    def try_consume_read_once_atomic(self, user_id: str, service: Service | str, operation: Operation | str = Operation.read, required_scope: Optional[str] = None) -> PermissionCheckResult:
        try:
            svc = _normalize_service(service)
            op = _normalize_operation(operation)
        except ValueError as e:
            return PermissionCheckResult(allowed=False, reason=f"invalid enum: {e}", permission_level=None, requires_approval=False, service=Service.other, operation=Operation.read, required_scope=required_scope)
        err = self._validate_inputs(user_id, svc, op)
        if err:
            return PermissionCheckResult(allowed=False, reason=err, permission_level=None, requires_approval=False, service=svc, operation=op, required_scope=required_scope)
        success, rec, reason = self.store.try_consume_read_once(user_id, svc, op, required_scope)
        if not success:
            return PermissionCheckResult(allowed=False, reason=reason, permission_level=rec.permission_level if rec else None, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)
        return PermissionCheckResult(allowed=True, reason=reason, permission_level=rec.permission_level, requires_approval=False, service=svc, operation=op, permission_record=rec, required_scope=required_scope)

    def consume_read_once(self, user_id: str, service: Service | str) -> bool:
        """
        Legacy compatibility helper. New authorization code MUST use try_consume_read_once_atomic().
        """
        try:
            svc = _normalize_service(service)
        except ValueError:
            return False
        try:
            success, _rec, _reason = self.store.try_consume_read_once(user_id, svc, Operation.read, None)
            return success
        except Exception:
            return False

    def create_exact_action(self, user_id: str, service: Service | str, operation: Operation | str, target: str, exact_content: str, amount: Optional[str] = None) -> ExactAction:
        return ExactAction(user_id=user_id, service=_normalize_service(service), operation=_normalize_operation(operation), target=target, exact_content=exact_content, amount=amount)

    def check_approval(self, proposed_action: ExactAction, approval: Optional[Approval]) -> ApprovalCheckResult:
        if approval is None:
            return ApprovalCheckResult(allowed=False, reason="No approval provided", approval=None, requires_approval=True)
        if approval.is_expired():
            return ApprovalCheckResult(allowed=False, reason="Approval expired", approval=approval, requires_approval=True)
        if approval.status!= ApprovalStatus.approved:
            return ApprovalCheckResult(allowed=False, reason=f"Approval not in approved state: {approval.status.value}", approval=approval, requires_approval=True)
        if not approval.is_valid_for(proposed_action):
            return ApprovalCheckResult(allowed=False, reason="Approval fingerprint mismatch", approval=approval, requires_approval=True)
        return ApprovalCheckResult(allowed=True, reason="Exact action approved", approval=approval, requires_approval=False)

    def grant(self, user_id: str, service: Service | str, level: PermissionLevel | str, scopes: Optional[List[str]] = None, expires_in: Optional[timedelta] = None, allowed_operations: Optional[Set[Operation] | List[Operation] | List[str] | Set[str]] = None) -> PermissionRecord:
        if not user_id or not user_id.strip():
            raise ValueError("user_id required")
        svc = _normalize_service(service)
        lvl = _normalize_permission_level(level)
        sc = _normalize_scopes(svc, scopes)

        if expires_in is not None:
            if not isinstance(expires_in, timedelta):
                raise ValueError("expires_in must be a timedelta")
            if expires_in.total_seconds() < 0:
                raise ValueError("expires_in must not be negative")

        if allowed_operations is None:
            if lvl == PermissionLevel.denied:
                ao = set()
            elif lvl == PermissionLevel.read_once:
                ao = {Operation.read}
            elif lvl == PermissionLevel.read_session:
                ao = {Operation.read}
            elif lvl == PermissionLevel.read_only:
                ao = {Operation.read}
            elif lvl == PermissionLevel.draft_only:
                ao = {Operation.read, Operation.draft}
            elif lvl == PermissionLevel.action_with_approval:
                ao = {Operation.read, Operation.draft}
            elif lvl == PermissionLevel.automatic_action:
                ao = set()
            else:
                ao = set()
        else:
            ao = _normalize_allowed_operations(allowed_operations)

        now = _now_utc()
        rec = PermissionRecord(user_id=user_id, service=svc, permission_level=lvl, scopes=sc, granted_at=now, expires_at=(now + expires_in) if expires_in else None, created_at=now, updated_at=now, allowed_operations=ao)
        return self.store.set(rec)

    def revoke(self, user_id: str, service: Service | str) -> bool:
        return self.store.revoke(user_id, _normalize_service(service))

_default_store = InMemoryPermissionStore()
_default_approval_store = InMemoryApprovalStore()
default_checker = PermissionChecker(store=_default_store, approval_store=_default_approval_store)

def check_permission(user_id: str, service: str, operation: str, required_scope: Optional[str] = None, store: Optional[PermissionStore] = None) -> PermissionCheckResult:
    checker = PermissionChecker(store=store) if store else default_checker
    return checker.check(user_id, service, operation, required_scope)

def grant_permission(user_id: str, service: str, level: str, scopes: Optional[List[str]] = None, expires_in: Optional[timedelta] = None, allowed_operations: Optional[List[str] | Set[str]] = None) -> PermissionRecord:
    return default_checker.grant(user_id, service, level, scopes, expires_in, allowed_operations=allowed_operations)

def revoke_permission(user_id: str, service: str) -> bool:
    return default_checker.revoke(user_id, service)
