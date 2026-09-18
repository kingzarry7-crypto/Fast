from __future__ import annotations

"""
web_permission_store.py

Persistent Neon PostgreSQL storage for KING ZARRY AI WEB permissions,
approvals, and security audit logs.

WEB ONLY.
This file must never read from or write to Telegram SQLite databases.

Security principles:
- Fail closed.
- Never store secrets.
- Permissions and approvals remain separate.
- Approvals are exact-action and one-time.
- Database operations use parameterized SQL.
- JSONB is used for scopes and allowed_operations.
- Approval consumption is atomic.
"""

import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from database import get_db_connection
from permissions import (
    Approval,
    ApprovalStatus,
    ExactAction,
    Operation,
    PermissionLevel,
    PermissionRecord,
    Service,
    _now_utc,
)


# ============================================================
# CONSTANTS
# ============================================================

_PERMISSION_LEVELS = {
    PermissionLevel.denied,
    PermissionLevel.read_once,
    PermissionLevel.read_session,
    PermissionLevel.read_only,
    PermissionLevel.draft_only,
    PermissionLevel.action_with_approval,
    PermissionLevel.automatic_action,
}

_APPROVAL_STATUSES = {
    ApprovalStatus.pending,
    ApprovalStatus.approved,
    ApprovalStatus.rejected,
    ApprovalStatus.executed,
}

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "api_key",
    "apikey",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "credential",
    "credentials",
    "private_key",
}


# ============================================================
# HELPERS
# ============================================================

def _utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _json_safe(value: Any) -> Any:
    """
    Convert supported Python values into JSON-safe values.

    This is deliberately conservative because these values are
    persisted into PostgreSQL JSONB.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        return _utc(value).isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, EnumLike):
        return value.value

    if isinstance(value, dict):
        result: Dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")

            result[key] = _json_safe(item)

        return result

    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]

    raise TypeError(
        f"Unsupported JSON value type: {type(value).__name__}"
    )


class EnumLike:
    """
    Internal marker used only for safe conversion.

    Enum values are handled explicitly below as well. This class
    intentionally has no runtime instances.
    """

    value: Any


def _enum_value(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)

    return str(value)


def _normalise_scopes(scopes: Iterable[str]) -> list[str]:
    if scopes is None:
        return []

    result = []

    for scope in scopes:
        if not isinstance(scope, str):
            raise ValueError("Permission scopes must be strings")

        scope = scope.strip()

        if not scope:
            raise ValueError("Permission scopes cannot contain empty values")

        if scope not in result:
            result.append(scope)

    return result


def _normalise_operations(
    operations: Iterable[Operation],
) -> list[str]:
    if operations is None:
        return []

    result = []

    for operation in operations:
        if not isinstance(operation, Operation):
            raise ValueError("allowed_operations must contain Operation values")

        value = operation.value

        if value not in result:
            result.append(value)

    return result


def _service(value: Any) -> Service:
    if isinstance(value, Service):
        return value

    return Service(str(value))


def _permission_level(value: Any) -> PermissionLevel:
    if isinstance(value, PermissionLevel):
        return value

    return PermissionLevel(str(value))


def _operation(value: Any) -> Operation:
    if isinstance(value, Operation):
        return value

    return Operation(str(value))


def _approval_status(value: Any) -> ApprovalStatus:
    if isinstance(value, ApprovalStatus):
        return value

    return ApprovalStatus(str(value))


def _contains_secret_key(value: Any) -> bool:
    """
    Recursively detect obvious secret-bearing keys.

    This is a safety check for audit details. It does not attempt
    to inspect arbitrary text for every possible secret format.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_KEYS:
                return True

            if _contains_secret_key(item):
                return True

    elif isinstance(value, (list, tuple)):
        return any(_contains_secret_key(item) for item in value)

    return False


