#!/usr/bin/env python3
"""PostgreSQL integration and concurrency tests for the ZARRY monthly budget ledger."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import os
import unittest
import uuid
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2

from zarry_gateway.budget import BudgetDenied, PostgresMonthlyBudgetLedger

if not os.environ.get("ZARRY_TEST_DATABASE_URL"):
    raise unittest.SkipTest("ZARRY_TEST_DATABASE_URL is required for PostgreSQL integration tests")
DSN = os.environ["ZARRY_TEST_DATABASE_URL"]


@contextmanager
def test_cursor_factory():
    conn = psycopg2.connect(DSN, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    ledger = PostgresMonthlyBudgetLedger(
        cursor_factory=test_cursor_factory,
        monthly_limit_usd=Decimal("2.00"),
    )
    month = ledger._month(datetime.now(timezone.utc))
    # Isolate the test bucket from migration-contract fixtures.
    with test_cursor_factory() as cur:
        cur.execute("DELETE FROM zarry_hf_budget_reservations WHERE billing_month=%s", (month,))
        cur.execute("DELETE FROM zarry_hf_monthly_budget WHERE billing_month=%s", (month,))

    request_ids = [uuid.uuid4() for _ in range(8)]

    def reserve_one(request_id):
        try:
            return ledger.reserve(request_id, Decimal("0.30")), None
        except BudgetDenied as exc:
            return None, str(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve_one, request_ids))

    accepted = [request_ids[i] for i, (value, _) in enumerate(results) if value is not None]
    denied = [error for value, error in results if value is None]
    assert len(accepted) == 6, (len(accepted), results)
    assert len(denied) == 2, (len(denied), results)

    with test_cursor_factory() as cur:
        cur.execute(
            "SELECT reserved_micro_usd, spent_micro_usd FROM zarry_hf_monthly_budget WHERE billing_month=%s",
            (month,),
        )
        reserved, spent = cur.fetchone()
        assert (reserved, spent) == (1_800_000, 0), (reserved, spent)

    # Idempotent reserve does not double-count; settle moves reserve to spend.
    assert ledger.reserve(accepted[0], Decimal("0.30")) == 300_000
    assert ledger.settle(accepted[0], Decimal("0.25")) == 250_000
    assert ledger.settle(accepted[0], Decimal("0.25")) == 250_000

    # Releasing an active reservation returns its reserved amount.
    ledger.release(accepted[1])
    ledger.release(accepted[1])  # repeat release is safe

    with test_cursor_factory() as cur:
        cur.execute(
            "SELECT reserved_micro_usd, spent_micro_usd FROM zarry_hf_monthly_budget WHERE billing_month=%s",
            (month,),
        )
        reserved, spent = cur.fetchone()
        assert (reserved, spent) == (1_200_000, 250_000), (reserved, spent)

    # A request ID cannot be reused with a different amount or after settlement.
    try:
        ledger.reserve(accepted[0], Decimal("0.31"))
    except BudgetDenied:
        pass
    else:
        raise AssertionError("Reusing a settled request ID with a new estimate must be denied")

    print("PASS: concurrent reservations respect the $2 cap; idempotent reserve/settle and release verified.")


if __name__ == "__main__":
    main()
