import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="codelabs-billing-batch-import")


@logger.inject_lambda_context(log_event=False)
async def handler(event: dict, context: LambdaContext) -> dict:
    """
    Triggered por SQS batch-import-queue.
    Flujo: descargar CSV/Excel de S3 → validar → crear comprobantes → encolar.
    """
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        lote_id = body.get("lote_id")
        logger.info("Processing batch import", extra={"lote_id": lote_id})
        # TODO Fase 4: implementar parseo y validación de lotes
    return {"statusCode": 200}