def _safe_audit_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if details is None:
        return {}

    if not isinstance(details, dict):
        raise ValueError("Audit details must be a dictionary")

    if _contains_secret_key(details):
        raise ValueError("Audit details contain a prohibited secret field")

    safe = _json_safe(details)

    encoded = json.dumps(
        safe,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    if len(encoded) > 10000:
        raise ValueError("Audit details are too large")

    return safe


# ============================================================
# DATABASE STORE
# ============================================================

class WebPermissionStore:
    """
    Persistent permission store backed by Neon PostgreSQL.

    This class implements the storage interface expected by the
    KING ZARRY AI web permission system.
    """

    def __init__(self, connection_factory=None):
        self._connection_factory = connection_factory or get_db_connection
        self._lock = threading.RLock()

    # --------------------------------------------------------
    # CONNECTION
    # --------------------------------------------------------

    def _connection(self):
        connection = self._connection_factory()

        if connection is None:
            raise RuntimeError("Web database connection unavailable")

        return connection

    # --------------------------------------------------------
    # PERMISSIONS
    # --------------------------------------------------------

    def get(
        self,
        user_id: str,
        service: Service,
    ) -> Optional[PermissionRecord]:
        if not isinstance(user_id, str) or not user_id.strip():
            return None

        try:
            service = _service(service)
        except Exception:
            return None

        connection = None

        try:
            connection = self._connection()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        user_id,
                        service,
                        permission_level,
                        scopes,
                        allowed_operations,
                        granted_at,
                        expires_at,
                        revoked_at
                    FROM web_permissions
                    WHERE user_id = %s
                      AND service = %s
                    LIMIT 1
                    """,
                    (user_id, service.value),
                )

                row = cursor.fetchone()

            if not row:
                return None

            return self._permission_from_row(row)

        except Exception:
            return None

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def set(self, record: PermissionRecord) -> bool:
        if not isinstance(record, PermissionRecord):
            return False

        try:
            user_id = str(record.user_id).strip()
            service = _service(record.service)
            level = _permission_level(record.permission_level)

            if not user_id:
                return False

            if level not in _PERMISSION_LEVELS:
                return False

            scopes = _normalise_scopes(record.scopes)

            operations = _normalise_operations(
                getattr(record, "allowed_operations", set())
            )

            connection = self._connection()

            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO web_permissions (
                            user_id,
                            service,
                            permission_level,
                            scopes,
                            allowed_operations,
                            granted_at,
                            expires_at,
                            revoked_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s::jsonb,
                            %s::jsonb,
                            %s,
                            %s,
                            %s
                        )
                        ON CONFLICT (user_id, service)
                        DO UPDATE SET
                            permission_level = EXCLUDED.permission_level,
                            scopes = EXCLUDED.scopes,
                            allowed_operations = EXCLUDED.allowed_operations,
                            granted_at = EXCLUDED.granted_at,
                            expires_at = EXCLUDED.expires_at,
                            revoked_at = EXCLUDED.revoked_at,
                            updated_at = NOW()
                        """,
                        (
                            user_id,
                            service.value,
                            level.value,
                            json.dumps(scopes),
                            json.dumps(operations),
                            _utc(record.granted_at),
                            _utc(record.expires_at),
                            _utc(record.revoked_at),
                        ),
                    )

                connection.commit()
                return True

            except Exception:
                connection.rollback()
                return False

            finally:
                connection.close()

        except Exception:
            return False

    def revoke(
        self,
        user_id: str,
        service: Service,
    ) -> bool:
        if not isinstance(user_id, str) or not user_id.strip():
            return False

        try:
            service = _service(service)
        except Exception:
            return False

        connection = None

        try:
            connection = self._connection()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE web_permissions
                    SET
                        permission_level = %s,
                        revoked_at = NOW(),
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND service = %s
                    """,
                    (
                        PermissionLevel.denied.value,
                        user_id,
                        service.value,
                    ),
                )

                changed = cursor.rowcount > 0

            connection.commit()
            return changed

        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass

            return False

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def try_consume_read_once(
        self,
        user_id: str,
        service: Service,
        operation: Operation,
        required_scope: str,
    ) -> Tuple[bool, Optional[PermissionRecord], str]:
        """
        Atomically consume a read_once permission.

        The UPDATE itself performs the eligibility checks, so two
        concurrent requests cannot both consume the same permission.
        """
        if not isinstance(user_id, str) or not user_id.strip():
            return False, None, "invalid user"

        try:
            service = _service(service)
            operation = _operation(operation)
        except Exception:
            return False, None, "invalid service or operation"

        if operation != Operation.read:
            return False, None, "read_once only supports read"

        if not isinstance(required_scope, str) or not required_scope.strip():
            return False, None, "invalid required scope"

        connection = None

        try:
            connection = self._connection()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE web_permissions
                    SET
                        revoked_at = NOW(),
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND service = %s
                      AND permission_level = %s
                      AND revoked_at IS NULL
                      AND (
                          expires_at IS NULL
                          OR expires_at > NOW()
                      )
                      AND scopes ? %s
                      AND allowed_operations ? %s
                    RETURNING
                        user_id,
                        service,
                        permission_level,
                        scopes,
                        allowed_operations,
                        granted_at,
                        expires_at,
                        revoked_at
                    """,
                    (
                        user_id,
                        service.value,
                        PermissionLevel.read_once.value,
                        required_scope,
                        Operation.read.value,
                    ),
                )

                row = cursor.fetchone()

            if not row:
                connection.rollback()
                return False, None, "read_once permission unavailable"

            record = self._permission_from_row(row)

            connection.commit()

            return True, record, "read_once consumed"

        except Exception as exc:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass

            return False, None, f"read_once storage error: {type(exc).__name__}"

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    # --------------------------------------------------------
    # PERMISSION ROW CONVERSION
    # --------------------------------------------------------

    def _permission_from_row(self, row) -> PermissionRecord:
        (
            user_id,
            service,
            permission_level,
            scopes,
            allowed_operations,
            granted_at,
            expires_at,
            revoked_at,
        ) = row

        if isinstance(scopes, str):
            scopes = json.loads(scopes)

        if isinstance(allowed_operations, str):
            allowed_operations = json.loads(allowed_operations)

        scope_set = {
            str(scope)
            for scope in (scopes or [])
        }

        operation_set: Set[Operation] = set()

        for value in allowed_operations or []:
            try:
                operation_set.add(Operation(str(value)))
            except Exception:
                # Unknown stored operations are ignored rather than
                # being converted into executable capabilities.
                continue

        return PermissionRecord(
            user_id=str(user_id),
            service=_service(service),
            permission_level=_permission_level(permission_level),
            scopes=scope_set,
            allowed_operations=operation_set,
            granted_at=_utc(granted_at),
            expires_at=_utc(expires_at),
            revoked_at=_utc(revoked_at),
        )


