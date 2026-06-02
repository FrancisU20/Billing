import logging
import sys

from aws_lambda_powertools import Logger

# Logger estructurado con Lambda Powertools
# Incluye automáticamente: function_name, function_version, cold_start, request_id
logger = Logger(service="codelabs-billing", level="DEBUG")


def configure_logging() -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(message)s",
    )
    # Silenciar loggers ruidosos
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
