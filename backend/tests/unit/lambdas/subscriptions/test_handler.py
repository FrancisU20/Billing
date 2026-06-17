from __future__ import annotations

import importlib
import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import patch

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import PaymentNotFoundError
from lambdas.subscriptions.domain.repositories.i_dlocal_client import (
    DLocalConfirmPaymentResult,
    DLocalCreatePaymentResult,
)
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from tests.unit.support import LambdaContext, api_event, configure_unit_environment, decode_response

configure_unit_environment()
os.environ.setdefault("PAYMENTS_TABLE", "unit-payments")
os.environ.setdefault("PLANS_TABLE", "unit-plans")
os.environ.setdefault("DLOCALGO_CREDENTIALS_NAME", "unit/dlocalgo-creds")
os.environ.setdefault("DLOCALGO_API_URL", "https://api-sbx.dlocalgo.com")


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


class FakeDLocalClient:
    def __init__(
        self,
        *,
        payment_id: str = "DP-001",
        checkout_token: str = "mct_test",
        confirm_status: str = "PAID",
        payer_id: str | None = "user-001",
        payer_email: str | None = "buyer@example.com",
        redirect_url: str | None = None,
        create_raises: Exception | None = None,
        confirm_raises: Exception | None = None,
    ) -> None:
        self._payment_id = payment_id
        self._checkout_token = checkout_token
        self._confirm_status = confirm_status
        self._payer_id = payer_id
        self._payer_email = payer_email
        self._redirect_url = redirect_url
        self._create_raises = create_raises
        self._confirm_raises = confirm_raises

    def create_payment(self, amount: str, currency: str, country: str) -> DLocalCreatePaymentResult:
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
        if self._confirm_raises:
            raise self._confirm_raises
        return DLocalConfirmPaymentResult(
            payment_id=self._payment_id,
            status=self._confirm_status,
            payer_id=self._payer_id,
            payer_email=self._payer_email,
            redirect_url=self._redirect_url,
        )


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


# ── Module reload helper ───────────────────────────────────────────────────────


def _reload_handler():
    mod_name = "lambdas.subscriptions.handler"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    _fake_creds = {"api_key": "test-key", "secret_key": "test-secret"}
    with (
        patch("shared.db.client.get_table"),
        patch("shared.secrets.client.get_secret_json", return_value=_fake_creds),
    ):
        return importlib.import_module(mod_name)


_handler_mod = _reload_handler()


# ── Tests ─────────────────────────────────────────────────────────────────────


class CreatePaymentHandlerTests(unittest.TestCase):
    def _call(self, body: dict, plan_catalog=None, dlocal=None, repo=None) -> dict:
        event = api_event(method="POST", path="/subscriptions/payments", body=body)
        _catalog = plan_catalog or FakePlanCatalog()
        _dl = dlocal or FakeDLocalClient()
        _repo = repo or FakePaymentRepository()
        with (
            patch.object(_handler_mod, "DynamoPlanCatalog", return_value=_catalog),
            patch.object(_handler_mod, "_dlocal", return_value=_dl),
            patch.object(_handler_mod, "DynamoPaymentRepository", return_value=_repo),
        ):
            return _handler_mod.handler(event, LambdaContext())

    def test_returns_201_with_order_id_and_checkout_token(self) -> None:
        dlocal = FakeDLocalClient(payment_id="DP-X", checkout_token="mct_xyz")
        resp = self._call({"plan_id": "plan-1"}, dlocal=dlocal)
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 201)
        self.assertEqual(body["data"]["order_id"], "DP-X")
        self.assertEqual(body["data"]["checkout_token"], "mct_xyz")
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
        event = api_event(method="DELETE", path="/subscriptions/payments")
        resp = _handler_mod.handler(event, LambdaContext())
        self.assertEqual(resp["statusCode"], 404)


