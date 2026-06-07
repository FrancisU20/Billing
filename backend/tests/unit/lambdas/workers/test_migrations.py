from __future__ import annotations

import importlib
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from botocore.exceptions import ClientError
from migrations.context import MigrationContext, MigrationResult
from migrations.definition import Migration
from migrations.versions import v0001_seed_plans

from lambdas.plans.domain.errors import PlanNotFoundError, PlanSlugExistsError
from lambdas.workers.migrations.infra.dynamo_migration_state_repository import (
    DynamoMigrationStateRepository,
    MigrationAlreadyRunningError,
)
from lambdas.workers.migrations.use_case import RunMigrationsUseCase
from tests.unit.support import LambdaContext, configure_unit_environment


class FakeMigrationStateRepository:
    def __init__(self, *, should_run: bool = True) -> None:
        self.should_run = should_run
        self.begin_calls: list[str] = []
        self.succeeded: list[tuple[str, MigrationResult]] = []
        self.failed: list[tuple[str, str]] = []

    def begin(self, migration: Migration) -> bool:
        self.begin_calls.append(migration.id)
        return self.should_run

    def mark_succeeded(self, migration: Migration, result: MigrationResult) -> None:
        self.succeeded.append((migration.id, result))

    def mark_failed(self, migration: Migration, error: str) -> None:
        self.failed.append((migration.id, error))


class FakeStateTable:
    table_name = "unit-migrations"

    def __init__(self, item: dict | None = None, fail_conditional: bool = False) -> None:
        self.item = item
        self.fail_conditional = fail_conditional
        self.put_items: list[dict] = []

    def get_item(self, **kwargs) -> dict:
        key = kwargs["Key"]
        if self.item and self.item["id"] == key["id"]:
            return {"Item": dict(self.item)}
        return {}

    def put_item(self, **kwargs) -> None:
        if self.fail_conditional:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException"}},
                "PutItem",
            )
        self.put_items.append(kwargs["Item"])
        self.item = dict(kwargs["Item"])


class FakePlan:
    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.id = f"plan-{slug}"


class FakePlanRepository:
    def __init__(self, existing_slugs: set[str] | None = None) -> None:
        self.existing_slugs = existing_slugs or set()
        self.commits: list[str] = []

    def get_by_slug(self, slug: str) -> FakePlan:
        if slug in self.existing_slugs:
            return FakePlan(slug)
        raise PlanNotFoundError()

    def commit(self, **kwargs) -> None:
        self.commits.append(kwargs["plan"].slug)


class FakeCreatePlanUseCase:
    def __init__(self, repo: FakePlanRepository, existing_slugs: set[str] | None = None) -> None:
        self.repo = repo
        self.existing_slugs = existing_slugs or set()
        self.commands: list[str] = []

    def execute(self, command):
        self.commands.append(command.slug)
        if command.slug in self.existing_slugs:
            raise PlanSlugExistsError()
        return FakePlan(command.slug)


class RunMigrationsUseCaseTests(unittest.TestCase):
    def test_runs_pending_migration_and_marks_success(self) -> None:
        repo = FakeMigrationStateRepository()
        calls: list[str] = []
        migration = Migration(
            id="0001_test",
            description="test migration",
            run=lambda context: calls.append(context.table("X")) or MigrationResult(created=1),
        )

        with patch("lambdas.workers.migrations.use_case.MIGRATIONS", (migration,)):
            result = RunMigrationsUseCase(repo, MigrationContext(tables={"X": "table"})).execute()

        self.assertEqual(calls, ["table"])
        self.assertEqual(result[0].status, "success")
        self.assertEqual(repo.succeeded[0][0], "0001_test")
        self.assertEqual(repo.succeeded[0][1].created, 1)

    def test_skips_completed_migration(self) -> None:
        repo = FakeMigrationStateRepository(should_run=False)
        migration = Migration(
            id="0001_done",
            description="done",
            run=lambda context: MigrationResult(created=1),
        )

        with patch("lambdas.workers.migrations.use_case.MIGRATIONS", (migration,)):
            result = RunMigrationsUseCase(repo, MigrationContext(tables={})).execute()

        self.assertEqual(result[0].status, "skipped")
        self.assertEqual(repo.succeeded, [])

    def test_marks_failure_and_reraises(self) -> None:
        repo = FakeMigrationStateRepository()

        def fail(context: MigrationContext) -> MigrationResult:
            raise RuntimeError("boom")

        migration = Migration(id="0001_fail", description="fail", run=fail)

        with (
            patch("lambdas.workers.migrations.use_case.MIGRATIONS", (migration,)),
            self.assertRaises(RuntimeError),
        ):
            RunMigrationsUseCase(repo, MigrationContext(tables={})).execute()

        self.assertEqual(repo.failed[0][0], "0001_fail")
        self.assertIn("boom", repo.failed[0][1])


