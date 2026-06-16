from __future__ import annotations

import importlib
import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import patch

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import (
    PaymentNotFoundError,
)
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from lambdas.subscriptions.infra.paypal_client import PayPalCaptureResult, PayPalOrderResult
from tests.unit.support import LambdaContext, api_event, configure_unit_environment, decode_response

configure_unit_environment()
os.environ.setdefault("PAYMENTS_TABLE", "unit-payments")
os.environ.setdefault("PLANS_TABLE", "unit-plans")
os.environ.setdefault("PAYPAL_CREDENTIALS_NAME", "unit/paypal-creds")
os.environ.setdefault("PAYPAL_API_URL", "https://api-m.sandbox.paypal.com")
os.environ.setdefault("PAYPAL_RETURN_URL", "https://billing-dev.codelabsecuador.com/register/payment?payment_status=approved")
os.environ.setdefault("PAYPAL_CANCEL_URL", "https://billing-dev.codelabsecuador.com/register/payment?payment_status=cancelled")


# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakePlanCatalog(IPlanCatalog):
    def __init__(
        self,
        *,
        monthly_price: Decimal = Decimal("5.99"),
        is_free: bool = False,
    ) -> None:
        self._monthly = monthly_price
        self._free = is_free

    def get(self, plan_id: str) -> PlanSummary:
        return PlanSummary(
            id=plan_id,
            monthly_price=self._monthly,
            annual_price=Decimal("57.00"),
            limit_cycle="month",
            is_free=self._free,
        )


class FakePayPalClient:
    def __init__(
        self,
        *,
        order_id: str = "ORD-001",
        payer_id: str = "PAY-001",
        payer_email: str | None = "buyer@example.com",
        create_raises: Exception | None = None,
        capture_raises: Exception | None = None,
    ) -> None:
        self._order_id = order_id
        self._payer_id = payer_id
        self._payer_email = payer_email
        self._create_raises = create_raises
        self._capture_raises = capture_raises

    def create_order(self, amount: str, currency: str) -> PayPalOrderResult:
        if self._create_raises:
            raise self._create_raises
        return PayPalOrderResult(order_id=self._order_id)

    def capture_order(self, order_id: str) -> PayPalCaptureResult:
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


# ── Module reload helper ───────────────────────────────────────────────────────


def _reload_handler():
    mod_name = "lambdas.subscriptions.handler"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    _fake_creds = {"client_id": "x", "secret": "y"}
    with (
        patch("shared.db.client.get_table"),
        patch("shared.secrets.client.get_secret_json", return_value=_fake_creds),
    ):
        return importlib.import_module(mod_name)


_handler_mod = _reload_handler()


# ── Tests ─────────────────────────────────────────────────────────────────────


class CreatePaymentHandlerTests(unittest.TestCase):
    def _call(self, body: dict, plan_catalog=None, paypal=None, repo=None) -> dict:
        event = api_event(method="POST", path="/subscriptions/payments", body=body)
        _catalog = plan_catalog or FakePlanCatalog()
        _pp = paypal or FakePayPalClient()
        _repo = repo or FakePaymentRepository()
        with (
            patch.object(_handler_mod, "DynamoPlanCatalog", return_value=_catalog),
            patch.object(_handler_mod, "_paypal", return_value=_pp),
            patch.object(_handler_mod, "DynamoPaymentRepository", return_value=_repo),
        ):
            return _handler_mod.handler(event, LambdaContext())

    def test_returns_201_with_order_id(self) -> None:
        resp = self._call({"plan_id": "plan-1"}, paypal=FakePayPalClient(order_id="ORD-X"))
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 201)
        self.assertEqual(body["data"]["order_id"], "ORD-X")
        self.assertEqual(body["data"]["amount"], "5.99")

    def test_returns_422_for_free_plan(self) -> None:
        resp = self._call(
            {"plan_id": "free"},
            plan_catalog=FakePlanCatalog(is_free=True),
        )
        self.assertEqual(resp["statusCode"], 422)
        body = decode_response(resp)
        self.assertEqual(body["error"]["code"], "FREE_PLAN_NO_PAYMENT")

    def test_returns_400_for_missing_plan_id(self) -> None:
        resp = self._call({})
        self.assertEqual(resp["statusCode"], 400)

    def test_unknown_route_returns_404(self) -> None:
        event = api_event(method="GET", path="/subscriptions/payments")
        resp = _handler_mod.handler(event, LambdaContext())
        self.assertEqual(resp["statusCode"], 404)


class CapturePaymentHandlerTests(unittest.TestCase):
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

    def _call(self, order_id: str, paypal=None, repo=None) -> dict:
        event = api_event(
            method="POST",
            path=f"/subscriptions/payments/{order_id}/capture",
            path_params={"order_id": order_id},
        )
        _pp = paypal or FakePayPalClient()
        _repo = repo or self._repo_with_payment(order_id)
        with (
            patch.object(_handler_mod, "_paypal", return_value=_pp),
            patch.object(_handler_mod, "DynamoPaymentRepository", return_value=_repo),
        ):
            return _handler_mod.handler(event, LambdaContext())

    def test_returns_200_with_payer_info(self) -> None:
        repo = self._repo_with_payment("ORD-1")
        paypal = FakePayPalClient(payer_id="PAY-99", payer_email="a@b.com")
        resp = self._call("ORD-1", paypal=paypal, repo=repo)
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["status"], "CAPTURED")
        self.assertEqual(body["data"]["payer_id"], "PAY-99")

    def test_returns_409_if_already_captured(self) -> None:
        repo = FakePaymentRepository()
        repo.save(Payment(
            order_id="ORD-1", tenant_id="", plan_id="p",
            amount="5.99", currency="USD", status="CAPTURED",
        ))
        resp = self._call("ORD-1", repo=repo)
        self.assertEqual(resp["statusCode"], 409)

    def test_returns_404_if_payment_not_found(self) -> None:
        resp = self._call("UNKNOWN", repo=FakePaymentRepository())
        self.assertEqual(resp["statusCode"], 404)


class GetPaymentHandlerTests(unittest.TestCase):
    def _repo_with_payment(self, order_id: str = "ORD-1") -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id="",
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status="CAPTURED",
                plan_cycle="month",
            )
        )
        return repo

    def _call(self, order_id: str, repo=None) -> dict:
        event = api_event(
            method="GET",
            path=f"/subscriptions/payments/{order_id}",
            path_params={"order_id": order_id},
        )
        _repo = repo or self._repo_with_payment(order_id)
        with patch.object(_handler_mod, "DynamoPaymentRepository", return_value=_repo):
            return _handler_mod.handler(event, LambdaContext())

    def test_returns_200_with_payment_data(self) -> None:
        resp = self._call("ORD-1")
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["order_id"], "ORD-1")
        self.assertEqual(body["data"]["status"], "CAPTURED")
        self.assertEqual(body["data"]["plan_cycle"], "month")

    def test_returns_404_if_not_found(self) -> None:
        resp = self._call("MISSING", repo=FakePaymentRepository())
        self.assertEqual(resp["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
