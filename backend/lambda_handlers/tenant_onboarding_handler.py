import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.workers.tenant_onboarding_worker import procesar_onboarding

logger = Logger(service="codelabs-billing-tenant-onboarding")


@logger.inject_lambda_context(log_event=False)
async def handler(event: dict, context: LambdaContext) -> dict:
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        await procesar_onboarding(
            tenant_id=body["tenant_id"],
            razon_social=body["razon_social"],
            admin_email=body["admin_email"],
        )
    return {"statusCode": 200}
