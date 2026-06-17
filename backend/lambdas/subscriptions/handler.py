from __future__ import annotations

"""
Subscriptions Lambda — AWS entry point.

Routes:
    POST /subscriptions/payments                          create dLocal payment   (public)
    POST /subscriptions/payments/{order_id}/confirm       confirm with card token  (public)
    GET  /subscriptions/payments/{order_id}               get payment status       (public)
    POST /subscriptions/payments/{order_id}/refund        refund payment           (superadmin JWT)
    POST /subscriptions/webhooks/dlocal                   dLocal Go webhook        (HMAC-verified)
"""

import hashlib
import hmac as _hmac_mod
import re

from lambdas._base.handler import public_lambda_handler
from lambdas._base.idempotency import idempotent
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.response import ApiResponse
from lambdas.subscriptions.domain.commands import ConfirmPaymentCommand, CreatePaymentCommand
from lambdas.subscriptions.infra.dlocal_client import DLocalClient
from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository
from lambdas.subscriptions.infra.plan_catalog import DynamoPlanCatalog
from lambdas.subscriptions.schemas import ConfirmPaymentRequest, CreatePaymentRequest
from lambdas.subscriptions.use_cases.confirm_payment import ConfirmPaymentUseCase
from lambdas.subscriptions.use_cases.create_payment import CreatePaymentUseCase
from lambdas.subscriptions.use_cases.get_payment import GetPaymentUseCase
from lambdas.subscriptions.use_cases.process_webhook import ProcessWebhookUseCase
from lambdas.subscriptions.use_cases.refund_payment import RefundPaymentUseCase
from shared.config import env
from shared.db.client import get_table
from shared.errors import ForbiddenError, NotFoundError
from shared.secrets.client import get_secret_json

_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE")
_PLANS_TABLE = get_table("PLANS_TABLE")
_IDEMPOTENCY_TABLE = get_table("IDEMPOTENCY_TABLE") if env("IDEMPOTENCY_TABLE", "") else None


def _dlocal() -> DLocalClient:
    creds = get_secret_json(env("DLOCALGO_CREDENTIALS_NAME"))
    return DLocalClient(
        base_url=env("DLOCALGO_API_URL"),
        api_key=creds["api_key"],
        secret_key=creds["secret_key"],
    )


@public_lambda_handler
@idempotent
def _create_payment(request: Request, context) -> dict:
    body = parse(CreatePaymentRequest, request.body)
    result = CreatePaymentUseCase(
        plan_catalog=DynamoPlanCatalog(_PLANS_TABLE),
        dlocal=_dlocal(),
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(
        CreatePaymentCommand(
            plan_id=body.plan_id,
            currency=body.currency,
        )
    )
    return ApiResponse.created(
        {
            "order_id": result.order_id,
            "checkout_token": result.checkout_token,
            "amount": result.amount,
            "net_amount": result.net_amount,
            "markup_pct": result.markup_pct,
            "currency": result.currency,
        },
        request.request_id,
    )


@public_lambda_handler
def _confirm_payment(request: Request, context) -> dict:
    order_id = require_path_param(request, "order_id")
    body = parse(ConfirmPaymentRequest, request.body)
    result = ConfirmPaymentUseCase(
        dlocal=_dlocal(),
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(
        ConfirmPaymentCommand(
            order_id=order_id,
            card_token=body.card_token,
            client_first_name=body.client_first_name,
            client_last_name=body.client_last_name,
            client_email=body.client_email,
            client_document_type=body.client_document_type,
            client_document=body.client_document,
        )
    )
    return ApiResponse.ok(
        {
            "order_id": result.order_id,
            "status": result.status,
            "payer_id": result.payer_id,
            "payer_email": result.payer_email,
            "redirect_url": result.redirect_url,
        },
        request.request_id,
    )


_PAYMENT_ID_PATTERN = re.compile(r"^/subscriptions/payments/([^/]+)$")
_CONFIRM_PATTERN = re.compile(r"^/subscriptions/payments/[^/]+/confirm$")
_REFUND_PATTERN = re.compile(r"^/subscriptions/payments/[^/]+/refund$")
_WEBHOOK_DLOCAL_PATTERN = re.compile(r"^/subscriptions/webhooks/dlocal$")


def _verify_dlocal_signature(raw_body: str, signature: str, secret_key: str) -> bool:
    expected = _hmac_mod.new(secret_key.encode(), raw_body.encode(), hashlib.sha256).hexdigest()
    return _hmac_mod.compare_digest(expected, signature.lower())


@public_lambda_handler
def _get_payment(request: Request, context) -> dict:
    order_id = require_path_param(request, "order_id")
    payment = GetPaymentUseCase(
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(order_id)
    return ApiResponse.ok(payment, request.request_id)


@public_lambda_handler
def _refund_payment(request: Request, context) -> dict:
    if not request.is_superadmin:
        raise ForbiddenError()
    order_id = require_path_param(request, "order_id")
    result = RefundPaymentUseCase(
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
        dlocal=_dlocal(),
    ).execute(order_id)
    return ApiResponse.ok(
        {"order_id": result.order_id, "refund_id": result.refund_id, "status": result.status},
        request.request_id,
    )


@public_lambda_handler
def _dlocal_webhook(request: Request, context) -> dict:
    signature = request.headers.get("x-signature", "")
    if not signature:
        raise ForbiddenError()
    creds = get_secret_json(env("DLOCALGO_CREDENTIALS_NAME"))
    if not _verify_dlocal_signature(request.raw_body, signature, creds["secret_key"]):
        raise ForbiddenError()

    event_type = request.body.get("type", "")
    data = request.body.get("data", {})
    order_id = data.get("order_id") or data.get("id", "")
    dlocal_status = data.get("status", "")

    if event_type != "PAYMENT" or not order_id or not dlocal_status:
        return ApiResponse.ok({"received": True}, request.request_id)

    result = ProcessWebhookUseCase(
        payment_repo=DynamoPaymentRepository(_PAYMENTS_TABLE),
    ).execute(order_id, dlocal_status)
    return ApiResponse.ok(
        {"order_id": result.order_id, "status": result.status, "updated": result.updated},
        request.request_id,
    )


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    http = ctx.get("http", {})
    method = http.get("method", "")
    path = http.get("path", event.get("rawPath", ""))

    if method == "POST" and path == "/subscriptions/payments":
        return _create_payment(event, context)

    if method == "POST" and _WEBHOOK_DLOCAL_PATTERN.match(path):
        return _dlocal_webhook(event, context)

    if method == "POST" and _REFUND_PATTERN.match(path):
        return _refund_payment(event, context)

    if method == "POST" and _CONFIRM_PATTERN.match(path):
        return _confirm_payment(event, context)

    if method == "GET" and _PAYMENT_ID_PATTERN.match(path):
        return _get_payment(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
