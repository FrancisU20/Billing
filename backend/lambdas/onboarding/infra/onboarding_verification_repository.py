from __future__ import annotations

from datetime import datetime

from botocore.exceptions import ClientError

from lambdas._base.idempotency import IdempotencyContext, completion_transact_item, mark_completed
from lambdas.onboarding.domain.errors import OnboardingVerificationNotFoundError
from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
from lambdas.onboarding.domain.repositories.i_onboarding_verification_repository import (
    IOnboardingVerificationRepository,
)
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.outbox import outbox_put_transact_item
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoOnboardingVerificationRepository(IOnboardingVerificationRepository):
    def __init__(self, table, outbox_table=None) -> None:
        self._table = table
        self._outbox_table = outbox_table

    def get_by_id(self, verification_id: str) -> OnboardingVerification:
        try:
            resp = self._table.get_item(Key={"id": verification_id}, ConsistentRead=True)
        except ClientError as exc:
            _log.error("DynamoDB get onboarding verification error", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item or item.get("entity_type") != "ONBOARDING_VERIFICATION":
            raise OnboardingVerificationNotFoundError()
        return self._from_item(item)

    def commit_request(
        self,
        *,
        verification: OnboardingVerification,
        events: list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        transact_items: list[dict] = [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": self._to_item(verification),
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            }
        ]

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        if self._outbox_table:
            for event in events:
                transact_items.append(
                    outbox_put_transact_item(
                        self._outbox_table.table_name,
                        event,
                        source="onboarding",
                    )
                )

        self._transact_write(transact_items, idempotency)

    def save_attempts(self, verification: OnboardingVerification) -> None:
        try:
            self._table.update_item(
                Key={"id": verification.id},
                UpdateExpression="SET attempts = :attempts, updated_at = :updated_at",
                ConditionExpression="attribute_exists(#id) AND entity_type = :entity_type",
                ExpressionAttributeNames={"#id": "id"},
                ExpressionAttributeValues={
                    ":attempts": verification.attempts,
                    ":updated_at": verification.updated_at.isoformat(),
                    ":entity_type": "ONBOARDING_VERIFICATION",
                },
            )
        except ClientError as exc:
            _log.error("DynamoDB save onboarding attempts error", error=str(exc))
            raise DatabaseError() from exc

    def mark_used(self, verification: OnboardingVerification) -> None:
        verification.mark_used()
        try:
            self._table.update_item(
                Key={"id": verification.id},
                UpdateExpression="SET used_at = :used_at, updated_at = :updated_at",
                ConditionExpression="attribute_exists(#id) AND entity_type = :entity_type",
                ExpressionAttributeNames={"#id": "id"},
                ExpressionAttributeValues={
                    ":used_at": verification.used_at.isoformat(),
                    ":updated_at": verification.updated_at.isoformat(),
                    ":entity_type": "ONBOARDING_VERIFICATION",
                },
            )
        except ClientError as exc:
            _log.warning("DynamoDB mark onboarding verification used failed", error=str(exc))

    def mark_used_transact_item(self, verification: OnboardingVerification) -> dict:
        verification.mark_used()
        return {
            "Update": {
                "TableName": self._table.table_name,
                "Key": {"id": verification.id},
                "UpdateExpression": "SET used_at = :used_at, updated_at = :updated_at",
                "ConditionExpression": (
                    "attribute_exists(#id) AND entity_type = :entity_type "
                    "AND (attribute_not_exists(used_at) OR used_at = :unused)"
                ),
                "ExpressionAttributeNames": {"#id": "id"},
                "ExpressionAttributeValues": {
                    ":used_at": verification.used_at.isoformat(),
                    ":updated_at": verification.updated_at.isoformat(),
                    ":entity_type": "ONBOARDING_VERIFICATION",
                    ":unused": None,
                },
            }
        }

    def _transact_write(
        self,
        transact_items: list[dict],
        idempotency: IdempotencyContext | None,
    ) -> None:
        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as exc:
            _log.error("DynamoDB onboarding verification transaction error", error=str(exc))
            raise DatabaseError() from exc

    def _to_item(self, verification: OnboardingVerification) -> dict:
        return {
            "id": verification.id,
            "entity_type": "ONBOARDING_VERIFICATION",
            "ruc": verification.ruc,
            "email": verification.email,
            "plan_id": verification.plan_id,
            "payload_hash": verification.payload_hash,
            "otp_hash": verification.otp_hash,
            "otp_salt": verification.otp_salt,
            "self_service": verification.self_service,
            "attempts": verification.attempts,
            "max_attempts": verification.max_attempts,
            "expires_at": verification.expires_at.isoformat(),
            "used_at": verification.used_at.isoformat() if verification.used_at else None,
            "created_at": verification.created_at.isoformat(),
            "updated_at": verification.updated_at.isoformat(),
            "ttl": verification.ttl,
        }

    def _from_item(self, item: dict) -> OnboardingVerification:
        return OnboardingVerification(
            id=item["id"],
            ruc=item["ruc"],
            email=item["email"],
            plan_id=item["plan_id"],
            payload_hash=item["payload_hash"],
            otp_hash=item["otp_hash"],
            otp_salt=item["otp_salt"],
            self_service=item.get("self_service", True),
            attempts=item.get("attempts", 0),
            max_attempts=item.get("max_attempts", 5),
            expires_at=datetime.fromisoformat(item["expires_at"]),
            used_at=datetime.fromisoformat(item["used_at"]) if item.get("used_at") else None,
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )
