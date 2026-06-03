import asyncio
import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.workers.sri_retry_worker import consultar_autorizacion_comprobante, reintentar_pendientes

logger = Logger(service="codelabs-billing-sri-retry")


@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: LambdaContext) -> dict:
    # Triggered por EventBridge scheduler
    if event.get("source") == "scheduler":
        logger.info("Scheduler trigger — retrying pending invoices")
        asyncio.run(reintentar_pendientes())
        return {"statusCode": 200}

    # Triggered por SQS
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        comprobante_id = body["comprobante_id"]
        clave_acceso = body["clave_acceso"]
        ambiente = body["ambiente"]
        logger.info("Querying SRI authorization", extra={"clave_acceso": clave_acceso})
        asyncio.run(consultar_autorizacion_comprobante(comprobante_id, clave_acceso, ambiente))

    return {"statusCode": 200}
