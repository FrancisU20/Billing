from __future__ import annotations

"""Run pending data migrations."""

from dataclasses import dataclass

from migrations.context import MigrationContext
from migrations.registry import MIGRATIONS

from lambdas.workers.migrations.ports import MigrationStateRepository


@dataclass(frozen=True)
class MigrationExecution:
    id: str
    status: str
    result: dict | None = None


class RunMigrationsUseCase:
    def __init__(self, repo: MigrationStateRepository, context: MigrationContext) -> None:
        self._repo = repo
        self._context = context

    def execute(self) -> list[MigrationExecution]:
        executions: list[MigrationExecution] = []
        for migration in MIGRATIONS:
            if not self._repo.begin(migration):
                executions.append(MigrationExecution(id=migration.id, status="skipped"))
                continue

            try:
                result = migration.run(self._context)
                self._repo.mark_succeeded(migration, result)
                executions.append(
                    MigrationExecution(
                        id=migration.id,
                        status="success",
                        result=result.to_dict(),
                    )
                )
            except Exception as exc:
                self._repo.mark_failed(migration, str(exc))
                raise

        return executions
