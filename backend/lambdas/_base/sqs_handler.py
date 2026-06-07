"""
Decorator @sqs_handler para workers SQS.

Diferencias con @lambda_handler:
- El event tiene `Records[]` en lugar de un body HTTP único
- Cada record se procesa independientemente
- Soporta partial batch failure: si un record falla, solo ese se reintenta
- El contexto de invocación se resetea en cada record para evitar contaminación

Uso:
    from lambdas._base.sqs_handler import sqs_handler, SQSRecord

    @sqs_handler
    def handler(record: SQSRecord, context) -> None:
        payload = InvoicePayload(**record.body)
        ProcessInvoiceUseCase().execute(payload)
"""
import functools
import json
from dataclasses import dataclass
from typing import Callable

from shared.errors import AppError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class SQSRecord:
    message_id:     str
    body:           dict
    receipt_handle: str
    attributes:     dict


def sqs_handler(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(event: dict, context) -> dict:
        records          = event.get("Records", [])
        failed_ids: list = []

        for raw in records:
            message_id = raw["messageId"]

            # Resetear contexto por record — evita que el message_id
            # del record anterior contamine los logs del siguiente
            clear_invocation_context()
            bind_invocation_context(
                message_id  = message_id,
                lambda_name = getattr(context, "function_name", "local"),
            )

            try:
                record = SQSRecord(
                    message_id     = message_id,
                    body           = json.loads(raw.get("body") or "{}"),
                    receipt_handle = raw["receiptHandle"],
                    attributes     = raw.get("attributes", {}),
                )
                func(record, context)
                _log.info("record procesado")

            except AppError as exc:
                _log.warning("error de aplicación en record", code=exc.code)
                failed_ids.append(message_id)

            except Exception:
                _log.error("error inesperado en record", exc_info=True)
                failed_ids.append(message_id)

        return {
            "batchItemFailures": [
                {"itemIdentifier": mid} for mid in failed_ids
            ]
        }

    return wrapper