class ConfirmPaymentHandlerTests(unittest.TestCase):
    def _repo_with_payment(self, order_id: str = "DP-1") -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id=None,
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status="CREATED",
                checkout_token="mct_tok",
            )
        )
        return repo

    def _call(self, order_id: str, body: dict, dlocal=None, repo=None) -> dict:
        event = api_event(
            method="POST",
            path=f"/subscriptions/payments/{order_id}/confirm",
            body=body,
            path_params={"order_id": order_id},
        )
        _dl = dlocal or FakeDLocalClient()
        _repo = repo or self._repo_with_payment(order_id)
        with (
            patch.object(_handler_mod, "_dlocal", return_value=_dl),
            patch.object(_handler_mod, "DynamoPaymentRepository", return_value=_repo),
        ):
            return _handler_mod.handler(event, LambdaContext())

    def test_returns_200_with_paid_status(self) -> None:
        repo = self._repo_with_payment("DP-1")
        dlocal = FakeDLocalClient(payer_id="user-99", payer_email="a@b.com", confirm_status="PAID")
        resp = self._call(
            "DP-1",
            {
                "card_token": "card_tok_abc",
                "client_first_name": "Test",
                "client_last_name": "User",
                "client_email": "test@example.com",
                "client_document_type": "CI",
                "client_document": "1712345678",
            },
            dlocal=dlocal,
            repo=repo,
        )
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["status"], "PAID")
        self.assertEqual(body["data"]["payer_id"], "user-99")

    def test_returns_redirect_url_for_pending_confirmation(self) -> None:
        repo = self._repo_with_payment("DP-1")
        dlocal = FakeDLocalClient(
            confirm_status="PENDING",
            redirect_url="https://3ds.example.test/auth",
        )
        resp = self._call(
            "DP-1",
            {
                "card_token": "card_tok_abc",
                "client_first_name": "Test",
                "client_last_name": "User",
                "client_email": "test@example.com",
                "client_document_type": "CI",
                "client_document": "1712345678",
            },
            dlocal=dlocal,
            repo=repo,
        )
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["status"], "PENDING")
        self.assertEqual(body["data"]["redirect_url"], "https://3ds.example.test/auth")

    def test_returns_409_if_already_paid(self) -> None:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id="DP-1",
                tenant_id=None,
                plan_id="p",
                amount="5.99",
                currency="USD",
                status="PAID",
                checkout_token="mct_tok",
            )
        )
        resp = self._call(
            "DP-1",
            {
                "card_token": "card_tok",
                "client_first_name": "Test",
                "client_last_name": "User",
                "client_email": "test@example.com",
                "client_document_type": "CI",
                "client_document": "1712345678",
            },
            repo=repo,
        )
        self.assertEqual(resp["statusCode"], 409)

    def test_returns_404_if_payment_not_found(self) -> None:
        resp = self._call(
            "UNKNOWN",
            {
                "card_token": "card_tok",
                "client_first_name": "Test",
                "client_last_name": "User",
                "client_email": "test@example.com",
                "client_document_type": "CI",
                "client_document": "1712345678",
            },
            repo=FakePaymentRepository(),
        )
        self.assertEqual(resp["statusCode"], 404)

    def test_returns_400_for_missing_card_token(self) -> None:
        resp = self._call("DP-1", {})
        self.assertEqual(resp["statusCode"], 400)


class GetPaymentHandlerTests(unittest.TestCase):
    def _repo_with_payment(self, order_id: str = "DP-1") -> FakePaymentRepository:
        repo = FakePaymentRepository()
        repo.save(
            Payment(
                order_id=order_id,
                tenant_id=None,
                plan_id="plan-abc",
                amount="5.99",
                currency="USD",
                status="PAID",
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
        resp = self._call("DP-1")
        self.assertEqual(resp["statusCode"], 200)
        body = decode_response(resp)
        self.assertEqual(body["data"]["order_id"], "DP-1")
        self.assertEqual(body["data"]["status"], "PAID")
        self.assertEqual(body["data"]["plan_cycle"], "month")

    def test_returns_404_if_not_found(self) -> None:
        resp = self._call("MISSING", repo=FakePaymentRepository())
        self.assertEqual(resp["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
