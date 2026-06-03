from alembic import command
from alembic.config import Config
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="codelabs-billing-migrations")


async def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Starting database migrations")

    cfg = Config()
    cfg.set_main_option("script_location", "app/infrastructure/database/migrations")

    command.upgrade(cfg, "head")

    logger.info("Database migrations completed successfully")
    return {"status": "success"}
