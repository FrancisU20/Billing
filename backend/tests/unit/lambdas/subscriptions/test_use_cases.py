from __future__ import annotations

import unittest
import urllib.error
from decimal import Decimal

from lambdas.subscriptions.domain.commands import CapturePaymentCommand, CreatePaymentCommand
from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import (
    FreePlanPaymentError,
    PaymentAlreadyCapturedError,
    PaymentCaptureError,
    PaymentCreationError,
    PaymentNotFoundError,
)
from lambdas.subscriptions.domain.repositories.i_paypal_client import (
    IPayPalClient,
    PayPalCaptureResult,
    PayPalOrderResult,
)
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from lambdas.subscriptions.use_cases.capture_payment import CapturePaymentUseCase
from lambdas.subscriptions.use_cases.create_payment import CreatePaymentUseCase
from lambdas.subscriptions.use_cases.get_payment import GetPaymentUseCase

# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakePlanCatalog(IPlanCatalog):
    def __init__(
        self,
        *,
        monthly_price: Decimal = Decimal("5.99"),
        annual_price: Decimal = Decimal("57.00"),
        limit_cycle: str = "month",
        is_free: bool = False,
    ) -> None:
        self._monthly = monthly_price
        self._annual = annual_price
        self._cycle = limit_cycle
        self._free = is_free

    def get(self, plan_id: str) -> PlanSummary:
        return PlanSummary(
            id=plan_id,
            monthly_price=self._monthly,
            annual_price=self._annual,
            limit_cycle=self._cycle,
            is_free=self._free,
        )


class FakePayPalClient(IPayPalClient):
    def __init__(
        self,
        *,
        order_id: str = "ORDER-123",
        payer_id: str = "PAYER-456",
        payer_email: str | None = "payer@example.com",
        create_raises: Exception | None = None,
        capture_raises: Exception | None = None,
    ) -> None:
        self._order_id = order_id
        self._payer_id = payer_id
        self._payer_email = payer_email
        self._create_raises = create_raises
        self._capture_raises = capture_raises
        self.create_calls: list[tuple[str, str]] = []
        self.capture_calls: list[str] = []

    def create_order(self, amount: str, currency: str) -> PayPalOrderResult:
        self.create_calls.append((amount, currency))
        if self._create_raises:
            raise self._create_raises
        return PayPalOrderResult(order_id=self._order_id)

    def capture_order(self, order_id: str) -> PayPalCaptureResult:
        self.capture_calls.append(order_id)
        if self._capture_raises:
            raise self._capture_raises
        return PayPalCaptureResult(
            order_id=order_id,
            status="COMPLETED",
            payer_id=self._payer_id,
            payer_email=self._payer_email,
        )


class FakePaymentRepository:
    def __init__(self) -> None:
        self._store: dict[str, Payment] = {}
        self.saved: list[Payment] = []

    def save(self, payment: Payment) -> None:
        self._store[payment.order_id] = payment
        self.saved.append(payment)

    def get_by_order_id(self, order_id: str) -> Payment:
        if order_id not in self._store:
            raise PaymentNotFoundError()
        return self._store[order_id]


# ── CreatePaymentUseCase ──────────────────────────────────────────────────────


class CreatePaymentUseCaseTests(unittest.TestCase):
    def _use_case(self, catalog=None, paypal=None, repo=None):
        return CreatePaymentUseCase(
            plan_catalog=catalog or FakePlanCatalog(),
            paypal=paypal or FakePayPalClient(),
            payment_repo=repo or FakePaymentRepository(),
        )

    def test_creates_order_and_persists_payment(self) -> None:
        repo = FakePaymentRepository()
        paypal = FakePayPalClient(order_id="ORD-1")
        result = self._use_case(paypal=paypal, repo=repo).execute(
            CreatePaymentCommand(plan_id="plan-abc")
        )
        self.assertEqual(result.order_id, "ORD-1")
        self.assertEqual(result.amount, "5.99")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(len(repo.saved), 1)
        self.assertEqual(repo.saved[0].status, "CREATED")

    def test_uses_annual_price_for_year_cycle(self) -> None:
        catalog = FakePlanCatalog(
            monthly_price=Decimal("5.99"),
            annual_price=Decimal("57.00"),
            limit_cycle="year",
        )
        paypal = FakePayPalClient()
        repo = FakePaymentRepository()
        result = self._use_case(catalog=catalog, paypal=paypal, repo=repo).execute(
            CreatePaymentCommand(plan_id="plan-y")
        )
        self.assertEqual(result.amount, "57.00")
        self.assertEqual(paypal.create_calls[0][0], "57.00")

    def test_raises_for_free_plan(self) -> None:
        catalog = FakePlanCatalog(
            monthly_price=Decimal("0.00"),
            annual_price=Decimal("0.00"),
            is_free=True,
        )
        with self.assertRaises(FreePlanPaymentError):
            self._use_case(catalog=catalog).execute(CreatePaymentCommand(plan_id="free"))

    def test_raises_payment_creation_error_on_paypal_http_error(self) -> None:
        paypal = FakePayPalClient(
            create_raises=urllib.error.HTTPError(None, 500, "Server Error", {}, None)
        )
        with self.assertRaises(PaymentCreationError):
            self._use_case(paypal=paypal).execute(CreatePaymentCommand(plan_id="plan-x"))

    def test_raises_payment_creation_error_on_network_error(self) -> None:
        paypal = FakePayPalClient(
            create_raises=urllib.error.URLError("Connection refused")
        )
        with self.assertRaises(PaymentCreationError):
            self._use_case(paypal=paypal).execute(CreatePaymentCommand(plan_id="plan-x"))

    def test_payment_stored_with_plan_id(self) -> None:
        repo = FakePaymentRepository()
        self._use_case(repo=repo).execute(CreatePaymentCommand(plan_id="plan-z"))
        self.assertEqual(repo.saved[0].plan_id, "plan-z")


