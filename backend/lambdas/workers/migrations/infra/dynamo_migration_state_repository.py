from __future__ import annotations

"""DynamoDB migration state repository."""

from datetime import UTC, datetime, timedelta

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from migrations.context import MigrationResult
from migrations.definition import Migration

from lambdas.workers.migrations.ports import MigrationAlreadyRunningError, MigrationStateRepository
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)
_LOCK_TTL = timedelta(minutes=15)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_time(value: datetime) -> str:
    return value.isoformat()


def _is_active_lock(item: dict, now: datetime) -> bool:
    lock_expires_at = item.get("lock_expires_at")
    if not lock_expires_at:
        return True
    try:
        return datetime.fromisoformat(lock_expires_at) > now
    except ValueError:
        return True


class DynamoMigrationStateRepository(MigrationStateRepository):
    def __init__(self, table) -> None:
        self._table = table
        self._active_attempts: dict[str, int] = {}

    def begin(self, migration: Migration) -> bool:
        now = _utc_now()
        now_iso = _format_time(now)
        existing = self._get(migration.id)
        if existing and existing.get("status") == "SUCCESS":
            return False
        if existing and existing.get("status") == "IN_PROGRESS" and _is_active_lock(existing, now):
            raise MigrationAlreadyRunningError()

        item = {
            "id": migration.id,
            "description": migration.description,
            "status": "IN_PROGRESS",
            "started_at": now_iso,
            "lock_expires_at": _format_time(now + _LOCK_TTL),
            "attempts": int(existing.get("attempts", 0)) + 1 if existing else 1,
        }
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression=(
                    Attr("id").not_exists()
                    | Attr("status").eq("FAILED")
                    | (Attr("status").eq("IN_PROGRESS") & Attr("lock_expires_at").lt(now_iso))
                ),
            )
            self._active_attempts[migration.id] = item["attempts"]
            return True
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                current = self._get(migration.id)
                if current and current.get("status") == "SUCCESS":
                    return False
                if current and current.get("status") == "IN_PROGRESS":
                    raise MigrationAlreadyRunningError() from exc
                return False
            _log.error("DynamoDB migration begin error", error=str(exc), migration=migration.id)
            raise DatabaseError() from exc

    def mark_succeeded(self, migration: Migration, result: MigrationResult) -> None:
        self._mark_done(migration, status="SUCCESS", result=result.to_dict())

    def mark_failed(self, migration: Migration, error: str) -> None:
        self._mark_done(migration, status="FAILED", error=error[:1000])

    def _get(self, migration_id: str) -> dict | None:
        try:
            return self._table.get_item(Key={"id": migration_id}).get("Item")
        except ClientError as exc:
            _log.error("DynamoDB migration get error", error=str(exc), migration=migration_id)
            raise DatabaseError() from exc

    def _mark_done(
        self,
        migration: Migration,
        *,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        item = self._get(migration.id) or {
            "id": migration.id,
            "description": migration.description,
            "attempts": 1,
        }
        expected_attempt = self._active_attempts.get(migration.id, int(item.get("attempts", 1)))
        item.update(
            {
                "status": status,
                "completed_at": _format_time(_utc_now()),
                "description": migration.description,
            }
        )
        item.pop("lock_expires_at", None)
        if result is not None:
            item["result"] = result
            item.pop("error", None)
        if error is not None:
            item["error"] = error
            item.pop("result", None)

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression=(
                    Attr("status").eq("IN_PROGRESS") & Attr("attempts").eq(expected_attempt)
                ),
            )
            self._active_attempts.pop(migration.id, None)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                _log.warning(
                    "migration completion lost active lock",
                    migration=migration.id,
                    expected_attempt=expected_attempt,
                )
                raise MigrationAlreadyRunningError() from exc
            _log.error("DynamoDB migration mark_done error", error=str(exc), migration=migration.id)
            raise DatabaseError() from exc
