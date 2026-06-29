from __future__ import annotations

"""
Worker: dLocal webhook processor.

The public HTTP endpoint only verifies HMAC and persists the signed payload into SQS.
This worker performs the payment state transition with SQS retries and DLQ support.
"""

import json

from lambdas._base.sqs_handler import SQSRecord, sqs_handler
from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository
from lambdas.subscriptions.use_cases.process_webhook import ProcessWebhookUseCase
from shared.config import env
from shared.db.client import get_table
from shared.logger import get_logger

_log = get_logger(__name__)

_payment_repo = DynamoPaymentRepository(get_table("PAYMENTS_TABLE"))
_use_case = ProcessWebhookUseCase(_payment_repo)


@sqs_handler
def handler(record: SQSRecord, context) -> None:
    message_type = record.body.get("type")
    if message_type != "DLOCAL_WEBHOOK":
        _log.warning("unknown dLocal webhook message ignored", message_type=message_type)
        return

    raw_body = record.body.get("raw_body", "")
    payload = json.loads(raw_body)
    if not isinstance(payload, dict):
        raise ValueError("dLocal webhook payload must be a JSON object")

    event_type = payload.get("type", "")
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("dLocal webhook data must be a JSON object")

    order_id = data.get("order_id", "")
    dlocal_status = data.get("status", "")
    if not order_id:
        _log.warning("dLocal webhook missing order_id", event_type=event_type)

    if event_type != "PAYMENT" or not order_id or not dlocal_status:
        _log.info("dLocal webhook ignored", event_type=event_type, order_id=order_id)
        return

    result = _use_case.execute(order_id, dlocal_status)
    _log.info(
        "dLocal webhook processed",
        order_id=result.order_id,
        status=result.status,
        updated=result.updated,
        source_request_id=record.body.get("request_id", ""),
        queue_name=env("DLOCAL_WEBHOOK_QUEUE_NAME", ""),
    )
