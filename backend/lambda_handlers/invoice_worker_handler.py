import asyncio
import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.workers.invoice_worker import procesar_comprobante

logger = Logger(service="codelabs-billing-invoice-worker")


@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: LambdaContext) -> dict:
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        comprobante_id = body["comprobante_id"]
        tenant_id = body["tenant_id"]
        logger.info("Processing invoice", extra={"comprobante_id": comprobante_id})
        asyncio.run(procesar_comprobante(comprobante_id, tenant_id))
    return {"statusCode": 200}
