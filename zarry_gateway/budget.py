"""Atomic monthly paid-inference budget ledger (USD microdollars)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from uuid import UUID

from database import get_db_cursor

DEFAULT_MONTHLY_LIMIT_MICRO_USD = 2_000_000  # $2.00


class BudgetDenied(RuntimeError):
    pass


class BudgetLedgerError(RuntimeError):
    pass


def _to_micro_usd(value) -> int:
    if value is None:
        raise BudgetDenied("A verified cost estimate is required")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise BudgetDenied("Cost estimate is invalid")
    if not amount.is_finite() or amount <= 0:
        raise BudgetDenied("Cost estimate must be a positive finite amount")
    return int((amount * Decimal(1_000_000)).to_integral_value(rounding=ROUND_CEILING))


def _row_value(row, key, index):
    return row.get(key) if isinstance(row, dict) else row[index]


class PostgresMonthlyBudgetLedger:
    """Concurrency-safe $2/month cap for gateway-routed paid HF inference.

    Unknown costs fail closed. A reservation must be settled or released after
    provider completion. This is not an account-wide Hugging Face billing cap.
    """

    def __init__(self, cursor_factory=get_db_cursor,
                 monthly_limit_usd=Decimal("2.00")):
        self.cursor_factory = cursor_factory
        self.limit_micro_usd = _to_micro_usd(monthly_limit_usd)

    @staticmethod
    def _month(now=None) -> date:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)
        return date(current.year, current.month, 1)

    def reserve(self, request_id: UUID, estimated_cost_usd, now=None) -> int:
        estimate = _to_micro_usd(estimated_cost_usd)
        if estimate > self.limit_micro_usd:
            raise BudgetDenied("Request estimate exceeds the monthly budget")
        month = self._month(now)
        with self.cursor_factory() as cur:
            # Lock any existing reservation first, matching settle/release lock order.
            cur.execute(
                "SELECT billing_month, reserved_micro_usd, status FROM "
                "zarry_hf_budget_reservations WHERE request_id=%s FOR UPDATE",
                (str(request_id),),
            )
            existing = cur.fetchone()
            if existing:
                same_month = _row_value(existing, "billing_month", 0) == month
                same_estimate = int(_row_value(existing, "reserved_micro_usd", 1)) == estimate
                if same_month and same_estimate and _row_value(existing, "status", 2) == "reserved":
                    return estimate
                raise BudgetDenied("Request ID has already been used")
            cur.execute(
                """INSERT INTO zarry_hf_monthly_budget
                   (billing_month, limit_micro_usd)
                   VALUES (%s, %s) ON CONFLICT (billing_month) DO NOTHING""",
                (month, self.limit_micro_usd),
            )
            cur.execute(
                "SELECT limit_micro_usd, reserved_micro_usd, spent_micro_usd "
                "FROM zarry_hf_monthly_budget WHERE billing_month=%s FOR UPDATE",
                (month,),
            )
            bucket = cur.fetchone()
            if not bucket:
                raise BudgetLedgerError("Monthly budget bucket could not be locked")
            # Recheck after taking the bucket lock: another request with the same
            # id may have inserted while this transaction waited.
            cur.execute(
                "SELECT billing_month, reserved_micro_usd, status FROM "
                "zarry_hf_budget_reservations WHERE request_id=%s FOR UPDATE",
                (str(request_id),),
            )
            existing = cur.fetchone()
            if existing:
                same_month = _row_value(existing, "billing_month", 0) == month
                same_estimate = int(_row_value(existing, "reserved_micro_usd", 1)) == estimate
                if same_month and same_estimate and _row_value(existing, "status", 2) == "reserved":
                    return estimate
                raise BudgetDenied("Request ID has already been used")
            limit_value = int(_row_value(bucket, "limit_micro_usd", 0))
            reserved = int(_row_value(bucket, "reserved_micro_usd", 1))
            spent = int(_row_value(bucket, "spent_micro_usd", 2))
            if reserved + spent + estimate > min(limit_value, self.limit_micro_usd):
                raise BudgetDenied("Monthly paid-inference budget exhausted")
            cur.execute(
                """UPDATE zarry_hf_monthly_budget
                   SET reserved_micro_usd=reserved_micro_usd+%s, updated_at=NOW()
                   WHERE billing_month=%s""",
                (estimate, month),
            )
            cur.execute(
                """INSERT INTO zarry_hf_budget_reservations
                   (request_id, billing_month, reserved_micro_usd, status)
                   VALUES (%s, %s, %s, 'reserved')""",
                (str(request_id), month, estimate),
            )
        return estimate

    def settle(self, request_id: UUID, actual_cost_usd) -> int:
        if actual_cost_usd is None:
            raise BudgetDenied("A verified actual provider cost is required to settle")
        try:
            actual_decimal = Decimal(str(actual_cost_usd))
        except (InvalidOperation, ValueError):
            raise BudgetDenied("Actual provider cost is invalid")
        if not actual_decimal.is_finite() or actual_decimal < 0:
            raise BudgetDenied("Actual provider cost must be finite and non-negative")
        actual = int((actual_decimal * Decimal(1_000_000)).to_integral_value(rounding=ROUND_CEILING))
        with self.cursor_factory() as cur:
            cur.execute(
                "SELECT billing_month, reserved_micro_usd, status, settled_micro_usd FROM "
                "zarry_hf_budget_reservations WHERE request_id=%s FOR UPDATE",
                (str(request_id),),
            )
            reservation = cur.fetchone()
            if not reservation:
                raise BudgetLedgerError("Budget reservation not found")
            month = _row_value(reservation, "billing_month", 0)
            reserved = int(_row_value(reservation, "reserved_micro_usd", 1))
            status = _row_value(reservation, "status", 2)
            if status == "settled":
                if actual == _row_value(reservation, "settled_micro_usd", 3):
                    return actual
                raise BudgetLedgerError("Reservation was already settled differently")
            if status != "reserved":
                raise BudgetLedgerError("Reservation is no longer active")
            cur.execute(
                "SELECT limit_micro_usd, reserved_micro_usd, spent_micro_usd "
                "FROM zarry_hf_monthly_budget WHERE billing_month=%s FOR UPDATE",
                (month,),
            )
            bucket = cur.fetchone()
            if not bucket:
                raise BudgetLedgerError("Monthly budget bucket not found")
            limit_value = int(_row_value(bucket, "limit_micro_usd", 0))
            bucket_reserved = int(_row_value(bucket, "reserved_micro_usd", 1))
            spent = int(_row_value(bucket, "spent_micro_usd", 2))
            if actual > reserved and spent + bucket_reserved - reserved + actual > limit_value:
                raise BudgetDenied("Actual provider cost exceeds remaining monthly budget")
            cur.execute(
                """UPDATE zarry_hf_monthly_budget SET
                   reserved_micro_usd=reserved_micro_usd-%s,
                   spent_micro_usd=spent_micro_usd+%s, updated_at=NOW()
                   WHERE billing_month=%s""",
                (reserved, actual, month),
            )
            cur.execute(
                """UPDATE zarry_hf_budget_reservations SET
                   settled_micro_usd=%s, status='settled', updated_at=NOW()
                   WHERE request_id=%s""",
                (actual, str(request_id)),
            )
        return actual

    def release(self, request_id: UUID) -> None:
        with self.cursor_factory() as cur:
            cur.execute(
                "SELECT billing_month, reserved_micro_usd, status FROM "
                "zarry_hf_budget_reservations WHERE request_id=%s FOR UPDATE",
                (str(request_id),),
            )
            reservation = cur.fetchone()
            if not reservation:
                return
            month = _row_value(reservation, "billing_month", 0)
            reserved = int(_row_value(reservation, "reserved_micro_usd", 1))
            status = _row_value(reservation, "status", 2)
            if status != "reserved":
                return
            cur.execute(
                """UPDATE zarry_hf_monthly_budget SET
                   reserved_micro_usd=reserved_micro_usd-%s, updated_at=NOW()
                   WHERE billing_month=%s""",
                (reserved, month),
            )
            cur.execute(
                """UPDATE zarry_hf_budget_reservations SET status='released',
                   updated_at=NOW() WHERE request_id=%s""",
                (str(request_id),),
            )
