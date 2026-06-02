import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="codelabs-billing-sri-retry")


@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Triggered por SQS sri-authorization-queue y por EventBridge (scheduler).
    Flujo: consultar estado de autorización al SRI → actualizar estado en DB.
    """
    source = event.get("source", "sqs")
    if source == "scheduler":
        logger.info("Retry scheduler triggered — querying RETRY_PENDING invoices")
        # TODO Fase 3: consultar comprobantes RETRY_PENDING y encolar
        return {"statusCode": 200}

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        clave_acceso = body.get("clave_acceso")
        logger.info("Querying SRI authorization", extra={"clave_acceso": clave_acceso})
        # TODO Fase 3: implementar consulta SOAP de autorización
    return {"statusCode": 200}
