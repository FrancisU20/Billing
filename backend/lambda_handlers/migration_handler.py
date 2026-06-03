from alembic import command
from alembic.config import Config
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="codelabs-billing-migrations")


# Handler síncrono: Alembic es sync y env.py gestiona su propio event loop
# con asyncio.run(). Usar async def aquí causaría conflicto de event loops.
@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Starting database migrations")

    cfg = Config()
    cfg.set_main_option("script_location", "app/infrastructure/database/migrations")

    command.upgrade(cfg, "head")

    logger.info("Database migrations completed successfully")
    return {"status": "success"}
