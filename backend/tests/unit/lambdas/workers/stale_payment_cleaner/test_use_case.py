from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.workers.stale_payment_cleaner.use_case import CleanStalePaymentsUseCase

_NOW = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)


class FakePaymentRepository:
    def __init__(self, payments: list[Payment]) -> None:
        self.payments = payments
        self.cancelled: list[str] = []
        self.skipped: set[str] = set()
        self.raises: set[str] = set()

    def list_stale_open_payments(self, *, cutoff: datetime) -> list[Payment]:
        return [
            payment
            for payment in self.payments
            if payment.status in {"CREATED", "PENDING"} and payment.created_at <= cutoff
        ]

    def cancel_stale_open_payment(self, *, order_id: str, cutoff: datetime) -> bool:
        if order_id in self.raises:
            raise RuntimeError("boom")
        if order_id in self.skipped:
            return False
        self.cancelled.append(order_id)
        return True


def _payment(order_id: str, *, status: str = "CREATED", age_minutes: int = 180) -> Payment:
    return Payment(
        order_id=order_id,
        tenant_id=None,
        plan_id="plan-1",
        amount="10.00",
        currency="USD",
        status=status,
        created_at=_NOW - timedelta(minutes=age_minutes),
    )


class CleanStalePaymentsUseCaseTests(unittest.TestCase):
    def test_cancels_created_and_pending_payments_older_than_grace(self) -> None:
        repo = FakePaymentRepository(
            [
                _payment("CREATED-OLD", status="CREATED", age_minutes=1500),
                _payment("PENDING-OLD", status="PENDING", age_minutes=1500),
                _payment("CREATED-NEW", status="CREATED", age_minutes=10),
                _payment("PAID-OLD", status="PAID", age_minutes=1500),
            ]
        )

        result = CleanStalePaymentsUseCase(repo, now=_NOW, grace_minutes=1440).execute()

        self.assertEqual(result.candidates, 2)
        self.assertEqual(result.cancelled, 2)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)
        self.assertEqual(repo.cancelled, ["CREATED-OLD", "PENDING-OLD"])

    def test_counts_conditional_skip_without_error(self) -> None:
        repo = FakePaymentRepository([_payment("PENDING-OLD", status="PENDING", age_minutes=1500)])
        repo.skipped.add("PENDING-OLD")

        result = CleanStalePaymentsUseCase(repo, now=_NOW, grace_minutes=1440).execute()

        self.assertEqual(result.candidates, 1)
        self.assertEqual(result.cancelled, 0)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.errors, 0)

    def test_continues_after_cancel_error(self) -> None:
        repo = FakePaymentRepository(
            [
                _payment("ERR", status="CREATED", age_minutes=1500),
                _payment("OK", status="PENDING", age_minutes=1500),
            ]
        )
        repo.raises.add("ERR")

        result = CleanStalePaymentsUseCase(repo, now=_NOW, grace_minutes=1440).execute()

        self.assertEqual(result.candidates, 2)
        self.assertEqual(result.cancelled, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 1)
        self.assertEqual(repo.cancelled, ["OK"])


if __name__ == "__main__":
    unittest.main()
