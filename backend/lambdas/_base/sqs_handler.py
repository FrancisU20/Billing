from __future__ import annotations

"""
@sqs_handler decorator for SQS workers.

Differences from @lambda_handler:
- The event has `Records[]` instead of a single HTTP body
- Each record is processed independently
- Supports partial batch failure: if a record fails, only that one is retried
- The invocation context is reset on each record to avoid contamination

Usage:
    from lambdas._base.sqs_handler import sqs_handler, SQSRecord

    @sqs_handler
    def handler(record: SQSRecord, context) -> None:
        payload = InvoicePayload(**record.body)
        ProcessInvoiceUseCase().execute(payload)
"""
import functools
import json
from collections.abc import Callable
from dataclasses import dataclass

from shared.errors import AppError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class SQSRecord:
    message_id: str
    body: dict
    receipt_handle: str
    attributes: dict


def sqs_handler(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(event: dict, context) -> dict:
        records = event.get("Records", [])
        failed_ids: list = []

        for raw in records:
            message_id = raw["messageId"]

            # Reset context per record — prevents the previous record's
            # message_id from contaminating the next record's logs
            clear_invocation_context()
            bind_invocation_context(
                message_id=message_id,
                lambda_name=getattr(context, "function_name", "local"),
            )

            try:
                record = SQSRecord(
                    message_id=message_id,
                    body=json.loads(raw.get("body") or "{}"),
                    receipt_handle=raw["receiptHandle"],
                    attributes=raw.get("attributes", {}),
                )
                func(record, context)
                _log.info("record processed")

            except AppError as exc:
                _log.warning("application error in record", code=exc.code)
                failed_ids.append(message_id)

            except Exception:
                _log.error("unexpected error in record", exc_info=True)
                failed_ids.append(message_id)

        return {"batchItemFailures": [{"itemIdentifier": mid} for mid in failed_ids]}

    return wrapper
