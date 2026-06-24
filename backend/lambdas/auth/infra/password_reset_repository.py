from __future__ import annotations

from datetime import datetime

from botocore.exceptions import ClientError

from lambdas.auth.domain.password_reset import PasswordReset
from lambdas.auth.domain.repositories.i_password_reset_repository import IPasswordResetRepository
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)
_ENTITY_TYPE = "PASSWORD_RESET"


class DynamoPasswordResetRepository(IPasswordResetRepository):
    def __init__(self, table) -> None:
        self._table = table

    def save(self, reset: PasswordReset) -> None:
        try:
            self._table.put_item(Item=self._to_item(reset))
        except ClientError as exc:
            _log.error("DynamoDB save password reset error", error=str(exc))
            raise DatabaseError() from exc

    def get_by_username(self, username: str) -> PasswordReset | None:
        try:
            resp = self._table.get_item(
                Key={"id": PasswordReset.id_for(username)},
                ConsistentRead=True,
            )
        except ClientError as exc:
            _log.error("DynamoDB get password reset error", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item or item.get("entity_type") != _ENTITY_TYPE:
            return None
        return self._from_item(item)

    def save_attempts(self, reset: PasswordReset) -> None:
        try:
            self._table.update_item(
                Key={"id": reset.id},
                UpdateExpression="SET attempts = :attempts, updated_at = :updated_at",
                ConditionExpression="attribute_exists(#id) AND entity_type = :entity_type",
                ExpressionAttributeNames={"#id": "id"},
                ExpressionAttributeValues={
                    ":attempts": reset.attempts,
                    ":updated_at": reset.updated_at.isoformat(),
                    ":entity_type": _ENTITY_TYPE,
                },
            )
        except ClientError as exc:
            _log.error("DynamoDB save password reset attempts error", error=str(exc))
            raise DatabaseError() from exc

    def mark_used(self, reset: PasswordReset) -> None:
        reset.mark_used()
        try:
            self._table.update_item(
                Key={"id": reset.id},
                UpdateExpression="SET used_at = :used_at, updated_at = :updated_at",
                ConditionExpression=(
                    "attribute_exists(#id) AND entity_type = :entity_type "
                    "AND attribute_not_exists(used_at)"
                ),
                ExpressionAttributeNames={"#id": "id"},
                ExpressionAttributeValues={
                    ":used_at": reset.used_at.isoformat(),
                    ":updated_at": reset.updated_at.isoformat(),
                    ":entity_type": _ENTITY_TYPE,
                },
            )
        except ClientError as exc:
            _log.error("DynamoDB mark password reset used error", error=str(exc))
            raise DatabaseError() from exc

    def _to_item(self, reset: PasswordReset) -> dict:
        item = {
            "id": reset.id,
            "entity_type": _ENTITY_TYPE,
            "username": reset.username,
            "code_hash": reset.code_hash,
            "code_salt": reset.code_salt,
            "attempts": reset.attempts,
            "max_attempts": reset.max_attempts,
            "expires_at": reset.expires_at.isoformat(),
            "created_at": reset.created_at.isoformat(),
            "updated_at": reset.updated_at.isoformat(),
            "ttl": reset.ttl,
        }
        if reset.used_at:
            item["used_at"] = reset.used_at.isoformat()
        return item

    def _from_item(self, item: dict) -> PasswordReset:
        return PasswordReset(
            username=item["username"],
            code_hash=item["code_hash"],
            code_salt=item["code_salt"],
            attempts=item.get("attempts", 0),
            max_attempts=item.get("max_attempts", 5),
            expires_at=datetime.fromisoformat(item["expires_at"]),
            used_at=datetime.fromisoformat(item["used_at"]) if item.get("used_at") else None,
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )
