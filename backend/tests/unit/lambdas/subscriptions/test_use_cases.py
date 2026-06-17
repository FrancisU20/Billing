from __future__ import annotations

import unittest
import urllib.error
from decimal import Decimal

from lambdas.subscriptions.domain.commands import ConfirmPaymentCommand, CreatePaymentCommand
from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import (
    FreePlanPaymentError,
    PaymentAlreadyConfirmedError,
    PaymentConfirmError,
    PaymentCreationError,
    PaymentNotFoundError,
    PaymentNotRefundableError,
    PaymentRefundError,
)
from lambdas.subscriptions.domain.repositories.i_dlocal_client import (
    DLocalConfirmPaymentResult,
    DLocalCreatePaymentResult,
    DLocalRefundResult,
    IDLocalClient,
)
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from lambdas.subscriptions.use_cases.confirm_payment import ConfirmPaymentUseCase
from lambdas.subscriptions.use_cases.create_payment import CreatePaymentUseCase
from lambdas.subscriptions.use_cases.get_payment import GetPaymentUseCase
from lambdas.subscriptions.use_cases.process_webhook import ProcessWebhookUseCase
from lambdas.subscriptions.use_cases.refund_payment import RefundPaymentUseCase

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


class FakeDLocalClient(IDLocalClient):
    def __init__(
        self,
        *,
        payment_id: str = "DP-001",
        checkout_token: str = "mct_test_token",
        payer_id: str | None = "user-123",
        payer_email: str | None = "payer@example.com",
        confirm_status: str = "PAID",
        redirect_url: str | None = None,
        create_raises: Exception | None = None,
        confirm_raises: Exception | None = None,
        refund_raises: Exception | None = None,
    ) -> None:
        self._payment_id = payment_id
        self._checkout_token = checkout_token
        self._payer_id = payer_id
        self._payer_email = payer_email
        self._confirm_status = confirm_status
        self._redirect_url = redirect_url
        self._create_raises = create_raises
        self._confirm_raises = confirm_raises
        self._refund_raises = refund_raises
        self.create_calls: list[tuple[str, str, str]] = []
        self.confirm_calls: list[tuple[str, str, str, str, str, str, str]] = []
        self.refund_calls: list[tuple[str, str, str]] = []

    def create_payment(self, amount: str, currency: str, country: str) -> DLocalCreatePaymentResult:
        self.create_calls.append((amount, currency, country))
        if self._create_raises:
            raise self._create_raises
        return DLocalCreatePaymentResult(
            payment_id=self._payment_id,
            checkout_token=self._checkout_token,
        )

    def confirm_payment(
        self,
        checkout_token: str,
        card_token: str,
        client_first_name: str,
        client_last_name: str,
        client_email: str,
        client_document_type: str,
        client_document: str,
    ) -> DLocalConfirmPaymentResult:
        self.confirm_calls.append(
            (
                checkout_token,
                card_token,
                client_first_name,
                client_last_name,
                client_email,
                client_document_type,
                client_document,
            )
        )
        if self._confirm_raises:
            raise self._confirm_raises
        return DLocalConfirmPaymentResult(
            payment_id=self._payment_id,
            status=self._confirm_status,
            payer_id=self._payer_id,
            payer_email=self._payer_email,
            redirect_url=self._redirect_url,
        )

    def refund_payment(self, order_id: str, amount: str, currency: str) -> DLocalRefundResult:
        self.refund_calls.append((order_id, amount, currency))
        if self._refund_raises:
            raise self._refund_raises
        return DLocalRefundResult(refund_id="REF-001", status="REFUNDED")


class FakePaymentRepository:
    def __init__(self) -> None:
        self._store: dict[str, Payment] = {}
        self.saved: list[Payment] = []
        self.linked: list[tuple[str, str]] = []

    def save(self, payment: Payment) -> None:
        self._store[payment.order_id] = payment
        self.saved.append(payment)

    def get_by_order_id(self, order_id: str) -> Payment:
        if order_id not in self._store:
            raise PaymentNotFoundError()
        return self._store[order_id]

    def link_tenant(self, order_id: str, tenant_id: str) -> None:
        self.linked.append((order_id, tenant_id))
        if order_id in self._store:
            self._store[order_id].tenant_id = tenant_id


# ── CreatePaymentUseCase ──────────────────────────────────────────────────────


class CreatePaymentUseCaseTests(unittest.TestCase):
    def _use_case(self, catalog=None, dlocal=None, repo=None):
        return CreatePaymentUseCase(
            plan_catalog=catalog or FakePlanCatalog(),
            dlocal=dlocal or FakeDLocalClient(),
            payment_repo=repo or FakePaymentRepository(),
        )

    def test_creates_payment_and_returns_checkout_token(self) -> None:
        repo = FakePaymentRepository()
        dlocal = FakeDLocalClient(payment_id="DP-1", checkout_token="mct_abc")
        result = self._use_case(dlocal=dlocal, repo=repo).execute(
            CreatePaymentCommand(plan_id="plan-abc")
        )
        self.assertEqual(result.order_id, "DP-1")
        self.assertEqual(result.checkout_token, "mct_abc")
        self.assertEqual(result.amount, "5.99")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(len(repo.saved), 1)
        self.assertEqual(repo.saved[0].status, "CREATED")
        self.assertEqual(repo.saved[0].checkout_token, "mct_abc")

    def test_passes_country_ec(self) -> None:
        dlocal = FakeDLocalClient()
        self._use_case(dlocal=dlocal).execute(CreatePaymentCommand(plan_id="plan-abc"))
        self.assertEqual(dlocal.create_calls[0][2], "EC")

    def test_uses_annual_price_for_year_cycle(self) -> None:
        catalog = FakePlanCatalog(
            monthly_price=Decimal("5.99"),
            annual_price=Decimal("57.00"),
            limit_cycle="year",
        )
        dlocal = FakeDLocalClient()
        result = self._use_case(catalog=catalog, dlocal=dlocal).execute(
            CreatePaymentCommand(plan_id="plan-y")
        )
        self.assertEqual(result.amount, "57.00")
        self.assertEqual(dlocal.create_calls[0][0], "57.00")

    def test_raises_for_free_plan(self) -> None:
        catalog = FakePlanCatalog(is_free=True)
        with self.assertRaises(FreePlanPaymentError):
            self._use_case(catalog=catalog).execute(CreatePaymentCommand(plan_id="free"))

    def test_raises_payment_creation_error_on_http_error(self) -> None:
        dlocal = FakeDLocalClient(
            create_raises=urllib.error.HTTPError(None, 500, "Server Error", {}, None)
        )
        with self.assertRaises(PaymentCreationError):
            self._use_case(dlocal=dlocal).execute(CreatePaymentCommand(plan_id="plan-x"))

    def test_raises_payment_creation_error_on_network_error(self) -> None:
        dlocal = FakeDLocalClient(create_raises=urllib.error.URLError("Connection refused"))
        with self.assertRaises(PaymentCreationError):
            self._use_case(dlocal=dlocal).execute(CreatePaymentCommand(plan_id="plan-x"))

    def test_payment_stored_with_plan_id(self) -> None:
        repo = FakePaymentRepository()
        self._use_case(repo=repo).execute(CreatePaymentCommand(plan_id="plan-z"))
        self.assertEqual(repo.saved[0].plan_id, "plan-z")


# ── ConfirmPaymentUseCase ─────────────────────────────────────────────────────


class ConfirmPaymentUseCaseTests(unittest.TestCase):
    def _repo_with_payment(
        self,
        order_id: str = "DP-1",
        checkout_token: str = "mct_abc",
        status: str = "CREATED",
    ) -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id=None,
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status=status,
                checkout_token=checkout_token,
            )
        )
        return repo

    def _use_case(self, dlocal=None, repo=None):
        return ConfirmPaymentUseCase(
            dlocal=dlocal or FakeDLocalClient(),
            payment_repo=repo or self._repo_with_payment(),
        )

    def test_confirms_and_sets_paid_status(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok")
        dlocal = FakeDLocalClient(payer_id="user-9", payer_email="x@x.com", confirm_status="PAID")
        result = ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
            ConfirmPaymentCommand(
                order_id="DP-1",
                card_token="card_tok_abc",
                client_first_name="Test",
                client_last_name="User",
                client_email="test@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )
        )
        self.assertEqual(result.status, "PAID")
        self.assertEqual(result.payer_id, "user-9")
        stored = repo.get_by_order_id("DP-1")
        self.assertEqual(stored.status, "PAID")
        self.assertIsNotNone(stored.confirmed_at)

    def test_passes_checkout_token_to_dlocal(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_special")
        dlocal = FakeDLocalClient()
        ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
            ConfirmPaymentCommand(
                order_id="DP-1",
                card_token="card_tok",
                client_first_name="Test",
                client_last_name="User",
                client_email="test@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )
        )
        self.assertEqual(dlocal.confirm_calls[0][0], "mct_special")

    def test_accepts_authorized_status(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok")
        dlocal = FakeDLocalClient(confirm_status="AUTHORIZED")
        result = ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
            ConfirmPaymentCommand(
                order_id="DP-1",
                card_token="card_tok",
                client_first_name="Test",
                client_last_name="User",
                client_email="test@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )
        )
        self.assertEqual(result.status, "PAID")

    def test_marks_failed_for_rejected_status(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok")
        dlocal = FakeDLocalClient(confirm_status="REJECTED")
        result = ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
            ConfirmPaymentCommand(
                order_id="DP-1",
                card_token="card_tok",
                client_first_name="Test",
                client_last_name="User",
                client_email="test@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )
        )
        self.assertEqual(result.status, "FAILED")
        stored = repo.get_by_order_id("DP-1")
        self.assertEqual(stored.status, "FAILED")
        self.assertIn("REJECTED", stored.error_detail)

    def test_marks_pending_for_redirect_response(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok")
        dlocal = FakeDLocalClient(
            confirm_status="PENDING",
            redirect_url="https://3ds.example.test/auth",
        )
        result = ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
            ConfirmPaymentCommand(
                order_id="DP-1",
                card_token="card_tok",
                client_first_name="Test",
                client_last_name="User",
                client_email="test@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )
        )
        self.assertEqual(result.status, "PENDING")
        self.assertEqual(result.redirect_url, "https://3ds.example.test/auth")
        stored = repo.get_by_order_id("DP-1")
        self.assertEqual(stored.status, "PENDING")

    def test_raises_if_already_paid(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok", status="PAID")
        with self.assertRaises(PaymentAlreadyConfirmedError):
            ConfirmPaymentUseCase(dlocal=FakeDLocalClient(), payment_repo=repo).execute(
                ConfirmPaymentCommand(
                    order_id="DP-1",
                    card_token="card_tok",
                    client_first_name="Test",
                    client_last_name="User",
                    client_email="test@example.com",
                    client_document_type="CI",
                    client_document="1712345678",
                )
            )

    def test_raises_if_payment_not_found(self) -> None:
        with self.assertRaises(PaymentNotFoundError):
            self._use_case(repo=FakePaymentRepository()).execute(
                ConfirmPaymentCommand(
                    order_id="MISSING",
                    card_token="card_tok",
                    client_first_name="Test",
                    client_last_name="User",
                    client_email="test@example.com",
                    client_document_type="CI",
                    client_document="1712345678",
                )
            )

    def test_marks_failed_and_raises_on_http_error(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok")
        dlocal = FakeDLocalClient(
            confirm_raises=urllib.error.HTTPError(None, 422, "Unprocessable", {}, None)
        )
        with self.assertRaises(PaymentConfirmError):
            ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
                ConfirmPaymentCommand(
                    order_id="DP-1",
                    card_token="card_tok",
                    client_first_name="Test",
                    client_last_name="User",
                    client_email="test@example.com",
                    client_document_type="CI",
                    client_document="1712345678",
                )
            )
        stored = repo.get_by_order_id("DP-1")
        self.assertEqual(stored.status, "FAILED")

    def test_marks_failed_and_raises_on_network_error(self) -> None:
        repo = self._repo_with_payment("DP-1", "mct_tok")
        dlocal = FakeDLocalClient(confirm_raises=urllib.error.URLError("timeout"))
        with self.assertRaises(PaymentConfirmError):
            ConfirmPaymentUseCase(dlocal=dlocal, payment_repo=repo).execute(
                ConfirmPaymentCommand(
                    order_id="DP-1",
                    card_token="card_tok",
                    client_first_name="Test",
                    client_last_name="User",
                    client_email="test@example.com",
                    client_document_type="CI",
                    client_document="1712345678",
                )
            )
        stored = repo.get_by_order_id("DP-1")
        self.assertEqual(stored.status, "FAILED")


# ── GetPaymentUseCase ─────────────────────────────────────────────────────────


class GetPaymentUseCaseTests(unittest.TestCase):
    def _repo_with_payment(
        self,
        order_id: str = "DP-1",
        plan_cycle: str = "month",
    ) -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id=None,
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status="PAID",
                plan_cycle=plan_cycle,
            )
        )
        return repo

    def test_returns_payment_dict_with_plan_cycle(self) -> None:
        repo = self._repo_with_payment("DP-1", plan_cycle="year")
        result = GetPaymentUseCase(repo).execute("DP-1")
        self.assertEqual(result["order_id"], "DP-1")
        self.assertEqual(result["status"], "PAID")
        self.assertEqual(result["plan_cycle"], "year")
        self.assertEqual(result["amount"], "5.99")

    def test_raises_if_not_found(self) -> None:
        with self.assertRaises(PaymentNotFoundError):
            GetPaymentUseCase(FakePaymentRepository()).execute("MISSING")


class RefundPaymentUseCaseTests(unittest.TestCase):
    def _paid_payment(self, order_id: str = "DP-1") -> Payment:
        p = Payment(
            order_id=order_id,
            tenant_id="tenant-1",
            plan_id="plan-1",
            amount="5.99",
            currency="USD",
            status="CREATED",
        )
        p.confirm(payer_id="user-1", payer_email="p@test.com")
        return p

    def _repo_with(self, payment: Payment) -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(payment)
        return repo

    def test_refunds_paid_payment(self) -> None:
        payment = self._paid_payment()
        repo = self._repo_with(payment)
        dlocal = FakeDLocalClient()
        result = RefundPaymentUseCase(repo, dlocal).execute("DP-1")
        self.assertEqual(result.order_id, "DP-1")
        self.assertEqual(result.refund_id, "REF-001")
        self.assertEqual(result.status, "REFUNDED")
        self.assertEqual(dlocal.refund_calls, [("DP-1", "5.99", "USD")])
        self.assertEqual(repo.saved[-1].status, "REFUNDED")

    def test_raises_if_not_found(self) -> None:
        with self.assertRaises(PaymentNotFoundError):
            RefundPaymentUseCase(FakePaymentRepository(), FakeDLocalClient()).execute("MISSING")

    def test_raises_if_not_paid(self) -> None:
        p = Payment(
            order_id="DP-1",
            tenant_id="tenant-1",
            plan_id="plan-1",
            amount="5.99",
            currency="USD",
            status="CREATED",
        )
        repo = self._repo_with(p)
        with self.assertRaises(PaymentNotRefundableError):
            RefundPaymentUseCase(repo, FakeDLocalClient()).execute("DP-1")

    def test_raises_if_already_refunded(self) -> None:
        payment = self._paid_payment()
        payment.refund()
        repo = self._repo_with(payment)
        with self.assertRaises(PaymentNotRefundableError):
            RefundPaymentUseCase(repo, FakeDLocalClient()).execute("DP-1")

    def test_wraps_dlocal_error(self) -> None:
        payment = self._paid_payment()
        repo = self._repo_with(payment)
        dlocal = FakeDLocalClient(refund_raises=RuntimeError("dLocal down"))
        with self.assertRaises(PaymentRefundError):
            RefundPaymentUseCase(repo, dlocal).execute("DP-1")

    def test_does_not_save_on_dlocal_failure(self) -> None:
        payment = self._paid_payment()
        repo = self._repo_with(payment)
        initial_save_count = len(repo.saved)
        dlocal = FakeDLocalClient(refund_raises=RuntimeError("dLocal down"))
        with self.assertRaises(PaymentRefundError):
            RefundPaymentUseCase(repo, dlocal).execute("DP-1")
        self.assertEqual(len(repo.saved), initial_save_count)


class ProcessWebhookUseCaseTests(unittest.TestCase):
    def _repo_with(
        self, *, order_id: str = "DP-1", status: str = "PENDING"
    ) -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id="tenant-1",
                plan_id="plan-1",
                amount="5.99",
                currency="USD",
                status=status,
            )
        )
        return repo

    def test_updates_status_to_paid(self) -> None:
        repo = self._repo_with(status="PENDING")
        result = ProcessWebhookUseCase(repo).execute("DP-1", "PAID")
        self.assertEqual(result.status, "PAID")
        self.assertTrue(result.updated)
        self.assertEqual(repo.get_by_order_id("DP-1").status, "PAID")

    def test_maps_approved_to_paid(self) -> None:
        repo = self._repo_with(status="PENDING")
        result = ProcessWebhookUseCase(repo).execute("DP-1", "APPROVED")
        self.assertEqual(result.status, "PAID")
        self.assertTrue(result.updated)

    def test_updates_status_to_rejected(self) -> None:
        repo = self._repo_with(status="PENDING")
        result = ProcessWebhookUseCase(repo).execute("DP-1", "REJECTED")
        self.assertEqual(result.status, "REJECTED")
        self.assertTrue(result.updated)

    def test_updates_status_to_failed(self) -> None:
        repo = self._repo_with(status="PENDING")
        result = ProcessWebhookUseCase(repo).execute("DP-1", "FAILED")
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(result.updated)

    def test_no_op_when_status_already_matches(self) -> None:
        repo = self._repo_with(status="PAID")
        initial_saves = len(repo.saved)
        result = ProcessWebhookUseCase(repo).execute("DP-1", "PAID")
        self.assertFalse(result.updated)
        self.assertEqual(len(repo.saved), initial_saves)

    def test_no_op_for_unknown_order(self) -> None:
        result = ProcessWebhookUseCase(FakePaymentRepository()).execute("MISSING", "PAID")
        self.assertFalse(result.updated)
        self.assertEqual(result.order_id, "MISSING")

    def test_no_op_for_unmapped_dlocal_status(self) -> None:
        repo = self._repo_with(status="PENDING")
        initial_saves = len(repo.saved)
        result = ProcessWebhookUseCase(repo).execute("DP-1", "PENDING")
        self.assertFalse(result.updated)
        self.assertEqual(len(repo.saved), initial_saves)

    def test_status_comparison_is_case_insensitive(self) -> None:
        repo = self._repo_with(status="PENDING")
        result = ProcessWebhookUseCase(repo).execute("DP-1", "paid")
        self.assertEqual(result.status, "PAID")
        self.assertTrue(result.updated)


if __name__ == "__main__":
    unittest.main()
