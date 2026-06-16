from __future__ import annotations

"""
Subscriptions Lambda — AWS entry point.

Routes:
    POST /subscriptions/payments                         create PayPal order  (public)
    POST /subscriptions/payments/{order_id}/capture      capture payment      (public)
    GET  /subscriptions/payments/{order_id}              get payment status   (public)
"""

import re

from lambdas._base.handler import public_lambda_handler
from lambdas._base.idempotency import idempotent
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.response import ApiResponse
from lambdas.subscriptions.domain.commands import CapturePaymentCommand, CreatePaymentCommand
from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository
from lambdas.subscriptions.infra.paypal_client import PayPalClient
from lambdas.subscriptions.infra.plan_catalog import DynamoPlanCatalog
from lambdas.subscriptions.schemas import CreatePaymentRequest
from lambdas.subscriptions.use_cases.capture_payment import CapturePaymentUseCase
from lambdas.subscriptions.use_cases.create_payment import CreatePaymentUseCase
from lambdas.subscriptions.use_cases.get_payment import GetPaymentUseCase
from shared.config import env
from shared.db.client import get_table
from shared.errors import NotFoundError
from shared.secrets.client import get_secret_json

_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE")
_PLANS_TABLE = get_table("PLANS_TABLE")
_IDEMPOTENCY_TABLE = get_table("IDEMPOTENCY_TABLE") if env("IDEMPOTENCY_TABLE", "") else None


def _paypal() -> PayPalClient:
    creds = get_secret_json(env("PAYPAL_CREDENTIALS_NAME"))
    return PayPalClient(
        base_url=env("PAYPAL_API_URL"),
        client_id=creds["client_id"],
        secret=creds["secret"],
        return_url=env("PAYPAL_RETURN_URL"),
        cancel_url=env("PAYPAL_CANCEL_URL"),
    )


@public_lambda_handler
@idempotent
def _create_payment(request: Request, context) -> dict:
    body = parse(CreatePaymentRequest, request.body)
    result = CreatePaymentUseCase(
        plan_catalog=DynamoPlanCatalog(_PLANS_TABLE),
        paypal=_paypal(),
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(
        CreatePaymentCommand(
            plan_id=body.plan_id,
            currency=body.currency,
        )
    )
    return ApiResponse.created(
        {"order_id": result.order_id, "amount": result.amount, "currency": result.currency},
        request.request_id,
    )


@public_lambda_handler
def _capture_payment(request: Request, context) -> dict:
    order_id = require_path_param(request, "order_id")
    result = CapturePaymentUseCase(
        paypal=_paypal(),
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(CapturePaymentCommand(order_id=order_id))
    return ApiResponse.ok(
        {
            "order_id": result.order_id,
            "status": result.status,
            "payer_id": result.payer_id,
            "payer_email": result.payer_email,
        },
        request.request_id,
    )


_PAYMENT_ID_PATTERN = re.compile(r"^/subscriptions/payments/([^/]+)$")
_CAPTURE_PATTERN = re.compile(r"^/subscriptions/payments/[^/]+/capture$")


@public_lambda_handler
def _get_payment(request: Request, context) -> dict:
    order_id = require_path_param(request, "order_id")
    payment = GetPaymentUseCase(
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(order_id)
    return ApiResponse.ok(payment, request.request_id)


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    http = ctx.get("http", {})
    method = http.get("method", "")
    path = http.get("path", event.get("rawPath", ""))

    if method == "POST" and path == "/subscriptions/payments":
        return _create_payment(event, context)

    if method == "POST" and _CAPTURE_PATTERN.match(path):
        return _capture_payment(event, context)

    if method == "GET" and _PAYMENT_ID_PATTERN.match(path):
        return _get_payment(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
