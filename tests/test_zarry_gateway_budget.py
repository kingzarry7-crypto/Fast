import unittest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from zarry_gateway.budget import (
    BudgetDenied,
    DEFAULT_MONTHLY_LIMIT_MICRO_USD,
    PostgresMonthlyBudgetLedger,
    _to_micro_usd,
)


class BudgetLedgerContractTests(unittest.TestCase):
    def test_default_cap_is_exactly_two_usd(self):
        self.assertEqual(DEFAULT_MONTHLY_LIMIT_MICRO_USD, 2_000_000)
        self.assertEqual(_to_micro_usd("2.00"), 2_000_000)

    def test_estimates_round_up_to_microdollar(self):
        self.assertEqual(_to_micro_usd("0.0000001"), 1)

    def test_unknown_zero_negative_and_nonfinite_estimates_fail_closed(self):
        for value in (None, "0", "-0.01", "NaN", "Infinity", "not-a-cost"):
            with self.subTest(value=value):
                with self.assertRaises(BudgetDenied):
                    _to_micro_usd(value)

    def test_estimate_larger_than_monthly_cap_is_rejected(self):
        ledger = PostgresMonthlyBudgetLedger(cursor_factory=None)
        with self.assertRaises(BudgetDenied):
            ledger.reserve(uuid4(), Decimal("2.01"))

    def test_month_bucket_uses_utc_month_boundary(self):
        value = datetime(2026, 11, 1, 0, 30, tzinfo=timezone.utc)
        self.assertEqual(
            PostgresMonthlyBudgetLedger._month(value).isoformat(),
            "2026-11-01",
        )

    def test_naive_datetime_is_treated_as_utc(self):
        value = datetime(2026, 10, 31, 23, 59)
        self.assertEqual(
            PostgresMonthlyBudgetLedger._month(value).isoformat(),
            "2026-10-01",
        )


if __name__ == "__main__":
    unittest.main()