# ============================================================
# APPROVAL STORE
# ============================================================

class WebApprovalStore:
    """
    Persistent approval store backed by Neon PostgreSQL.

    Approvals are separate from permissions and are consumed
    atomically exactly once.
    """

    def __init__(self, connection_factory=None):
        self._connection_factory = connection_factory or get_db_connection
        self._lock = threading.RLock()

    def _connection(self):
        connection = self._connection_factory()

        if connection is None:
            raise RuntimeError("Web database connection unavailable")

        return connection

    # --------------------------------------------------------
    # CREATE / UPDATE
    # --------------------------------------------------------

    def set(self, approval: Approval) -> bool:
        if not isinstance(approval, Approval):
            return False

        try:
            action = approval.action

            if not isinstance(action, ExactAction):
                return False

            fingerprint = action.fingerprint()

            connection = self._connection()

            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO web_approvals (
                            id,
                            user_id,
                            service,
                            operation,
                            target,
                            exact_content,
                            amount,
                            action_fingerprint,
                            status,
                            created_at,
                            approved_at,
                            rejected_at,
                            executed_at,
                            expires_at
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        ON CONFLICT (id)
                        DO UPDATE SET
                            status = EXCLUDED.status,
                            approved_at = EXCLUDED.approved_at,
                            rejected_at = EXCLUDED.rejected_at,
                            executed_at = EXCLUDED.executed_at,
                            expires_at = EXCLUDED.expires_at
                        """,
                        (
                            uuid.UUID(str(approval.approval_id)),
                            str(action.user_id),
                            action.service.value,
                            action.operation.value,
                            str(action.target),
                            str(action.exact_content),
                            action.amount,
                            fingerprint,
                            approval.status.value,
                            _utc(approval.created_at),
                            _utc(getattr(approval, "approved_at", None)),
                            _utc(getattr(approval, "rejected_at", None)),
                            _utc(getattr(approval, "executed_at", None)),
                            _utc(getattr(approval, "expires_at", None)),
                        ),
                    )

                connection.commit()
                return True

            except Exception:
                connection.rollback()
                return False

            finally:
                connection.close()

        except Exception:
            return False

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def get(self, approval_id: str) -> Optional[Approval]:
        if not isinstance(approval_id, str) or not approval_id.strip():
            return None

        try:
            approval_uuid = uuid.UUID(approval_id)
        except Exception:
            return None

        connection = None

        try:
            connection = self._connection()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        service,
                        operation,
                        target,
                        exact_content,
                        amount,
                        action_fingerprint,
                        status,
                        created_at,
                        approved_at,
                        rejected_at,
                        executed_at,
                        expires_at
                    FROM web_approvals
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (approval_uuid,),
                )

                row = cursor.fetchone()

            if not row:
                return None

            return self._approval_from_row(row)

        except Exception:
            return None

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    # --------------------------------------------------------
    # ATOMIC CONSUMPTION
    # --------------------------------------------------------

    def consume_approval(
        self,
        approval_id: str,
        action: ExactAction,
    ) -> Tuple[bool, Optional[Approval], str]:
        """
        Atomically consume an approved action.

        PostgreSQL performs the state transition:

            approved -> executed

        only when:
        - the approval exists
        - the fingerprint matches
        - the user/action matches
        - the approval is not expired
        - the current state is approved

        This prevents double execution under concurrent requests.
        """
        if not isinstance(approval_id, str) or not approval_id.strip():
            return False, None, "invalid approval id"

        if not isinstance(action, ExactAction):
            return False, None, "invalid action"

        try:
            approval_uuid = uuid.UUID(approval_id)
        except Exception:
            return False, None, "invalid approval id"

        fingerprint = action.fingerprint()

        connection = None

        try:
            connection = self._connection()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE web_approvals
                    SET
                        status = %s,
                        executed_at = NOW()
                    WHERE id = %s
                      AND user_id = %s
                      AND service = %s
                      AND operation = %s
                      AND target = %s
                      AND exact_content = %s
                      AND action_fingerprint = %s
                      AND status = %s
                      AND (
                          expires_at IS NULL
                          OR expires_at > NOW()
                      )
                    RETURNING
                        id,
                        user_id,
                        service,
                        operation,
                        target,
                        exact_content,
                        amount,
                        action_fingerprint,
                        status,
                        created_at,
                        approved_at,
                        rejected_at,
                        executed_at,
                        expires_at
                    """,
                    (
                        ApprovalStatus.executed.value,
                        approval_uuid,
                        str(action.user_id),
                        action.service.value,
                        action.operation.value,
                        str(action.target),
                        str(action.exact_content),
                        fingerprint,
                        ApprovalStatus.approved.value,
                    ),
                )

                row = cursor.fetchone()

            if not row:
                connection.rollback()
                return False, None, "approval unavailable, expired, consumed, or fingerprint mismatch"

            approval = self._approval_from_row(row)

            connection.commit()

            return True, approval, "approval consumed"

        except Exception as exc:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass

            return False, None, f"approval storage error: {type(exc).__name__}"

        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    # --------------------------------------------------------
    # APPROVAL ROW CONVERSION
    # --------------------------------------------------------

    def _approval_from_row(self, row) -> Approval:
        (
            approval_id,
            user_id,
            service,
            operation,
            target,
            exact_content,
            amount,
            stored_fingerprint,
            status,
            created_at,
            approved_at,
            rejected_at,
            executed_at,
            expires_at,
        ) = row

        action = ExactAction(
            user_id=str(user_id),
            service=_service(service),
            operation=_operation(operation),
            target=str(target),
            exact_content=str(exact_content),
            amount=amount,
        )

        # Never trust the database fingerprint blindly.
        # The canonical action must produce the same fingerprint.
        calculated_fingerprint = action.fingerprint()

        if calculated_fingerprint != str(stored_fingerprint):
            raise ValueError("Stored approval fingerprint mismatch")

        return Approval(
            approval_id=str(approval_id),
            action=action,
            status=_approval_status(status),
            created_at=_utc(created_at),
            approved_at=_utc(approved_at),
            rejected_at=_utc(rejected_at),
            executed_at=_utc(executed_at),
            expires_at=_utc(expires_at),
        )