# ── CapturePaymentUseCase ─────────────────────────────────────────────────────


class CapturePaymentUseCaseTests(unittest.TestCase):
    def _repo_with_payment(self, order_id: str = "ORD-1") -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id="",
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status="CREATED",
            )
        )
        return repo

    def _use_case(self, paypal=None, repo=None):
        return CapturePaymentUseCase(
            paypal=paypal or FakePayPalClient(),
            payment_repo=repo or self._repo_with_payment(),
        )

    def test_captures_and_updates_payment(self) -> None:
        repo = self._repo_with_payment("ORD-1")
        paypal = FakePayPalClient(payer_id="PAY-9", payer_email="x@x.com")
        result = CapturePaymentUseCase(paypal=paypal, payment_repo=repo).execute(
            CapturePaymentCommand(order_id="ORD-1")
        )
        self.assertEqual(result.status, "CAPTURED")
        self.assertEqual(result.payer_id, "PAY-9")
        stored = repo.get_by_order_id("ORD-1")
        self.assertEqual(stored.status, "CAPTURED")
        self.assertIsNotNone(stored.captured_at)

    def test_raises_if_already_captured(self) -> None:
        repo = FakePaymentRepository()
        payment = Payment(
            order_id="ORD-1", tenant_id="", plan_id="p", amount="5.99",
            currency="USD", status="CAPTURED",
        )
        repo.save(payment)
        with self.assertRaises(PaymentAlreadyCapturedError):
            CapturePaymentUseCase(
                paypal=FakePayPalClient(), payment_repo=repo
            ).execute(CapturePaymentCommand(order_id="ORD-1"))

    def test_raises_if_payment_not_found(self) -> None:
        with self.assertRaises(PaymentNotFoundError):
            self._use_case(repo=FakePaymentRepository()).execute(
                CapturePaymentCommand(order_id="MISSING")
            )

    def test_marks_failed_and_raises_on_paypal_http_error(self) -> None:
        repo = self._repo_with_payment("ORD-1")
        paypal = FakePayPalClient(
            capture_raises=urllib.error.HTTPError(None, 422, "Unprocessable", {}, None)
        )
        with self.assertRaises(PaymentCaptureError):
            CapturePaymentUseCase(paypal=paypal, payment_repo=repo).execute(
                CapturePaymentCommand(order_id="ORD-1")
            )
        stored = repo.get_by_order_id("ORD-1")
        self.assertEqual(stored.status, "FAILED")

    def test_marks_failed_and_raises_on_network_error(self) -> None:
        repo = self._repo_with_payment("ORD-1")
        paypal = FakePayPalClient(
            capture_raises=urllib.error.URLError("timeout")
        )
        with self.assertRaises(PaymentCaptureError):
            CapturePaymentUseCase(paypal=paypal, payment_repo=repo).execute(
                CapturePaymentCommand(order_id="ORD-1")
            )
        stored = repo.get_by_order_id("ORD-1")
        self.assertEqual(stored.status, "FAILED")


# ── GetPaymentUseCase ─────────────────────────────────────────────────────────


class GetPaymentUseCaseTests(unittest.TestCase):
    def _repo_with_payment(
        self,
        order_id: str = "ORD-1",
        plan_cycle: str = "month",
    ) -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id="",
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status="CAPTURED",
                plan_cycle=plan_cycle,
            )
        )
        return repo

    def test_returns_payment_dict_with_plan_cycle(self) -> None:
        repo = self._repo_with_payment("ORD-1", plan_cycle="year")
        result = GetPaymentUseCase(repo).execute("ORD-1")
        self.assertEqual(result["order_id"], "ORD-1")
        self.assertEqual(result["status"], "CAPTURED")
        self.assertEqual(result["plan_cycle"], "year")
        self.assertEqual(result["amount"], "5.99")

    def test_raises_if_not_found(self) -> None:
        with self.assertRaises(PaymentNotFoundError):
            GetPaymentUseCase(FakePaymentRepository()).execute("MISSING")


if __name__ == "__main__":
    unittest.main()
