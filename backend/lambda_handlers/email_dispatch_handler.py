import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.workers.email_dispatch_worker import enviar_bienvenida_tenant, enviar_comprobante_email

logger = Logger(service="codelabs-billing-email-dispatch")


@logger.inject_lambda_context(log_event=False)
async def handler(event: dict, context: LambdaContext) -> dict:
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        msg_type = body.get("type", "COMPROBANTE")

        if msg_type == "WELCOME":
            logger.info("Sending welcome email", extra={"email": body.get("email")})
            await enviar_bienvenida_tenant(
                email=body["email"],
                razon_social=body["razon_social"],
                temp_password=body["temp_password"],
            )
        else:
            comprobante_id = body["comprobante_id"]
            tenant_id = body["tenant_id"]
            logger.info("Dispatching email", extra={"comprobante_id": comprobante_id})
            await enviar_comprobante_email(comprobante_id, tenant_id)

    return {"statusCode": 200}