# ============================================================
# AUDIT STORE
# ============================================================

class WebAuditLogStore:
    """
    Persistent Neon audit log.

    Only security metadata should be written here.
    Private message bodies, passwords, tokens and credentials
    must never be placed into audit details.
    """

    def __init__(self, connection_factory=None):
        self._connection_factory = connection_factory or get_db_connection

    def _connection(self):
        connection = self._connection_factory()

        if connection is None:
            raise RuntimeError("Web database connection unavailable")

        return connection

    def write(
        self,
        event: str,
        user_id: Optional[str] = None,
        service: Optional[Service] = None,
        tool_name: Optional[str] = None,
        approval_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not isinstance(event, str) or not event.strip():
            return False

        if len(event) > 100:
            return False

        if tool_name is not None:
            if not isinstance(tool_name, str) or len(tool_name) > 255:
                return False

        try:
            safe_details = _safe_audit_details(details)

            service_value = None

            if service is not None:
                service_value = _service(service).value

            approval_uuid = None

            if approval_id is not None:
                approval_uuid = uuid.UUID(str(approval_id))

            connection = self._connection()

            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO web_audit_logs (
                            user_id,
                            event,
                            service,
                            tool_name,
                            approval_id,
                            details
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s::jsonb
                        )
                        """,
                        (
                            user_id,
                            event.strip(),
                            service_value,
                            tool_name,
                            approval_uuid,
                            json.dumps(
                                safe_details,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        ),
                    )

                connection.commit()
                return True

            except Exception:
                connection.rollback()
                return False

            finally:
                connection.close()

        except Exception:
            return False


# ============================================================
# COMBINED WEB SECURITY STORE
# ============================================================

class WebSecurityStore:
    """
    Convenience container for all persistent web security stores.

    This is intentionally separate from Telegram persistence.
    """

    def __init__(self, connection_factory=None):
        self.permissions = WebPermissionStore(connection_factory)
        self.approvals = WebApprovalStore(connection_factory)
        self.audit = WebAuditLogStore(connection_factory)


# ============================================================
# DEFAULT INSTANCES
# ============================================================

default_web_permission_store = WebPermissionStore()
default_web_approval_store = WebApprovalStore()
default_web_audit_store = WebAuditLogStore()

default_web_security_store = WebSecurityStore()


# ============================================================
# HEALTH CHECK
# ============================================================

def check_web_security_database() -> Dict[str, Any]:
    """
    Verify that the three security tables are reachable.

    This does not modify any data.
    """
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    to_regclass('public.web_permissions'),
                    to_regclass('public.web_approvals'),
                    to_regclass('public.web_audit_logs')
                """
            )

            row = cursor.fetchone()

        permissions_table = row[0] is not None
        approvals_table = row[1] is not None
        audit_table = row[2] is not None

        healthy = (
            permissions_table
            and approvals_table
            and audit_table
        )

        return {
            "healthy": healthy,
            "web_permissions": permissions_table,
            "web_approvals": approvals_table,
            "web_audit_logs": audit_table,
            "web_only": True,
            "message": (
                "Web security database ready"
                if healthy
                else "One or more web security tables are missing"
            ),
        }

    except Exception as exc:
        return {
            "healthy": False,
            "web_permissions": False,
            "web_approvals": False,
            "web_audit_logs": False,
            "web_only": True,
            "message": f"Database health check failed: {type(exc).__name__}",
        }

    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


