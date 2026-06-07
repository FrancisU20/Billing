from __future__ import annotations

"""Migrations Lambda — invoked by CI/CD after API deploy."""

from migrations.context import MigrationContext

from lambdas.workers.migrations.infra.dynamo_migration_state_repository import (
    DynamoMigrationStateRepository,
)
from lambdas.workers.migrations.use_case import RunMigrationsUseCase
from shared.config import env
from shared.db.client import get_table
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)

_migrations_table = get_table("MIGRATIONS_TABLE")
_plans_table = get_table("PLANS_TABLE")


def _repo() -> DynamoMigrationStateRepository:
    return DynamoMigrationStateRepository(_migrations_table)


def _context() -> MigrationContext:
    return MigrationContext(
        tables={
            "PLANS_TABLE": _plans_table,
        }
    )


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    request_id = getattr(context, "aws_request_id", "local")
    bind_invocation_context(
        request_id=request_id,
        lambda_name=getattr(context, "function_name", "local"),
    )

    try:
        executions = RunMigrationsUseCase(_repo(), _context()).execute()
        _log.info("migrations completed", count=len(executions), env=env("ENV", "dev"))
        return {
            "success": True,
            "executions": [
                {
                    "id": execution.id,
                    "status": execution.status,
                    "result": execution.result,
                }
                for execution in executions
            ],
        }
    except AppError:
        _log.warning("migration application error", exc_info=True)
        raise
    except Exception:
        _log.error("migration unexpected error", exc_info=True)
        raise InternalError()