class SeedPlansMigrationTests(unittest.TestCase):
    def test_seed_plans_creates_all_initial_plans(self) -> None:
        repo = FakePlanRepository()
        use_case = FakeCreatePlanUseCase(repo)

        with (
            patch.object(v0001_seed_plans, "DynamoPlanRepository", return_value=repo),
            patch.object(v0001_seed_plans, "CreatePlanUseCase", return_value=use_case),
        ):
            result = v0001_seed_plans.run(MigrationContext(tables={"PLANS_TABLE": object()}))

        self.assertEqual(result.created, 5)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(repo.commits, ["free", "basic", "pyme", "pro", "enterprise"])

    def test_seed_plans_skips_existing_slugs(self) -> None:
        repo = FakePlanRepository(existing_slugs={"free", "basic"})
        use_case = FakeCreatePlanUseCase(repo)

        with (
            patch.object(v0001_seed_plans, "DynamoPlanRepository", return_value=repo),
            patch.object(v0001_seed_plans, "CreatePlanUseCase", return_value=use_case),
        ):
            result = v0001_seed_plans.run(MigrationContext(tables={"PLANS_TABLE": object()}))

        self.assertEqual(result.created, 3)
        self.assertEqual(result.skipped, 2)
        self.assertEqual(repo.commits, ["pyme", "pro", "enterprise"])
        self.assertIn("skipped:free:plan-free:already_exists", result.details)

    def test_seed_plans_handles_slug_lock_race(self) -> None:
        repo = FakePlanRepository()
        use_case = FakeCreatePlanUseCase(repo, existing_slugs={"free"})

        with (
            patch.object(v0001_seed_plans, "DynamoPlanRepository", return_value=repo),
            patch.object(v0001_seed_plans, "CreatePlanUseCase", return_value=use_case),
        ):
            result = v0001_seed_plans.run(MigrationContext(tables={"PLANS_TABLE": object()}))

        self.assertEqual(result.created, 4)
        self.assertEqual(result.skipped, 1)
        self.assertNotIn("free", repo.commits)
        self.assertIn("skipped:free:already_exists", result.details)


class DynamoMigrationStateRepositoryTests(unittest.TestCase):
    def test_begin_returns_false_for_successful_migration(self) -> None:
        table = FakeStateTable({"id": "0001_done", "status": "SUCCESS"})
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_done",
            description="done",
            run=lambda context: MigrationResult(),
        )

        self.assertFalse(repo.begin(migration))
        self.assertEqual(table.put_items, [])

    def test_begin_raises_when_migration_is_running(self) -> None:
        table = FakeStateTable({"id": "0001_running", "status": "IN_PROGRESS"})
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_running",
            description="running",
            run=lambda context: MigrationResult(),
        )

        with self.assertRaises(MigrationAlreadyRunningError):
            repo.begin(migration)

    def test_begin_allows_expired_in_progress_migration_retry(self) -> None:
        expired_at = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        table = FakeStateTable(
            {
                "id": "0001_expired",
                "status": "IN_PROGRESS",
                "attempts": 1,
                "lock_expires_at": expired_at,
            }
        )
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_expired",
            description="expired",
            run=lambda context: MigrationResult(),
        )

        self.assertTrue(repo.begin(migration))
        self.assertEqual(table.item["status"], "IN_PROGRESS")
        self.assertEqual(table.item["attempts"], 2)
        self.assertIn("lock_expires_at", table.item)

    def test_begin_allows_failed_migration_retry(self) -> None:
        table = FakeStateTable({"id": "0001_retry", "status": "FAILED", "attempts": 1})
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_retry",
            description="retry",
            run=lambda context: MigrationResult(),
        )

        self.assertTrue(repo.begin(migration))
        self.assertEqual(table.item["status"], "IN_PROGRESS")
        self.assertEqual(table.item["attempts"], 2)

    def test_begin_detects_racing_in_progress_write(self) -> None:
        table = FakeStateTable({"id": "0001_race", "status": "IN_PROGRESS"}, fail_conditional=True)
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_race",
            description="race",
            run=lambda context: MigrationResult(),
        )

        with self.assertRaises(MigrationAlreadyRunningError):
            repo.begin(migration)

    def test_mark_succeeded_clears_lock_and_stale_error(self) -> None:
        table = FakeStateTable(
            {
                "id": "0001_done",
                "status": "FAILED",
                "attempts": 1,
                "error": "previous error",
            }
        )
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_done",
            description="done",
            run=lambda context: MigrationResult(),
        )

        self.assertTrue(repo.begin(migration))
        repo.mark_succeeded(migration, MigrationResult(created=1))

        self.assertEqual(table.item["status"], "SUCCESS")
        self.assertEqual(table.item["result"]["created"], 1)
        self.assertNotIn("lock_expires_at", table.item)
        self.assertNotIn("error", table.item)

    def test_mark_succeeded_rejects_lost_active_lock(self) -> None:
        table = FakeStateTable({"id": "0001_lost", "status": "FAILED", "attempts": 1})
        repo = DynamoMigrationStateRepository(table)
        migration = Migration(
            id="0001_lost",
            description="lost",
            run=lambda context: MigrationResult(),
        )

        self.assertTrue(repo.begin(migration))
        table.item["attempts"] = 3
        table.fail_conditional = True

        with self.assertRaises(MigrationAlreadyRunningError):
            repo.mark_succeeded(migration, MigrationResult(created=1))


class MigrationsHandlerTests(unittest.TestCase):
    def _load(self):
        configure_unit_environment()
        os.environ["MIGRATIONS_TABLE"] = "unit-migrations"
        os.environ["PLANS_TABLE"] = "unit-plans"
        sys.modules.pop("lambdas.workers.migrations.handler", None)
        return importlib.import_module("lambdas.workers.migrations.handler")

    def test_handler_returns_execution_summary(self) -> None:
        module = self._load()
        repo = FakeMigrationStateRepository()
        migration = Migration(
            id="0001_handler",
            description="handler",
            run=lambda context: MigrationResult(created=1),
        )

        with (
            patch.object(module, "_repo", return_value=repo),
            patch("lambdas.workers.migrations.use_case.MIGRATIONS", (migration,)),
        ):
            result = module.handler({}, LambdaContext())

        self.assertTrue(result["success"])
        self.assertEqual(result["executions"][0]["id"], "0001_handler")
        self.assertEqual(result["executions"][0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