# ============================================================
# BASIC SELF TEST
# ============================================================

def _run_tests():
    """
    Lightweight structural tests.

    These tests do not require external services and do not
    modify Neon.
    """
    print("Running web_permission_store structural tests...")

    assert callable(default_web_permission_store.get)
    assert callable(default_web_permission_store.set)
    assert callable(default_web_permission_store.revoke)
    assert callable(default_web_permission_store.try_consume_read_once)

    assert callable(default_web_approval_store.get)
    assert callable(default_web_approval_store.set)
    assert callable(default_web_approval_store.consume_approval)

    assert callable(default_web_audit_store.write)

    scopes = _normalise_scopes(
        ["read_email", "read_email", "draft_email"]
    )

    assert scopes == [
        "read_email",
        "draft_email",
    ]

    operations = _normalise_operations(
        {
            Operation.read,
            Operation.send,
        }
    )

    assert set(operations) == {
        Operation.read.value,
        Operation.send.value,
    }

    safe = _safe_audit_details(
        {
            "reason": "permission_granted",
            "service": "gmail",
        }
    )

    assert safe["reason"] == "permission_granted"

    blocked = False

    try:
        _safe_audit_details(
            {
                "token": "DO_NOT_STORE"
            }
        )
    except ValueError:
        blocked = True

    assert blocked

    print("All web_permission_store structural tests PASSED")


if __name__ == "__main__":
    _run_tests()
