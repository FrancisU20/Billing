import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="codelabs-billing-email-dispatch")


@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Triggered por SQS email-dispatch-queue.
    Flujo: cargar PDF/XML de S3 → enviar con Brevo → fallback a Mailgun.
    """
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        comprobante_id = body.get("comprobante_id")
        logger.info("Dispatching email", extra={"comprobante_id": comprobante_id})
        # TODO Fase 3: implementar envío con fallback de proveedores
    return {"statusCode": 200}
