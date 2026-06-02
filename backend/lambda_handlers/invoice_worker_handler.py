import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="codelabs-billing-invoice-worker")


@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Triggered por SQS invoice-processing-queue (batch_size=1).
    Flujo: descargar XML firmado de S3 → enviar al SRI → encolar para autorización.
    """
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        comprobante_id = body.get("comprobante_id")
        logger.info("Processing invoice", extra={"comprobante_id": comprobante_id})
        # TODO Fase 3: implementar lógica de envío al SRI
    return {"statusCode": 200}
